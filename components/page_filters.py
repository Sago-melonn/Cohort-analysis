"""
Paneles de filtros a nivel de página — barra horizontal compacta.

Controles:
  - Métrica, Moneda, Churn  → RadioItems inline con accent-color
  - País, Tipo de orden     → Dropdown single-select
  - Segmento                → Dropdown multi-select
  - Cohorte base            → Input texto
  - FX COP/USD, MXN/USD     → Input número (72 px)
"""
import pandas as pd
from dash import dcc, html


def _default_corte_base() -> str:
    """Devuelve el corte base por defecto según el año actual.

    Se fija en 2024 hasta 2026 inclusive, y luego avanza año a año.
    Ej: en 2027 el default pasa a 2025-12-01.
    """
    year = pd.Timestamp.today().year
    base_year = max(year - 2, 2024)
    return f"{base_year}-12-01"


# ── Helpers internos ──────────────────────────────────────────────────────────

def _lbl(text: str) -> html.P:
    return html.P(text, className="fb-label")


def _sep() -> html.Div:
    return html.Div(className="fb-sep")


def _radio(id_: str, options: list, value: str, col: bool = False) -> dcc.RadioItems:
    """Radio inline (fila) o columna según col=True."""
    return dcc.RadioItems(
        id=id_,
        options=options,
        value=value,
        inline=not col,
        className="fb-radio fb-radio--col" if col else "fb-radio",
        labelClassName="fb-radio-label",
        inputClassName="fb-radio-input",
    )


def _dropdown(id_: str, options: list, value, multi: bool = False,
              width: int = 130) -> dcc.Dropdown:
    """Dropdown compacto estilo select."""
    return dcc.Dropdown(
        id=id_,
        options=options,
        value=value,
        multi=multi,
        clearable=False,
        searchable=False,
        className="fb-select",
        style={"minWidth": f"{width}px"},
    )


def _fx_rows(prefix: str) -> list:
    """Dos filas FX COP/USD y FX MXN/USD."""
    return [
        html.Div([
            html.Span("FX COP/USD", className="fb-fx-label"),
            dcc.Input(id=f"{prefix}-fx-cop", type="text", value="3800",
                      debounce=True, className="fb-fx-input"),
        ], className="fb-fx-row"),
        html.Div([
            html.Span("FX MXN/USD", className="fb-fx-label"),
            dcc.Input(id=f"{prefix}-fx-mxn", type="text", value="17.5",
                      debounce=True, className="fb-fx-input"),
        ], className="fb-fx-row"),
    ]


# ── Grupos reutilizables ──────────────────────────────────────────────────────

def _g_metric(prefix: str) -> html.Div:
    return html.Div([
        _lbl("Métrica"),
        _radio(f"{prefix}-metric", [
            {"label": "Revenue", "value": "revenue"},
            {"label": "Órdenes", "value": "orders"},
        ], "revenue"),
    ], className="fb-group")


def _g_pais(prefix: str) -> html.Div:
    return html.Div([
        _lbl("País"),
        _radio(f"{prefix}-pais", [
            {"label": "Consolidado", "value": "CONSOLIDADO"},
            {"label": html.Span([
                html.Img(src="https://flagcdn.com/16x12/co.png", className="fb-flag"),
                " Col",
            ]), "value": "COL"},
            {"label": html.Span([
                html.Img(src="https://flagcdn.com/16x12/mx.png", className="fb-flag"),
                " Mex",
            ]), "value": "MEX"},
        ], "CONSOLIDADO"),
    ], className="fb-group")


def _g_moneda(prefix: str) -> html.Div:
    """Moneda + FX — el grupo entero se oculta cuando metric=orders."""
    return html.Div([
        _lbl("Moneda"),
        _radio(f"{prefix}-moneda", [
            {"label": "Moneda local", "value": "local"},
            {"label": "USD",          "value": "usd"},
        ], "local"),
        html.Div(_fx_rows(prefix), className="fb-fx-block"),
    ], className="fb-group")


