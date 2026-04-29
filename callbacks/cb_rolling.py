"""
Vista: Rolling Forecast Total — Órdenes

Lógica:
  Real:     sum(order_count) por order_month del input de órdenes.
  Forecast: cohortes existentes (con NNO) → NNO × factor_estacional(mes).
            cohortes budget (sin dato real) → budget_NNO × 15% en M1,
            × factor_estacional en M2+.
  Línea de corte = último order_month con datos reales.
"""
import concurrent.futures

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from components.page_filters import rolling_filters
from data.data_loader import load_budget_nnr, load_forecast, load_orders
from data.transforms import (
    apply_cohort_overrides,
    build_filters,
    calc_nno_by_cohort,
)

_GEO_LBL = {"CONSOLIDADO": "Consolidado", "COL": "Colombia", "MEX": "México"}
_COUNTRY_ID = {"COL": 1, "MEX": 2}

_SEASONAL_MONTHS: dict[int, set[int]] = {
    1: {11, 12},
    2: {5, 11, 12},
}
_SFACTOR = 1.4

_W = {
    "lbl":  "140px",
    "st":    "30px",
    "sel":   "60px",
    "real":  "92px",
    "fc":    "92px",
    "tot":   "92px",
    "bud":   "86px",
    "pct":   "68px",
}


# ── Layout ────────────────────────────────────────────────────────────────────

def rolling_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [html.H2("Rolling Forecast Total — Órdenes", className="page-title")],
                className="page-header",
            ),
            rolling_filters(),
            html.Div(id="rf-kpis",            className="kpi-strip"),
            html.Div(id="rf-chart-container",  className="page-section card"),
            html.Div(id="rf-table",            className="page-section"),
        ],
        className="page",
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


