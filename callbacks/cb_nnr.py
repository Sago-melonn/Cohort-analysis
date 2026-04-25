"""
Vista: NNR / NNO — Revenue y Órdenes Nuevas por Cohorte

Metodología:
  - NNR(cohorte) = Σ sellers × avg(Rev_M2/factor_M2, Rev_M3/factor_M3)
  - NNO(cohorte) = Σ sellers × avg(Orders_M2/factor_M2, Orders_M3/factor_M3)
  - Estacionalidad hardcoded: COL → Nov, Dic = 1.4 | MEX → May, Nov, Dic = 1.4
  - Status por cohorte: completo (M2+M3) | parcial (solo M2) | pendiente (sin M2 aún)
  - Budget 2026: staging.finance.financial_planning_budget_nnr (en USD brutos)
  - Tabla agrupada Año → Q → Mes (html.Details collapsible)
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from components.page_filters import nnr_filters
from data.data_loader import load_budget_nnr, load_orders, load_revenue
from data.transforms import (
    apply_cohort_overrides,
    build_filters,
    calc_nnr_by_cohort,
    calc_nno_by_cohort,
    prepare_revenue,
    revenue_display_unit,
)

# ── Constantes de tabla ───────────────────────────────────────────────────────

_W = {
    "lbl":  "130px",
    "st":    "30px",
    "sel":   "66px",
    "nnr":   "86px",
    "bud":   "80px",
    "pct":   "66px",
    "nno":   "70px",
}
_GEO_LBL = {"CONSOLIDADO": "Consolidado", "COL": "Colombia", "MEX": "México"}


# ── Layout ────────────────────────────────────────────────────────────────────

def nnr_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [html.H2("Net New Revenue / Net New Orders", className="page-title")],
                className="page-header",
            ),
            nnr_filters(),
            html.Div(id="nnr-kpis",           className="kpi-container"),
            html.Div(id="nnr-chart-container", className="page-section card"),
            html.Div(id="nnr-table",           className="page-section"),
        ],
        className="page",
    )


# ── Helpers UI ────────────────────────────────────────────────────────────────

def _kpi_card(title: str, value: str, subtitle: str, variant: str = "primary") -> html.Div:
    return html.Div(
        [
            html.P(title,    className="kpi-title"),
            html.P(value,    className=f"kpi-value kpi-value--{variant}"),
            html.P(subtitle, className="kpi-subtitle"),
        ],
        className="kpi-card",
    )


def _fmt_val(val, is_rev: bool) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:,.1f}" if is_rev else f"{int(round(val)):,}"


def _fmt_delta(val) -> tuple[str, str]:
    """(texto, color) para una variación porcentual."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—", "#6B6B9A"
    return f"{val:+.0%}", "#00C97A" if val >= 0 else "#FF820F"


def _status_icon(status: str) -> html.Span:
    if status == "completo":
        return html.Span("✓", title="Completo (M2+M3)",
                         style={"color": "#00C97A", "fontWeight": "700", "fontSize": "13px"})
    if status == "parcial":
        return html.Span("~", title="Parcial (solo M2)",
                         style={"color": "#FF820F", "fontWeight": "700", "fontSize": "13px"})
    return html.Span("–", title="Pendiente (sin M2/M3 aún)",
                     style={"color": "#AAAAAA", "fontSize": "13px"})


# ── Helpers de datos ──────────────────────────────────────────────────────────

def _budget_to_display(usd: float, unit: str, fx_cop: float, fx_mxn: float) -> float:
    """Convierte presupuesto de USD brutos a la unidad de display."""
    if unit == "MM COP":
        return usd * fx_cop / 1_000_000
    if unit == "K MXN":
        return usd * fx_mxn / 1_000
    return usd / 1_000   # K USD (default)


