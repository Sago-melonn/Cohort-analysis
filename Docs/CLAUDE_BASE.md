# SG&A Control — Memoria del Proyecto

## Rol de Claude Code
Eres el desarrollador del dashboard SG&A Control. Antes de cada sesión, lee este archivo completo.

## Reglas de trabajo
- Antes de ejecutar cualquier tarea, presenta un plan paso a paso
- Espera aprobación explícita antes de proceder
- Si hay dudas, pregunta antes de asumir

---

## Stack v2 (activo desde marzo 2026)
| Componente | Tecnología |
|---|---|
| Visualización | **Dash (Plotly)** |
| Base de datos | Amazon Redshift |
| Queries | SQL |
| App | Python |

> La v1 en Streamlit (`app/main.py`) queda como referencia de lógica de negocio pero está **deprecada**. No agregar código nuevo allí.

---

## Marca Melonn

### Logo
`https://i.postimg.cc/bNP45qQ2/MELONN-LOGO-Oscuro.png` (logo blanco/claro, para fondos oscuros)

### Tipografía
- Títulos: **Poppins Bold (700)**
- Subtítulos / labels: Poppins SemiBold (600)
- Texto: Poppins Regular (400)
- Importar via Google Fonts en `app.py`

### Paleta v2 — Light Mode Only
| Nombre | HEX | Uso |
|---|---|---|
| Page BG | `#F8F7FF` | Fondo de la app |
| Sidebar BG | `#FFFFFF` | Fondo sidebar |
| Sidebar Header | `#1A1659` | Zona logo en sidebar |
| Primary | `#4827BE` | Títulos, acentos, nav activo |
| Deep Blue | `#1A1659` | Texto primario |
| Soft Lilac | `#9684E1` | Bordes suaves, separadores |
| Muted | `#6B6B9A` | Texto secundario, labels |
| Card BG | `#FFFFFF` | Fondo de cards |
| Card Border | `#EDE9F8` | Borde de cards |
| Verde | `#00C97A` | Métricas favorables |
| Naranja | `#FF820F` | Métricas desfavorables |
| Amarillo | `#FFD700` | Alerta / cumplimiento intermedio |
| Light Lilac | `#F0EDFC` | Hover / nav activo bg |

### Estilo de diseño
- **Sin dark mode** — solo light mode
- Cards: `border-radius: 12px`, `box-shadow: 0 2px 16px rgba(72,39,190,0.08)`, sin glassmorphism
- Limpio, sofisticado, minimalista

---

## Estructura del proyecto v2

```
sga-control/
├── CLAUDE.md
├── requirements.txt
├── .env                        # Credenciales (no commitear)
├── queries/
│   ├── sga_main.sql            # Query master (actuals + budget agregados)
│   └── queries_sga_main.sql    # Referencia: query a nivel transacción
├── run.py                      # Entry point — python run.py desde la raíz del proyecto
├── app/
│   ├── __init__.py             # Crea instancia dash_app (importar desde aquí siempre)
│   ├── layout.py               # Shell (sidebar + dcc.Location + page-content)
│   ├── pages/
│   │   ├── landing.py          # Página 1 — Landing ✅
│   │   ├── summary.py          # Página 2 — Summary ✅
│   │   └── mi_ceco.py          # Página 3 — Mi CeCo (stub, pendiente)
│   ├── components/             # Componentes reutilizables (KPI cards, tablas, etc.)
│   ├── callbacks/
│   │   ├── routing.py          # Callback principal: URL → page-content + nav activo
│   │   ├── callbacks_landing.py  # Sin callbacks (navegación vía dcc.Link)
│   │   └── callbacks_summary.py  # 3 callbacks: mes options, render full, trend chart
│   ├── assets/
│   │   ├── style.css           # CSS global + Summary page styles
│   │   └── trails.js           # Efecto partículas mouse (brand colors)
│   ├── connection.py           # Conexión Redshift (sin cambios desde v1)
│   └── data_loader.py          # load_sga_data(), load_sga_transactions(), load_status_dates()
└── app/
    └── main.py                 # (referencia) Streamlit deprecado
```

### Routing
- `dcc.Location(id="url")` captura el pathname
- Callback en `callbacks/routing.py` mapea pathname → layout de página + clases nav activo
- Rutas: `/` → landing | `/summary` → summary | `/mi-ceco` → mi_ceco

### Sidebar
- Fijo izquierda, 240px de ancho
- Zona superior `#1A1659`: logo Melonn blanco centrado
- Zona nav `#FFFFFF`: items con icon + label
- Nav activo: bg `#F0EDFC`, texto `#4827BE`, borde izquierdo `3px solid #4827BE`

---

## Data Layer (sin cambios respecto a v1)

### Tablas Redshift (schema: finance)
| Tabla | Descripción |
|---|---|
| `financial_planning_eeff` | Actuals contables COL & MEX |
| `financial_planning_account_mapping` | Mapeo auxiliar → cuenta SG&A |
| `financial_planning_budgets_sga` | Presupuesto SG&A |
| `financial_planning_cost_center_mapping` | Jerarquía centros de costo |

