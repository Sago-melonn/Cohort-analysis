"""
Vista: NRR / NOR — Retención Base

Metodología:
  - Universo "base":  cohort_month ≤ corte_base (fijo)
  - Universo "todos": cohort_month < M-12 (dinámico por mes M)
  - Suavizado 3 períodos a nivel de cohorte antes del ratio
  - NOR(M) = smooth_orders(M) / smooth_orders(M-12)
  - NRR(M) = smooth_revenue(M) / smooth_revenue(M-12)
  - Forecast (solo NOR): extiende la serie con forecasted_orders

Cards:
  - Todas las métricas usan los últimos 3 meses CERRADOS.
  - Mes cerrado más reciente = mes anterior al mes en curso.
"""
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, clientside_callback, dcc, html
from dash.exceptions import PreventUpdate

from components.page_filters import nor_filters
from data.data_loader import load_forecast, load_orders, load_revenue
from data.transforms import (
    apply_cohort_overrides,
    build_filters,
    calc_retention_series,
    prepare_revenue,
    revenue_display_unit,
)

_PAIS_LABEL = {"CONSOLIDADO": "Consolidado", "COL": "Colombia", "MEX": "México"}


# ── Layout ────────────────────────────────────────────────────────────────────

def nor_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H2("Net Revenue Retention / Net Order Retention", className="page-title"),
                ],
                className="page-header",
            ),
            nor_filters(),
            html.Div(id="nor-kpis",            className="kpi-strip"),
            html.Div([
                # Toggle % Ratio / Absoluto — esquina superior derecha del card
                html.Div(
                    dcc.RadioItems(
                        id="nor-vista",
                        options=[
                            {"label": "% Ratio",  "value": "ratio"},
                            {"label": "Absoluto", "value": "absoluto"},
                        ],
                        value="ratio",
                        inline=True,
                        className="fb-radio",
                        labelClassName="fb-radio-label",
                        inputClassName="fb-radio-input",
                    ),
                    className="chart-vista-toggle",
                ),
                html.Div(id="nor-chart-container"),
            ], className="page-section card chart-card-wrapper"),
            html.Div(id="nor-table",         className="page-section"),
            html.Div(id="nor-churn-section", className="page-section"),
            # Div oculto usado como output dummy del clientside_callback de pills
            html.Div(id="nor-pills-dummy", style={"display": "none"}),
        ],
        className="page",
    )


# ── Clientside callback: sincroniza .fb-pill--on con el value de Dash ─────────
# Lee `value` directamente desde React (no desde input.checked del DOM),
# lo que garantiza consistencia independientemente del timing de renderizado.
clientside_callback(
    """
    function(value) {
        setTimeout(function () {
            var active = value || [];
            document.querySelectorAll(".fb-pill").forEach(function (pill) {
                var seg = pill.textContent.trim();
                pill.classList.toggle("fb-pill--on", active.indexOf(seg) !== -1);
            });
        }, 0);
        return window.dash_clientside.no_update;
    }
    """,
    Output("nor-pills-dummy", "style"),
    Input("nor-segmentos", "value"),
    prevent_initial_call=False,
)


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _kpi_card(title, value, subtitle, variant="primary"):
    return html.Div(
        [
            html.P(title,    className="kpi-title"),
            html.P(value,    className=f"kpi-value kpi-value--{variant}"),
            html.P(subtitle, className="kpi-subtitle"),
        ],
        className="kpi-card",
    )