def _fmt_ord(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{int(round(val)):,}"


def _fmt_pct(val) -> tuple[str, str]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—", "#6B6B9A"
    return f"{val:+.0%}", "#00C97A" if val >= 0 else "#FF820F"


def _status_icon(status: str) -> html.Span:
    icons = {
        "completo": ("✓", "#00C97A"),
        "parcial":  ("~", "#FF820F"),
        "budget":   ("◎", "#9684E1"),
        "pendiente": ("–", "#AAAAAA"),
    }
    txt, clr = icons.get(status, ("–", "#AAAAAA"))
    return html.Span(txt, title=status,
                     style={"color": clr, "fontWeight": "700", "fontSize": "13px"})


# ── Helpers de cálculo ────────────────────────────────────────────────────────

def _sf(country_id: int, month: int) -> float:
    return _SFACTOR if month in _SEASONAL_MONTHS.get(country_id, set()) else 1.0


def _weighted_sf(month: int, country_weights: dict) -> float:
    """Factor estacional ponderado por cantidad de sellers por país."""
    total = sum(country_weights.values())
    if total == 0:
        return max(_sf(1, month), _sf(2, month))
    return sum(
        country_weights.get(cid, 0) / total * _sf(cid, month)
        for cid in [1, 2]
    )


def _get_bud_nno_by_country(df_bud_raw: pd.DataFrame, cohort_m, bud_col: str, pais: str) -> dict:
    """Devuelve {country_id: budget_nno} para la cohorte dada."""
    if df_bud_raw.empty or bud_col not in df_bud_raw.columns:
        return {}
    rows = df_bud_raw[df_bud_raw["date"] == pd.Timestamp(cohort_m)]
    if rows.empty:
        return {}
    if pais == "CONSOLIDADO":
        return {
            int(cid): float(rows[rows["country_id"] == cid][bud_col].sum())
            for cid in [1, 2]
        }
    cid = _COUNTRY_ID.get(pais, 1)
    return {cid: float(rows[rows["country_id"] == cid][bud_col].sum())}


def _project_budget_cohort(cohort_m, future_months: list, bud_by_country: dict, pais: str) -> float:
    """Proyecta el total de órdenes de una cohorte presupuestada para los future_months."""
    total = 0.0
    for m in future_months:
        if m < cohort_m:
            continue
        for cid, bud_nno in bud_by_country.items():
            if bud_nno <= 0:
                continue
            sf = 0.15 if m == cohort_m else _sf(cid, m.month)
            total += bud_nno * sf
    return total


# ── Cálculo central ───────────────────────────────────────────────────────────

def _compute_data(
    df_ord: pd.DataFrame,
    nno: pd.Series,
    nno_status: pd.Series,
    df_bud_raw: pd.DataFrame,
    df_fc: pd.DataFrame,
    pais: str,
    escenario: str,
    end_month: pd.Timestamp,
    today_m: "pd.Timestamp | None" = None,
    build_detail: bool = True,
):
    """
    Returns:
        real_by_month  : pd.Series (order_month → actual_orders)
        fc_by_month    : pd.Series (calendar_month → projected_orders)
        cutoff         : pd.Timestamp
        cohort_rows    : list[dict]  (vacío si build_detail=False)
    """
    bud_col = f"budget_nno_{escenario}"

    # ── Real orders ───────────────────────────────────────────────────────────
    real_by_month = pd.Series(dtype=float)
    if not df_ord.empty:
        real_by_month = (
            df_ord.groupby("order_month")["order_count"].sum().sort_index()
        )

    if real_by_month.empty:
        return real_by_month, pd.Series(dtype=float), None, []

    cutoff = real_by_month.index.max()
    next_m = cutoff + pd.DateOffset(months=1)
    future_months = pd.date_range(start=next_m, end=end_month, freq="MS").tolist()

    # ── Country weights per cohort (para factor estacional ponderado) ─────────
    cw_by_cohort: dict[pd.Timestamp, dict] = {}
    if pais == "CONSOLIDADO" and not df_ord.empty:
        cw_raw = (
            df_ord.groupby(["cohort_month", "country_id"])["seller_id"]
            .nunique()
            .unstack(fill_value=0)
        )
        cw_raw.index = pd.to_datetime(cw_raw.index)
        for c, row in cw_raw.iterrows():
            cw_by_cohort[pd.Timestamp(c)] = {int(cid): int(cnt) for cid, cnt in row.items()}

    # ── Per-seller NNO y órdenes reales (solo para detalle de tabla) ──────────
    per_seller_nno:  dict[tuple, float] = {}
    per_seller_real: dict[tuple, float] = {}
    seller_names:    dict[int, str]     = {}
    real_by_cohort_cal: dict = {}   # (cohort_m, order_m) → orders
    real_by_seller_cal: dict = {}   # (cohort_m, seller_id, order_m) → orders

    if build_detail and not df_ord.empty:
        # Nombres
        if "seller_name" in df_ord.columns:
            for sid, name in df_ord[["seller_id","seller_name"]].drop_duplicates().values:
                seller_names[int(sid)] = str(name)

        # Real por seller×cohorte
        for (c, s), v in (
            df_ord.groupby(["cohort_month", "seller_id"])["order_count"].sum().items()
        ):
            per_seller_real[(pd.Timestamp(c), int(s))] = float(v)

        # Real por (cohort_month × order_month) — para tabla de meses
        for (c, m), v in df_ord.groupby(["cohort_month", "order_month"])["order_count"].sum().items():
            real_by_cohort_cal[(pd.Timestamp(c), pd.Timestamp(m))] = float(v)
        for (c, s, m), v in df_ord.groupby(["cohort_month", "seller_id", "order_month"])["order_count"].sum().items():
            real_by_seller_cal[(pd.Timestamp(c), int(s), pd.Timestamp(m))] = float(v)

        # NNO por seller (M2/M3 normalizado)
        m23 = df_ord[df_ord["lifecycle_month"].isin([2, 3])].copy()
        if not m23.empty:
            m23["_fac"] = m23.apply(
                lambda r: _sf(int(r["country_id"]), int(r["order_month"].month)), axis=1
            )
            m23["_adj"] = m23["order_count"] / m23["_fac"]
            for (c, s), v in (
                m23.groupby(["cohort_month", "seller_id"])["_adj"].mean().items()
            ):
                per_seller_nno[(pd.Timestamp(c), int(s))] = float(v)

    # ── Forecast desde load_forecast (fuente primaria) ───────────────────────
    fc_acc: dict[pd.Timestamp, float] = {m: 0.0 for m in future_months}

    # Pre-índices para el detalle por cohorte y seller
    fc_by_cohort_idx: dict = {}   # cohort_ts → {forecast_m: total_orders}
    fc_by_seller_idx: dict = {}   # (cohort_ts, seller_id) → {forecast_m: orders}
    cohorts_with_fc:  set  = set()

    if not df_fc.empty:
        _dfc = df_fc.copy()
        _dfc["forecast_month"] = pd.to_datetime(_dfc["forecast_month"])
        _dfc["cohort_month"]   = pd.to_datetime(_dfc["cohort_month"])
        # Cohorte del mes actual: forzar proyección desde budget (no forecast)
        if today_m is not None:
            _dfc = _dfc[_dfc["cohort_month"] != today_m]
        _dfc_fut = _dfc[_dfc["forecast_month"] > cutoff]

        if not _dfc_fut.empty:
            # Total por mes calendario → línea del gráfico
            for fc_m, total in (
                _dfc_fut.groupby("forecast_month")["forecasted_orders"].sum().items()
            ):
                m_ts = pd.Timestamp(fc_m)
                if m_ts in fc_acc:
                    fc_acc[m_ts] += float(total)

            # Por cohorte × mes calendario
            for (c, fc_m), v in (
                _dfc_fut.groupby(["cohort_month", "forecast_month"])["forecasted_orders"]
                .sum().items()
            ):
                c_ts = pd.Timestamp(c)
                m_ts = pd.Timestamp(fc_m)
                if c_ts not in fc_by_cohort_idx:
                    fc_by_cohort_idx[c_ts] = {}
                fc_by_cohort_idx[c_ts][m_ts] = float(v)
                cohorts_with_fc.add(c_ts)

            # Por seller × mes calendario
            if "seller_id" in _dfc_fut.columns:
                for (c, s, fc_m), v in (
                    _dfc_fut.groupby(["cohort_month", "seller_id", "forecast_month"])
                    ["forecasted_orders"].sum().items()
                ):
                    key = (pd.Timestamp(c), int(s))
                    if key not in fc_by_seller_idx:
                        fc_by_seller_idx[key] = {}
                    fc_by_seller_idx[key][pd.Timestamp(fc_m)] = float(v)

    # ── Cohortes budget (futuras sin forecast en el DB) ───────────────────────
    last_status_m = (
        pd.Timestamp(nno_status.index.max()) if not nno_status.empty else cutoff
    )
    budget_cohort_start = last_status_m + pd.DateOffset(months=1)
    budget_cohort_months = pd.date_range(
        start=budget_cohort_start, end=end_month, freq="MS"
    )

    budget_only_cohorts: set = set()  # cohortes del mes actual sin orders ni forecast

    for cohort_m in budget_cohort_months:
        c_ts = pd.Timestamp(cohort_m)
        if c_ts in cohorts_with_fc:
            continue  # ya cubierto por load_forecast
        bud_by_cty = _get_bud_nno_by_country(df_bud_raw, cohort_m, bud_col, pais)
        if not bud_by_cty or not any(v > 0 for v in bud_by_cty.values()):
            continue  # sin dato presupuestado, omitir

        budget_only_cohorts.add(c_ts)
        if c_ts not in fc_by_cohort_idx:
            fc_by_cohort_idx[c_ts] = {}

        for m in future_months:
            if m < cohort_m:
                continue
            m_total = 0.0
            for cid, bud_nno in bud_by_cty.items():
                if bud_nno <= 0:
                    continue
                sf = 0.15 if m == cohort_m else _sf(cid, m.month)
                m_total += bud_nno * sf
            if m_total > 0:
                fc_acc[m] += m_total
                fc_by_cohort_idx[c_ts][m] = (
                    fc_by_cohort_idx[c_ts].get(m, 0.0) + m_total
                )

    fc_by_month = pd.Series(fc_acc).sort_index() if fc_acc else pd.Series(dtype=float)

    if not build_detail:
        return real_by_month, fc_by_month, cutoff, []

    # ── Detalle por cohorte (para la tabla) ───────────────────────────────────
    cohort_rows = []

    all_cohorts = sorted(set(
        [pd.Timestamp(c) for c in nno.index]
        + [pd.Timestamp(c) for c in nno_status.index]
        + list(cohorts_with_fc)
        + list(budget_only_cohorts)   # cohortes del mes corriente sin órdenes
    ))

    for cohort_m in all_cohorts:
        if cohort_m in budget_only_cohorts:
            st = "budget"
        else:
            st = str(nno_status.get(cohort_m, "pendiente"))

        if not df_ord.empty:
            coh_df   = df_ord[df_ord["cohort_month"] == cohort_m]
            sellers  = int(coh_df["seller_id"].nunique()) if not coh_df.empty else 0
            real_ord = float(coh_df["order_count"].sum())
        else:
            sellers  = 0
            real_ord = 0.0

        # Forecast desde load_forecast
        fc_month_data = fc_by_cohort_idx.get(cohort_m, {})
        fc_ord = sum(fc_month_data.values())

        # Budget NNO (referencia)
        bud_by_cty = _get_bud_nno_by_country(df_bud_raw, cohort_m, bud_col, pais)
        bud_nno = sum(bud_by_cty.values()) if bud_by_cty else np.nan
        if isinstance(bud_nno, float) and bud_nno == 0.0:
            bud_nno = np.nan

        total_ord = real_ord + fc_ord
        vs_pct = (
            total_ord / bud_nno - 1
            if not np.isnan(bud_nno) and bud_nno > 0 else np.nan
        )

        # Sellers drill-down
        s_ids = {s for (c, s) in per_seller_real if c == cohort_m}
        s_ids |= {s for (c, s) in fc_by_seller_idx if c == cohort_m}
        seller_rows = []
        for s_id in sorted(s_ids):
            s_real = per_seller_real.get((cohort_m, s_id), 0.0)
            s_fc_months = fc_by_seller_idx.get((cohort_m, s_id), {})
            s_fc = sum(s_fc_months.values())
            s_md: dict = {
                m: v for (c, s, m), v in real_by_seller_cal.items()
                if c == cohort_m and s == s_id
            }
            s_md.update(s_fc_months)
            seller_rows.append({
                "seller_id":   s_id,
                "seller_name": seller_names.get(s_id, str(s_id)),
                "real":        s_real,
                "fc":          s_fc,
                "total":       s_real + s_fc,
                "month_data":  s_md,
            })

        # month_data: reales + forecast
        _cmd: dict = {
            m: v for (c, m), v in real_by_cohort_cal.items() if c == cohort_m
        }
        _cmd.update(fc_month_data)

        cohort_rows.append({
            "cohort_month": cohort_m,
            "status":       st,
            "sellers":      sellers,
            "real":         real_ord,
            "fc":           fc_ord,
            "total":        total_ord,
            "budget_nno":   bud_nno,
            "vs_pct":       vs_pct,
            "month_data":   _cmd,
            "seller_rows":  seller_rows,
        })

    cohort_rows.sort(key=lambda r: r["cohort_month"])
    return real_by_month, fc_by_month, cutoff, cohort_rows


# ── Sección: KPIs ─────────────────────────────────────────────────────────────

def _build_kpis(geo_results: list) -> list:
    """geo_results: list of (label, v25, v26) tuples — one per geography."""
    cards = []
    for lbl, v25, v26 in geo_results:
        if v25 and v26 and v25 > 0:
            yoy     = (v26 / v25) - 1
            pct_txt = f"{yoy:+.1%}"
            variant = "primary" if yoy >= 0 else "naranja"
            sub     = f"Fc: {int(round(v26/1000)):,}K  vs  Dic '25: {int(round(v25/1000)):,}K"
        else:
            pct_txt = "—"
            variant = "muted"
            sub     = "Sin datos"
        cards.append(_kpi_card(f"Dic '26 YoY — {lbl}", pct_txt, sub, variant))
    return cards


# ── Sección: Gráfico ──────────────────────────────────────────────────────────

def _build_chart(real_by_month, fc_by_month, cutoff, pais, escenario, end_month=None):
    geo_lbl = _GEO_LBL.get(pais, pais)
    esc_lbl = 'Base ("Junta")' if escenario == "base" else "Bear"

    fig = go.Figure()

    def _k(v):
        return f"<b>{int(round(v / 1000)):,}K</b>"

    # Calcular offset vertical (5% del máximo) para separar etiquetas de la línea
    all_vals = []
    if not real_by_month.empty:
        all_vals.extend(real_by_month.values)
    if not fc_by_month.empty:
        all_vals.extend(fc_by_month.values)
    y_max  = max(all_vals) if all_vals else 1
    y_pad  = y_max * 0.05

    # Real line + etiquetas elevadas
    if not real_by_month.empty:
        rxs = list(real_by_month.index)
        rys = list(real_by_month.values)
        fig.add_trace(go.Scatter(
            x=rxs, y=rys,
            name="Real",
            mode="lines+markers",
            line=dict(color="#4827BE", width=2.5),
            marker=dict(size=6, color="#4827BE"),
            hovertemplate="%{x|%b %Y}<br>Real: <b>%{y:,.0f}</b><extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=rxs, y=[v + y_pad for v in rys],
            mode="text",
            text=[_k(v) for v in rys],
            texttemplate="%{text}",
            textposition="middle center",
            textfont=dict(size=11, color="#4827BE"),
            cliponaxis=False,
            showlegend=False,
            hoverinfo="skip",
        ))

    # Forecast line + etiquetas elevadas (solo K)
    if not fc_by_month.empty and cutoff is not None:
        bridge_x = [cutoff] + list(fc_by_month.index)
        bridge_y = (
            [float(real_by_month[cutoff])] + list(fc_by_month.values)
            if cutoff in real_by_month.index
            else list(fc_by_month.values)
        )
        label_xs = list(fc_by_month.index)
        label_ys = list(fc_by_month.values)

        fig.add_trace(go.Scatter(
            x=bridge_x, y=bridge_y,
            name=f"Forecast ({esc_lbl})",
            mode="lines+markers",
            line=dict(color="#FF820F", width=2.5, dash="dash"),
            marker=dict(size=6, color="#FF820F"),
            hovertemplate="%{x|%b %Y}<br>Forecast: <b>%{y:,.0f}</b><extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=label_xs, y=[v + y_pad for v in label_ys],
            mode="text",
            text=[_k(v) for v in label_ys],
            texttemplate="%{text}",
            textposition="middle center",
            textfont=dict(size=11, color="#FF820F"),
            cliponaxis=False,
            showlegend=False,
            hoverinfo="skip",
        ))

    # Línea vertical en el corte
    if cutoff is not None:
        fig.add_vline(
            x=cutoff.timestamp() * 1000,
            line_width=1.5, line_dash="dot", line_color="#AAAAAA",
            annotation_text="Corte real",
            annotation_position="top right",
            annotation_font_size=10,
            annotation_font_color="#888888",
        )

    _tick_months = pd.date_range("2025-01-01", "2026-12-01", freq="MS")
    fig.update_layout(
        xaxis=dict(
            title=None,
            tickmode="array",
            tickvals=list(_tick_months),
            ticktext=[m.strftime("%b %Y") for m in _tick_months],
            tickangle=-45,
            tickfont=dict(size=10),
            gridcolor="#f0f0f0",
            range=[
                "2024-12-15",
                (end_month + pd.DateOffset(months=1)).strftime("%Y-%m-%d")
                if end_month else "2027-01-15",
            ],
        ),
        yaxis=dict(title="Órdenes", gridcolor="#f5f5f5",
                   range=[0, y_max * 1.20]),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=100, b=80),
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    title = f"Rolling Forecast — {geo_lbl}"
    return html.Div([
        html.H3(title, className="section-title"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ])


# ── Sección: Tabla ────────────────────────────────────────────────────────────

def _build_table(cohort_rows: list, escenario: str, col_months: list, cutoff) -> html.Div:
    if not cohort_rows:
        return html.Div(html.P("Sin datos.", className="placeholder-hint"))

    _LBL = "140px"
    _ST  = "30px"
    _MW  = "68px"   # ancho por mes
    _TOT = "80px"

    def _hc(text, w, align="right", bg="#1A1659"):
        return html.Div(text, className="ct-cell ct-header-cell", style={
            "minWidth": w, "maxWidth": w, "textAlign": align,
            "background": bg, "color": "#fff",
            "whiteSpace": "pre", "lineHeight": "1.2",
            "padding": "4px 5px", "fontSize": "11px",
        })

    def _lc(text, bg="#fff", fg="#1A1659", bold=False, expandable=False):
        cls = "ct-cell ct-year-label" if expandable else "ct-cell"
        return html.Div(text, className=cls, style={
            "minWidth": _LBL, "maxWidth": _LBL,
            "background": bg, "color": fg,
            "fontWeight": "700" if bold else "400",
            "textAlign": "left",
            "position": "sticky", "left": "0", "zIndex": "1",
        })

    def _nc(val, w, bg="#fff", fg="#1A1659", bold=False):
        txt = _fmt_ord(val) if (val is not None and not (isinstance(val, float) and np.isnan(val)) and val > 0) else "—"
        return html.Div(txt, className="ct-cell", style={
            "minWidth": w, "maxWidth": w, "textAlign": "right",
            "background": bg, "color": fg,
            "fontWeight": "700" if bold else "400",
            "fontSize": "12px",
        })

    def _month_cell(val, m, bg="#fff", fg="#1A1659", bold=False):
        is_past = (m <= cutoff) if cutoff else True
        cell_bg = bg if is_past else (
            "#FFF9F4" if bg in ("#fff", "#F8F6FE", "#FDFCFF") else bg
        )
        txt = _fmt_ord(val) if (val is not None and val > 0) else "—"
        return html.Div(txt, className="ct-cell", style={
            "minWidth": _MW, "maxWidth": _MW, "textAlign": "right",
            "background": cell_bg, "color": fg,
            "fontWeight": "700" if bold else "400",
            "fontSize": "12px",
        })

    # ── Header de meses ───────────────────────────────────────────────────────
    month_hdrs = []
    for m in col_months:
        is_past = (m <= cutoff) if cutoff else True
        bg = "#1A1659" if is_past else "#7059B0"
        month_hdrs.append(html.Div(
            m.strftime("%b\n'%y"),
            className="ct-cell ct-header-cell",
            style={
                "minWidth": _MW, "maxWidth": _MW, "textAlign": "right",
                "background": bg, "color": "#fff",
                "whiteSpace": "pre", "lineHeight": "1.2",
                "padding": "4px 4px", "fontSize": "11px",
            },
        ))

    header = html.Div([
        _hc("Cohorte", _LBL, "left"),
        _hc("",        _ST),
        *month_hdrs,
        _hc("Total",   _TOT),
    ], className="ct-row ct-header-row", style={"minHeight": "42px"})

    # ── Helpers de agregación ─────────────────────────────────────────────────

    def _agg_md(rows):
        agg: dict = {}
        for r in rows:
            for m, v in r.get("month_data", {}).items():
                agg[m] = agg.get(m, 0.0) + v
        return agg

    def _month_cells(md, bg="#fff", fg="#1A1659", bold=False):
        return [_month_cell(md.get(m), m, bg=bg, fg=fg, bold=bold) for m in col_months]

    def _agg_row(rows, label, bg="#fff", lbl_bg=None, fg="#1A1659",
                 bold=False, expandable=False):
        lb   = lbl_bg or bg
        amd  = _agg_md(rows)
        tot  = sum(amd.values())
        return html.Div([
            _lc(label, bg=lb, fg=fg, bold=bold, expandable=expandable),
            html.Div("", className="ct-cell",
                     style={"minWidth": _ST, "maxWidth": _ST, "background": lb}),
            *_month_cells(amd, bg=bg, fg=fg, bold=bold),
            _nc(tot, _TOT, bg=bg, fg=fg, bold=bold),
        ], className="ct-row ct-detail-row")

    def _cohort_row_html(row):
        bg  = "#F8F6FE"
        md  = row.get("month_data", {})
        tot = sum(md.values())
        has_sellers = bool(row["seller_rows"])
        label = row["cohort_month"].strftime("%b %Y")

        st_cell = html.Div(
            _status_icon(row["status"]),
            className="ct-cell",
            style={"minWidth": _ST, "maxWidth": _ST,
                   "textAlign": "center", "background": bg},
        )

        main = html.Div([
            _lc(label, bg=bg, expandable=has_sellers),
            st_cell,
            *_month_cells(md, bg=bg),
            _nc(tot, _TOT, bg=bg),
        ], className="ct-row ct-detail-row")

        if not has_sellers:
            return html.Div([main], className="ct-group-nodrill")

        s_rows_html = []
        for sr in row["seller_rows"]:
            sb   = "#FDFCFF"
            s_md = sr.get("month_data", {})
            s_tot = sum(s_md.values())
            s_rows_html.append(html.Div([
                html.Div(
                    sr["seller_name"],
                    className="ct-cell",
                    style={
                        "minWidth": _LBL, "maxWidth": _LBL,
                        "paddingLeft": "36px", "textAlign": "left",
                        "fontSize": "11px", "color": "#6B6B9A",
                        "background": sb, "position": "sticky", "left": "0", "zIndex": "1",
                    },
                ),
                html.Div("", className="ct-cell",
                         style={"minWidth": _ST, "maxWidth": _ST, "background": sb}),
                *_month_cells(s_md, bg=sb, fg="#888"),
                _nc(s_tot, _TOT, bg=sb, fg="#555", bold=True),
            ], className="ct-row"))

        return html.Details([
            html.Summary(main, className="ct-summary"),
            html.Div(s_rows_html, className="ct-detail-body"),
        ], className="ct-group")

    # ── Agrupar Año → Q → Mes ─────────────────────────────────────────────────
    from collections import defaultdict
    by_year: dict = defaultdict(lambda: defaultdict(list))
    for row in cohort_rows:
        y = row["cohort_month"].year
        q = (row["cohort_month"].month - 1) // 3 + 1
        by_year[y][q].append(row)

    groups = []
    open_year = pd.Timestamp.today().year

    for year in sorted(by_year.keys()):
        yr_flat = [r for q_rows in by_year[year].values() for r in q_rows]
        yr_row  = _agg_row(yr_flat, str(year), bg="#EDE9F8", lbl_bg="#EDE9F8",
                           bold=True, expandable=True)
        q_groups = []
        for q in range(1, 5):
            if q not in by_year[year]:
                continue
            q_rows = by_year[year][q]
            q_row  = _agg_row(q_rows, f"Q{q} {year}", bg="#F3F0FC", lbl_bg="#F3F0FC",
                              bold=True, expandable=True)
            m_rows = [_cohort_row_html(r) for r in q_rows]

            if len(q_rows) == 1:
                q_groups.append(html.Div([q_row] + m_rows, className="ct-group-nodrill"))
            else:
                q_groups.append(html.Details([
                    html.Summary(q_row, className="ct-summary"),
                    html.Div(m_rows, className="ct-detail-body"),
                ], className="ct-group"))

        is_open = (year == open_year)
        if len(yr_flat) == 1:
            groups.append(html.Div([yr_row] + q_groups, className="ct-group-nodrill"))
        else:
            groups.append(html.Details([
                html.Summary(yr_row, className="ct-summary"),
                html.Div(q_groups, className="ct-detail-body"),
            ], className="ct-group", open=is_open))

    # Fila Total
    tot_amd = _agg_md(cohort_rows)
    grand   = sum(tot_amd.values())
    total_row = html.Div([
        _lc("Total", bg="#4827BE", fg="#fff", bold=True),
        html.Div("", className="ct-cell",
                 style={"minWidth": _ST, "maxWidth": _ST, "background": "#4827BE"}),
        *[html.Div(
            _fmt_ord(tot_amd.get(m, 0)) if tot_amd.get(m, 0) > 0 else "—",
            className="ct-cell",
            style={"minWidth": _MW, "maxWidth": _MW, "textAlign": "right",
                   "background": "#4827BE", "color": "#fff", "fontWeight": "700",
                   "fontSize": "12px"},
          ) for m in col_months],
        _nc(grand, _TOT, bg="#4827BE", fg="#fff", bold=True),
    ], className="ct-row ct-detail-row")

    legend = html.Div([
        html.Span("✓ Completo", style={"color": "#00C97A", "marginRight": "14px", "fontSize": "11px"}),
        html.Span("~ Parcial",  style={"color": "#FF820F", "marginRight": "14px", "fontSize": "11px"}),
        html.Span("◎ Budget",   style={"color": "#9684E1", "marginRight": "14px", "fontSize": "11px"}),
        html.Span("– Pendiente", style={"color": "#AAAAAA", "fontSize": "11px"}),
        html.Span(" │ Fondo claro = forecast", style={"color": "#AAA", "marginLeft": "14px", "fontSize": "11px"}),
    ], style={"padding": "6px 0 10px"})

    table = html.Div(
        html.Div([header, *groups, total_row], className="ct-table"),
        className="ct-wrap",
    )

    return html.Div([
        html.H3("Detalle por Cohorte", className="section-title"),
        legend,
        table,
    ], className="page-section card")


# ── Callback principal ────────────────────────────────────────────────────────

@callback(
    Output("rf-kpis",            "children"),
    Output("rf-chart-container", "children"),
    Output("rf-table",           "children"),
    Input("rf-pais",      "value"),
    Input("rf-escenario", "value"),
    Input("url",          "pathname"),
    State("cohort-overrides", "data"),
    prevent_initial_call=False,
)
def update_rolling(pais, escenario, pathname, cohort_overrides):
    if pathname != "/rolling":
        raise PreventUpdate

    pais      = pais      or "CONSOLIDADO"
    escenario = escenario or "base"

    filters = build_filters(pais, None, "incluir", None)

    _empty = html.Div(
        [html.P("Sin datos.", className="placeholder-hint")],
        className="placeholder-box",
    )

    df_ord = load_orders(filters)
    df_fc  = load_forecast(filters)

    if not df_ord.empty:
        df_ord = apply_cohort_overrides(df_ord, cohort_overrides, "order_month")
    if not df_fc.empty:
        df_fc = apply_cohort_overrides(df_fc, cohort_overrides, "forecast_month")

    _today   = pd.Timestamp.today().replace(day=1).normalize()
    _today_m = _today  # cohorte del mes en curso — fuerza proyección desde budget
    if not df_ord.empty:
        df_ord = df_ord[pd.to_datetime(df_ord["order_month"]) < _today]

    if df_ord.empty:
        return [_kpi_card("Sin datos", "—", "", "muted")], _empty, _empty

    nno, nno_status = calc_nno_by_cohort(df_ord)

    df_bud_raw = load_budget_nnr()
    end_month  = pd.Timestamp(f"{_today.year}-12-01")

    real_by_m, fc_by_m, cutoff, cohort_rows = _compute_data(
        df_ord, nno, nno_status, df_bud_raw, df_fc, pais, escenario, end_month,
        today_m=_today_m,
    )

    if cutoff is None:
        return [_kpi_card("Sin datos", "—", "", "muted")], _empty, _empty

    col_months = pd.date_range(
        "2025-01-01",
        max(end_month, fc_by_m.index.max()) if not fc_by_m.empty else end_month,
        freq="MS",
    ).tolist()

    # ── KPIs: Dec YoY para Consolidado, COL y MEX siempre ────────────────────
    _DEC25 = pd.Timestamp("2025-12-01")
    _DEC26 = pd.Timestamp("2026-12-01")

    def _dec_vals(geo):
        f = build_filters(geo, None, "incluir", None)
        d = load_orders(f)
        d_fc = load_forecast(f)
        if not d.empty:
            d = apply_cohort_overrides(d, cohort_overrides, "order_month")
            d = d[pd.to_datetime(d["order_month"]) < _today]
        if not d_fc.empty:
            d_fc = apply_cohort_overrides(d_fc, cohort_overrides, "forecast_month")
        if d.empty:
            return None, None
        n, ns = calc_nno_by_cohort(d)
        _, fc_g, _, _ = _compute_data(
            d, n, ns, df_bud_raw, d_fc, geo, escenario, end_month,
            today_m=_today_m, build_detail=False,
        )
        real_g = d.groupby("order_month")["order_count"].sum()
        real_g.index = pd.to_datetime(real_g.index)
        v25 = float(real_g[_DEC25]) if _DEC25 in real_g.index else None
        v26 = float(fc_g[_DEC26])   if not fc_g.empty and _DEC26 in fc_g.index else None
        return v25, v26

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        fut_cons = pool.submit(_dec_vals, "CONSOLIDADO")
        fut_col  = pool.submit(_dec_vals, "COL")
        fut_mex  = pool.submit(_dec_vals, "MEX")
        geo_results = [
            ("Consolidado", *fut_cons.result()),
            ("Colombia",    *fut_col.result()),
            ("México",      *fut_mex.result()),
        ]

    kpis  = _build_kpis(geo_results)
    chart = _build_chart(real_by_m, fc_by_m, cutoff, pais, escenario, end_month)
    table = _build_table(cohort_rows, escenario, col_months, cutoff)

    return kpis, chart, table