### Funciones en data_loader.py
| Función | Descripción |
|---|---|
| `load_sga_data()` | DataFrame agregado (actuals + budget). TTL 1h. |
| `load_sga_transactions(cost_center_l2, year)` | Transacciones individuales por CeCo+año. TTL 1h. |
| `load_status_dates()` | `{country_id: max_date}` por país. TTL 1h. |

### Columnas de `load_sga_data()`
`date · country_id · cost_center_l1 · cost_center_l2 · concept · has_ceco · actual_amount · budget_amount · record_type`

### Campo `has_ceco`
- En actuals: valor real de `am.has_ceco` (0 o 1)
- En budget rows: `NULL` → se infiere en Python via `concept_ceco_map`
- `_infer_ceco(row)`: si actual → usa has_ceco directo; si budget → usa concept_ceco_map

### Filtro SG&A
- `country_id = 1` (COL): `auxiliary_code LIKE '5%'`
- `country_id = 2` (MEX): `auxiliary_code LIKE '6%'`

### Helpers de formato (replicar en v2)
- `_to_usd(amount, cid, fx_cop, fx_mxn)` — divide por fx según país
- `_fmt_amount(val, sym)` — escala K/M/B con sufijo moneda
- `_cum_color(pct)` — verde <95%, amarillo 95-105%, naranja >105%
- Desviación $: verde si ≤ 0 (gastó menos), naranja si > 0 (sobrepasó budget)

### Filtros estándar de datos
| Parámetro | Valor |
|---|---|
| Seller states | Activos: `(2, 3, 9, 10)` |
| Año default | Año máximo disponible en data |
| Mes default | Smart: si cumplimiento CeCo < 50% → mes anterior |
| Período | YTD o Mes actual |
| Moneda | USD (consolidado siempre) o Moneda Local (COP/MXN por país) |
| FX defaults | COP/USD: 3800 · MXN/USD: 17.5 |

---

## Lógica de negocio — Contribution Margins (referencia)

### Breakdowns estándar
- Consolidado: `country_id IN (1, 2)` → siempre en USD
- Colombia: `country_id = 1` → COP o USD según toggle
- México: `country_id = 2` → MXN o USD según toggle

### KPIs principales por bloque
| KPI | Cálculo |
|---|---|
| Ejecutado | SUM(actual_amount) con conversión FX si USD mode |
| Budget | SUM(budget_amount) con conversión FX si USD mode |
| Cumplimiento % | Ejecutado / Budget × 100 |
| Desviación $ | Ejecutado − Budget |

### Orden fijo de CeCos
`["Leadership", "Product & Tech", "Sales & Marketing", "Experience", "Operations", "Finance & Legal", "People", "G&A"]`

Reglas de normalización:
- CECos con Budget == 0 → renombrar a "G&A"
- "Finance" + "Legal" → mergear a "Finance & Legal"

---

## Estado del proyecto (2026-03-20)

### v1 — Streamlit (deprecado)
- [x] Queries validados en Redshift
- [x] Conexión Redshift configurada
- [x] Landing, Summary, Mi CeCo implementados

### v2 — Dash (activo)
- [x] CLAUDE.md actualizado
- [x] Estructura de archivos definida
- [x] Layout base + navbar (sidebar fijo, dcc.Location, routing)
- [x] Página 1: Landing (logo, status cards COL/MEX, botón CTA)
- [x] Página 2: Summary (filter bar sticky, 4 secciones, 4 callbacks)
- [x] Página 3: By CeCo (filtros, detalle por concepto, transacciones, tendencia por concepto)
- [x] Export Excel — Summary (3 sheets: Consolidado/Colombia/México)
- [x] Export Excel — By CeCo (2 sheets: Presupuesto pivot + Ejecución transaccional)
- [ ] Forecast
- [ ] Export PDF

---

## Página 2 — Summary (implementada)

### Filtros (IDs)
| ID | Tipo | Descripción |
|---|---|---|
| `sum-anio` | Dropdown | Año — opciones de data real, default = año max |
| `sum-mes` | Dropdown | Mes — opciones según año, smart default |
| `sum-periodo` | RadioItems | `"YTD"` \| `"mes"` |
| `sum-moneda` | RadioItems | `"usd"` \| `"local"` |
| `sum-fx-cop` | Input number | FX COP/USD, default 3800 |
| `sum-fx-mxn` | Input number | FX MXN/USD, default 17.5 |

### Callbacks en `callbacks_summary.py`
1. `update_mes_options(anio)` → opciones + smart default de mes
2. `render_summary(anio, mes, periodo, moneda, fx_cop, fx_mxn)` → `sum-content` children
3. `render_trend(scope, anio, mes, fx_cop, fx_mxn)` → `sum-trend-graph` figure
4. `export_summary_excel(n_clicks, ...)` → `sum-download-excel` data — genera Excel en BytesIO