def _fmt_pct(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return f"{val * 100:.0f}%"


def _fmt_num(val, decimals: int = 0) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return f"{val:,.{decimals}f}"


def _ratio_variant(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "muted"
    if val >= 1.0:
        return "verde"
    if val >= 0.9:
        return "primary"
    return "muted"


# ── Lógica de cards (3M sobre meses cerrados) ─────────────────────────────────

def _last_closed_month() -> pd.Timestamp:
    """Primer día del mes anterior al mes en curso."""
    today = pd.Timestamp.today()
    return (today.replace(day=1) - pd.DateOffset(months=1)).normalize()


def _avg_3m(df: pd.DataFrame) -> float | None:
    tail = df.tail(3)["ratio"]
    return float(tail.mean()) if not tail.empty else None


def _last_val(df: pd.DataFrame) -> float | None:
    return float(df["ratio"].iloc[-1]) if not df.empty else None


def _tendencia_3m(df: pd.DataFrame) -> float | None:
    """
    (avg últimos 3 meses cerrados) − (avg 3 meses anteriores), en pp.
    Requiere al menos 6 filas.
    """
    vals = df["ratio"].tolist()
    if len(vals) >= 6:
        return (sum(vals[-3:]) / 3 - sum(vals[-6:-3]) / 3) * 100
    return None


# ── Sección Churn ─────────────────────────────────────────────────────────────

def _build_churn_section(
    df_orders_all: "pd.DataFrame",
    df_rev_p: "pd.DataFrame",
    metric: str,
    universo: str,
    corte_base: str,
    last_closed: "pd.Timestamp",
    unit: str,
) -> "html.Div":
    """
    Sección de análisis de churn al pie de la vista NOR/NRR.
    - df_orders_all : load_orders  con include_churn=True (para NOR)
    - df_rev_p      : load_revenue con include_churn=True + prepare_revenue (para NRR)
    - metric        : 'nor' → órdenes | 'nrr' → revenue
    Filtros ya aplicados antes de llamar: país, segmentos.
    Siempre usa churn_flag == 1 (ignora el filtro de churn del sidebar).
    """
    # Elegir fuente según métrica
    if metric == "nor":
        src      = df_orders_all
        val_col  = "order_count"
        date_col = "order_month"
        val_lbl  = "Órdenes"
    else:
        src      = df_rev_p
        val_col  = "display_value"
        date_col = "revenue_month"
        val_lbl  = f"Revenue ({unit})"

    if src.empty:
        return html.Div()

    # Universo de cohortes (misma lógica que NOR/NRR)
    corte_ts = pd.Timestamp(corte_base)
    if universo == "base":
        universe_mask = src["cohort_month"] <= corte_ts
    else:
        cutoff_todos = (last_closed - pd.DateOffset(months=11)).normalize()
        universe_mask = src["cohort_month"] <= cutoff_todos

    df_u = src[universe_mask]

    churned_ids = df_u[df_u["churn_flag"] == 1]["seller_id"].unique()
    if len(churned_ids) == 0:
        return html.Div(
            [html.P("Sin sellers en churn para el universo seleccionado.", className="placeholder-hint")],
            className="page-section card",
        )

    jan_2025 = pd.Timestamp("2025-01-01")
    df_churn = df_u[
        df_u["seller_id"].isin(churned_ids) &
        (df_u[date_col] >= jan_2025) &
        (df_u[date_col] <= last_closed)
    ]

    if df_churn.empty:
        return html.Div(
            [html.P(f"Sin {val_lbl.lower()} de sellers en churn desde Ene 2025.", className="placeholder-hint")],
            className="page-section card",
        )

    # ── Agregar por mes × seller ──────────────────────────────────────────────
    monthly = (
        df_churn
        .groupby([date_col, "seller_id", "seller_name"], as_index=False)[val_col]
        .sum()
    )
    monthly[date_col] = pd.to_datetime(monthly[date_col])
    # alias común para simplificar el resto del código
    monthly = monthly.rename(columns={date_col: "period", val_col: "value"})

    month_totals = (
        monthly.groupby("period", as_index=False)["value"]
        .sum()
        .sort_values("period")
    )

    # ── Gráfico de barras mes a mes ───────────────────────────────────────────
    is_rev    = (metric == "nrr")
    fmt_val   = (lambda v: f"{v:,.1f}") if is_rev else (lambda v: f"{int(v):,}")
    hover_lbl = val_lbl

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=month_totals["period"],
        y=month_totals["value"],
        marker_color="#4827BE",
        text=[fmt_val(v) for v in month_totals["value"]],
        textposition="outside",
        textfont=dict(size=10, color="#4827BE", family="Arial Black, sans-serif"),
        cliponaxis=False,
        hovertemplate=f"<b>%{{x|%b %Y}}</b><br>{hover_lbl}: %{{y:,.1f}}<extra></extra>"
        if is_rev else
        f"<b>%{{x|%b %Y}}</b><br>{hover_lbl}: %{{y:,}}<extra></extra>",
    ))
    x_pad = pd.DateOffset(weeks=3)
    fig.update_layout(
        title=dict(
            text=f"{val_lbl} — Sellers en Churn",
            font=dict(size=14, color="#1A1659"),
        ),
        xaxis=dict(
            tickformat="%b %Y", dtick="M1", tickangle=-45,
            gridcolor="#f5f5f5",
            range=[jan_2025 - x_pad, last_closed + x_pad],
        ),
        yaxis=dict(gridcolor="#f5f5f5", title=val_lbl),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=60, b=80),
        height=360,
        showlegend=False,
    )
    chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

    # ── Tabla: top 5 + Otros ──────────────────────────────────────────────────
    month_totals_desc = month_totals.sort_values("period", ascending=False).copy()
    month_totals_desc["_year"] = month_totals_desc["period"].dt.year

    tbl_header = html.Div([
        html.Div("Período",  className="nt-cell nt-label nt-hdr"),
        html.Div(val_lbl,    className="nt-cell nt-num   nt-hdr"),
        html.Div("Sellers",  className="nt-cell nt-num   nt-hdr"),
    ], className="nt-row")

    year_blocks = []
    for year, ydf in month_totals_desc.groupby("_year", sort=False):
        month_groups = []
        for _, mrow in ydf.sort_values("period", ascending=True).iterrows():
            m_ts      = pd.Timestamp(mrow["period"])
            m_lbl     = m_ts.strftime("%b %Y")
            m_total   = mrow["value"]
            m_total_s = fmt_val(m_total)
            sellers_m = monthly[monthly["period"] == m_ts]
            n_sellers = sellers_m["seller_id"].nunique()
            top10     = sellers_m.nlargest(10, "value")

            month_summary = html.Summary(
                html.Div([
                    html.Div(m_lbl,    className="nt-cell nt-label nt-month-lbl"),
                    html.Div(m_total_s, className="nt-cell nt-num nt-ratio-val"),
                    html.Div(str(n_sellers), className="nt-cell nt-num"),
                ], className="nt-row nt-month-row"),
                className="nt-summary",
            )

            detail_rows = [
                html.Div([
                    html.Div(row["seller_name"],    className="nt-cell nt-label nt-seller-name"),
                    html.Div(fmt_val(row["value"]), className="nt-cell nt-num"),
                    html.Div("",                    className="nt-cell nt-num"),
                ], className="nt-row nt-detail-row")
                for _, row in top10.iterrows()
            ]

            # Fila "Otros (N)" si hay más de 10 sellers
            n_otros      = n_sellers - len(top10)
            otros_val    = m_total - top10["value"].sum()
            if n_otros > 0:
                detail_rows.append(html.Div([
                    html.Div(f"Otros ({n_otros})", className="nt-cell nt-label nt-seller-name nt-otros"),
                    html.Div(fmt_val(otros_val),   className="nt-cell nt-num nt-otros"),
                    html.Div("",                   className="nt-cell nt-num"),
                ], className="nt-row nt-detail-row nt-rev-row"))

            month_groups.append(
                html.Details([month_summary, *detail_rows], className="nt-month-group")
            )

        year_summary = html.Summary(
            html.Div([
                html.Div(str(year), className="nt-cell nt-label nt-year-lbl"),
                html.Div("",        className="nt-cell nt-num"),
                html.Div("",        className="nt-cell nt-num"),
            ], className="nt-row nt-year-row"),
            className="nt-summary",
        )
        year_blocks.append(
            html.Details(
                [year_summary, *month_groups],
                className="nt-year-group",
                open=(year == pd.Timestamp.today().year),
            )
        )

    table = html.Div(
        html.Div([tbl_header, *year_blocks], className="nt-table"),
        className="ct-wrap",
    )

    return html.Div([
        html.H3(f"Churn — {val_lbl} mensuales", className="section-title"),
        chart,
        html.H3("Detalle por mes", className="section-title", style={"marginTop": "20px"}),
        table,
    ], className="page-section card")


