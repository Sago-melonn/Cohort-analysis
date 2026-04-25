"""
Vista: NRR / NOR — Retención Base

Metodología:
  - Universo "base":  cohort_month ≤ corte_base (fijo)
  - Universo "todos": cohort_month < M-12 (dinámico por mes M)
  - Suavizado 3 períodos a nivel de cohorte antes del ratio
  - NOR(M) = smooth_orders(M) / smooth_orders(M-12)
  - NRR(M) = smooth_revenue(M) / smooth_revenue(M-12)
  - Forecast (solo NOR): extiende la serie con forecasted_orders

Gráfico 1 — % Ratio:
  - Muestra NOR o NRR mensual como porcentaje YoY.
  - Hover incluye numerador, denominador y corte de cohortes del mes.

Gráfico 2 — Evolución absoluta (universo fijo):
  - Universo "base"  → siempre cohortes ≤ corte_base  (mismo grupo todo el tiempo)
  - Universo "todos" → reutiliza smooth_num de la serie de retención  (M-13 dinámico)
  - Muestra la tendencia real de la base como insumo del plan de negocio.

Cards:
  - Todas las métricas usan los últimos 3 meses CERRADOS.
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
                [html.H2("Net Revenue Retention / Net Order Retention", className="page-title")],
                className="page-header",
            ),
            nor_filters(),
            html.Div(id="nor-kpis",          className="kpi-strip"),
            html.Div(id="nor-chart-container", className="page-section card"),
            html.Div(id="nor-table",           className="page-section"),
            html.Div(id="nor-abs-chart",       className="page-section card"),
            html.Div(id="nor-churn-section",   className="page-section"),
            html.Div(id="nor-pills-dummy", style={"display": "none"}),
        ],
        className="page",
    )


# ── Clientside callback: sincroniza .fb-pill--on con el value de Dash ─────────
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


# ── Lógica de cards ───────────────────────────────────────────────────────────

def _last_closed_month() -> pd.Timestamp:
    today = pd.Timestamp.today()
    return (today.replace(day=1) - pd.DateOffset(months=1)).normalize()


def _avg_3m(df: pd.DataFrame) -> float | None:
    tail = df.tail(3)["ratio"]
    return float(tail.mean()) if not tail.empty else None


def _last_val(df: pd.DataFrame) -> float | None:
    return float(df["ratio"].iloc[-1]) if not df.empty else None


def _tendencia_3m(df: pd.DataFrame) -> float | None:
    vals = df["ratio"].tolist()
    if len(vals) >= 6:
        return (sum(vals[-3:]) / 3 - sum(vals[-6:-3]) / 3) * 100
    return None


# ── Evolución absoluta universo fijo ──────────────────────────────────────────

def _abs_fixed_universe(
    df_source: pd.DataFrame,
    value_col: str,
    month_col: str,
    fixed_cutoff: pd.Timestamp,
    df_fc: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Serie absoluta con universo fijo (cohorts ≤ fixed_cutoff).

    Suavizado rolling 3 por cohorte (mismo que calc_retention_series),
    luego suma por mes. Para forecast: suma directa de forecasted_orders
    para cohorts ≤ fixed_cutoff en meses futuros.

    Retorna DataFrame: month_col | smooth_total | is_forecast
    """
    _empty = pd.DataFrame(columns=[month_col, "smooth_total", "is_forecast"])
    if df_source.empty:
        return _empty

    df_f = df_source[df_source["cohort_month"] <= fixed_cutoff].copy()
    if df_f.empty:
        return _empty

    agg = (
        df_f.groupby(["cohort_month", month_col])[value_col]
        .sum()
        .reset_index()
        .sort_values(["cohort_month", month_col])
    )
    agg["smooth"] = (
        agg.groupby("cohort_month")[value_col]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )
    last_actual = agg[month_col].max()

    actuals = (
        agg.groupby(month_col)["smooth"]
        .sum()
        .reset_index()
        .rename(columns={"smooth": "smooth_total"})
    )
    actuals["is_forecast"] = False

    result = actuals.copy()

    if df_fc is not None and not df_fc.empty:
        fc_f = df_fc[df_fc["cohort_month"] <= fixed_cutoff].copy()
        if not fc_f.empty:
            fc_future = fc_f[fc_f["forecast_month"] > last_actual]
            if not fc_future.empty:
                fc_m = (
                    fc_future.groupby("forecast_month")["forecasted_orders"]
                    .sum()
                    .reset_index()
                    .rename(columns={
                        "forecast_month": month_col,
                        "forecasted_orders": "smooth_total",
                    })
                )
                fc_m["is_forecast"] = True
                result = pd.concat([result, fc_m], ignore_index=True)

    return result.sort_values(month_col).reset_index(drop=True)


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

    monthly = (
        df_churn
        .groupby([date_col, "seller_id", "seller_name"], as_index=False)[val_col]
        .sum()
    )
    monthly[date_col] = pd.to_datetime(monthly[date_col])
    monthly = monthly.rename(columns={date_col: "period", val_col: "value"})

    month_totals = (
        monthly.groupby("period", as_index=False)["value"]
        .sum()
        .sort_values("period")
    )

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
        hovertemplate=(
            f"<b>%{{x|%b %Y}}</b><br>{hover_lbl}: %{{y:,.1f}}<extra></extra>"
            if is_rev else
            f"<b>%{{x|%b %Y}}</b><br>{hover_lbl}: %{{y:,}}<extra></extra>"
        ),
    ))
    x_pad = pd.DateOffset(weeks=3)
    fig.update_layout(
        title=dict(text=f"{val_lbl} — Sellers en Churn", font=dict(size=14, color="#1A1659")),
        xaxis=dict(
            tickformat="%b %Y", dtick="M1", tickangle=-45, gridcolor="#f5f5f5",
            range=[jan_2025 - x_pad, last_closed + x_pad],
        ),
        yaxis=dict(gridcolor="#f5f5f5", title=val_lbl),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=60, r=30, t=60, b=80), height=360, showlegend=False,
    )
    chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

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
                    html.Div(m_lbl,     className="nt-cell nt-label nt-month-lbl"),
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
            n_otros   = n_sellers - len(top10)
            otros_val = m_total - top10["value"].sum()
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
    Output("nor-abs-chart",       "children"),
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
    Input("url",           "pathname"),
    State("cohort-overrides", "data"),
    prevent_initial_call=False,
)
def update_nor(metric, pais, moneda, fx_cop, fx_mxn,
               segmentos, churn, universo, corte_base, use_forecast, pathname,
               cohort_overrides):
    if pathname != "/nor":
        raise PreventUpdate

    metric       = metric       or "nor"
    universo     = universo     or "base"
    use_forecast = use_forecast or "no"

    corte_base = (
        pd.Timestamp(corte_base).replace(day=1).strftime("%Y-%m-%d")
        if corte_base
        else pd.Timestamp.today().replace(month=12, day=1)
            .replace(year=max(pd.Timestamp.today().year - 2, 2024))
            .strftime("%Y-%m-%d")
    )

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

    nor_actual = (
        nor_df[~nor_df["is_forecast"]].dropna(subset=["ratio"])
        if not nor_df.empty else pd.DataFrame()
    )
    nrr_actual = (
        nrr_df[~nrr_df["is_forecast"]].dropna(subset=["ratio"])
        if not nrr_df.empty else pd.DataFrame()
    )
    nor_closed = (
        nor_actual[nor_actual["month"] <= last_closed]
        if not nor_actual.empty else nor_actual
    )
    nrr_closed = (
        nrr_actual[nrr_actual["month"] <= last_closed]
        if not nrr_actual.empty else nrr_actual
    )

    # ── KPIs ──────────────────────────────────────────────────────────────────
    nor_3m    = _avg_3m(nor_closed)
    nrr_3m    = _avg_3m(nrr_closed)
    nor_last  = _last_val(nor_closed)
    nrr_last  = _last_val(nrr_closed)
    nor_trend = _tendencia_3m(nor_closed)
    nrr_trend = _tendencia_3m(nrr_closed)

    last_closed_lbl = last_closed.strftime("%b %Y")
    unit            = revenue_display_unit(pais, moneda)
    pais_label      = _PAIS_LABEL.get(pais or "CONSOLIDADO", pais or "Consolidado")

    def _trend_card(label, trend_val):
        if trend_val is None:
            return _kpi_card(label, "—", "vs trimestre anterior", "muted")
        txt = f"{trend_val:+.0f} pp vs trim. anterior"
        return _kpi_card(label, txt, "vs trimestre anterior", "verde" if trend_val >= 0 else "primary")

    if metric == "nor":
        kpis = [
            _kpi_card("NOR 3M",         _fmt_pct(nor_3m),  "Últimos 3 meses cerrados",   _ratio_variant(nor_3m)),
            _kpi_card("NOR último mes",  _fmt_pct(nor_last), last_closed_lbl,             _ratio_variant(nor_last)),
            _trend_card("Tendencia NOR", nor_trend),
            _kpi_card("NRR 3M (ref.)",   _fmt_pct(nrr_3m),  "Revenue — 3 meses cerrados", _ratio_variant(nrr_3m)),
        ]
    else:
        kpis = [
            _kpi_card("NRR 3M",         _fmt_pct(nrr_3m),  "Últimos 3 meses cerrados",   _ratio_variant(nrr_3m)),
            _kpi_card("NRR último mes",  _fmt_pct(nrr_last), last_closed_lbl,             _ratio_variant(nrr_last)),
            _trend_card("Tendencia NRR", nrr_trend),
            _kpi_card("NOR 3M (ref.)",   _fmt_pct(nor_3m),  "Órdenes — 3 meses cerrados", _ratio_variant(nor_3m)),
        ]

    # ── Gráfico 1 — % Ratio ───────────────────────────────────────────────────
    fig1 = go.Figure()
    universo_lbl = "Base" if universo == "base" else "Todos (≥ 12 meses)"
    x_start = pd.Timestamp("2025-01-01")
    x_end   = (
        pd.Timestamp("2026-12-31")
        if metric == "nor" and use_forecast == "si"
        else last_closed
    )
    x_pad = pd.DateOffset(weeks=3)

    def _add_ratio_trace(fig, df_act, df_fc_series, color, fc_color, name, is_orders):
        if df_act.empty:
            return
        # Agregar cohorts_cutoff como string para el hover
        df_p = df_act.copy()
        df_p["cutoff_str"] = pd.to_datetime(df_p["cohorts_cutoff"]).dt.strftime("%b %Y")

        hover_num_lbl = "Órdenes (T)" if is_orders else f"Revenue (T) ({unit})"
        hover_den_lbl = "Órdenes (T-12)" if is_orders else f"Revenue (T-12) ({unit})"
        num_fmt = ":,.0f" if is_orders else ":,.1f"

        fig.add_trace(go.Scatter(
            x=df_p["month"], y=df_p["ratio"],
            name=name, mode="lines",
            showlegend=False, hoverinfo="skip",
            line=dict(color=color, width=2),
        ))
        fig.add_trace(go.Scatter(
            x=df_p["month"], y=df_p["ratio"],
            name=name, mode="markers+text",
            hoveron="points",
            text=[f"{v:.0%}" for v in df_p["ratio"]],
            textposition="top center",
            textfont=dict(size=10, color=color, family="Arial Black, sans-serif"),
            cliponaxis=False,
            customdata=df_p[["smooth_num", "smooth_den", "ratio", "cutoff_str"]].values,
            marker=dict(size=5, color=color),
            hovertemplate=(
                f"<b>%{{x|%b %Y}}</b><br>"
                f"{hover_num_lbl}: %{{customdata[0]{num_fmt}}}<br>"
                f"{hover_den_lbl}: %{{customdata[1]{num_fmt}}}<br>"
                f"<b>{name}: %{{customdata[2]:.0%}}</b><br>"
                f"Cohortes hasta: %{{customdata[3]}}"
                f"<extra></extra>"
            ),
        ))

        if df_fc_series is not None and not df_fc_series.empty:
            df_fc_p = df_fc_series.copy()
            df_fc_p["cutoff_str"] = pd.to_datetime(df_fc_p["cohorts_cutoff"]).dt.strftime("%b %Y")
            # Puente invisible
            if not df_p.empty:
                _bridge = pd.concat([df_p.iloc[[-1]], df_fc_p.iloc[[0]]])
                fig.add_trace(go.Scatter(
                    x=_bridge["month"], y=_bridge["ratio"],
                    mode="lines",
                    line=dict(color=fc_color, width=2, dash="dot"),
                    showlegend=False, hoverinfo="skip",
                ))
            fig.add_trace(go.Scatter(
                x=df_fc_p["month"], y=df_fc_p["ratio"],
                name=f"{name} (forecast)", mode="lines",
                showlegend=False, hoverinfo="skip",
                line=dict(color=fc_color, width=2, dash="dot"),
            ))
            fig.add_trace(go.Scatter(
                x=df_fc_p["month"], y=df_fc_p["ratio"],
                name=f"{name} (forecast)", mode="markers+text",
                hoveron="points",
                text=[f"{v:.0%}" for v in df_fc_p["ratio"]],
                textposition="top center",
                textfont=dict(size=10, color=fc_color, family="Arial Black, sans-serif"),
                cliponaxis=False,
                customdata=df_fc_p[["smooth_num", "smooth_den", "ratio", "cutoff_str"]].values,
                marker=dict(size=5, color=fc_color),
                hovertemplate=(
                    f"<b>%{{x|%b %Y}}</b><br>"
                    f"{hover_num_lbl}: %{{customdata[0]{num_fmt}}}<br>"
                    f"{hover_den_lbl}: %{{customdata[1]{num_fmt}}}<br>"
                    f"<b>{name} forecast: %{{customdata[2]:.0%}}</b><br>"
                    f"Cohortes hasta: %{{customdata[3]}}"
                    f"<extra></extra>"
                ),
            ))

    if metric == "nor":
        nor_act = (
            nor_df[~nor_df["is_forecast"] & (nor_df["month"] <= last_closed)]
            .dropna(subset=["ratio"])
            if not nor_df.empty else pd.DataFrame()
        )
        nor_fc = (
            nor_df[nor_df["is_forecast"]].dropna(subset=["ratio"])
            if use_forecast == "si" and not nor_df.empty else None
        )
        _add_ratio_trace(fig1, nor_act, nor_fc, "#4827BE", "#F97316", "NOR", is_orders=True)
    else:
        nrr_act = (
            nrr_df[~nrr_df["is_forecast"] & (nrr_df["month"] <= last_closed)]
            .dropna(subset=["ratio"])
            if not nrr_df.empty else pd.DataFrame()
        )
        _add_ratio_trace(fig1, nrr_act, None, "#22C55E", "#F97316", "NRR", is_orders=False)

    _active_df = nor_df if metric == "nor" else nrr_df
    if not _active_df.empty:
        _visible = _active_df[
            (_active_df["month"] >= x_start) & (_active_df["month"] <= x_end)
        ].dropna(subset=["ratio"])
        _data_max = float(_visible["ratio"].max()) if not _visible.empty else 1.1
    else:
        _data_max = 1.1
    # Mínimo de 110% para que el eje tenga espacio, techo ajustado al dato real
    y_max = max(1.1, _data_max * 1.15)

    fig1.add_hline(
        y=1.0, line_dash="dash", line_color="#aaa", opacity=0.6,
        annotation_text="100%", annotation_position="right",
    )
    fig1.update_layout(
        title=dict(
            text=f"{metric.upper()} — {pais_label} ({universo_lbl})",
            font=dict(size=14, color="#1A1659"),
        ),
        xaxis=dict(
            title="Mes", tickformat="%b %Y", dtick="M1", tickangle=-45,
            gridcolor="#f5f5f5", range=[x_start - x_pad, x_end + x_pad],
        ),
        yaxis=dict(
            title="Ratio de retención", tickformat=".0%",
            gridcolor="#f5f5f5", range=[0.5, y_max],
        ),
        hovermode="closest", hoverdistance=2,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=60, r=40, t=90, b=80), height=440,
    )
    chart1 = dcc.Graph(figure=fig1, config={"displayModeBar": False})

    # ── Gráfico 2 — Evolución absoluta universo fijo ──────────────────────────
    # Para "base": universo fijo en corte_base (mismas cohortes siempre).
    # Para "todos": reutiliza smooth_num de la serie de retención (M-13 dinámico).
    is_orders = (metric == "nor")
    val_lbl2  = "Órdenes" if is_orders else f"Revenue ({unit})"
    fixed_cutoff = pd.Timestamp(corte_base)

    if universo == "base":
        df_src2 = df_orders_cut if is_orders else df_rev_p_cut
        val_col2 = "order_count" if is_orders else "display_value"
        month_col2 = "order_month" if is_orders else "revenue_month"
        fc_for_abs = df_fc if is_orders else None
        abs_series = _abs_fixed_universe(df_src2, val_col2, month_col2, fixed_cutoff, fc_for_abs)
        corte_lbl  = fixed_cutoff.strftime("%b %Y")
        abs_title  = f"Evolución {val_lbl2} — base fija cohortes ≤ {corte_lbl} — {pais_label}"
    else:
        # "todos": reutiliza smooth_num de la serie ya calculada
        series_src = nor_df if is_orders else nrr_df
        if not series_src.empty:
            abs_series = (
                series_src[["month", "smooth_num", "is_forecast"]]
                .rename(columns={"month": month_col2 if universo == "base" else "month",
                                  "smooth_num": "smooth_total"})
                .copy()
            )
            # Fix: unify column name
            abs_series = series_src[["month", "smooth_num", "is_forecast"]].copy()
            abs_series = abs_series.rename(columns={"smooth_num": "smooth_total"})
        else:
            abs_series = pd.DataFrame(columns=["month", "smooth_total", "is_forecast"])
        abs_title = f"Evolución {val_lbl2} — cohortes con ≥ 13 meses — {pais_label}"

    fig2 = go.Figure()
    _empty_abs = html.Div(
        [html.P("Sin datos para el gráfico de evolución absoluta.", className="placeholder-hint")],
        className="placeholder-box",
    )

    if abs_series.empty or abs_series["smooth_total"].isna().all():
        abs_chart = _empty_abs
    else:
        # Columna de mes (puede ser month_col2 o "month" según universo)
        _mc = "month" if "month" in abs_series.columns else month_col2

        abs_act = abs_series[~abs_series["is_forecast"]].copy()
        abs_fc  = abs_series[abs_series["is_forecast"]].copy()

        def _lbl_k(v: float) -> str:
            """Formato compacto para etiquetas: órdenes → '105K', revenue → valor con unidad."""
            if is_orders:
                return f"{v / 1_000:.0f}K"
            # Revenue ya en unidades compactas (MM COP / K MXN / K USD)
            return f"{v:,.0f}" if abs(v) >= 10 else f"{v:.1f}"

        # Trace actuals
        if not abs_act.empty:
            fig2.add_trace(go.Scatter(
                x=abs_act[_mc], y=abs_act["smooth_total"],
                name=val_lbl2, mode="lines+markers+text",
                line=dict(color="#4827BE", width=2),
                marker=dict(size=4, color="#4827BE"),
                text=[_lbl_k(v) for v in abs_act["smooth_total"]],
                textposition="top center",
                textfont=dict(size=9, color="#4827BE", family="Arial Black, sans-serif"),
                cliponaxis=False,
                hovertemplate=(
                    f"<b>%{{x|%b %Y}}</b><br>{val_lbl2}: %{{y:,.0f}}<extra></extra>"
                    if is_orders else
                    f"<b>%{{x|%b %Y}}</b><br>{val_lbl2}: %{{y:,.1f}}<extra></extra>"
                ),
            ))

        # Trace forecast
        if not abs_fc.empty:
            if not abs_act.empty:
                _bridge = pd.concat([abs_act.iloc[[-1]], abs_fc.iloc[[0]]])
                fig2.add_trace(go.Scatter(
                    x=_bridge[_mc], y=_bridge["smooth_total"],
                    mode="lines", line=dict(color="#F97316", width=2, dash="dot"),
                    showlegend=False, hoverinfo="skip",
                ))
            fig2.add_trace(go.Scatter(
                x=abs_fc[_mc], y=abs_fc["smooth_total"],
                name=f"{val_lbl2} (forecast)", mode="lines+markers+text",
                line=dict(color="#F97316", width=2, dash="dot"),
                marker=dict(size=4, color="#F97316"),
                text=[_lbl_k(v) for v in abs_fc["smooth_total"]],
                textposition="top center",
                textfont=dict(size=9, color="#F97316", family="Arial Black, sans-serif"),
                cliponaxis=False,
                hovertemplate=(
                    f"<b>%{{x|%b %Y}}</b><br>{val_lbl2} forecast: %{{y:,.0f}}<extra></extra>"
                    if is_orders else
                    f"<b>%{{x|%b %Y}}</b><br>{val_lbl2} forecast: %{{y:,.1f}}<extra></extra>"
                ),
            ))

        # Línea de referencia: último mes cerrado
        fig2.add_vline(
            x=last_closed.timestamp() * 1000,
            line_dash="dot", line_color="#9684E1", opacity=0.5,
            annotation_text="Hoy", annotation_position="top right",
            annotation_font=dict(size=10, color="#6B6B9A"),
        )

        _all_vals = abs_series["smooth_total"].dropna()
        # 1.25 de espacio extra para que las etiquetas de texto no queden cortadas
        y2_max = float(_all_vals.max()) * 1.25 if not _all_vals.empty else 1.0

        fig2.update_layout(
            title=dict(text=abs_title, font=dict(size=14, color="#1A1659")),
            xaxis=dict(
                title="Mes", tickformat="%b %Y", dtick="M1", tickangle=-45,
                gridcolor="#f5f5f5",
                range=[x_start - x_pad, x_end + x_pad],
            ),
            yaxis=dict(
                title=val_lbl2, gridcolor="#f5f5f5",
                range=[0, y2_max],
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            hovermode="closest",
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=60, r=40, t=90, b=80), height=380,
        )
        abs_chart = dcc.Graph(figure=fig2, config={"displayModeBar": False})

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

        tbl_header = html.Div([
            html.Div("Período",    className="nt-cell nt-label nt-hdr"),
            html.Div("Tipo",       className="nt-cell nt-tipo  nt-hdr"),
            html.Div("Num. (T)",   className="nt-cell nt-num   nt-hdr"),
            html.Div("Den. (−12)", className="nt-cell nt-num   nt-hdr"),
            html.Div("Ratio",      className="nt-cell nt-num   nt-hdr"),
        ], className="nt-row")

        merged["_year"] = pd.to_datetime(merged["month"]).dt.year
        year_blocks = []

        for year, ydf in merged.groupby("_year", sort=False):
            month_groups = []
            for _, r in ydf.sort_values("month", ascending=True).iterrows():
                is_fc     = bool(r.get("is_forecast", False))
                fc_cls    = " nt-fc" if is_fc else ""
                month_lbl = pd.Timestamp(r["month"]).strftime("%b %Y")
                if metric == "nor":
                    detail_tipo  = "Órdenes"
                    detail_num   = _fmt_num(r.get("nor_num"), 0)
                    detail_den   = _fmt_num(r.get("nor_den"), 0)
                    detail_ratio = _fmt_pct(r.get("nor"))
                    detail_cls   = f"nt-row nt-detail-row{fc_cls}"
                else:
                    detail_tipo  = f"Revenue ({unit})"
                    detail_num   = _fmt_num(r.get("nrr_num"), 0)
                    detail_den   = _fmt_num(r.get("nrr_den"), 0)
                    detail_ratio = _fmt_pct(r.get("nrr"))
                    detail_cls   = f"nt-row nt-detail-row nt-rev-row{fc_cls}"

                month_groups.append(
                    html.Div([
                        html.Div(month_lbl,    className=f"nt-cell nt-label nt-month-lbl{fc_cls}"),
                        html.Div(detail_tipo,  className="nt-cell nt-tipo nt-detail-tipo"),
                        html.Div(detail_num,   className="nt-cell nt-num"),
                        html.Div(detail_den,   className="nt-cell nt-num"),
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
    churn_filters  = build_filters(pais, segmentos, "incluir", None)
    df_orders_ch   = apply_cohort_overrides(load_orders(churn_filters),  cohort_overrides, "order_month")
    df_rev_ch      = apply_cohort_overrides(load_revenue(churn_filters), cohort_overrides, "revenue_month")
    df_rev_ch_p    = prepare_revenue(df_rev_ch, pais, moneda, fx_cop, fx_mxn)
    churn_section  = _build_churn_section(
        df_orders_ch, df_rev_ch_p,
        metric, universo, corte_base, last_closed, unit,
    )

    return kpis, chart1, abs_chart, table, churn_section