def _prepare_budget(
    df_budget: pd.DataFrame,
    pais: str,
    unit: str,
    fx_cop: float,
    fx_mxn: float,
) -> pd.DataFrame:
    """
    Devuelve DataFrame indexed by date con columnas:
      nnr_base, nno_base, nnr_bear, nno_bear
    NNR columns en unidad de display; NNO en órdenes (sin conversión).
    """
    cols_out = ["nnr_base", "nno_base", "nnr_bear", "nno_bear"]
    _empty = pd.DataFrame(columns=cols_out)

    if df_budget.empty:
        return _empty

    _country_map = {"COL": 1, "MEX": 2}
    pais_id = _country_map.get(pais)

    if pais_id is not None:
        df = df_budget[df_budget["country_id"] == pais_id].copy()
    else:
        # Consolidado: suma de ambos países
        df = (
            df_budget
            .groupby("date")[["budget_nnr_base", "budget_nno_base",
                               "budget_nnr_bear", "budget_nno_bear"]]
            .sum()
            .reset_index()
        )

    if df.empty:
        return _empty

    df = df.set_index("date")
    result = pd.DataFrame(index=pd.to_datetime(df.index))
    for scen in ("base", "bear"):
        result[f"nnr_{scen}"] = df[f"budget_nnr_{scen}"].apply(
            lambda x: _budget_to_display(float(x), unit, fx_cop, fx_mxn)
        )
        result[f"nno_{scen}"] = df[f"budget_nno_{scen}"].astype(float)

    return result


# ── Sección: KPIs ─────────────────────────────────────────────────────────────

def _build_kpi_row(
    series: pd.Series,
    is_rev: bool,
    budget: pd.DataFrame,
    unit: str,
    escenario: str,
    status: pd.Series,
) -> list:
    """Devuelve 4 KPI cards para una métrica (NNR o NNO)."""
    met_lbl = "NNR" if is_rev else "NNO"
    esc_lbl = 'Base ("Junta")' if escenario == "base" else "Bear"
    bud_col = f"{'nnr' if is_rev else 'nno'}_{escenario}"

    s2026    = series[series.index.year == 2026] if not series.empty else pd.Series(dtype=float)
    st2026   = status[status.index.year == 2026] if not status.empty else pd.Series(dtype=str)
    real_ytd = float(s2026.sum()) if not s2026.empty else 0.0
    n_par    = int((st2026 == "parcial").sum()) if not st2026.empty else 0

    if not s2026.empty:
        last_m   = pd.to_datetime(s2026.index).max().strftime("%b")
        ytd_sub  = f"Ene–{last_m} 2026"
        if n_par:
            ytd_sub += f" ({n_par} parcial)"
    else:
        ytd_sub = "Sin datos 2026"

    b2026   = budget[budget.index.year == 2026] if not budget.empty else pd.DataFrame()
    bud_ytd = None
    bud_fy  = None
    if not b2026.empty and bud_col in b2026.columns:
        ytd_idx = b2026[b2026.index.isin(s2026.index)]
        bud_ytd = float(ytd_idx[bud_col].sum()) if not ytd_idx.empty else None
        bud_fy  = float(b2026[bud_col].sum())

    pct_ytd = real_ytd / bud_ytd - 1 if bud_ytd else None
    pct_fy  = real_ytd / bud_fy      if bud_fy  else None
    var_ytd, _ = _fmt_delta(pct_ytd)
    var_fy      = f"{pct_fy:.0%}" if pct_fy is not None else "—"
    unit_lbl    = f" ({unit})" if is_rev else ""

    return [
        _kpi_card(f"{met_lbl} Real YTD{unit_lbl}", _fmt_val(real_ytd, is_rev), ytd_sub,          "primary"),
        _kpi_card(f"Budget {esc_lbl} YTD",          _fmt_val(bud_ytd,  is_rev), "Mismo período",  "muted"),
        _kpi_card("Ejecución YTD",                   var_ytd,                    f"vs Budget {esc_lbl}",
                  "verde" if (pct_ytd or 0) >= 0 else "naranja"),
        _kpi_card("% del Full Year",                 var_fy,                     "Real YTD / Budget anual", "primary"),
    ]


def _build_kpis(
    nnr: pd.Series,
    nno: pd.Series,
    status: pd.Series,
    budget: pd.DataFrame,
    unit: str,
    escenario: str,
) -> list:
    nnr_cards = _build_kpi_row(nnr, True,  budget, unit, escenario, status)
    nno_cards = _build_kpi_row(nno, False, budget, unit, escenario, status)

    def _wrap(row_label, cards):
        return html.Div([
            html.P(row_label, className="kpi-row-label"),
            html.Div(cards, className="kpi-strip"),
        ], className="kpi-section")

    return [
        _wrap("NNR — Revenue",  nnr_cards),
        _wrap("NNO — Órdenes", nno_cards),
    ]