# ── Callback ──────────────────────────────────────────────────────────────────

@callback(
    Output("nor-kpis",            "children"),
    Output("nor-chart-container", "children"),
    Output("nor-table",           "children"),
    Output("nor-churn-section",   "children"),
    Input("nor-metric",    "value"),
    Input("nor-pais",      "value"),
    Input("nor-moneda",    "value"),
    Input("nor-fx-cop",    "value"),
    Input("nor-fx-mxn",    "value"),
    Input("nor-segmentos", "value"),
    Input("nor-churn",     "value"),
    Input("nor-universo",  "value"),
    Input("nor-corte-base","date"),
    Input("nor-forecast",  "value"),
    Input("nor-vista",     "value"),
    Input("url",           "pathname"),
    State("cohort-overrides", "data"),
    prevent_initial_call=False,
)
def update_nor(metric, pais, moneda, fx_cop, fx_mxn,
               segmentos, churn, universo, corte_base, use_forecast, vista, pathname,
               cohort_overrides):
    if pathname != "/nor":
        raise PreventUpdate

    metric       = metric       or "nor"
    universo     = universo     or "base"
    use_forecast = use_forecast or "no"
    vista        = vista        or "ratio"
    # Normalizar a día 1 del mes (DatePickerSingle puede devolver cualquier día)
    corte_base = (
        pd.Timestamp(corte_base).replace(day=1).strftime("%Y-%m-%d")
        if corte_base else pd.Timestamp.today().replace(month=12, day=1).replace(year=max(pd.Timestamp.today().year - 2, 2024)).strftime("%Y-%m-%d")
    )

    # Forecast solo aplica para NOR
    if metric == "nrr":
        use_forecast = "no"

    last_closed = _last_closed_month()

    filters   = build_filters(pais, segmentos, churn, None)
    df_orders = apply_cohort_overrides(load_orders(filters),  cohort_overrides, "order_month")
    df_rev    = apply_cohort_overrides(load_revenue(filters), cohort_overrides, "revenue_month")
    df_rev_p  = prepare_revenue(df_rev, pais, moneda, fx_cop, fx_mxn)

    df_fc = None
    if use_forecast == "si":
        df_fc = apply_cohort_overrides(load_forecast(filters), cohort_overrides, "forecast_month")

    # Cortar actuals en last_closed: evita que un mes parcial (ej. Abril en curso)
    # sea tomado como last_actual en calc_retention_series y deje Abril en el limbo
    # (excluido de actuals por > last_closed y de forecast por is_forecast=False).
    df_orders_cut = (
        df_orders[df_orders["order_month"] <= last_closed]
        if not df_orders.empty else df_orders
    )
    df_rev_p_cut = (
        df_rev_p[df_rev_p["revenue_month"] <= last_closed]
        if not df_rev_p.empty else df_rev_p
    )

    nor_df = calc_retention_series(
        df_orders_cut, "order_count", "order_month",
        universo, corte_base, df_fc,
    )
    nrr_df = calc_retention_series(
        df_rev_p_cut, "display_value", "revenue_month",
        universo, corte_base, None,
    )

    # ── Series reales (sin forecast) ──────────────────────────────────────────
    nor_actual = (
        nor_df[~nor_df["is_forecast"]].dropna(subset=["ratio"])
        if not nor_df.empty else pd.DataFrame()
    )
    nrr_actual = (
        nrr_df[~nrr_df["is_forecast"]].dropna(subset=["ratio"])
        if not nrr_df.empty else pd.DataFrame()
    )

    # ── Corte en último mes cerrado ───────────────────────────────────────────
    nor_closed = (
        nor_actual[nor_actual["month"] <= last_closed]
        if not nor_actual.empty else nor_actual
    )
    nrr_closed = (
        nrr_actual[nrr_actual["month"] <= last_closed]
        if not nrr_actual.empty else nrr_actual
    )

    # ── Valores para cards ────────────────────────────────────────────────────
    nor_3m    = _avg_3m(nor_closed)
    nrr_3m    = _avg_3m(nrr_closed)
    nor_last  = _last_val(nor_closed)
    nrr_last  = _last_val(nrr_closed)
    nor_trend = _tendencia_3m(nor_closed)
    nrr_trend = _tendencia_3m(nrr_closed)

    last_closed_lbl = last_closed.strftime("%b %Y")

    def _trend_card(label, trend_val):
        if trend_val is None:
            return _kpi_card(label, "—", "vs trimestre anterior", "muted")
        txt = f"{trend_val:+.0f} pp vs trim. anterior"
        var = "verde" if trend_val >= 0 else "primary"
        return _kpi_card(label, txt, "vs trimestre anterior", var)

    # ── KPIs según métrica seleccionada ───────────────────────────────────────
    if metric == "nor":
        kpis = [
            _kpi_card("NOR 3M",        _fmt_pct(nor_3m),   "Últimos 3 meses cerrados",    _ratio_variant(nor_3m)),
            _kpi_card("NOR último mes", _fmt_pct(nor_last),  last_closed_lbl,              _ratio_variant(nor_last)),
            _trend_card("Tendencia NOR", nor_trend),
            _kpi_card("NRR 3M (ref.)", _fmt_pct(nrr_3m),   "Revenue — 3 meses cerrados",  _ratio_variant(nrr_3m)),
        ]
    else:  # nrr
        kpis = [
            _kpi_card("NRR 3M",        _fmt_pct(nrr_3m),   "Últimos 3 meses cerrados",    _ratio_variant(nrr_3m)),
            _kpi_card("NRR último mes", _fmt_pct(nrr_last),  last_closed_lbl,              _ratio_variant(nrr_last)),
            _trend_card("Tendencia NRR", nrr_trend),
            _kpi_card("NOR 3M (ref.)", _fmt_pct(nor_3m),   "Órdenes — 3 meses cerrados",  _ratio_variant(nor_3m)),
        ]

    # ── Gráfico ───────────────────────────────────────────────────────────────
    fig = go.Figure()
    pais_label   = _PAIS_LABEL.get(pais or "CONSOLIDADO", pais or "Consolidado")
    universo_lbl = "Base" if universo == "base" else "Todos (≥ 12 meses)"
    unit         = revenue_display_unit(pais, moneda)

    # Rango eje X — padding de 3 semanas para que las etiquetas de borde no se corten
    x_start = pd.Timestamp("2025-01-01")
    x_end   = (
        pd.Timestamp("2026-12-31")
        if metric == "nor" and use_forecast == "si"
        else last_closed
    )
    x_pad = pd.DateOffset(weeks=3)

    # ── Helpers de formato según vista ───────────────────────────────────────
    is_abs = vista == "absoluto"

    def _fmt_act(v):
        """Formato etiqueta: % en ratio, entero/decimal en absoluto."""
        if metric == "nor":
            return f"{v:.0%}" if not is_abs else f"{v:,.0f}"
        return f"{v:.0%}" if not is_abs else f"{v:,.1f}"

    def _y_col():
        return "smooth_num" if is_abs else "ratio"

    # ── Traces ───────────────────────────────────────────────────────────────
    if metric == "nor":
        nor_act = (
            nor_df[~nor_df["is_forecast"] & (nor_df["month"] <= last_closed)]
            .dropna(subset=["ratio"])
            if not nor_df.empty else pd.DataFrame()
        )
        if not nor_act.empty:
            fig.add_trace(go.Scatter(
                x=nor_act["month"],
                y=nor_act[_y_col()],
                name="NOR",
                mode="lines",
                showlegend=False,
                hoverinfo="skip",
                line=dict(color="#4827BE", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=nor_act["month"],
                y=nor_act[_y_col()],
                name="NOR",
                mode="markers+text",
                hoveron="points",
                text=[_fmt_act(v) for v in nor_act[_y_col()]],
                textposition="top center",
                textfont=dict(size=10, color="#4827BE", family="Arial Black, sans-serif"),
                cliponaxis=False,
                customdata=nor_act[["smooth_num", "smooth_den", "ratio"]].values,
                marker=dict(size=5, color="#4827BE"),
                hovertemplate=(
                    "<b>%{x|%b %Y}</b><br>"
                    "Órdenes (T): %{customdata[0]:,.0f}<br>"
                    "Órdenes (T-12): %{customdata[1]:,.0f}<br>"
                    "<b>NOR: %{customdata[2]:.0%}</b>"
                    "<extra></extra>"
                ) if is_abs else (
                    "<b>%{x|%b %Y}</b><br>"
                    "Órdenes (T): %{customdata[0]:,.0f}<br>"
                    "Órdenes (T-12): %{customdata[1]:,.0f}<br>"
                    "<b>NOR: %{y:.0%}</b>"
                    "<extra></extra>"
                ),
            ))
        if use_forecast == "si":
            nor_fc = (
                nor_df[nor_df["is_forecast"]].dropna(subset=["ratio"])
                if not nor_df.empty else pd.DataFrame()
            )
            if not nor_fc.empty:
                # Traza puente: línea de conexión visual (Marzo→Abril) sin hover ni etiqueta
                if not nor_act.empty:
                    _bridge = pd.concat([nor_act.iloc[[-1]], nor_fc.iloc[[0]]])
                    fig.add_trace(go.Scatter(
                        x=_bridge["month"],
                        y=_bridge[_y_col()],
                        mode="lines",
                        line=dict(color="#F97316", width=2, dash="dot"),
                        showlegend=False,
                        hoverinfo="skip",
                    ))
                # Traza forecast: empieza en Abril — línea sin hover + puntos con hover
                fig.add_trace(go.Scatter(
                    x=nor_fc["month"],
                    y=nor_fc[_y_col()],
                    name="NOR (forecast)",
                    mode="lines",
                    showlegend=False,
                    hoverinfo="skip",
                    line=dict(color="#F97316", width=2, dash="dot"),
                ))
                fig.add_trace(go.Scatter(
                    x=nor_fc["month"],
                    y=nor_fc[_y_col()],
                    name="NOR (forecast)",
                    mode="markers+text",
                    hoveron="points",
                    text=[_fmt_act(v) for v in nor_fc[_y_col()]],
                    textposition="top center",
                    textfont=dict(size=10, color="#F97316", family="Arial Black, sans-serif"),
                    cliponaxis=False,
                    customdata=nor_fc[["smooth_num", "smooth_den", "ratio"]].values,
                    marker=dict(size=5, color="#F97316"),
                    hovertemplate=(
                        "<b>%{x|%b %Y}</b><br>"
                        "Órdenes (T): %{customdata[0]:,.0f}<br>"
                        "Órdenes (T-12): %{customdata[1]:,.0f}<br>"
                        "<b>NOR: %{customdata[2]:.0%}</b>"
                        "<extra></extra>"
                    ) if is_abs else (
                        "<b>%{x|%b %Y}</b><br>"
                        "Órdenes (T): %{customdata[0]:,.0f}<br>"
                        "Órdenes (T-12): %{customdata[1]:,.0f}<br>"
                        "<b>NOR: %{y:.0%}</b>"
                        "<extra></extra>"
                    ),
                ))
    else:  # nrr
        nrr_act = (
            nrr_df[~nrr_df["is_forecast"] & (nrr_df["month"] <= last_closed)]
            .dropna(subset=["ratio"])
            if not nrr_df.empty else pd.DataFrame()
        )
        if not nrr_act.empty:
            fig.add_trace(go.Scatter(
                x=nrr_act["month"],
                y=nrr_act[_y_col()],
                name="NRR",
                mode="lines",
                showlegend=False,
                hoverinfo="skip",
                line=dict(color="#22C55E", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=nrr_act["month"],
                y=nrr_act[_y_col()],
                name="NRR",
                mode="markers+text",
                hoveron="points",
                text=[_fmt_act(v) for v in nrr_act[_y_col()]],
                textposition="top center",
                textfont=dict(size=10, color="#22C55E", family="Arial Black, sans-serif"),
                cliponaxis=False,
                customdata=nrr_act[["smooth_num", "smooth_den", "ratio"]].values,
                marker=dict(size=5, color="#22C55E"),
                hovertemplate=(
                    "<b>%{x|%b %Y}</b><br>"
                    f"Revenue (T) ({unit}): %{{customdata[0]:,.1f}}<br>"
                    f"Revenue (T-12) ({unit}): %{{customdata[1]:,.1f}}<br>"
                    "<b>NRR: %{customdata[2]:.0%}</b>"
                    "<extra></extra>"
                ) if is_abs else (
                    "<b>%{x|%b %Y}</b><br>"
                    f"Revenue (T) ({unit}): %{{customdata[0]:,.1f}}<br>"
                    f"Revenue (T-12) ({unit}): %{{customdata[1]:,.1f}}<br>"
                    "<b>NRR: %{y:.0%}</b>"
                    "<extra></extra>"
                ),
            ))

    # ── Rango eje Y ───────────────────────────────────────────────────────────
    _active_df = nor_df if metric == "nor" else nrr_df
    _ycol      = _y_col()
    if not _active_df.empty:
        _visible = _active_df[
            (_active_df["month"] >= x_start) & (_active_df["month"] <= x_end)
        ].dropna(subset=[_ycol])
        _data_max = float(_visible[_ycol].max()) if not _visible.empty else (2.0 if not is_abs else 1.0)
    else:
        _data_max = 2.0 if not is_abs else 1.0
    y_max = _data_max * 1.15

    # En modo ratio: mínimo visible 200% y límite inferior 50%
    if not is_abs:
        y_max = max(2.0, y_max)
        y_min = 0.5
        fig.add_hline(
            y=1.0,
            line_dash="dash", line_color="#aaa", opacity=0.6,
            annotation_text="100%", annotation_position="right",
        )
    else:
        y_min = 0.0

    # ── Layout ────────────────────────────────────────────────────────────────
    if is_abs:
        y_title = "Órdenes (suavizado)" if metric == "nor" else f"Revenue ({unit}, suavizado)"
        y_fmt   = None
    else:
        y_title = "Ratio de retención"
        y_fmt   = ".0%"

    chart_title = (
        f"{metric.upper()} — {pais_label} ({universo_lbl})"
        if not is_abs
        else f"{'Órdenes' if metric == 'nor' else 'Revenue'} Base — {pais_label} ({universo_lbl})"
    )

    fig.update_layout(
        title=dict(
            text=chart_title,
            font=dict(size=14, color="#1A1659"),
        ),
        xaxis=dict(
            title="Mes",
            tickformat="%b %Y",
            dtick="M1",
            tickangle=-45,
            gridcolor="#f5f5f5",
            range=[x_start - x_pad, x_end + x_pad],
        ),
        yaxis=dict(
            title=y_title,
            tickformat=y_fmt,
            gridcolor="#f5f5f5",
            range=[y_min, y_max],
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="closest",
        hoverdistance=2,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=40, t=90, b=80),
        height=440,
    )

    chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

    # ── Tabla de trazabilidad ─────────────────────────────────────────────────
    if nor_df.empty and nrr_df.empty:
        table = html.Div(
            [html.P("Sin datos para los filtros seleccionados.", className="placeholder-hint")],
            className="placeholder-box",
        )
    else:
        merged = nor_df[
            ["month", "smooth_num", "smooth_den", "ratio", "is_forecast"]
        ].rename(columns={"smooth_num": "nor_num", "smooth_den": "nor_den", "ratio": "nor"})

        if not nrr_df.empty:
            nrr_sub = nrr_df[["month", "smooth_num", "smooth_den", "ratio"]].rename(
                columns={"smooth_num": "nrr_num", "smooth_den": "nrr_den", "ratio": "nrr"}
            )
            merged = merged.merge(nrr_sub, on="month", how="left")

        merged = merged.sort_values("month", ascending=False).head(36)
        unit   = revenue_display_unit(pais, moneda)

        # Header fijo
        tbl_header = html.Div([
            html.Div("Período",         className="nt-cell nt-label nt-hdr"),
            html.Div("Tipo",            className="nt-cell nt-tipo  nt-hdr"),
            html.Div("Num. (T)",        className="nt-cell nt-num   nt-hdr"),
            html.Div("Den. (−12)",      className="nt-cell nt-num   nt-hdr"),
            html.Div("Ratio",           className="nt-cell nt-num   nt-hdr"),
        ], className="nt-row")

        # Agrupar por año (más reciente primero)
        merged["_year"] = pd.to_datetime(merged["month"]).dt.year
        year_blocks = []

        for i, (year, ydf) in enumerate(merged.groupby("_year", sort=False)):
            month_groups = []
            for _, r in ydf.sort_values("month", ascending=True).iterrows():
                is_fc     = bool(r.get("is_forecast", False))
                fc_cls    = " nt-fc" if is_fc else ""
                month_lbl = pd.Timestamp(r["month"]).strftime("%b %Y")
                # Resumen y fila de detalle según métrica activa
                if metric == "nor":
                    summary_txt  = f"NOR {_fmt_pct(r.get('nor'))}"
                    detail_tipo  = "Órdenes"
                    detail_num   = _fmt_num(r.get("nor_num"), 0)
                    detail_den   = _fmt_num(r.get("nor_den"), 0)
                    detail_ratio = _fmt_pct(r.get("nor"))
                    detail_cls   = f"nt-row nt-detail-row{fc_cls}"
                else:
                    summary_txt  = f"NRR {_fmt_pct(r.get('nrr'))}"
                    detail_tipo  = f"Revenue ({unit})"
                    detail_num   = _fmt_num(r.get("nrr_num"), 0)
                    detail_den   = _fmt_num(r.get("nrr_den"), 0)
                    detail_ratio = _fmt_pct(r.get("nrr"))
                    detail_cls   = f"nt-row nt-detail-row nt-rev-row{fc_cls}"

                month_groups.append(
                    html.Div([
                        html.Div(month_lbl,   className=f"nt-cell nt-label nt-month-lbl{fc_cls}"),
                        html.Div(detail_tipo, className="nt-cell nt-tipo nt-detail-tipo"),
                        html.Div(detail_num,  className="nt-cell nt-num"),
                        html.Div(detail_den,  className="nt-cell nt-num"),
                        html.Div(detail_ratio, className="nt-cell nt-num nt-ratio-val"),
                    ], className=detail_cls)
                )

            year_summary = html.Summary(
                html.Div([
                    html.Div(str(year), className="nt-cell nt-label nt-year-lbl"),
                    html.Div("",        className="nt-cell nt-tipo"),
                    html.Div("",        className="nt-cell nt-num"),
                    html.Div("",        className="nt-cell nt-num"),
                    html.Div("",        className="nt-cell nt-num"),
                ], className="nt-row nt-year-row"),
                className="nt-summary",
            )

            year_blocks.append(
                html.Details(
                    [year_summary, *month_groups],
                    className="nt-year-group",
                    open=(year == pd.Timestamp.today().year),
                )
            )

        table = html.Div([
            html.H3("Trazabilidad del cálculo", className="section-title"),
            html.Div(
                html.Div([tbl_header, *year_blocks], className="nt-table"),
                className="ct-wrap",
            ),
        ], className="page-section card")

    # ── Sección Churn ─────────────────────────────────────────────────────────
    churn_filters    = build_filters(pais, segmentos, "incluir", None)  # siempre include_churn=True
    df_orders_churn  = apply_cohort_overrides(load_orders(churn_filters),  cohort_overrides, "order_month")
    df_rev_churn     = apply_cohort_overrides(load_revenue(churn_filters), cohort_overrides, "revenue_month")
    df_rev_churn_p   = prepare_revenue(df_rev_churn, pais, moneda, fx_cop, fx_mxn)
    churn_section    = _build_churn_section(
        df_orders_churn, df_rev_churn_p,
        metric, universo, corte_base, last_closed,
        unit,
    )

    return kpis, chart, table, churn_section