def _g_order_type(prefix: str) -> html.Div:
    return html.Div([
        _lbl("Tipo de orden"),
        _radio(f"{prefix}-order-type", [
            {"label": "D2C + B2B", "value": "ambos"},
            {"label": "D2C",       "value": "D2C"},
            {"label": "B2B",       "value": "B2B"},
        ], "ambos"),
    ], className="fb-group")


def _g_segmento(prefix: str) -> html.Div:
    return html.Div([
        _lbl("Segmento"),
        _dropdown(f"{prefix}-segmentos", [
            {"label": "Starter",    "value": "Starter"},
            {"label": "Plus",       "value": "Plus"},
            {"label": "Top",        "value": "Top"},
            {"label": "Enterprise", "value": "Enterprise"},
        ], ["Starter", "Plus", "Top", "Enterprise"], multi=True, width=200),
    ], className="fb-group")


def _g_segmento_pills(prefix: str) -> html.Div:
    """Segmento como pills siempre visibles — toggles sin dropdown."""
    return html.Div([
        _lbl("Segmento"),
        dcc.Checklist(
            id=f"{prefix}-segmentos",
            options=[
                {"label": "Starter",    "value": "Starter"},
                {"label": "Plus",       "value": "Plus"},
                {"label": "Top",        "value": "Top"},
                {"label": "Enterprise", "value": "Enterprise"},
            ],
            value=["Starter", "Plus", "Top", "Enterprise"],
            className="fb-pills",
            labelClassName="fb-pill",
            inputClassName="fb-pill-input",
        ),
    ], className="fb-group")


def _g_churn(prefix: str) -> html.Div:
    return html.Div([
        _lbl("Churn"),
        _radio(f"{prefix}-churn", [
            {"label": "Incluir", "value": "incluir"},
            {"label": "Excluir", "value": "excluir"},
        ], "incluir"),
    ], className="fb-group")


def _g_corte_base(prefix: str) -> html.Div:
    default_date = _default_corte_base()
    return html.Div([
        _lbl("Cohorte base (≤)"),
        dcc.DatePickerSingle(
            id=f"{prefix}-corte-base",
            date=default_date,
            min_date_allowed="2022-01-01",
            max_date_allowed=f"{pd.Timestamp.today().year}-12-01",
            initial_visible_month=default_date,
            display_format="MMM YYYY",
            first_day_of_week=1,
            clearable=False,
            className="fb-date-picker",
        ),
    ], className="fb-group")


def _g_universo(prefix: str) -> html.Div:
    return html.Div([
        _lbl("Cohortes"),
        _radio(f"{prefix}-universo", [
            {"label": "Base",  "value": "base"},
            {"label": "Todos", "value": "todos"},
        ], "base"),
    ], className="fb-group")


def _g_forecast(prefix: str) -> html.Div:
    return html.Div([
        _lbl("Forecast"),
        _radio(f"{prefix}-forecast", [
            {"label": "No", "value": "no"},
            {"label": "Sí", "value": "si"},
        ], "no"),
    ], className="fb-group")


def _g_vista(prefix: str) -> html.Div:
    return html.Div([
        _lbl("Vista"),
        _radio(f"{prefix}-vista", [
            {"label": "% Ratio",  "value": "ratio"},
            {"label": "Absoluto", "value": "absoluto"},
        ], "ratio"),
    ], className="fb-group")


def _g_fx_only(prefix: str) -> html.Div:
    """Solo FX sin toggle de moneda (NNR/NNO)."""
    return html.Div([
        _lbl("FX"),
        html.Div(_fx_rows(prefix), className="fb-fx-block"),
    ], className="fb-group")


# ── Paneles por página ────────────────────────────────────────────────────────

def inputs_filters() -> html.Div:
    return html.Div([
        _g_metric("inputs"),
        _sep(),
        _g_pais("inputs"),
        _sep(),
        _g_moneda("inputs"),
    ], className="filter-bar")


