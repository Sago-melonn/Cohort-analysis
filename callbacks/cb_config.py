"""
Callbacks de la página Configuración — gestión de overrides de cohorte por seller.

Store: "cohort-overrides" (localStorage)
  Formato: list of {seller_id, seller_name, original_cohort, override_cohort}
"""
import json

import pandas as pd
from dash import ALL, Input, Output, State, callback, callback_context, html
from dash.exceptions import PreventUpdate

from data.data_loader import load_sellers

_BTN_DEL = {
    "padding": "3px 10px", "fontSize": "12px", "fontWeight": "700",
    "border": "1px solid #E0D0F8", "borderRadius": "5px",
    "background": "#FFF5F5", "color": "#C0392B", "cursor": "pointer",
}

_TH = {"padding": "7px 12px", "fontSize": "11px", "fontWeight": "700",
       "background": "#1A1659", "color": "#fff", "textAlign": "left"}
_TD = {"padding": "6px 12px", "fontSize": "12px", "borderBottom": "1px solid #EDE9F8"}


# ── Poblar dropdown de sellers cuando se navega a /config ────────────────────

@callback(
    Output("cfg-seller-dd", "options"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)
def load_seller_options(pathname):
    if pathname != "/config":
        raise PreventUpdate
    df = load_sellers()
    if df.empty:
        return []
    country_lbl = {1: "🇨🇴", 2: "🇲🇽"}
    options = []
    for _, row in df.iterrows():
        flag = country_lbl.get(int(row.get("country_id", 0)), "")
        name = row.get("seller_name", "")
        sid  = int(row["seller_id"])
        options.append({"label": f"{flag} {name} (ID {sid})", "value": sid})
    return options


# ── Mostrar cohorte original al seleccionar un seller ─────────────────────────

@callback(
    Output("cfg-original-cohort", "children"),
    Input("cfg-seller-dd", "value"),
    prevent_initial_call=True,
)
def show_original_cohort(seller_id):
    if seller_id is None:
        return "—"
    df = load_sellers()
    if df.empty:
        return "—"
    row = df[df["seller_id"] == int(seller_id)]
    if row.empty:
        return "—"
    cohort_ts = pd.Timestamp(row.iloc[0]["cohort_month"])
    return cohort_ts.strftime("%b %Y")


# ── Agregar override ──────────────────────────────────────────────────────────

@callback(
    Output("cohort-overrides", "data",     allow_duplicate=True),
    Output("cfg-msg",          "children"),
    Output("cfg-seller-dd",    "value"),
    Output("cfg-new-cohort",   "date"),
    Input("cfg-add-btn", "n_clicks"),
    State("cfg-seller-dd",    "value"),
    State("cfg-new-cohort",   "date"),
    State("cohort-overrides", "data"),
    prevent_initial_call=True,
)
def add_override(n_clicks, seller_id, new_cohort_date, overrides):
    if not n_clicks:
        raise PreventUpdate

    # Validaciones
    if seller_id is None:
        return overrides, _msg("Selecciona un seller.", "error"), seller_id, new_cohort_date
    if not new_cohort_date:
        return overrides, _msg("Selecciona la nueva cohorte.", "error"), seller_id, new_cohort_date

    df = load_sellers()
    row = df[df["seller_id"] == int(seller_id)] if not df.empty else pd.DataFrame()
    if row.empty:
        return overrides, _msg("Seller no encontrado.", "error"), seller_id, new_cohort_date

    seller_name    = str(row.iloc[0].get("seller_name", seller_id))
    original_cohort = pd.Timestamp(row.iloc[0]["cohort_month"]).strftime("%Y-%m-%d")
    new_cohort      = pd.Timestamp(new_cohort_date).replace(day=1).strftime("%Y-%m-%d")

    if new_cohort == original_cohort:
        return overrides, _msg("La nueva cohorte es igual a la original.", "warn"), seller_id, new_cohort_date

    overrides = list(overrides or [])

    # Actualizar si ya existe, si no agregar
    existing = [i for i, o in enumerate(overrides) if o["seller_id"] == int(seller_id)]
    entry = {
        "seller_id":       int(seller_id),
        "seller_name":     seller_name,
        "original_cohort": original_cohort,
        "override_cohort": new_cohort,
    }
    if existing:
        overrides[existing[0]] = entry
        msg = _msg(f"Cohorte de {seller_name} actualizada a {pd.Timestamp(new_cohort).strftime('%b %Y')}.", "ok")
    else:
        overrides.append(entry)
        msg = _msg(f"Override agregado para {seller_name}.", "ok")

    return overrides, msg, None, None   # limpia inputs


# ── Eliminar override (pattern-matching) ──────────────────────────────────────

@callback(
    Output("cohort-overrides", "data",    allow_duplicate=True),
    Input({"type": "del-override", "index": ALL}, "n_clicks"),
    State("cohort-overrides", "data"),
    prevent_initial_call=True,
)
def delete_override(n_clicks_list, overrides):
    if not any(n for n in n_clicks_list if n):
        raise PreventUpdate
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered_prop = ctx.triggered[0]["prop_id"]
    try:
        idx = json.loads(triggered_prop.split(".")[0])["index"]
    except Exception:
        raise PreventUpdate

    overrides = list(overrides or [])
    if 0 <= idx < len(overrides):
        overrides.pop(idx)
    return overrides


# ── Renderizar tabla de overrides activos ─────────────────────────────────────

@callback(
    Output("cfg-overrides-table", "children"),
    Input("cohort-overrides", "data"),
    prevent_initial_call=False,
)
def render_overrides_table(overrides):
    overrides = overrides or []

    title = html.H3("Overrides activos", className="section-title")

    if not overrides:
        return html.Div([
            title,
            html.P("Sin ajustes configurados. Los overrides que agregues aquí "
                   "afectarán todas las páginas del tablero.",
                   style={"color": "#888", "fontSize": "13px"}),
        ])

    header = html.Tr([
        html.Th("Seller",             style=_TH),
        html.Th("Cohorte original",   style={**_TH, "textAlign": "center"}),
        html.Th("Cohorte ajustada",   style={**_TH, "textAlign": "center"}),
        html.Th("Meses adelantados",  style={**_TH, "textAlign": "center"}),
        html.Th("",                   style={**_TH, "width": "60px"}),
    ])

    rows = []
    for i, entry in enumerate(overrides):
        orig = pd.Timestamp(entry["original_cohort"])
        new  = pd.Timestamp(entry["override_cohort"])
        diff = (orig.year - new.year) * 12 + (orig.month - new.month)
        diff_lbl = f"+{diff}m" if diff > 0 else f"{diff}m"
        diff_color = "#1A7A3A" if diff > 0 else "#C0392B"

        rows.append(html.Tr([
            html.Td(f"{entry['seller_name']} (ID {entry['seller_id']})", style=_TD),
            html.Td(orig.strftime("%b %Y"), style={**_TD, "textAlign": "center", "color": "#888"}),
            html.Td(new.strftime("%b %Y"),  style={**_TD, "textAlign": "center",
                                                   "fontWeight": "600", "color": "#4827BE"}),
            html.Td(diff_lbl, style={**_TD, "textAlign": "center",
                                     "fontWeight": "700", "color": diff_color}),
            html.Td(
                html.Button("✕", id={"type": "del-override", "index": i},
                            n_clicks=0, style=_BTN_DEL),
                style={**_TD, "textAlign": "center"},
            ),
        ]))

    table = html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )

    return html.Div([title, table])


# ── Helper ────────────────────────────────────────────────────────────────────

def _msg(text: str, kind: str = "ok") -> html.Span:
    colors = {"ok": "#1A7A3A", "warn": "#B7760A", "error": "#C0392B"}
    return html.Span(text, style={"color": colors.get(kind, "#333"), "fontWeight": "500"})
