"""
Vista: NDR / ODR — Retención por Cohorte

Metodología:
  - Universo: todos los cohortes disponibles (sin filtro de corte base)
  - Suavizado forward 3 períodos por cohorte:
        smooth(C, Mn) = mean(raw(C,Mn), raw(C,Mn+1), raw(C,Mn+2))
        usando solo los meses con dato (min 1, max 3)
  - Eje Y: cohortes (desc), Eje X: lifecycle months M1, M2, ..., Mn
  - Promedio aritmético: mean de cohortes con dato en Mn (solo años seleccionados)
  - Promedio ponderado: ponderado por Σ raw(M1..M12) de cada cohorte
  - Hitos destacados: M13, M25, M37, M49
  - Años activos: interactivos; años con peso < umbral mínimo se auto-desactivan
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import io

from dash import Input, Output, State, callback, clientside_callback, ctx, dcc, html
from dash.exceptions import PreventUpdate

from components.page_filters import ndr_filters
from data.data_loader import load_orders, load_revenue, load_forecast
from data.transforms import (
    apply_cohort_overrides,
    build_filters,
    calc_cohort_matrix,
    prepare_revenue,
    revenue_display_unit,
)

_MILESTONES = {13, 25, 37, 49}
_HITOS      = [0, 1, 3, 6, 12, 13, 18, 24, 25, 36, 37, 48, 49]

_LBL_W  = 110   # px — columna etiqueta cohorte
_CELL_W = 78    # px — cada celda de lifecycle month
_MW     = 96    # px — columna meta (Σ M1-M12)
_META_BG = "#EEF6EE"  # verde suave para columnas meta
_FC_BG   = "#FFF3E0"  # naranja suave para celdas forecast
_FC_FG   = "#B25F00"  # texto naranja oscuro para celdas forecast

# Peso anual mínimo (Σ M1-M12 por año) para que el año se auto-active
# por debajo de este umbral el año arranca OFF (evita distorsión de cohortes muy pequeños)
_MIN_YEAR_WEIGHT_BY_UNIT: dict[str, float] = {
    "K MXN":  2_000.0,   # MEX 2021 ≈ 1 982 → auto-OFF ✓
    "MM COP": 10.0,
    "K USD":  100.0,
    "":       100.0,     # orders
}


def _meta_hdr(text: str) -> html.Div:
    """Encabezado de columna meta (verde oscuro)."""
    return html.Div(text, className="ct-cell ct-header-cell", style={
        "minWidth": f"{_MW}px", "maxWidth": f"{_MW}px",
        "background": "#1A7A3A", "color": "#fff",
        "fontWeight": "700", "fontSize": "11px",
        "textAlign": "right",
    })


def _meta_cell(text: str, bg: str = _META_BG, fg: str = "#1A4D2E",
               bold: bool = False) -> html.Div:
    """Celda de columna meta."""
    return html.Div(text, className="ct-cell", style={
        "minWidth": f"{_MW}px", "maxWidth": f"{_MW}px",
        "textAlign": "right", "background": bg,
        "color": fg, "fontWeight": "700" if bold else "500",
        "fontSize": "12px",
    })


# ── Layout ────────────────────────────────────────────────────────────────────

_BTN_STYLE = {
    "padding": "5px 14px",
    "fontSize": "12px",
    "fontWeight": "600",
    "borderRadius": "6px",
    "border": "1.5px solid #4827BE",
    "background": "#fff",
    "color": "#4827BE",
    "cursor": "pointer",
    "display": "flex",
    "alignItems": "center",
    "gap": "6px",
}


def ndr_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [html.H2("Net Dollar Retention / Net Order Retention", className="page-title")],
                className="page-header",
            ),
            ndr_filters(),
            # ── Secciones de ratio (chart + promedios + tabla ratio) ───────────
            html.Div(id="ndr-chart-container", className="page-section card"),
            html.Div(id="ndr-averages",        className="page-section card"),
            # ── Tablas Sin suavizar + Suavizado ────────────────────────────────
            html.Div(id="ndr-table",           className="page-section"),
            # ── Tabla de ratios (también controlada por year-select) ───────────
            html.Div(id="ndr-ratio-section",   className="page-section"),
            # ── Exportación ────────────────────────────────────────────────────
            html.Div([
                html.Button("↓ Exportar Excel", id="ndr-btn-export",
                            n_clicks=0, style=_BTN_STYLE),
                dcc.Download(id="ndr-download"),
            ], style={"display": "flex", "gap": "10px", "padding": "8px 0"}),
            dcc.Store(id="ndr-store"),
            html.Div(id="ndr-pills-dummy",      style={"display": "none"}),
            html.Div(id="ndr-year-pills-dummy", style={"display": "none"}),
        ],
        className="page",
    )


# ── Clientside callbacks: sincroniza pills ─────────────────────────────────────

# Segmento pills (excluye year pills para no interferir)
clientside_callback(
    """
    function(value) {
        setTimeout(function () {
            var active = value || [];
            document.querySelectorAll(".fb-pill:not(.fb-year-pill)").forEach(function (pill) {
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

# Year pills
clientside_callback(
    """
    function(value) {
        setTimeout(function () {
            var active = (value || []).map(String);
            document.querySelectorAll(".fb-year-pill").forEach(function (pill) {
                var yr = pill.textContent.trim();
                pill.classList.toggle("fb-pill--on", active.indexOf(yr) !== -1);
            });
        }, 0);
        return window.dash_clientside.no_update;
    }
    """,
    Output("ndr-year-pills-dummy", "style"),
    Input("ndr-year-select", "value"),
    prevent_initial_call=False,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(val, is_rev: bool) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:,.1f}" if is_rev else f"{int(round(val)):,}"


def _fmt_pct(val) -> str:
    """Ratio como porcentaje sin decimales, ej. 0.82 → '82%'."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val * 100:.0f}%"


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


# ── Seller data helper ────────────────────────────────────────────────────────

def _compute_seller_data(
    df: pd.DataFrame,
    val_col: str,
    top_n: int = 5,
) -> "dict[pd.Timestamp, pd.DataFrame]":
    """
    Por cada cohorte retorna un DataFrame con top_n sellers + 'Otros'.
    Filas = nombre del seller (o 'Otros'), columnas = lifecycle_month (int).
    Ranking por Σ M1-M12.
    """
    if df.empty:
        return {}

    agg = (
        df.groupby(["cohort_month", "seller_id", "seller_name", "lifecycle_month"])[val_col]
        .sum()
        .reset_index()
    )

    result: dict = {}
    for cohort_ts, cdf in agg.groupby("cohort_month"):
        spivot = cdf.pivot_table(
            index=["seller_id", "seller_name"],
            columns="lifecycle_month",
            values=val_col,
            aggfunc="sum",
        )
        spivot.columns = [int(c) for c in spivot.columns]

        m1_12 = [c for c in spivot.columns if 1 <= c <= 12]
        w = spivot[m1_12].sum(axis=1, skipna=True).sort_values(ascending=False)
        spivot = spivot.loc[w.index]

        # Display names (seller_name; append id only on duplicates)
        names = [name for _, name in spivot.index]
        display_names = []
        for sid, nm in spivot.index:
            if names.count(nm) > 1:
                display_names.append(f"{nm} ({sid})")
            else:
                display_names.append(nm)

        if len(spivot) <= top_n:
            out = spivot.copy()
            out.index = display_names
        else:
            top_df = spivot.iloc[:top_n].copy()
            top_df.index = display_names[:top_n]
            otros = spivot.iloc[top_n:].sum(min_count=1).to_frame().T
            otros.index = ["Otros"]
            out = pd.concat([top_df, otros])

        result[pd.Timestamp(cohort_ts)] = out

    return result


# ── Sección: Gráfico ──────────────────────────────────────────────────────────

_CHART_MAX_LM = 37   # x-axis cap para el gráfico de curva promedio
_TIPO_LBL = {"revenue": "NDR", "orders": "ODR"}
_GEO_LBL  = {"CONSOLIDADO": "Consolidado", "COL": "COL", "MEX": "MEX"}


def _chart_title(metric: str, pais: str) -> str:
    tipo = _TIPO_LBL.get(metric, "ODR")
    geo  = _GEO_LBL.get(pais, pais)
    return f"{tipo} — {geo}"


def _build_chart(
    simple_ratio_avgs: dict,
    weighted_ratio_avgs: dict,
    metric: str,
    pais: str,
    fc_mask: "pd.DataFrame | None" = None,
) -> dcc.Graph:
    """Curva promedio de ratios Mn/M1. Traza sólida = actuals, punteada = forecast."""

    # Último lifecycle_month donde al menos un cohorte aún tiene datos reales
    last_act_lm: "int | None" = None
    if fc_mask is not None and not fc_mask.empty:
        actual_lms = [int(lm) for lm in fc_mask.columns if not bool(fc_mask[lm].all())]
        if actual_lms:
            last_act_lm = max(actual_lms)

    lms_s = sorted(
        k for k, v in simple_ratio_avgs.items()
        if v is not None and not np.isnan(v) and k <= _CHART_MAX_LM
    )
    lms_w = sorted(
        k for k, v in weighted_ratio_avgs.items()
        if v is not None and not np.isnan(v) and k <= _CHART_MAX_LM
    )

    if last_act_lm is not None:
        lms_s_act = [lm for lm in lms_s if lm <= last_act_lm]
        lms_s_fc  = [lm for lm in lms_s if lm >= last_act_lm]  # solapan en last_act_lm para conectar
        lms_w_act = [lm for lm in lms_w if lm <= last_act_lm]
        lms_w_fc  = [lm for lm in lms_w if lm >= last_act_lm]
    else:
        lms_s_act, lms_s_fc = lms_s, []
        lms_w_act, lms_w_fc = lms_w, []

    title = _chart_title(metric, pais)
    fig = go.Figure()

    def _add_trace(lms, avgs, name, color, width, is_fc):
        if not lms:
            return
        ys = [avgs[lm] for lm in lms]
        fig.add_trace(go.Scatter(
            x=lms, y=ys,
            name=name,
            mode="lines+markers+text",
            line=dict(color=color, width=width, dash="dash" if is_fc else "solid"),
            marker=dict(size=5, color=color, symbol="diamond-open" if is_fc else "circle"),
            text=[f"<b>{v:.0%}</b>" for v in ys],
            textposition="top center",
            textfont=dict(size=9, color=color),
            showlegend=not is_fc,
        ))

    _add_trace(lms_s_act, simple_ratio_avgs,   "Avg Aritmético", "#00C97A", 2,   False)
    _add_trace(lms_s_fc,  simple_ratio_avgs,   "Avg Aritmético", "#00C97A", 2,   True)
    _add_trace(lms_w_act, weighted_ratio_avgs, "Avg Ponderado",  "#4827BE", 2.5, False)
    _add_trace(lms_w_fc,  weighted_ratio_avgs, "Avg Ponderado",  "#4827BE", 2.5, True)

    # Línea vertical en el límite actual/forecast
    if last_act_lm is not None and (lms_s_fc or lms_w_fc):
        fig.add_vline(
            x=last_act_lm + 0.5,
            line=dict(color="#FF8C00", width=1.5, dash="dot"),
            annotation_text=" Forecast →",
            annotation_position="top right",
            annotation_font=dict(color="#FF8C00", size=11),
        )

    # Líneas verticales en hitos
    all_lm_present = set(simple_ratio_avgs) | set(weighted_ratio_avgs)
    for ms in sorted(_MILESTONES):
        if ms in all_lm_present and ms <= _CHART_MAX_LM:
            fig.add_vline(
                x=ms,
                line=dict(color="#00C97A", width=1.5, dash="dot"),
                annotation_text=f" M{ms}",
                annotation_position="top right",
                annotation_font=dict(color="#00C97A", size=11),
            )

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#1A1659")),
        xaxis=dict(
            title="Mes de vida",
            tickmode="linear", dtick=1, tick0=0,
            tickprefix="M",
            range=[-0.5, _CHART_MAX_LM + 0.5],
            gridcolor="#f5f5f5",
        ),
        yaxis=dict(
            title="Ratio Mn/M1",
            tickformat=".0%",
            gridcolor="#f5f5f5",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=70, b=60),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_traces(hoverinfo="skip", hovertemplate=None)
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


# ── Sección: Tabla de hitos ───────────────────────────────────────────────────

def _build_averages_table(
    simple_ratio_avgs: dict,
    weighted_ratio_avgs: dict,
    all_lm: list,
    metric: str,
    pais: str,
) -> html.Div:
    """Tabla de promedios de ratio Mn/M1 en los hitos clave."""

    hitos_present = [lm for lm in _HITOS if lm in all_lm]
    tipo = _TIPO_LBL.get(metric, "ODR")
    geo  = _GEO_LBL.get(pais, pais)
    title = f"Data points {tipo} — {geo}"

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
            html.Div(f"M{lm}", className=lbl_cls),
            html.Div(_fmt_pct(simple_ratio_avgs.get(lm)),   className="nt-cell nt-num"),
            html.Div(_fmt_pct(weighted_ratio_avgs.get(lm)), className="nt-cell nt-num"),
        ], className=row_cls))

    return html.Div([
        html.H3(title, className="section-title"),
        html.Div(html.Div(rows, className="nt-table"), className="ct-wrap"),
    ])


# ── Sección: Heatmap ─────────────────────────────────────────────────────────

def _build_heatmap(
    df: pd.DataFrame,
    simple_avgs: dict,
    weighted_avgs: dict,
    all_lm: list,
    is_rev: bool,
    title: str = "Valores suavizados por cohorte",
    seller_data: "dict | None" = None,
    fc_mask: "pd.DataFrame | None" = None,
) -> html.Div:
    """
    Tabla agrupada por año (collapsible con <details>/<summary> nativo).
    Cada año muestra un subtotal (suma) siempre visible.
    Al expandir se ven las cohortes individuales del año.
    """
    smooth_df = df

    # Cuartiles globales sobre todos los valores
    all_vals = smooth_df.values.flatten().astype(float)
    all_vals = all_vals[~np.isnan(all_vals)]
    if len(all_vals) >= 4:
        q1, q2, q3 = (float(np.percentile(all_vals, p)) for p in (25, 50, 75))
    else:
        q1 = q2 = q3 = 0.0

    # Columnas M1-M12 para el peso Σ
    m1_12_cols = [c for c in all_lm if 1 <= c <= 12]

    # Agrupar por año — orden ascendente (2021 → 2026)
    smooth_idx = smooth_df.copy()
    smooth_idx.index = pd.to_datetime(smooth_idx.index)
    years = sorted(smooth_idx.index.year.unique())
    year_totals = smooth_idx.groupby(smooth_idx.index.year).sum(min_count=1)

    def _cohort_m1_12(cohort_ts) -> float:
        return sum(
            float(smooth_idx.loc[cohort_ts, lm])
            for lm in m1_12_cols
            if lm in smooth_idx.columns and pd.notna(smooth_idx.loc[cohort_ts, lm])
        )

    def _year_m1_12(ytotal: pd.Series) -> float:
        if ytotal.empty:
            return 0.0
        return sum(
            float(ytotal.get(lm, np.nan))
            for lm in m1_12_cols
            if pd.notna(ytotal.get(lm, np.nan))
        )

    # ── Header ────────────────────────────────────────────────────────────────
    hdr_cells = [
        html.Div("Cohorte", className="ct-cell ct-header-cell",
                 style=_lbl_s({"background": "#1A1659"})),
        _meta_hdr("Σ M1-M12"),
    ]
    for lm in all_lm:
        ms_extra = {"background": "#00C97A", "color": "#fff", "fontWeight": "700"} if lm in _MILESTONES else {}
        hdr_cells.append(html.Div(
            f"M{lm}",
            className="ct-cell ct-header-cell",
            style={**_num_s(lm), **ms_extra},
        ))
    header = html.Div(hdr_cells, className="ct-row ct-header-row")

    # ── Grupos por año ────────────────────────────────────────────────────────
    groups = []
    for year in years:
        cohorts_in_year = sorted(smooth_idx[smooth_idx.index.year == year].index)
        ytotal = year_totals.loc[year] if year in year_totals.index else pd.Series(dtype=float)
        yr_m1_12 = _year_m1_12(ytotal)

        # Fila resumen del año
        yr_cells = [
            html.Div(str(year), className="ct-cell ct-year-label",
                     style=_lbl_s({"background": "#EDE9F8", "fontWeight": "700"})),
            _meta_cell(f"{yr_m1_12:,.0f}", bg="#EDE9F8", fg="#1A4D2E", bold=True),
        ]
        for lm in all_lm:
            raw_val = ytotal.get(lm, np.nan) if not ytotal.empty else np.nan
            v = float(raw_val) if pd.notna(raw_val) else None
            ms_fg = "#4827BE" if lm in _MILESTONES else "#1A1659"
            text = _fmt(v, is_rev) if v is not None else "—"
            yr_cells.append(html.Div(text, className="ct-cell", style={
                **_num_s(lm), "background": "#EDE9F8", "color": ms_fg, "fontWeight": "700",
            }))
        year_row = html.Div(yr_cells, className="ct-row ct-year-row")

        # Filas de detalle
        detail_rows = []
        for cohort_ts in cohorts_in_year:
            lbl = cohort_ts.strftime("%b %Y")
            c_m1_12 = _cohort_m1_12(cohort_ts)
            cells = [
                html.Div(lbl, className="ct-cell ct-month-label",
                         style=_lbl_s({"background": "#F8F6FE"})),
                _meta_cell(f"{c_m1_12:,.0f}", bg="#F4FAF4"),
            ]
            for lm in all_lm:
                raw_val = smooth_idx.loc[cohort_ts, lm] if lm in smooth_idx.columns else np.nan
                v = float(raw_val) if pd.notna(raw_val) else None
                _is_fc = (
                    fc_mask is not None
                    and lm in fc_mask.columns
                    and cohort_ts in fc_mask.index
                    and bool(fc_mask.loc[cohort_ts, lm])
                )
                if v is not None:
                    if _is_fc:
                        style = {**_num_s(lm), "background": _FC_BG, "color": _FC_FG}
                    else:
                        style = {**_num_s(lm), **_cell_style(v, q1, q2, q3)}
                    if lm in _MILESTONES:
                        style["fontWeight"] = "700"
                    text = _fmt(v, is_rev)
                else:
                    style = {**_num_s(lm), "background": "#F8F6FE"}
                    text = ""
                cells.append(html.Div(text, className="ct-cell ct-detail-cell", style=style))
            cohort_row = html.Div(cells, className="ct-row ct-detail-row")

            # Seller drill-down (solo si hay datos y más de 1 seller)
            sdf = seller_data.get(cohort_ts) if seller_data else None
            if sdf is not None and len(sdf) > 1:
                seller_rows = []
                for seller_nm, srow in sdf.iterrows():
                    s_m1_12 = sum(
                        float(srow[lm]) for lm in m1_12_cols
                        if lm in srow.index and pd.notna(srow.get(lm))
                    )
                    s_cells = [
                        html.Div(str(seller_nm), className="ct-cell ct-seller-label",
                                 style=_lbl_s()),
                        _meta_cell(f"{s_m1_12:,.0f}", bg="#FDFCFF", fg="#555"),
                    ]
                    for lm in all_lm:
                        sv = srow.get(lm, np.nan) if lm in srow.index else np.nan
                        sv = float(sv) if pd.notna(sv) else None
                        text = _fmt(sv, is_rev) if sv is not None else ""
                        s_cells.append(html.Div(text, className="ct-cell ct-seller-cell",
                                                style=_num_s(lm)))
                    seller_rows.append(html.Div(s_cells, className="ct-row"))

                detail_rows.append(html.Details([
                    html.Summary(cohort_row, className="ct-cohort-summary"),
                    html.Div(seller_rows, className="ct-seller-body"),
                ], className="ct-cohort-group"))
            else:
                detail_rows.append(cohort_row)

        if len(cohorts_in_year) <= 1:
            groups.append(html.Div(
                [html.Div(yr_cells, className="ct-row ct-year-row")] + detail_rows,
                className="ct-group-nodrill",
            ))
        else:
            groups.append(html.Details(
                [
                    html.Summary(year_row, className="ct-summary"),
                    html.Div(detail_rows, className="ct-detail-body"),
                ],
                className="ct-group",
            ))

    # ── Fila Total (suma de todos los cohortes por mes) ───────────────────────
    def _col_sum(lm: int):
        if lm not in smooth_idx.columns:
            return None
        col = smooth_idx[lm].dropna()
        return float(col.sum()) if not col.empty else None

    grand_total_m1_12 = sum(
        v for lm in m1_12_cols if (v := _col_sum(lm)) is not None
    )
    total_cells = [
        html.Div("Total", className="ct-cell",
                 style=_lbl_s({"background": "#4827BE", "color": "#fff", "fontWeight": "700"})),
        _meta_cell(f"{grand_total_m1_12:,.0f}", bg="#4827BE", fg="#fff", bold=True),
    ]
    for lm in all_lm:
        total_v = _col_sum(lm)
        ms_fg = "#00C97A" if lm in _MILESTONES else "#fff"
        text = _fmt(total_v, is_rev) if total_v is not None else "—"
        total_cells.append(html.Div(text, className="ct-cell", style={
            **_num_s(lm), "background": "#4827BE", "color": ms_fg, "fontWeight": "700",
        }))
    total_row = html.Div(total_cells, className="ct-row")

    table = html.Div(
        html.Div([header, *groups, total_row], className="ct-table"),
        className="ct-wrap",
    )

    _fc_legend = []
    if fc_mask is not None and bool(fc_mask.values.any()):
        _fc_legend = [html.Div([
            html.Span("", style={
                "display": "inline-block", "width": "11px", "height": "11px",
                "background": _FC_BG, "border": f"1.5px solid {_FC_FG}",
                "borderRadius": "2px", "verticalAlign": "middle",
                "marginRight": "5px",
            }),
            html.Span("Forecast", style={
                "color": _FC_FG, "fontSize": "11px", "verticalAlign": "middle",
            }),
        ], style={"padding": "0 0 6px 0"})]

    return html.Div([
        html.H3(title, className="section-title"),
        *_fc_legend,
        table,
    ], className="page-section card")


# ── Sección: Tabla de ratios NDR/ODR ─────────────────────────────────────────

def _build_ratio_heatmap(
    smooth_df: pd.DataFrame,
    weights: pd.Series,
    simple_ratio_avgs: dict,
    weighted_ratio_avgs: dict,
    all_lm: list,
    title: str = "Ratios NDR/ODR por cohorte (Mn / M1)",
    deselected_years: "set | None" = None,
    fc_mask: "pd.DataFrame | None" = None,
) -> html.Div:
    """
    Tabla de ratios Mn / M1 por cohorte, agrupada por año (ascendente).
    Columnas iniciales: Σ M1-M12 (peso absoluto).
    Años desactivados (deselected_years): grisados visualmente.
    Los promedios en simple_ratio_avgs / weighted_ratio_avgs ya reflejan
    solo los años activos (calculados en update_ratio_section).
    """
    if 1 not in smooth_df.columns or smooth_df.empty:
        return html.Div()

    deselected = deselected_years or set()

    smooth_idx = smooth_df.copy()
    smooth_idx.index = pd.to_datetime(smooth_idx.index)

    # Ratio por cohorte: cada fila ÷ M1 de esa fila
    ratio_df = smooth_idx.div(smooth_idx[1], axis=0)

    # Cuartiles solo sobre años activos (para colorear correctamente)
    active_mask = ~smooth_idx.index.year.isin(deselected)
    vals_active = ratio_df[active_mask].values.flatten().astype(float)
    vals_active = vals_active[~np.isnan(vals_active)]
    if len(vals_active) >= 4:
        q1, q2, q3 = (float(np.percentile(vals_active, p)) for p in (25, 50, 75))
    else:
        q1 = q2 = q3 = 0.0

    # Ratio pooled por año: Σ Mn_año / Σ M1_año
    year_abs = smooth_idx.groupby(smooth_idx.index.year).sum(min_count=1)
    year_ratio_totals = year_abs.div(year_abs[1], axis=0)

    # Pesos por cohorte y por año
    weights_idx = weights.copy()
    weights_idx.index = pd.to_datetime(weights_idx.index)
    # Total weight = only active years (for weighted avg meta cell)
    active_weights = weights_idx[weights_idx.index.year.isin(
        set(smooth_idx.index.year.unique()) - deselected
    )]
    total_weight = float(active_weights.sum()) if not active_weights.empty else 0.0

    year_weights = weights_idx.groupby(weights_idx.index.year).sum()

    years = sorted(smooth_idx.index.year.unique())

    # ── Header ────────────────────────────────────────────────────────────────
    hdr_cells = [
        html.Div("Cohorte", className="ct-cell ct-header-cell",
                 style=_lbl_s({"background": "#1A1659"})),
        _meta_hdr("Σ M1-M12"),
    ]
    for lm in all_lm:
        ms_extra = {"background": "#00C97A", "color": "#fff", "fontWeight": "700"} if lm in _MILESTONES else {}
        hdr_cells.append(html.Div(
            f"M{lm}",
            className="ct-cell ct-header-cell",
            style={**_num_s(lm), **ms_extra},
        ))
    header = html.Div(hdr_cells, className="ct-row ct-header-row")

    # ── Grupos por año ────────────────────────────────────────────────────────
    groups = []
    for year in years:
        is_deselected = year in deselected
        cohorts_in_year = sorted(smooth_idx[smooth_idx.index.year == year].index)
        ytotal_r = (
            year_ratio_totals.loc[year]
            if year in year_ratio_totals.index
            else pd.Series(dtype=float)
        )
        yr_w = float(year_weights.get(year, 0.0))

        # Estilo del año según si está activo o no
        if is_deselected:
            yr_bg = "#F2F2F2"
            yr_fg = "#AAAAAA"
            yr_meta_fg = "#BBBBBB"
        else:
            yr_bg = "#EDE9F8"
            yr_fg = "#1A1659"
            yr_meta_fg = "#1A4D2E"

        # Fila resumen del año
        yr_cells = [
            html.Div(
                str(year) + (" ✕" if is_deselected else ""),
                className="ct-cell ct-year-label",
                style=_lbl_s({"background": yr_bg, "fontWeight": "700", "color": yr_fg}),
            ),
            _meta_cell(f"{yr_w:,.0f}", bg=yr_bg, fg=yr_meta_fg, bold=True),
        ]
        for lm in all_lm:
            raw_val = ytotal_r.get(lm, np.nan) if not ytotal_r.empty else np.nan
            v = float(raw_val) if pd.notna(raw_val) else None
            if is_deselected:
                ms_fg = yr_fg
            else:
                ms_fg = "#4827BE" if lm in _MILESTONES else "#1A1659"
            text = _fmt_pct(v) if v is not None else "—"
            yr_cells.append(html.Div(text, className="ct-cell", style={
                **_num_s(lm),
                "background": yr_bg, "color": ms_fg, "fontWeight": "700",
            }))
        year_row = html.Div(yr_cells, className="ct-row ct-year-row")

        # Filas de detalle (cohortes individuales)
        detail_rows = []
        for cohort_ts in cohorts_in_year:
            lbl = cohort_ts.strftime("%b %Y")
            c_w = float(weights_idx.get(cohort_ts, 0.0))

            if is_deselected:
                lbl_bg   = "#F5F5F5"
                cell_bg  = "#F5F5F5"
                cell_fg  = "#BBBBBB"
                meta_fg  = "#BBBBBB"
                lbl_color = "#AAAAAA"
            else:
                lbl_bg   = "#F8F6FE"
                cell_bg  = "#F8F6FE"
                cell_fg  = None        # usa heatmap normal
                meta_fg  = "#1A4D2E"
                lbl_color = None

            cells = [
                html.Div(lbl, className="ct-cell ct-month-label",
                         style=_lbl_s({"background": lbl_bg,
                                       **({"color": lbl_color} if lbl_color else {})})),
                _meta_cell(f"{c_w:,.0f}",
                           bg="#F4FAF4" if not is_deselected else "#F5F5F5",
                           fg=meta_fg),
            ]
            for lm in all_lm:
                raw_val = ratio_df.loc[cohort_ts, lm] if lm in ratio_df.columns else np.nan
                v = float(raw_val) if pd.notna(raw_val) else None
                _is_fc = (
                    not is_deselected
                    and fc_mask is not None
                    and lm in fc_mask.columns
                    and cohort_ts in fc_mask.index
                    and bool(fc_mask.loc[cohort_ts, lm])
                )
                if v is not None:
                    if is_deselected:
                        style = {**_num_s(lm), "background": cell_bg, "color": cell_fg}
                    elif _is_fc:
                        style = {**_num_s(lm), "background": _FC_BG, "color": _FC_FG}
                        if lm in _MILESTONES:
                            style["fontWeight"] = "700"
                    else:
                        style = {**_num_s(lm), **_cell_style(v, q1, q2, q3)}
                        if lm in _MILESTONES:
                            style["fontWeight"] = "700"
                    text = _fmt_pct(v)
                else:
                    style = {**_num_s(lm), "background": lbl_bg}
                    text = ""
                cells.append(html.Div(text, className="ct-cell ct-detail-cell", style=style))
            detail_rows.append(html.Div(cells, className="ct-row ct-detail-row"))

        if len(cohorts_in_year) <= 1:
            groups.append(html.Div(
                [html.Div(yr_cells, className="ct-row ct-year-row")] + detail_rows,
                className="ct-group-nodrill",
            ))
        else:
            groups.append(html.Details(
                [
                    html.Summary(year_row, className="ct-summary"),
                    html.Div(detail_rows, className="ct-detail-body"),
                ],
                className="ct-group",
            ))

    # ── Filas de promedio ─────────────────────────────────────────────────────
    def _avg_row_r(label: str, avgs: dict, bg: str, fg: str,
                   meta1: str = "—") -> html.Div:
        cells = [
            html.Div(label, className="ct-cell",
                     style=_lbl_s({"background": bg, "color": fg, "fontWeight": "700"})),
            _meta_cell(meta1, bg=bg, fg=fg, bold=True),
        ]
        for lm in all_lm:
            v = avgs.get(lm)
            text = _fmt_pct(v) if v is not None else "—"
            ms_fg = "#00C97A" if lm in _MILESTONES else fg
            cells.append(html.Div(text, className="ct-cell", style={
                **_num_s(lm),
                "background": bg, "color": ms_fg, "fontWeight": "700",
            }))
        return html.Div(cells, className="ct-row")

    n_excl = len(deselected)
    arith_lbl = f"Avg Aritmético (excl. {n_excl} año{'s' if n_excl != 1 else ''})" if n_excl else "Avg Aritmético"
    row_simple   = _avg_row_r(arith_lbl, simple_ratio_avgs, "#E8E2F8", "#1A1659")
    row_weighted = _avg_row_r(
        "Avg Ponderado", weighted_ratio_avgs, "#4827BE", "#ffffff",
        meta1=f"{total_weight:,.0f}",
    )

    table = html.Div(
        html.Div([header, *groups, row_simple, row_weighted], className="ct-table"),
        className="ct-wrap",
    )

    _fc_legend = []
    if fc_mask is not None and bool(fc_mask.values.any()):
        _fc_legend = [html.Div([
            html.Span("", style={
                "display": "inline-block", "width": "11px", "height": "11px",
                "background": _FC_BG, "border": f"1.5px solid {_FC_FG}",
                "borderRadius": "2px", "verticalAlign": "middle",
                "marginRight": "5px",
            }),
            html.Span("Forecast", style={
                "color": _FC_FG, "fontSize": "11px", "verticalAlign": "middle",
            }),
        ], style={"padding": "0 0 6px 0"})]

    return html.Div([
        html.H3(title, className="section-title"),
        *_fc_legend,
        table,
    ], className="page-section card")


# ── Callback principal — carga datos y construye tablas raw + smooth ──────────

@callback(
    Output("ndr-year-select", "options"),
    Output("ndr-year-select", "value"),
    Output("ndr-table",       "children"),
    Output("ndr-store",       "data"),
    Input("ndr-metric",    "value"),
    Input("ndr-pais",      "value"),
    Input("ndr-moneda",    "value"),
    Input("ndr-fx-cop",    "value"),
    Input("ndr-fx-mxn",    "value"),
    Input("ndr-segmentos", "value"),
    Input("ndr-churn",     "value"),
    Input("ndr-forecast",  "value"),
    Input("url",           "pathname"),
    State("cohort-overrides", "data"),
    State("ndr-year-select", "value"),
    prevent_initial_call=False,
)
def update_ndr(metric, pais, moneda, fx_cop, fx_mxn, segmentos, churn, forecast_on, pathname, cohort_overrides, current_years):
    if pathname != "/ndr":
        raise PreventUpdate

    metric = metric or "orders"
    is_rev = metric == "revenue"

    filters = build_filters(pais, segmentos, churn, None)

    if is_rev:
        df_raw  = load_revenue(filters)
        df_raw  = apply_cohort_overrides(df_raw, cohort_overrides, "revenue_month")
        df_raw  = prepare_revenue(df_raw, pais, moneda, fx_cop, fx_mxn)
        val_col = "display_value"
        unit    = revenue_display_unit(pais, moneda)
        val_lbl = f"Revenue ({unit})"
    else:
        df_raw  = load_orders(filters)
        df_raw  = apply_cohort_overrides(df_raw, cohort_overrides, "order_month")
        val_col = "order_count"
        unit    = ""
        val_lbl = "Órdenes"

    _empty_ui = html.Div(
        [html.P("Sin datos.", className="placeholder-hint")],
        className="placeholder-box",
    )

    if df_raw.empty:
        return [], [], _empty_ui, None

    # Excluir el mes actual (dato incompleto — todavía no ha cerrado)
    _today = pd.Timestamp.today().replace(day=1).normalize()
    df_raw = df_raw.copy()
    df_raw["cohort_month"] = pd.to_datetime(df_raw["cohort_month"])
    df_raw["_max_lm"] = (
        (_today.year  - df_raw["cohort_month"].dt.year)  * 12
        + (_today.month - df_raw["cohort_month"].dt.month)
    )
    df_raw = df_raw[df_raw["lifecycle_month"] <= df_raw["_max_lm"]].drop(columns=["_max_lm"])

    if df_raw.empty:
        return [], [], _empty_ui, None

    # Shift lifecycle_month: M0 = acquisition month, M1 = first full month, ...
    df_raw = df_raw.copy()
    df_raw["lifecycle_month"] = df_raw["lifecycle_month"] - 1

    # Raw pivot (actuals only — para tabla "Sin suavizar")
    raw_pivot = (
        df_raw.groupby(["cohort_month", "lifecycle_month"])[val_col]
        .sum()
        .unstack("lifecycle_month")
    )
    raw_pivot.index = pd.to_datetime(raw_pivot.index)
    raw_pivot.columns = [int(c) for c in raw_pivot.columns]

    # Máximo lifecycle_month actual por cohorte (antes de extender con forecast)
    actual_max_lm = df_raw.groupby("cohort_month")["lifecycle_month"].max()
    actual_max_lm.index = pd.to_datetime(actual_max_lm.index)

    # Extender con forecast (solo ODR — forecast solo cubre órdenes)
    forecast_on = forecast_on or "no"
    forecast_active = (forecast_on == "si") and not is_rev
    df_combined = df_raw
    fc_agg = pd.DataFrame()        # forecast agregado por cohorte × lm
    df_fc_sellers = pd.DataFrame() # forecast con seller_name para drill-down

    if forecast_active:
        df_fc = load_forecast(filters)
        if not df_fc.empty:
            df_fc = apply_cohort_overrides(df_fc, cohort_overrides, "forecast_month")
            df_fc = df_fc.copy()
            df_fc["cohort_month"] = pd.to_datetime(df_fc["cohort_month"])
            df_fc["lifecycle_month"] = df_fc["lifecycle_month"] - 1
            df_fc = df_fc[df_fc["lifecycle_month"] >= 1]
            df_fc = df_fc[df_fc["cohort_month"].isin(actual_max_lm.index)]
            df_fc = df_fc.merge(
                actual_max_lm.rename("_max_lm"),
                left_on="cohort_month", right_index=True,
                how="left",
            )
            df_fc = df_fc[df_fc["lifecycle_month"] > df_fc["_max_lm"]].drop(columns=["_max_lm"])
            if not df_fc.empty:
                fc_agg = (
                    df_fc.groupby(["cohort_month", "lifecycle_month"])["forecasted_orders"]
                    .sum()
                    .reset_index()
                    .rename(columns={"forecasted_orders": val_col})
                )
                # Seller names desde actuals para el drill-down
                _seller_nm = (
                    df_raw.drop_duplicates("seller_id")
                    .set_index("seller_id")["seller_name"]
                )
                _fc_s = df_fc.copy()
                _fc_s["seller_name"] = (
                    _fc_s["seller_id"].map(_seller_nm)
                    .fillna(_fc_s["seller_id"].astype(str))
                )
                _fc_s = _fc_s.rename(columns={"forecasted_orders": val_col})
                df_fc_sellers = _fc_s[
                    ["cohort_month", "seller_id", "seller_name", "lifecycle_month", val_col]
                ]
                df_combined = pd.concat(
                    [df_raw[["cohort_month", "lifecycle_month", val_col]], fc_agg],
                    ignore_index=True,
                )

    smooth_df, weights = calc_cohort_matrix(df_combined, val_col)

    # Máscara forecast para smooth: True donde lm > último real del cohorte
    fc_mask = pd.DataFrame(False, index=smooth_df.index, columns=smooth_df.columns)
    if forecast_active and not smooth_df.empty:
        for cohort_ts in smooth_df.index:
            max_lm = int(actual_max_lm.get(pd.Timestamp(cohort_ts), 0) or 0)
            fc_mask.loc[cohort_ts, [lm for lm in smooth_df.columns if int(lm) > max_lm]] = True

    # Raw pivot para display (actuals + forecast cuando está activo)
    if not fc_agg.empty:
        _raw_disp = pd.concat(
            [df_raw[["cohort_month", "lifecycle_month", val_col]], fc_agg],
            ignore_index=True,
        )
        raw_pivot_display = (
            _raw_disp.groupby(["cohort_month", "lifecycle_month"])[val_col]
            .sum()
            .unstack("lifecycle_month")
        )
        raw_pivot_display.index = pd.to_datetime(raw_pivot_display.index)
        raw_pivot_display.columns = [int(c) for c in raw_pivot_display.columns]
    else:
        raw_pivot_display = raw_pivot

    # Máscara forecast para tabla raw (mismo criterio)
    fc_mask_raw = pd.DataFrame(False, index=raw_pivot_display.index, columns=raw_pivot_display.columns)
    if forecast_active and not raw_pivot_display.empty:
        for cohort_ts in raw_pivot_display.index:
            max_lm = int(actual_max_lm.get(pd.Timestamp(cohort_ts), 0) or 0)
            fc_mask_raw.loc[cohort_ts, [lm for lm in raw_pivot_display.columns if int(lm) > max_lm]] = True

    if smooth_df.empty:
        return [], [], _empty_ui, None

    all_lm = sorted(
        set(smooth_df.columns.tolist())
        | set(raw_pivot_display.columns.tolist())
        | set(raw_pivot.columns.tolist())
    )

    # ── Etiquetas de unidad para títulos de tablas ────────────────────────────
    unit_sfx = f" — {unit}" if is_rev else ""   # ej. " — MM COP" o "" para órdenes

    # ── Determinar años activos por defecto ───────────────────────────────────
    weights_ts = weights.copy()
    weights_ts.index = pd.to_datetime(weights_ts.index)
    year_weights_s = weights_ts.groupby(weights_ts.index.year).sum()

    threshold = _MIN_YEAR_WEIGHT_BY_UNIT.get(unit, 100.0)
    year_options = [{"label": str(y), "value": str(y)}
                    for y in sorted(year_weights_s.index)]
    default_values = [str(y) for y, w in year_weights_s.items()
                      if float(w) >= threshold]

    # Si es carga inicial (url trigger) o no había selección previa → defaults
    # Si el usuario ya había interactuado → preservar su selección
    triggered = ctx.triggered_id if ctx.triggered else "url"
    if triggered == "url" or not current_years:
        year_values = default_values
    else:
        available = {opt["value"] for opt in year_options}
        preserved = [y for y in current_years if y in available]
        year_values = preserved if preserved else default_values

    # ── Construir tablas raw y suavizado ──────────────────────────────────────
    if not df_fc_sellers.empty:
        _df_for_sellers = pd.concat([
            df_raw[["cohort_month", "seller_id", "seller_name", "lifecycle_month", val_col]],
            df_fc_sellers,
        ], ignore_index=True)
        seller_data = _compute_seller_data(_df_for_sellers, val_col, top_n=5)
    else:
        seller_data = _compute_seller_data(df_raw, val_col, top_n=5)
    heatmap_raw = _build_heatmap(
        raw_pivot_display, {}, {}, all_lm, is_rev,
        title=f"Sin suavizar{unit_sfx}",
        seller_data=seller_data,
        fc_mask=fc_mask_raw if forecast_active else None,
    )
    abs_title = (
        f"Suavizado forward 3m + Forecast{unit_sfx}"
        if forecast_active else
        f"Suavizado forward 3m{unit_sfx}"
    )
    heatmap_abs = _build_heatmap(
        smooth_df, {}, {}, all_lm, is_rev,
        title=abs_title,
        fc_mask=fc_mask if forecast_active else None,
    )

    # ── Serializar datos para ratio section y exportación ────────────────────
    smooth_serial = smooth_df.copy()
    smooth_serial.index = smooth_serial.index.astype(str)
    weights_serial = weights.copy()
    weights_serial.index = weights_serial.index.astype(str)
    raw_serial = raw_pivot.copy()
    raw_serial.index = raw_serial.index.astype(str)

    fc_mask_data: dict = {}
    if forecast_active and not fc_mask.empty:
        _fm = fc_mask.copy()
        _fm.index = _fm.index.astype(str)
        fc_mask_data = _fm.to_dict()

    store = {
        "smooth":           smooth_serial.to_dict(),
        "raw":              raw_serial.to_dict(),
        "weights":          weights_serial.to_dict(),
        "all_lm":           all_lm,
        "is_rev":           is_rev,
        "metric":           metric,
        "pais":             pais or "CONSOLIDADO",
        "unit":             unit,
        "forecast_active":  forecast_active,
        "fc_mask":          fc_mask_data,
    }

    return year_options, year_values, html.Div([heatmap_raw, heatmap_abs]), store


# ── Callback ratio — reacciona al store y a la selección de años ──────────────

@callback(
    Output("ndr-chart-container", "children"),
    Output("ndr-averages",        "children"),
    Output("ndr-ratio-section",   "children"),
    Input("ndr-store",       "data"),
    Input("ndr-year-select", "value"),
    prevent_initial_call=False,
)
def update_ratio_section(store, selected_years):
    if not store:
        raise PreventUpdate

    smooth_df, raw_pivot, weights, all_lm, is_rev, fc_mask = _store_to_smooth(store)
    metric = store.get("metric", "orders")
    pais   = store.get("pais",   "CONSOLIDADO")
    unit   = store.get("unit",   "")

    smooth_ts  = smooth_df.copy()
    smooth_ts.index = pd.to_datetime(smooth_ts.index)
    weights_ts = weights.copy()
    weights_ts.index = pd.to_datetime(weights_ts.index)

    all_years = set(int(y) for y in smooth_ts.index.year.unique())

    # Años seleccionados (values son strings)
    selected_set = set(int(y) for y in (selected_years or []))
    deselected   = all_years - selected_set

    # Filtrar smooth y weights a años seleccionados
    if selected_set:
        mask         = smooth_ts.index.year.isin(selected_set)
        smooth_sel   = smooth_ts[mask]
        weights_sel  = weights_ts[weights_ts.index.year.isin(selected_set)]
    else:
        # Nada seleccionado: sin datos de ratio
        smooth_sel  = smooth_ts.iloc[0:0]
        weights_sel = weights_ts.iloc[0:0]

    # ── Recalcular promedios de ratio en base a años activos ─────────────────
    simple_ratio_avgs   = {}
    weighted_ratio_avgs = {}
    if not smooth_sel.empty and 1 in smooth_sel.columns:
        ratio_df_sel = smooth_sel.div(smooth_sel[1], axis=0)
        for lm in all_lm:
            if lm not in ratio_df_sel.columns:
                continue
            col_all = ratio_df_sel[lm].dropna()
            if col_all.empty:
                continue
            simple_ratio_avgs[lm] = float(col_all.mean())
            w     = weights_sel.reindex(col_all.index).fillna(0.0)
            w_sum = float(w.sum())
            weighted_ratio_avgs[lm] = (
                float((col_all * w).sum() / w_sum) if w_sum > 0 else float(col_all.mean())
            )

    # ── Construir chart, promedios y tabla ratio ──────────────────────────────
    chart    = _build_chart(simple_ratio_avgs, weighted_ratio_avgs, metric, pais, fc_mask=fc_mask)
    averages = _build_averages_table(simple_ratio_avgs, weighted_ratio_avgs, all_lm, metric, pais)

    tipo     = _TIPO_LBL.get(metric, "ODR")
    geo      = _GEO_LBL.get(pais, pais)
    heatmap_ratio = _build_ratio_heatmap(
        smooth_df,
        weights,
        simple_ratio_avgs,
        weighted_ratio_avgs,
        all_lm,
        title=f"Ratios {tipo} — {geo} (Mn / M1)",
        deselected_years=deselected,
        fc_mask=fc_mask,
    )

    return chart, averages, heatmap_ratio


# ── Exportación a Excel ───────────────────────────────────────────────────────

def _store_to_smooth(
    store: dict,
) -> "tuple[pd.DataFrame, pd.DataFrame, pd.Series, list, bool, pd.DataFrame | None]":
    """Reconstruye smooth_df, raw_pivot, weights, all_lm, is_rev, fc_mask desde el store."""
    smooth_df = pd.DataFrame(store["smooth"])
    smooth_df.index = pd.to_datetime(smooth_df.index)
    smooth_df.columns = [int(c) for c in smooth_df.columns]

    raw_pivot = pd.DataFrame(store.get("raw", {}))
    if not raw_pivot.empty:
        raw_pivot.index = pd.to_datetime(raw_pivot.index)
        raw_pivot.columns = [int(c) for c in raw_pivot.columns]

    weights = pd.Series(store["weights"])
    weights.index = pd.to_datetime(weights.index)

    all_lm = [int(x) for x in store["all_lm"]]
    is_rev = store["is_rev"]

    fc_mask = None
    if store.get("forecast_active") and store.get("fc_mask"):
        _fm = pd.DataFrame(store["fc_mask"])
        if not _fm.empty:
            _fm.index = pd.to_datetime(_fm.index)
            _fm.columns = [int(c) for c in _fm.columns]
            fc_mask = _fm

    return smooth_df, raw_pivot, weights, all_lm, is_rev, fc_mask


def _df_to_excel(buf: io.BytesIO, sheets: "dict[str, pd.DataFrame]") -> None:
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)


@callback(
    Output("ndr-download", "data"),
    Input("ndr-btn-export", "n_clicks"),
    State("ndr-store",       "data"),
    State("ndr-year-select", "value"),
    prevent_initial_call=True,
)
def export_ndr(n_clicks, store, selected_years):
    """Exporta un Excel con tres hojas: Raw, Absolutos (suavizado) y Ratios NDR-ODR."""
    if not store:
        raise PreventUpdate

    smooth_df, raw_pivot, weights, all_lm, is_rev, _fc_mask = _store_to_smooth(store)
    smooth_df.index = pd.to_datetime(smooth_df.index)
    weights.index   = pd.to_datetime(weights.index)

    def _build_flat_rows(df: pd.DataFrame, lms: list, round_int: bool) -> list:
        rows = []
        for ts in sorted(df.index):
            row = {"Año": ts.year, "Mes": ts.strftime("%b"), "Cohorte": ts.strftime("%b %Y")}
            for lm in lms:
                v = df.loc[ts, lm] if lm in df.columns else None
                if v is not None and not np.isnan(v):
                    row[f"M{lm}"] = round(v) if round_int else v
                else:
                    row[f"M{lm}"] = None
            rows.append(row)
        return rows

    # ── Hoja 1: Raw ───────────────────────────────────────────────────────────
    df_raw_exp = (
        pd.DataFrame(_build_flat_rows(raw_pivot, all_lm, round_int=True))
        if not raw_pivot.empty else pd.DataFrame()
    )

    # ── Hoja 2: Absolutos (suavizados) ───────────────────────────────────────
    df_abs = pd.DataFrame(_build_flat_rows(smooth_df, all_lm, round_int=True))

    # ── Hoja 3: Ratios (usando años seleccionados) ────────────────────────────
    if 1 not in smooth_df.columns:
        sheets = {"Raw": df_raw_exp, "Absolutos": df_abs}
    else:
        smooth_ts  = smooth_df.copy()
        weights_ts = weights.copy()

        selected_set = set(int(y) for y in (selected_years or []))
        if selected_set:
            mask        = smooth_ts.index.year.isin(selected_set)
            smooth_sel  = smooth_ts[mask]
            weights_sel = weights_ts[weights_ts.index.year.isin(selected_set)]
        else:
            smooth_sel  = smooth_ts.iloc[0:0]
            weights_sel = weights_ts.iloc[0:0]

        # Ratio promedios
        s_ratio: dict = {}
        w_ratio: dict = {}
        if not smooth_sel.empty and 1 in smooth_sel.columns:
            ratio_sel = smooth_sel.div(smooth_sel[1], axis=0)
            for lm in all_lm:
                if lm not in ratio_sel.columns:
                    continue
                col_all = ratio_sel[lm].dropna()
                if col_all.empty:
                    continue
                s_ratio[lm] = float(col_all.mean())
                w     = weights_sel.reindex(col_all.index).fillna(0.0)
                w_sum = float(w.sum())
                w_ratio[lm] = (
                    float((col_all * w).sum() / w_sum) if w_sum > 0 else float(col_all.mean())
                )

        ratio_df     = smooth_df.div(smooth_df[1], axis=0)
        total_weight = float(weights_ts[weights_ts.index.year.isin(selected_set)].sum()) if selected_set else 0.0

        ratio_rows = []
        for ts in sorted(ratio_df.index):
            c_w = float(weights.get(ts, 0.0))
            is_active = ts.year in selected_set
            row = {
                "Año": ts.year, "Mes": ts.strftime("%b"), "Cohorte": ts.strftime("%b %Y"),
                "Σ M1-M12": round(c_w),
                "Activo": "Sí" if is_active else "No",
            }
            for lm in all_lm:
                v = ratio_df.loc[ts, lm] if lm in ratio_df.columns else None
                row[f"M{lm}"] = round(v * 100, 1) if (v is not None and not np.isnan(v)) else None
            ratio_rows.append(row)

        row_s = {"Año": "", "Mes": "", "Cohorte": "Avg Aritmético", "Σ M1-M12": None, "Activo": ""}
        for lm in all_lm:
            v = s_ratio.get(lm)
            row_s[f"M{lm}"] = round(v * 100, 1) if v is not None else None
        ratio_rows.append(row_s)

        row_w = {"Año": "", "Mes": "", "Cohorte": "Avg Ponderado", "Σ M1-M12": round(total_weight), "Activo": ""}
        for lm in all_lm:
            v = w_ratio.get(lm)
            row_w[f"M{lm}"] = round(v * 100, 1) if v is not None else None
        ratio_rows.append(row_w)

        sheets = {
            "Raw":            df_raw_exp,
            "Absolutos":      df_abs,
            "Ratios NDR-ODR": pd.DataFrame(ratio_rows),
        }

    buf = io.BytesIO()
    _df_to_excel(buf, sheets)
    buf.seek(0)
    return dcc.send_bytes(buf.read(), "ndr_odr_export.xlsx")