def nor_filters() -> html.Div:
    return html.Div([
        # ── Bloque Generales ──────────────────────────────────────
        html.Div([
            html.Span("Generales", className="page-filter-label"),
            html.Div([
                _g_pais("nor"),
                _sep(),
                _g_moneda("nor"),
                _sep(),
                _g_segmento_pills("nor"),
            ], className="filter-bar"),
        ], className="filter-panel-row"),

        # ── Bloque Adicionales ────────────────────────────────────
        html.Div([
            html.Span("Adicionales", className="page-filter-label"),
            html.Div([
                html.Div([
                    _lbl("Métrica"),
                    _radio("nor-metric", [
                        {"label": "NOR", "value": "nor"},
                        {"label": "NRR", "value": "nrr"},
                    ], "nor"),
                ], className="fb-group"),
                _sep(),
                _g_churn("nor"),
                _sep(),
                _g_universo("nor"),
                _sep(),
                _g_corte_base("nor"),
                _sep(),
                _g_forecast("nor"),
            ], className="filter-bar"),
        ], className="filter-panel-row"),
    ], className="filter-panel")


def ndr_filters() -> html.Div:
    return html.Div([
        # ── Bloque Generales ──────────────────────────────────────
        html.Div([
            html.Span("Generales", className="page-filter-label"),
            html.Div([
                _g_pais("ndr"),
                _sep(),
                _g_moneda("ndr"),
                _sep(),
                _g_segmento_pills("ndr"),
            ], className="filter-bar"),
        ], className="filter-panel-row"),
        # ── Bloque Adicionales ────────────────────────────────────
        html.Div([
            html.Span("Adicionales", className="page-filter-label"),
            html.Div([
                html.Div([
                    _lbl("Métrica"),
                    _radio("ndr-metric", [
                        {"label": "ODR — Órdenes", "value": "orders"},
                        {"label": "NDR — Revenue", "value": "revenue"},
                    ], "orders"),
                ], className="fb-group"),
                _sep(),
                _g_churn("ndr"),
                _sep(),
                _g_forecast("ndr"),
                _sep(),
                html.Div([
                    _lbl("Años"),
                    dcc.Checklist(
                        id="ndr-year-select",
                        options=[],
                        value=[],
                        inline=True,
                        className="fb-pills",
                        labelClassName="fb-pill fb-year-pill",
                        inputClassName="fb-pill-input",
                    ),
                ], className="fb-group"),
            ], className="filter-bar"),
        ], className="filter-panel-row"),
    ], className="filter-panel")


def rolling_filters() -> html.Div:
    return html.Div([
        # ── Bloque Generales ──────────────────────────────────────
        html.Div([
            html.Span("Generales", className="page-filter-label"),
            html.Div([
                _g_pais("rf"),
            ], className="filter-bar"),
        ], className="filter-panel-row"),
        # ── Bloque Adicionales ────────────────────────────────────
        html.Div([
            html.Span("Adicionales", className="page-filter-label"),
            html.Div([
                html.Div([
                    _lbl("Escenario"),
                    _radio("rf-escenario", [
                        {"label": 'Base ("Junta")', "value": "base"},
                        {"label": "Bear",           "value": "bear"},
                    ], "base"),
                ], className="fb-group"),
            ], className="filter-bar"),
        ], className="filter-panel-row"),
    ], className="filter-panel")


def nnr_filters() -> html.Div:
    return html.Div([
        # ── Bloque Generales ──────────────────────────────────────
        html.Div([
            html.Span("Generales", className="page-filter-label"),
            html.Div([
                _g_pais("nnr"),
                _sep(),
                _g_moneda("nnr"),
            ], className="filter-bar"),
        ], className="filter-panel-row"),
        # ── Bloque Adicionales ────────────────────────────────────
        html.Div([
            html.Span("Adicionales", className="page-filter-label"),
            html.Div([
                html.Div([
                    _lbl("Métrica"),
                    _radio("nnr-metric", [
                        {"label": "NNO — Órdenes", "value": "orders"},
                        {"label": "NNR — Revenue", "value": "revenue"},
                    ], "revenue"),
                ], className="fb-group"),
                _sep(),
                html.Div([
                    _lbl("Escenario"),
                    _radio("nnr-escenario", [
                        {"label": 'Base ("Junta")', "value": "base"},
                        {"label": "Bear",           "value": "bear"},
                    ], "base"),
                ], className="fb-group"),
            ], className="filter-bar"),
        ], className="filter-panel-row"),
    ], className="filter-panel")
