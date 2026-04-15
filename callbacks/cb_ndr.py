"""
Vista: NDR / ODR — Retención por Cohorte

Metodología:
  - Universo: todos los cohortes disponibles (sin filtro de corte base)
  - Suavizado forward 3 períodos por cohorte:
        smooth(C, Mn) = mean(raw(C,Mn), raw(C,Mn+1), raw(C,Mn+2))
        usando solo los meses con dato (min 1, max 3)
  - Eje Y: cohortes (desc), Eje X: lifecycle months M1, M2, ..., Mn
  - Promedio aritmético: mean de cohortes con dato en Mn
  - Promedio ponderado: ponderado por Σ raw(M1..M12) de cada cohorte
  - Hitos destacados: M13 y M25
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback, clientside_callback, dcc, html
from dash.exceptions import PreventUpdate

from components.page_filters import ndr_filters
from data.data_loader import load_orders, load_revenue
from data.transforms import (
    build_filters,
    calc_cohort_matrix,
    prepare_revenue,
    revenue_display_unit,
)

_MILESTONES = {13, 25}
_HITOS      = [1, 3, 6, 12, 13, 18, 24, 25]

_LBL_W  = 110   # px — columna etiqueta cohorte
_CELL_W = 78    # px — cada celda de lifecycle month


# ── Layout ────────────────────────────────────────────────────────────────────

def ndr_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [html.H2("Net Dollar Retention / Net Order Retention", className="page-title")],
                className="page-header",
            ),
            ndr_filters(),
            html.Div(id="ndr-chart-container", className="page-section card"),
            html.Div(id="ndr-averages",        className="page-section card"),
            html.Div(id="ndr-table",           className="page-section"),
            html.Div(id="ndr-pills-dummy", style={"display": "none"}),
        ],
        className="page",
    )


# ── Clientside callback: sincroniza pills de segmento ─────────────────────────
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
    Output("ndr-pills-dummy", "style"),
    Input("ndr-segmentos", "value"),
    prevent_initial_call=False,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(val, is_rev: bool) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:,.1f}" if is_rev else f"{int(round(val)):,}"


def _cell_style(val: float, q1: float, q2: float, q3: float) -> dict:
    """Color de celda por cuartil."""
    if np.isnan(val):
        return {}
    if val >= q3:
        return {"background": "#4827BE", "color": "#fff"}
    if val >= q2:
        return {"background": "#9684E1", "color": "#fff"}
    if val >= q1:
        return {"background": "#D4C9F5", "color": "#1A1659"}
    return {"background": "#F0EDFC", "color": "#1A1659"}


def _lbl_s(extra: dict | None = None) -> dict:
    s = {
        "minWidth": f"{_LBL_W}px", "maxWidth": f"{_LBL_W}px",
        "position": "sticky", "left": "0", "zIndex": "1",
    }
    if extra:
        s.update(extra)
    return s


def _num_s(lm: int | None = None, extra: dict | None = None) -> dict:
    s = {"minWidth": f"{_CELL_W}px", "maxWidth": f"{_CELL_W}px", "textAlign": "right"}
    if lm in _MILESTONES:
        s["borderLeft"] = "2px solid #00C97A"
    if extra:
        s.update(extra)
    return s


# ── Sección: Gráfico ──────────────────────────────────────────────────────────

def _build_chart(
    simple_avgs: dict,
    weighted_avgs: dict,
    val_lbl: str,
    is_rev: bool,
) -> dcc.Graph:

    lms_s = sorted(k for k, v in simple_avgs.items()   if v is not None and not np.isnan(v))
    lms_w = sorted(k for k, v in weighted_avgs.items() if v is not None and not np.isnan(v))
    fmt_h = ":.1f" if is_rev else ":,.0f"

    fig = go.Figure()

    if lms_s:
        fig.add_trace(go.Scatter(
            x=lms_s,
            y=[simple_avgs[lm] for lm in lms_s],
            name="Avg Aritmético",
            mode="lines+markers",
            line=dict(color="#00C97A", width=2),
            marker=dict(size=5, color="#00C97A"),
            hovertemplate=f"<b>M%{{x}}</b><br>{val_lbl}: %{{y{fmt_h}}}<extra>Avg Aritmético</extra>",
        ))

    if lms_w:
        fig.add_trace(go.Scatter(
            x=lms_w,
            y=[weighted_avgs[lm] for lm in lms_w],
            name="Avg Ponderado",
            mode="lines+markers",
            line=dict(color="#4827BE", width=2.5),
            marker=dict(size=5, color="#4827BE"),
            hovertemplate=f"<b>M%{{x}}</b><br>{val_lbl}: %{{y{fmt_h}}}<extra>Avg Ponderado</extra>",
        ))

    # Líneas verticales en hitos M13 y M25
    all_lm_present = set(simple_avgs) | set(weighted_avgs)
    for ms in sorted(_MILESTONES):
        if ms in all_lm_present:
            fig.add_vline(
                x=ms,
                line=dict(color="#00C97A", width=1.5, dash="dot"),
                annotation_text=f" M{ms}",
                annotation_position="top right",
                annotation_font=dict(color="#00C97A", size=11),
            )

    fig.update_layout(
        title=dict(text=f"Curva Promedio — {val_lbl}", font=dict(size=14, color="#1A1659")),
        xaxis=dict(
            title="Mes de vida",
            tickmode="linear", dtick=1, tick0=1,
            tickprefix="M",
            gridcolor="#f5f5f5",
        ),
        yaxis=dict(title=val_lbl, gridcolor="#f5f5f5"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=60, b=60),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return dcc.Graph(figure=fig, config={"displayModeBar": False})


# ── Sección: Tabla de hitos ───────────────────────────────────────────────────

def _build_averages_table(
    simple_avgs: dict,
    weighted_avgs: dict,
    all_lm: list,
    is_rev: bool,
) -> html.Div:

    hitos_present = [lm for lm in _HITOS if lm in all_lm]

    header = html.Div([
        html.Div("Mes de vida",    className="nt-cell nt-label nt-hdr"),
        html.Div("Avg Aritmético", className="nt-cell nt-num   nt-hdr"),
        html.Div("Avg Ponderado",  className="nt-cell nt-num   nt-hdr"),
    ], className="nt-row")

    rows = [header]
    for lm in hitos_present:
        is_ms   = lm in _MILESTONES
        lbl_cls = "nt-cell nt-label" + (" ndr-hito-lbl" if is_ms else "")
        row_cls = "nt-row" + (" ndr-hito-row" if is_ms else "")
        rows.append(html.Div([
            html.Div(f"M{lm}",
                     className=lbl_cls),
            html.Div(_fmt(simple_avgs.get(lm),   is_rev), className="nt-cell nt-num"),
            html.Div(_fmt(weighted_avgs.get(lm), is_rev), className="nt-cell nt-num"),
        ], className=row_cls))

    return html.Div([
        html.H3("Promedios por hito", className="section-title"),
        html.Div(html.Div(rows, className="nt-table"), className="ct-wrap"),
    ])


# ── Sección: Heatmap ─────────────────────────────────────────────────────────

def _build_heatmap(
    smooth_df: pd.DataFrame,
    simple_avgs: dict,
    weighted_avgs: dict,
    all_lm: list,
    is_rev: bool,
) -> html.Div:

    # Cuartiles globales sobre todos los valores suavizados
    all_vals = smooth_df.values.flatten().astype(float)
    all_vals = all_vals[~np.isnan(all_vals)]
    if len(all_vals) >= 4:
        q1, q2, q3 = (float(np.percentile(all_vals, p)) for p in (25, 50, 75))
    else:
        q1 = q2 = q3 = 0.0

    # ── Header ────────────────────────────────────────────────────────────────
    hdr_lbl = html.Div(
        "Cohorte",
        className="ct-cell ct-header-cell",
        style=_lbl_s({"background": "#1A1659"}),
    )
    hdr_cells = [hdr_lbl]
    for lm in all_lm:
        ms_extra = {"background": "#00C97A", "color": "#fff", "fontWeight": "700"} if lm in _MILESTONES else {}
        hdr_cells.append(html.Div(
            f"M{lm}",
            className="ct-cell ct-header-cell",
            style={**_num_s(lm), **ms_extra},
        ))
    header = html.Div(hdr_cells, className="ct-row ct-header-row")

    # ── Filas de datos (cohorte más reciente arriba) ───────────────────────────
    data_rows = []
    for cohort_ts in sorted(smooth_df.index, reverse=True):
        lbl = pd.Timestamp(cohort_ts).strftime("%b %Y")
        cells = [html.Div(
            lbl,
            className="ct-cell",
            style=_lbl_s({"background": "#fff", "fontWeight": "600", "color": "#1A1659"}),
        )]
        for lm in all_lm:
            raw_val = smooth_df.loc[cohort_ts, lm]
            v = float(raw_val) if pd.notna(raw_val) else None
            if v is not None:
                style = {**_num_s(lm), **_cell_style(v, q1, q2, q3)}
                if lm in _MILESTONES:
                    style["fontWeight"] = "700"
                text = _fmt(v, is_rev)
            else:
                style = _num_s(lm)
                text = ""
            cells.append(html.Div(text, className="ct-cell", style=style))
        data_rows.append(html.Div(cells, className="ct-row"))

    # ── Filas de subtotales ───────────────────────────────────────────────────
    def _avg_row(label: str, avgs: dict, bg: str, fg: str) -> html.Div:
        cells = [html.Div(
            label,
            className="ct-cell",
            style=_lbl_s({"background": bg, "color": fg, "fontWeight": "700"}),
        )]
        for lm in all_lm:
            v = avgs.get(lm)
            text = _fmt(v, is_rev) if v is not None else "—"
            ms_fg = "#00C97A" if lm in _MILESTONES else fg
            cells.append(html.Div(text, className="ct-cell", style={
                **_num_s(lm),
                "background": bg, "color": ms_fg, "fontWeight": "700",
            }))
        return html.Div(cells, className="ct-row")

    row_simple   = _avg_row("Avg Aritmético", simple_avgs,   "#E8E2F8", "#1A1659")
    row_weighted = _avg_row("Avg Ponderado",  weighted_avgs, "#4827BE", "#ffffff")

    table = html.Div(
        html.Div([header, *data_rows, row_simple, row_weighted], className="ct-table"),
        className="ct-wrap",
    )

    return html.Div([
        html.H3("Valores suavizados por cohorte", className="section-title"),
        table,
    ], className="page-section card")


# ── Callback principal ────────────────────────────────────────────────────────

@callback(
    Output("ndr-chart-container", "children"),
    Output("ndr-averages",        "children"),
    Output("ndr-table",           "children"),
    Input("ndr-metric",    "value"),
    Input("ndr-pais",      "value"),
    Input("ndr-moneda",    "value"),
    Input("ndr-fx-cop",    "value"),
    Input("ndr-fx-mxn",    "value"),
    Input("ndr-segmentos", "value"),
    Input("ndr-churn",     "value"),
    Input("url",           "pathname"),
    prevent_initial_call=False,
)
def update_ndr(metric, pais, moneda, fx_cop, fx_mxn, segmentos, churn, pathname):
    if pathname != "/ndr":
        raise PreventUpdate

    metric = metric or "orders"
    is_rev = metric == "revenue"

    filters = build_filters(pais, segmentos, churn, None)

    if is_rev:
        df_raw  = load_revenue(filters)
        df_raw  = prepare_revenue(df_raw, pais, moneda, fx_cop, fx_mxn)
        val_col = "display_value"
        unit    = revenue_display_unit(pais, moneda)
        val_lbl = f"Revenue ({unit})"
    else:
        df_raw  = load_orders(filters)
        val_col = "order_count"
        val_lbl = "Órdenes"

    _empty = html.Div(
        [html.P("Sin datos.", className="placeholder-hint")],
        className="placeholder-box",
    )

    if df_raw.empty:
        return _empty, _empty, _empty

    smooth_df, weights = calc_cohort_matrix(df_raw, val_col)

    if smooth_df.empty:
        return _empty, _empty, _empty

    all_lm = sorted(smooth_df.columns.tolist())

    # ── Promedios por lifecycle month ─────────────────────────────────────────
    simple_avgs   = {}
    weighted_avgs = {}
    for lm in all_lm:
        col = smooth_df[lm].dropna()
        if col.empty:
            continue
        simple_avgs[lm] = float(col.mean())
        w     = weights.reindex(col.index).fillna(0.0)
        w_sum = float(w.sum())
        weighted_avgs[lm] = (
            float((col * w).sum() / w_sum) if w_sum > 0 else float(col.mean())
        )

    # ── Construir secciones ───────────────────────────────────────────────────
    chart    = _build_chart(simple_avgs, weighted_avgs, val_lbl, is_rev)
    averages = _build_averages_table(simple_avgs, weighted_avgs, all_lm, is_rev)
    heatmap  = _build_heatmap(smooth_df, simple_avgs, weighted_avgs, all_lm, is_rev)

    return chart, averages, heatmap