### Secciones de `sum-content`
1. **Gastos con CeCo** — 3 bloques (Consolidado/Colombia/Mexico): 4 KPIs + tabs Por Concepto/Por CeCo + bar chart mensual USD + botón `sum-export-btn`
2. **Gastos sin CeCo** — 3 KPI de ejecutado + tabla detalle consolidada USD
3. **Composicion del Gasto** — 3 donuts (ceco vs no-ceco) + tablas expandibles
4. **Tendencia 12 meses** — radio scope + `dcc.Graph(id="sum-trend-graph")`

### Helpers en callbacks_summary.py
- `_load_raw()` — carga y parsea fechas; try/except → `pd.DataFrame()` vacío si falla
- `_add_ceco_eff(df)` — infiere `has_ceco_eff` para actuals y budget
- `_to_usd(amount, cid)` — convierte según fx
- `_is_usd_block(cids)` — True si usd_mode o consolidado
- `_fmt_blk(val, cids)` — formatea K/M/B con símbolo moneda
- `_cum_col(pct)` — verde/amarillo/naranja por cumplimiento
- `_agg_block(df, cids)` — retorna (act_total, bud_total, df_conc, df_cc)
- `_CECO_ORDER` — orden fijo de 8 CeCos

---

## Página 3 — By CeCo (implementada)

### Ruta
`/centro-costos` → `pages/mi_ceco.py` + `callbacks/callbacks_ceco.py`

### Nav label
"🔍 By CeCo" (admin y lider)

### Filtros (IDs)
| ID | Tipo | Descripción |
|---|---|---|
| `ceco-anio` | Dropdown | Año |
| `ceco-mes` | Dropdown | Mes — smart default |
| `ceco-selector` | Dropdown | CeCo — filtrado por `budget > 0`, orden fijo, `minWidth: 200px` |
| `ceco-periodo` | RadioItems | `"YTD"` \| `"mes"` |
| `ceco-moneda` | RadioItems | `"usd"` \| `"local"` |
| `ceco-fx-cop` | Input number | FX COP/USD, default 3800 |
| `ceco-fx-mxn` | Input number | FX MXN/USD, default 17.5 |

### CeCo selector — reglas
- Fuente: `budget_amount > 0` (no actuals)
- Orden fijo igual que `_CECO_ORDER`
- `_fmt_ceco()` normaliza DB names: `sales_&_marketing` → `Sales & Marketing`
- Admins y rol `["all"]`: todos los CeCos, dropdown habilitado
- Líderes: solo sus CeCos asignados, dropdown deshabilitado

### Callbacks en `callbacks_ceco.py`
1. `update_ceco_mes(anio)` → opciones mes + smart default
2. `render_ceco(anio, mes, ceco_raw, periodo, moneda, fx_cop, fx_mxn, session)` → `ceco-content`
3. `render_ceco_trend(scope, concept, anio, mes, ceco_raw, fx_cop, fx_mxn)` → `ceco-trend-graph`
4. `export_ceco_excel(n_clicks, ...)` → `ceco-download-excel` data

### Secciones de `ceco-content`
1. **KPIs** — Ejecutado / Budget / Cumplimiento % / Desviación $ (Consolidado USD)
2. **Detalle por Concepto** — expanders por concepto con tabla país + transacciones + botón `ceco-export-btn`
3. **Tendencia 12 meses** — dropdown concepto (`ceco-trend-concept`) + radio scope + área chart línea única `#4827BE`

### Gráfico tendencia — detalles
- Dropdown concepto: default "Labor expenses" o primero disponible
- Eje X: formato `mm/yy` (ej: `03/25`)
- Etiquetas: `$XXK`, ocultar si valor == 0
- Primer punto: `"top right"`, último: `"top left"`, resto: `"top center"`
- Si todos los valores son 0 → anotación "Sin ejecución en los últimos 12 meses"
- Márgenes: `l=20, r=80, t=40, b=70`

### Export Excel — By CeCo
- Archivo: `SGA_ByCeCo_{ceco}_{año}_{mes:02d}.xlsx`
- Sheet "Presupuesto": pivot CeCo × Concepto × mes (budget_amount raw)
- Sheet "Ejecución": transacciones individuales via `load_sga_transactions()`, monto en USD
- Formato: headers `#4827BE` blanco bold, filas alternas `#F0EDFC`/`#FFFFFF`

### Export Excel — Summary
- Archivo: `SGA_Summary_{año}_{mes:02d}.xlsx`
- 3 sheets: Consolidado | Colombia | México
- Cada sheet: título merged + tabla Por Concepto + tabla Por CeCo
- Formato: mismo estilo headers/filas

### Componentes estáticos en layouts
- `pages/summary.py` incluye `dcc.Download(id="sum-download-excel")`
- `pages/mi_ceco.py` incluye `dcc.Download(id="ceco-download-excel")`