# ── Sección: Gráfico ──────────────────────────────────────────────────────────

def _build_chart(
    nnr: pd.Series,
    nno: pd.Series,
    status: pd.Series,
    budget: pd.DataFrame,
    metric: str,
    pais: str,
    unit: str,
) -> html.Div:
    is_rev     = metric == "revenue"
    series     = nnr if is_rev else nno
    met_lbl    = "NNR" if is_rev else "NNO"
    bud_prefix = "nnr" if is_rev else "nno"
    geo_lbl    = _GEO_LBL.get(pais, pais)
    y_title    = f"{met_lbl} ({unit})" if is_rev else f"{met_lbl} (Órdenes)"

    _start_2025 = pd.Timestamp("2025-01-01")

    # Filtrar a partir de Enero 2025
    series_plot = series[series.index >= _start_2025] if not series.empty else series
    status_plot = status[status.index >= _start_2025] if not status.empty else status

    # ── Construir traza única de barras ───────────────────────────────────────
    # Meses con valor + meses pendiente (sin M2/M3 aún)
    series_idx = series_plot.index if not series_plot.empty else pd.DatetimeIndex([])
    pend_only  = (
        status_plot.index[
            (status_plot == "pendiente") & ~status_plot.index.isin(series_idx)
        ]
        if not status_plot.empty else pd.DatetimeIndex([])
    )
    all_bar_months = series_idx.union(pend_only).sort_values()

    bar_vals   = []
    bar_colors = []
    bar_texts  = []

    _color_map = {
        "completo": "#4827BE",
        "parcial":  "#9684E1",
        "pendiente": "#D4C9F5",
    }

    for m in all_bar_months:
        # Valor
        if not series_plot.empty and m in series_plot.index:
            v_raw = series_plot[m]
            v     = float(v_raw) if not pd.isna(v_raw) else 0.0
        else:
            v = 0.0

        # Status
        st = "pendiente"
        if not status_plot.empty and m in status_plot.index:
            st = str(status_plot[m])

        bar_vals.append(v)
        bar_colors.append(_color_map.get(st, "#D4C9F5"))

        month_lbl = f"<b>{m.strftime('%b')}</b>"
        if v > 0:
            val_str = f"{v:,.0f}" if is_rev else f"{int(round(v)):,}"
            bar_texts.append(f"{month_lbl}<br><b>{val_str}</b>")
        else:
            bar_texts.append(month_lbl)

    fig = go.Figure()

    if len(all_bar_months) > 0:
        fig.add_trace(go.Bar(
            x=all_bar_months,
            y=bar_vals,
            name=met_lbl,
            marker_color=bar_colors,
            text=bar_texts,
            texttemplate="%{text}",
            textposition="outside",
            textfont=dict(size=10, color="#1A1659"),
            hovertemplate=f"%{{x|%b %Y}}<br>{met_lbl}: %{{y:,.1f}}<extra></extra>",
        ))

    # ── Líneas de budget 2026 con etiquetas ───────────────────────────────────
    if not budget.empty:
        b2026 = budget[budget.index.year == 2026]
        for scen, color, scen_name in [
            ("base", "#00C97A", 'Base ("Junta")'),
            ("bear", "#FF820F", "Bear"),
        ]:
            col = f"{bud_prefix}_{scen}"
            if col not in b2026.columns or b2026.empty:
                continue
            bud_vals  = b2026[col].values
            bud_texts = [
                f"<b>{v:,.0f}</b>" if not pd.isna(v) else ""
                for v in bud_vals
            ]
            fig.add_trace(go.Scatter(
                x=b2026.index,
                y=bud_vals,
                name=f"Budget {scen_name}",
                mode="lines+markers+text",
                text=bud_texts,
                texttemplate="%{text}",
                textposition="top center",
                textfont=dict(size=9, color=color),
                line=dict(color=color, width=2, dash="dash"),
                marker=dict(size=6, color=color),
                hovertemplate=f"%{{x|%b %Y}}<br>Budget {scen_name}: %{{y:,.1f}}<extra></extra>",
            ))

    fig.update_layout(
        barmode="overlay",
        xaxis=dict(
            title="Cohorte (mes de entrada)",
            tickformat="%b %Y",
            tickangle=-30,
            gridcolor="#f5f5f5",
            range=[_start_2025 - pd.Timedelta(days=20), None],
        ),
        yaxis=dict(title=y_title, gridcolor="#f5f5f5"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=80, b=70),
        height=460,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    title = f"{met_lbl} por Cohorte — {geo_lbl}"
    return html.Div([
        html.H3(title, className="section-title"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])


# ── Sección: Tabla Año → Q → Mes ─────────────────────────────────────────────

def _build_table(
    nnr: pd.Series,
    nno: pd.Series,
    status: pd.Series,
    sellers: pd.Series,
    budget: pd.DataFrame,
    unit: str,
    escenario: str,
) -> html.Div:
    esc_short = "Base" if escenario == "base" else "Bear"
    bud_nnr   = f"nnr_{escenario}"
    bud_nno   = f"nno_{escenario}"

    all_ts = sorted(set(
        list(nnr.index if not nnr.empty else [])
        + list(nno.index if not nno.empty else [])
        + list(status.index if not status.empty else [])
    ))
    if not all_ts:
        return html.Div(html.P("Sin datos.", className="placeholder-hint"))

    all_ts = [pd.Timestamp(c) for c in all_ts]

    # ── Factories ─────────────────────────────────────────────────────────────
    def _hc(text, w, align="right", bg="#1A1659"):
        return html.Div(text, className="ct-cell ct-header-cell", style={
            "minWidth": w, "maxWidth": w, "textAlign": align,
            "background": bg, "color": "#fff",
            "whiteSpace": "normal", "lineHeight": "1.25",
            "padding": "5px 6px",
        })

    def _lc(text, bg="#fff", fg="#1A1659", bold=False, expandable=False):
        cls = "ct-cell ct-year-label" if expandable else "ct-cell"
        return html.Div(text, className=cls, style={
            "minWidth": _W["lbl"], "maxWidth": _W["lbl"],
            "background": bg, "color": fg,
            "fontWeight": "700" if bold else "400",
            "textAlign": "left",
            "position": "sticky", "left": "0", "zIndex": "1",
        })

    def _nc(text, w, bg="#fff", fg="#1A1659", bold=False):
        return html.Div(text, className="ct-cell", style={
            "minWidth": w, "maxWidth": w, "textAlign": "right",
            "background": bg, "color": fg,
            "fontWeight": "700" if bold else "400",
        })

    def _pc(val, bg="#fff"):
        txt, clr = _fmt_delta(val)
        return html.Div(txt, className="ct-cell", style={
            "minWidth": _W["pct"], "maxWidth": _W["pct"],
            "textAlign": "right", "fontWeight": "600",
            "color": clr, "background": bg,
        })

    header = html.Div([
        _hc("Cohorte",              _W["lbl"], "left"),
        _hc("",                     _W["st"]),
        _hc("Sellers",              _W["sel"]),
        _hc(f"NNR\n({unit})",       _W["nnr"]),
        _hc(f"Bud {esc_short}\nNNR", _W["bud"]),
        _hc("% NNR",                _W["pct"]),
        _hc("NNO",                  _W["nno"]),
        _hc(f"Bud {esc_short}\nNNO", _W["bud"]),
        _hc("% NNO",                _W["pct"]),
    ], className="ct-row ct-header-row", style={"minHeight": "46px"})

    def _safe(s, key, default=np.nan):
        try:
            v = s[key]
            return float(v) if not pd.isna(v) else default
        except Exception:
            return default

    def _safe_str(s, key):
        try:
            return str(s[pd.Timestamp(key)])
        except Exception:
            return "pendiente"

    def _make_row(label, cohorts, bg="#fff", lbl_bg=None, fg="#1A1659",
                  bold=False, show_status=False, expandable=False):
        lb = lbl_bg or bg

        nnr_v = sum(_safe(nnr, c) for c in cohorts if not np.isnan(_safe(nnr, c))) or np.nan
        nno_v = sum(_safe(nno, c) for c in cohorts if not np.isnan(_safe(nno, c))) or np.nan
        sel_v = int(sum(_safe(sellers, c, 0) for c in cohorts))

        # Budget — solo 2026
        bud_cohorts = [c for c in cohorts if pd.Timestamp(c).year == 2026]
        nnr_bud_v = np.nan
        nno_bud_v = np.nan
        nnr_pct   = np.nan
        nno_pct   = np.nan

        if bud_cohorts and not budget.empty:
            bud_idx = budget.reindex([pd.Timestamp(c) for c in bud_cohorts])
            if bud_nnr in budget.columns:
                nnr_bud_v = float(bud_idx[bud_nnr].sum(skipna=True))
                if nnr_bud_v > 0 and not np.isnan(nnr_v):
                    nnr_pct = nnr_v / nnr_bud_v - 1
            if bud_nno in budget.columns:
                nno_bud_v = float(bud_idx[bud_nno].sum(skipna=True))
                if nno_bud_v > 0 and not np.isnan(nno_v):
                    nno_pct = nno_v / nno_bud_v - 1

        has_bud = bool(bud_cohorts)

        st_cell = html.Div("", className="ct-cell",
                           style={"minWidth": _W["st"], "maxWidth": _W["st"],
                                  "textAlign": "center", "background": bg})
        if show_status and len(cohorts) == 1:
            st = _safe_str(status, cohorts[0])
            st_cell = html.Div(_status_icon(st), className="ct-cell",
                               style={"minWidth": _W["st"], "maxWidth": _W["st"],
                                      "textAlign": "center", "background": bg})

        return html.Div([
            _lc(label, bg=lb, fg=fg, bold=bold, expandable=expandable),
            st_cell,
            _nc(f"{sel_v:,}" if sel_v else "—", _W["sel"],  bg=bg, fg=fg, bold=bold),
            _nc(_fmt_val(nnr_v, True),            _W["nnr"],  bg=bg, fg=fg, bold=bold),
            _nc(_fmt_val(nnr_bud_v, True) if has_bud else "—", _W["bud"], bg=bg, fg=fg, bold=bold),
            _pc(nnr_pct, bg) if has_bud else _nc("—", _W["pct"], bg=bg, fg=fg),
            _nc(_fmt_val(nno_v, False),           _W["nno"],  bg=bg, fg=fg, bold=bold),
            _nc(_fmt_val(nno_bud_v, False) if has_bud else "—", _W["bud"], bg=bg, fg=fg, bold=bold),
            _pc(nno_pct, bg) if has_bud else _nc("—", _W["pct"], bg=bg, fg=fg),
        ], className="ct-row ct-detail-row")

    # ── Agrupar Año → Q → Mes ─────────────────────────────────────────────────
    years  = sorted({c.year for c in all_ts})
    groups = []

    for year in years:
        yr_cs  = [c for c in all_ts if c.year == year]
        yr_row = _make_row(str(year), yr_cs,
                           bg="#EDE9F8", lbl_bg="#EDE9F8", bold=True, expandable=True)

        q_groups = []
        for q in range(1, 5):
            q_months = {1: [1,2,3], 2: [4,5,6], 3: [7,8,9], 4: [10,11,12]}[q]
            q_cs = [c for c in yr_cs if c.month in q_months]
            if not q_cs:
                continue

            q_row = _make_row(f"Q{q} {year}", q_cs,
                              bg="#F3F0FC", lbl_bg="#F3F0FC", bold=True, expandable=True)

            month_rows = [
                _make_row(c.strftime("%b %Y"), [c], bg="#fff", show_status=True)
                for c in q_cs
            ]

            if len(q_cs) == 1:
                q_groups.append(html.Div([q_row] + month_rows, className="ct-group-nodrill"))
            else:
                q_groups.append(html.Details([
                    html.Summary(q_row, className="ct-summary"),
                    html.Div(month_rows, className="ct-detail-body"),
                ], className="ct-group"))

        open_year = (year == 2026)
        if len(yr_cs) == 1:
            groups.append(html.Div([yr_row] + q_groups, className="ct-group-nodrill"))
        else:
            groups.append(html.Details([
                html.Summary(yr_row, className="ct-summary"),
                html.Div(q_groups, className="ct-detail-body"),
            ], className="ct-group", open=open_year))

    total_row = _make_row("Total", all_ts,
                          bg="#4827BE", lbl_bg="#4827BE", fg="#fff", bold=True)

    legend = html.Div([
        html.Span("✓ Completo (M2+M3)", style={"color": "#00C97A", "marginRight": "16px", "fontSize": "12px"}),
        html.Span("~ Parcial (solo M2)", style={"color": "#FF820F", "marginRight": "16px", "fontSize": "12px"}),
        html.Span("– Pendiente",         style={"color": "#AAAAAA", "fontSize": "12px"}),
    ], style={"padding": "6px 0 10px"})

    table = html.Div(
        html.Div([header, *groups, total_row], className="ct-table"),
        className="ct-wrap",
    )

    return html.Div([
        html.H3("NNR / NNO por Cohorte", className="section-title"),
        legend,
        table,
    ], className="page-section card")


# ── Callback principal ────────────────────────────────────────────────────────

@callback(
    Output("nnr-kpis",           "children"),
    Output("nnr-chart-container","children"),
    Output("nnr-table",          "children"),
    Input("nnr-metric",    "value"),
    Input("nnr-pais",      "value"),
    Input("nnr-moneda",    "value"),
    Input("nnr-fx-cop",    "value"),
    Input("nnr-fx-mxn",    "value"),
    Input("nnr-escenario", "value"),
    Input("url",           "pathname"),
    State("cohort-overrides", "data"),
    prevent_initial_call=False,
)
def update_nnr(metric, pais, moneda, fx_cop, fx_mxn, escenario, pathname, cohort_overrides):
    if pathname != "/nnr":
        raise PreventUpdate

    metric   = metric   or "orders"
    pais     = pais     or "CONSOLIDADO"
    moneda   = moneda   or "local"
    escenario = escenario or "base"
    is_rev   = metric == "revenue"

    fx_cop_f = float(fx_cop or 3800)
    fx_mxn_f = float(fx_mxn or 17.5)
    unit     = revenue_display_unit(pais, moneda)

    # Filtros: todos los segmentos, incluir churn
    filters  = build_filters(pais, None, "incluir", None)

    _empty_ui = html.Div(
        [html.P("Sin datos.", className="placeholder-hint")],
        className="placeholder-box",
    )

    # ── Cargar datos ──────────────────────────────────────────────────────────
    df_ord = load_orders(filters)
    df_rev = load_revenue(filters)

    if not df_ord.empty:
        df_ord = apply_cohort_overrides(df_ord, cohort_overrides, "order_month")

    if not df_rev.empty:
        df_rev = apply_cohort_overrides(df_rev, cohort_overrides, "revenue_month")
        df_rev = prepare_revenue(df_rev, pais, moneda, fx_cop_f, fx_mxn_f)

    # Excluir mes actual (dato incompleto)
    _today = pd.Timestamp.today().replace(day=1).normalize()
    if not df_ord.empty:
        df_ord = df_ord[pd.to_datetime(df_ord["order_month"]) < _today]
    if not df_rev.empty:
        df_rev = df_rev[pd.to_datetime(df_rev["revenue_month"]) < _today]

    if df_ord.empty and df_rev.empty:
        return [_kpi_card("Sin datos", "—", "", "muted")], _empty_ui, _empty_ui

    # ── Calcular NNR y NNO por cohorte ────────────────────────────────────────
    nnr, nnr_status = calc_nnr_by_cohort(df_rev) if not df_rev.empty else (pd.Series(dtype=float), pd.Series(dtype=str))
    nno, nno_status = calc_nno_by_cohort(df_ord) if not df_ord.empty else (pd.Series(dtype=float), pd.Series(dtype=str))

    # Status unificado: usar el de la métrica seleccionada; si no hay, el otro
    status = nnr_status if is_rev else nno_status
    if status.empty:
        status = nno_status if is_rev else nnr_status

    # Sellers por cohorte
    sellers = pd.Series(dtype=float)
    if not df_ord.empty:
        sellers = df_ord.groupby("cohort_month")["seller_id"].nunique()
        sellers.index = pd.to_datetime(sellers.index)

    # ── Budget ────────────────────────────────────────────────────────────────
    df_budget = load_budget_nnr()
    budget    = _prepare_budget(df_budget, pais, unit, fx_cop_f, fx_mxn_f)

    # ── Construir secciones ───────────────────────────────────────────────────
    kpis  = _build_kpis(nnr, nno, status, budget, unit, escenario)
    chart = _build_chart(nnr, nno, status, budget, metric, pais, unit)
    table = _build_table(nnr, nno, status, sellers, budget, unit, escenario)

    return kpis, chart, table
