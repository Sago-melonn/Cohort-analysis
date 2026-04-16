# PROYECTO: COHORTES — Melonn
> Documento de contexto para Claude — actualizar con cada sesión de trabajo
> Ver `CLAUDE_BASE.md` para referencia del proyecto SG&A Control (stack y arquitectura)

---

## 🎯 OBJETIVO DEL PROYECTO

Construir una aplicación de análisis de cohortes para **Melonn** que permita:
- Calcular y visualizar **NDR** (Net Dollar Retention) y **NOR** (Net Order Retention) por cohorte
- Analizar la **retención de revenue** a lo largo del tiempo (curva M0 → Mn)
- Identificar cohortes de alto/bajo valor para Revenue Ops y Finance
- Desplegar una app funcional con la identidad visual de Melonn

---

## 📁 ARCHIVOS EN ESTA CARPETA

```
Docs/
├── CLAUDE.md                                              ← Este archivo (contexto Cohortes)
├── CLAUDE_BASE.md                                         ← SG&A Control — referencia de stack
├── Melonn Cohort Analysis & NDR (Interno) 2025 12.xlsx   ← Excel fuente de metodología
├── Código Cohortes V4 (lectura de inputs + NOR + NDR).txt ← Código React existente (v4)
└── Cohortes/
    ├── metodologia/     ← Docs de lógica de cálculo
    ├── research/        ← Hallazgos y decisiones (ver research/preguntas_negocio.md)
    ├── queries/         ← SQL para Redshift
    ├── outputs/         ← Reportes y exports
    └── assets/          ← Mockups y diagramas
```

---

## 🛠️ STACK TECNOLÓGICO

### App existente (v4 — React)
El código `Código Cohortes V4 (...).txt` es una app **React + Firebase/Firestore** que:
- Lee el Excel directamente desde el browser (SheetJS/XLSX)
- Guarda datos en Firestore para compartir entre usuarios
- Tiene 3 tabs: **Inputs** (datos reales), **NOR** (suavizado), **NDR** (retención %)
- Filtra por: País (COL / MEX / Consolidado), Segmento, Churn

### Stack de referencia Melonn (SG&A Control — ver CLAUDE_BASE.md)
| Componente | Tecnología |
|---|---|
| App | **Dash (Plotly)** |
| Base de datos | **Amazon Redshift** |
| Queries | **SQL** |
| Backend | **Python** |
| Entry point | `python run.py` |

> La nueva versión debe conectarse a Redshift en lugar de leer Excel manual. El código v4 contiene la lógica de cálculo correcta — reutilizar sus fórmulas.

---

## 🎨 MARCA MELONN (heredada del SG&A Control)

### Logo
`https://i.postimg.cc/bNP45qQ2/MELONN-LOGO-Oscuro.png`

### Paleta — Light Mode Only
| Nombre | HEX | Uso |
|---|---|---|
| Page BG | `#F8F7FF` | Fondo de la app |
| Sidebar Header | `#1A1659` | Header / sidebar |
| Primary | `#4827BE` | Títulos, acentos, nav activo |
| Deep Blue | `#1A1659` | Texto primario |
| Soft Lilac | `#9684E1` | Bordes suaves |
| Verde | `#00C97A` | Retención alta / métricas favorables |
| Naranja | `#FF820F` | Churn / métricas desfavorables |
| Muted | `#6B6B9A` | Texto secundario |
| Card BG | `#FFFFFF` | Fondo de cards |
| Card Border | `#EDE9F8` | Borde de cards |
| Light Lilac | `#F0EDFC` | Hover / nav activo bg |

### Tipografía: Poppins (Bold 700 títulos, SemiBold 600 labels, Regular 400 texto)
### Sin dark mode — solo light mode
### Cards: border-radius 12px, box-shadow 0 2px 16px rgba(72,39,190,0.08)

---

## 👥 ROLES / SKILLS DE TRABAJO

### 🎨 UI/UX
- Replicar y mejorar la UI del código v4
- Vistas principales: **Inputs** (datos reales), **NOR/NRR** (YoY retención), **NDR/ODR** (curva atemporal por cohorte)
- Tabla heatmap de cohortes con M0 como base, resaltando **M13** y **M25** en verde `#00C97A`
- Panel de KPIs con NNR, NNO del período
- Integración de datos reales + forecast en la misma visualización
- Sidebar fijo igual que SG&A Control

### 💰 Finance — Nuevo Revenue
- **NNR** = tamaño real de un seller nuevo = avg(Rev M2 + Rev M3), ajustado por estacionalidad
- Revenue en **MM COP** (Colombia), moneda local (México), consolidado en USD
- FX defaults: **COP/USD = 3800**, **MXN/USD = 17.5**
- Los inputs del modelo financiero salen de NNR, NNO, NRR y NOR

### 📊 Revenue Ops — Análisis de Cohortes
- Cohorte = mes de la **primera facturación** del seller (campo `Cohorte` en Inputs)
- Datos desde **Dic 2020** hasta **Dic 2025** (~61 cohortes mensuales)
- Segmentos activos: **Starter, Plus, Top, Enterprise** (Tiny deprioritizado desde Q1 2024)
- **Corte pre/post 2025:** sellers con entrada ≤ Dic 2024 = "Base" (analizados con NRR/NOR); sellers ≥ Ene 2025 = "Nuevos" (analizados con NDR/ODR)
- Hitos clave de retención: **M13** y **M25**

### 🛠️ Desarrollador
- El código v4 tiene la lógica de base — **reutilizar sus fórmulas de NDR y NOR**
- Nueva versión: Dash + Redshift (como SG&A Control)
- Reutilizar `connection.py` y patrón `data_loader.py` del SG&A
- Seguir arquitectura: `app/`, `queries/`, `callbacks/`, `components/`, `assets/`

### 🔬 Data Science — Queries
- Inputs en Redshift deben replicar estructura de `Inputs_Col` e `Inputs_Mex` del Excel
- Columnas clave: `seller_id`, `cohorte`, `segment`, `churn_flag`, `outlier_flag`, revenue mensual, órdenes mensual
- Las queries van en `Cohortes/queries/` con nombre descriptivo

---

## 📐 GLOSARIO OFICIAL DE MÉTRICAS

> ⚠️ Usar siempre estos nombres y definiciones. No mezclar terminología.

### NNR — Net New Revenue
**Qué es:** El "tamaño" real de un seller nuevo al entrar a Melonn.

**Fórmula:**
```
NNR(seller) = avg( Rev(M2) + Rev(M3) )
```
- M0 = mes de entrada, M1 = primer mes completo, M2 y M3 = base más estable
- **Ajuste de estacionalidad:** si el seller entró en un mes de temporada alta (ej. Oct-Dic), el M2/M3 estarían inflados. Se aplica un factor de desestacionalización (input variable configurable)

**Uso:** Plan de negocio, informes de junta, modelo financiero (captura cuánto revenue nuevo entró al negocio mes a mes)

---

### NNO — Net New Orders
**Qué es:** Mismo concepto que NNR pero en órdenes.

**Fórmula:**
```
NNO(seller) = avg( Orders(M2) + Orders(M3) )
```

**Uso:** Plan de negocio, modelo financiero (driver principal del negocio)

---

### NRR — Net Revenue Retention
**Qué es:** Crecimiento YoY del mismo grupo de clientes maduros (pre-2025).

**Universo (dos modos, seleccionable en UI):**
- **Base madura:** `cohort_month ≤ corte_base` (fijo, default Dic 2024)
- **Todos:** `cohort_month < M-12` (dinámico — para Mar 2026 incluye cohortes hasta Feb 2025)
- El mismo universo aplica a numerador y denominador de cada mes M.

**Fórmula:**
```
1. raw(cohorte C, mes M)    = Σ display_value  de C en M
2. smooth(cohorte C, mes M) = mean( raw(C, M-2..M) )   ← rolling 3 por cohorte, min_periods=1
3. smooth_total(M)          = Σ smooth(C, M)  para C en universo(M)
4. NRR(M) = smooth_total(M) / smooth_total(M-12)
```
- Suavizado a nivel de cohorte (no de seller)
- Sin forecast de revenue — la serie se corta en el último mes real

**Resultado tipo 110%** = clientes crecen YoY

**Aplica a:** Clientes **pre-2025** ("Base") o todos con ≥ 12 meses de vida

**Nota:** NRR puede estar inflado por aumentos de precio, nuevos servicios cobrados, cambios de comportamiento. Por eso se complementa con NOR.

---

### NOR — Net Order Retention
**Qué es:** Igual que NRR pero en órdenes. Métrica preferida por ser más limpia.

**Universo (dos modos, seleccionable en UI):**
- **Base madura:** `cohort_month ≤ corte_base` (fijo, default Dic 2024)
- **Todos:** `cohort_month < M-12` (dinámico — para Mar 2026 incluye cohortes hasta Feb 2025)
- El mismo universo aplica a numerador y denominador de cada mes M.

**Fórmula (implementada en `calc_retention_series`):**
```
1. raw(cohorte C, mes M)    = Σ order_count   de C en M
2. smooth(cohorte C, mes M) = mean( raw(C, M-2..M) )   ← rolling 3 por cohorte, min_periods=1
3. smooth_total(M)          = Σ smooth(C, M)  para C en universo(M)
4. NOR(M) = smooth_total(M) / smooth_total(M-12)
```
- Suavizado a nivel de cohorte (no de seller); si hay menos de 3 meses usa los disponibles
- Con toggle **Forecast (Sí/No)**: meses futuros usan `forecasted_orders` en lugar de `order_count`
- Trazabilidad: tabla mes × (cohortes hasta | num | den | NOR | NRR)

**Aplica a:** Clientes **pre-2025** ("Base") o todos con ≥ 12 meses de vida

**Por qué es preferida:** No está distorsionada por precios ni nuevos servicios. Refleja el driver real del negocio.

---

### NDR — Net Dollar Retention
**Qué es:** Curva atemporal de cuánto crece el revenue de una cohorte nueva respecto a su M0.

**Fórmula:**
```
NDR(cohorte, Mn) = Revenue(cohorte, Mn) / Revenue(cohorte, M0)
```
- **Base = M0** (mes de entrada de la cohorte, primera facturación)
- Resultado: tabla triangular cohortes × meses de vida (M0=100%, M1=x%, ..., M24=x%)
- Aplica suavizado de 3 períodos sobre el revenue antes del cálculo

**Resultado esperado (heatmap):**
```
Cohorte     | M0    | M1   | M2   | ... | M13  | ... | M25
2025-01-01  | 100%  | x%   | x%   | ... | x%   | ... | x%
2025-02-01  | 100%  | x%   | ...
```

**Promedios al pie:**
- Promedio simple: media aritmética de cohortes con dato en Mn
- Promedio ponderado: ponderado por NNR de cada cohorte ← más representativo

**Aplica a:** Clientes **post-2025** ("Nuevos"), primeros 24 meses de vida

**Hitos destacados:** M13 y M25 (verde `#00C97A`)

---

### ODR — Order Dollar Retention
**Qué es:** Igual que NDR pero en órdenes. Sin sigla oficial en el mercado — nombre interno Melonn.

**Fórmula:**
```
ODR(cohorte, Mn) = Orders(cohorte, Mn) / Orders(cohorte, M0)
```

**Aplica a:** Clientes **post-2025** ("Nuevos")

**Por qué es preferida:** Igual que NOR — más limpia que NDR porque no está afectada por precio.

---

### Rolling Forecast
**Qué es:** Forecast de órdenes a nivel de cliente hasta Dic 2026, conectado con el análisis histórico.

> Ver también: `Cohortes/research/preguntas_negocio.md` para el detalle de casos de uso.

**Objetivo:** En la misma visualización ver datos reales (histórico) + proyectados (forecast) para:
- **NOR de pre-2025:** ¿cómo se comportaría si el forecast se cumple?
- **ODR de post-2025:** ¿cómo crecerían los sellers nuevos según el forecast?

**Permite:**
- Entender el comportamiento actual de la base de clientes
- Cuestionar si el forecast es consistente con los patrones históricos
- Sugerir inputs para el modelo financiero
- Analizar NNR por trimestre para informes de junta

---

## 📐 FUENTE DE DATOS Y FILTROS

### Estructura del Excel (Inputs)
- **Inputs_Col**: ~3,735 sellers × 216 columnas
  - Columnas fijas: `seller_id`, `seller_name`, `Cohorte`, `Segment`, `Churn_flag`, `Pilot & outliers flag`, `Regrettable flag`
  - Columnas de fechas: revenue mensual desde 2020-12-01 hasta 2025-12-01
- **Inputs_Mex**: misma estructura para México

### Filtros del modelo
| Filtro | Opciones | Default |
|---|---|---|
| País | COL / MEX / Consolidado | Consolidado |
| Order type | Online, B2B | Ambos incluidos |
| Segmentos | Tiny, Starter, Plus, Top, Enterprise | Starter, Plus, Top, Enterprise |
| Churn | Incluir / Excluir | Incluir |
| Outliers | Remover / No remover | No remover |
| Tipo cohorte | Original / Ajustada | Original |
| FX COP/USD | número | 3800 |
| FX MXN/USD | número | 17.5 |
| Factor estacionalidad NNR | número | por definir |

### Corte pre/post 2025
| Grupo | Sellers | Métricas |
|---|---|---|
| **Base** | Entrada ≤ Dic 2024 (default) | NRR, NOR |
| **Nuevos** | Entrada ≥ Ene 2025 (default) | NDR, ODR, NNR, NNO |
| Excepción | 1 seller MEX — corte a definir | — |

> El corte "Base" es **configurable por el usuario** — default Dic 2024 pero editable. En 2027 podría moverse a Dic 2025.

---

### Estructura de Col NDR en el Excel (referencia SQL)
La hoja tiene 3 bloques verticales:
1. **Sellers activos** por cohorte × período (M0...M60)
2. **Orders** por cohorte × período
3. **Revenue en MM COP** por cohorte × período ← base para NDR

---

## 🗄️ TABLAS REDSHIFT Y QUERIES

### Schema y tablas fuente
| Tabla | Schema | Descripción |
|---|---|---|
| `dim_seller` | `data_warehouse` | Maestro de sellers — cohorte, segmento, país, churn |
| `fact_sell_order` | `data_warehouse` | Órdenes — fecha, seller, tipo (D2C/B2B), GMV |
| `Rentabilidad_master` | `profitability` (ver `.sql`) | Revenue P&L completo por seller × mes × bodega |

### Campos clave de dim_seller
| Campo | Uso |
|---|---|
| `id` | seller_id — join principal |
| `cohort` | Timestamp → `DATE_TRUNC('month')` = cohort_month |
| `segment` | Filtro: Starter, Plus, Top, Enterprise (excluir Tiny) |
| `country_id` | 1 = COL, 2 = MEX |
| `state` | `<> 'Active'` → churn_flag = 1 (v4: sellers que churnearon y volvieron tienen churn_date pero state='Active' — usar state) |

### Campos clave de staging.orbita.sell_order (fuente de órdenes)
> ⚠️ NO usar `core.data_warehouse.fact_sell_order` para órdenes — solo tiene datos desde Ene 2023. Usar `staging.orbita.sell_order` que tiene historia completa desde Feb 2021.

| Campo | Uso |
|---|---|
| `seller_id` | Join con dim_seller |
| `id` | COUNT(id) = order_count por mes |
| `fulfillment_type_id` | JOIN con `staging.orbita.fulfillment_type` → campo `order_type` ('D2C'/'B2B') |
| `assigned_warehouse_id` | JOIN con `staging.orbita.warehouse` → `timezone_code` para conversión UTC |

**Items reservation date:** capturar de `staging.orbita.sell_order_log` WHERE `sell_order_state_id = 2`, usando `MIN(action_date)`. El log se usa SOLO para capturar esta fecha — los datos de la orden vienen de sell_order.

**Filtro bodega:** `w.operated_by_melonn = 1`

### Fórmula de Revenue Total P&L
```
total_revenue =
  + COALESCE(ir_picking_revenue, ir_estimated_picking_revenue, 0)
  + COALESCE(ir_packaging_revenue, ir_estimated_packaging_revenue, 0)
  + COALESCE(ir_transport_revenue, ir_estimated_transport_revenue, 0)
  + COALESCE(ir_payment_on_delivery_revenue, ir_estimated_payment_on_delivery_revenue, 0)
  + COALESCE(ir_transport_insurance_revenue, ir_estimated_transport_insurance_revenue, 0)
  - COALESCE(ir_discount, ir_estimated_discount, 0)
  + COALESCE(anti_picking_charge, 0) + COALESCE(anti_shipping_charge, 0)
  + COALESCE(estimated_revenue_warehousing_revenue, 0)        -- ya coalesceado (real→est)
  + COALESCE(estimated_revenue_warehousing_insurance_revenue, 0)
  - COALESCE(warehousing_discount, 0)
  + COALESCE(inbound_revenue, 0) - COALESCE(inbound_discount, 0)
  + COALESCE(revenue_estimated_saas, 0)                       -- ya coalesceado (real→est)
  + COALESCE(ex_packaging_revenue, 0) + COALESCE(ex_transport_revenue, 0)
  + COALESCE(ex_seller_support_revenue, 0) + COALESCE(interest_arrears, 0)
  + COALESCE(vas, 0) + COALESCE(adjecencies_revenue, 0)
  [- COALESCE(credit_notes_amount, 0)]  ← solo si flag include_credit_notes = TRUE
```
**Notas:**
- D2C/B2B: usar prefijos `d2c_ir_` / `b2b_ir_` según filtro; sin filtro usar `ir_` (total)
- Warehousing y SaaS: el master ya aplica COALESCE(real, estimado) internamente
- Credit notes: default **excluido** (pueden cubrir múltiples meses → genera ruido)
- Agregación: sumar todas las bodegas del seller → un valor por seller × mes

### Revenue — Arquitectura dual source
| Período | Fuente | Tabla |
|---|---|---|
| Feb 2021 – Dic 2023 | Excel ETL cargado a Redshift | `staging.finance.financial_planning_historical_revenue` |
| Ene 2024 – presente | Redshift profitability | `staging.profitability.*` (Rentabilidad_master embebido) |

**Tabla histórica:** `staging.finance.financial_planning_historical_revenue`
- Columnas: `date DATE`, `seller_id INTEGER`, `total_revenue NUMERIC(18,2)`, `country_id INTEGER`
- 63,862 rows: sellers COL (country_id=1) + MEX (country_id=2), granularidad seller × mes
- Cargada via `Cohortes/scripts/02_load_historical_revenue.py` desde `historical_revenue.csv`

**Billing types mapeados (external_revenue vía Rentabilidad_master):**
| billing_type | Campo destino |
|---|---|
| `Intereses mora`, `Intereses`, `Intereses WK` | `interest_arrears` |
| `Alistamiento` | `alistamiento_revenue` (sumado en `external_revenue`) |

### Queries disponibles (✅ validadas en Redshift)
| Archivo | Descripción | Estado |
|---|---|---|
| `Cohortes/queries/01_inputs_orders.sql` | Órdenes por seller × mes — fuente: staging.orbita | ✅ D3 OK |
| `Cohortes/queries/02_inputs_revenue.sql` | Revenue P&L por seller × mes — UNION ALL dual source | ✅ D4 OK |
| `Cohortes/queries/03_inputs_forecast.sql` | Forecast de órdenes por seller × mes — fuente: core.forecast | ✅ D5 OK |
| `Cohortes/queries/00_validacion_redshift.sql` | Script de validación A–D | ✅ Completo |
| `Cohortes/scripts/01_create_historical_table.sql` | DDL tabla histórica | ✅ Creada |
| `Cohortes/scripts/02_load_historical_revenue.py` | ETL Excel → Redshift histórico | ✅ Cargado |

---

## 🔄 ESTADO DEL PROYECTO

| Fase | Estado | Notas |
|------|--------|-------|
| Excel de metodología analizado | ✅ Hecho | |
| Código v4 (React) documentado | ✅ Hecho | |
| Glosario de métricas definido | ✅ Hecho | NNR, NNO, NRR, NOR, NDR, ODR |
| Stack y marca Melonn definidos | ✅ Hecho | |
| Preguntas de negocio definidas | 🟡 En progreso | Pendiente sesión siguiente |
| Tablas Redshift identificadas | ✅ Hecho | dim_seller, orbita.sell_order, Rentabilidad_master |
| Schemas Redshift confirmados | ✅ Hecho | core.data_warehouse, core.experience, staging.orbita, staging.profitability, staging.finance |
| Data histórica revenue cargada | ✅ Hecho | staging.finance.financial_planning_historical_revenue (Feb 2021–Dic 2023) |
| Query órdenes (01) | ✅ Validada | staging.orbita.sell_order — historia completa Feb 2021 |
| Query revenue (02) | ✅ Validada | UNION ALL: histórico + Redshift desde Ene 2024 |
| Query forecast (03) | ✅ Validada | core.forecast.official_forecast_temp — Feb–Dic 2026 |
| PRD completo | 🔴 Pendiente | |
| App v2 — Landing page | ✅ Hecho | Logo, mes cerrado/parcial, botón "Entrar al Dashboard" |
| App v2 — Scaffold (layout + sidebar + routing) | ✅ Hecho | Shell flex row, sidebar sticky, routing con PreventUpdate |
| App v2 — Vista Inputs (heatmap + KPIs) | ✅ Hecho | Tabla custom 2 niveles, drill-down inline, KPIs, sticky filter bar |
| App v2 — Vista NOR/NRR | ✅ Hecho | KPIs + gráfico Plotly + trazabilidad + sección Churn (bar chart + tabla TOP10) — cb_nor.py |
| App v2 — Vista NDR/ODR | ✅ Hecho | Gráfico + tabla hitos + heatmap absolutos (agrupado año/mes) + tabla ratios Mn/M1 + exportación Excel 2 hojas — cb_ndr.py |
| App v2 — Vista NNR/NNO | 🔴 Pendiente | Stub en cb_nnr.py |
| Deploy | 🔴 Pendiente | |

---

## 📝 DECISIONES TOMADAS

| Fecha | Decisión |
|---|---|
| 2026-04-08 | Cohorte = mes de primera facturación del seller |
| 2026-04-08 | Segmentos activos: Starter, Plus, Top, Enterprise (Tiny excluido por default) |
| 2026-04-08 | Hitos de retención clave: M13 y M25 (ampliado a M13, M25, M37, M49 el 2026-04-16) |
| 2026-04-08 | NNR = avg(M2+M3), ajustado por estacionalidad (factor input variable) |
| 2026-04-08 | NDR base = M0 (mes de entrada), no M1 |
| 2026-04-08 | Corte Base/Nuevos = Dic 2024 (excepción: 1 seller MEX) |
| 2026-04-08 | NDR en órdenes = ODR (Order Dollar Retention) — nombre interno Melonn |
| 2026-04-08 | NOR y ODR preferidos sobre NRR y NDR por ser más limpios (no afectados por precio) |
| 2026-04-08 | FX defaults: COP/USD = 3800, MXN/USD = 17.5 |
| 2026-04-08 | Nueva app: Dash + Redshift (mismo stack que SG&A Control) |
| 2026-04-09 | Schemas Redshift: core.data_warehouse, core.experience, staging.orbita, staging.profitability, staging.finance |
| 2026-04-09 | Fecha inicio real del sistema: Feb 2021 (no Dic 2020 como aparece en Excel) |
| 2026-04-09 | Fuente de órdenes: staging.orbita.sell_order (historia desde Feb 2021) — NO fact_sell_order (solo desde Ene 2023) |
| 2026-04-09 | Revenue Ene 2024+: Redshift profitability. Revenue Feb 2021–Dic 2023: tabla histórica en staging.finance |
| 2026-04-09 | Items reservation date: staging.orbita.sell_order_log WHERE sell_order_state_id = 2, MIN(action_date) |
| 2026-04-09 | lifecycle_month: M1 = mes de entrada (DATEDIFF month + 1) |
| 2026-04-09 | Queries 01 y 02 validadas end-to-end (D3 OK, D4 OK) |
| 2026-04-09 | Forecast: core.forecast.official_forecast_temp — truncar date a mes. NO filtrar por version_id (la tabla ya refleja el forecast oficial; version_id es control interno) |
| 2026-04-09 | Forecast: cohort_month de dim_seller (no del forecast) — ajustes administrativos de cohorte aplican solos |
| 2026-04-09 | Forecast: 11 meses de horizonte (Feb–Dic 2026), ya filtrado por bodega Melonn |
| 2026-04-09 | Query 03 validada (D5 OK) |
| 2026-04-09 | App v2 Fase 2 — scaffold completo: layout, sidebar, routing, 4 callbacks stub, data_loader, connection |
| 2026-04-09 | App v2 Fase 3 — Vista Inputs implementada con datos reales: pivot cohorte × mes, agrupado por año con html.Details |
| 2026-04-09 | data/transforms.py — funciones puras: build_filters, prepare_revenue, calc_nnr, calc_nno, pivot_cohort, pivot_cohort_by_year, quartile_styles, revenue_display_unit |
| 2026-04-09 | Tabla heatmap: secciones por año, solo año actual abierto por defecto (date.today().year), resto colapsadas |
| 2026-04-09 | NaN → None: usar astype(object).where() antes de to_dict("records") para serialización JSON segura |
| 2026-04-09 | dcc.Location debe ir FUERA del div.app-shell (flex container) — si está dentro, rompe el layout |
| 2026-04-09 | Callback update_inputs solo corre en pathname == "/inputs" (no en landing "/") |
| 2026-04-11 | Vista Inputs rediseñada: tabla custom html.Div flex (NO DataTable) con 2 niveles — nivel 1: cohorte-año × meses + Total; nivel 2: click expande cohorte-mes inline |
| 2026-04-11 | Heatmap coloreado con inline styles por cuartil (sin style_data_conditional de DataTable) |
| 2026-04-11 | Query 01 v3: eliminado JOIN fulfillment_type y columna order_type — D2C+B2B consolidados en SQL. Filtro order_type eliminado del UI de Inputs |
| 2026-04-11 | Unidades revenue: COL+local → MM COP (÷1M), MEX+local → K MXN (÷1K), USD/Consolidado → K USD |
| 2026-04-11 | Números sin decimales en Inputs (fmt_spec ",.0f" para revenue y órdenes) |
| 2026-04-11 | KPIs Inputs: NNR y NNO con tooltip hover (sin texto "avg M2+M3" visible); "Sellers activos" = churn_flag==0 con órdenes en último mes; eliminado KPI "Cohortes activas" |
| 2026-04-11 | Filter bar de Inputs sticky (position: sticky, top: 0, z-index: 50) — queda fija al scrollear |
| 2026-04-11 | Filtros Inputs alineados a la izquierda (justify-content: flex-start); Métrica en fila horizontal igual que País |
| 2026-04-13 | NOR/NRR: suavizado 3 períodos a nivel de cohorte (no de seller), antes del ratio |
| 2026-04-13 | NOR/NRR: universo seleccionable — "Base madura" (≤ corte_base fijo) o "Todos" (cohort_month < M-12 dinámico) |
| 2026-04-13 | NOR/NRR: mismo universo para numerador y denominador de cada mes M |
| 2026-04-13 | NOR: toggle Forecast (Sí/No) — extiende serie con forecasted_orders como línea punteada |
| 2026-04-13 | NRR: sin forecast (no existe revenue proyectado), serie se corta en último mes real |
| 2026-04-13 | calc_retention_series() en transforms.py — función genérica para NOR y NRR |
| 2026-04-13 | nor_filters(): quitado toggle Métrica, agregados Universo y Forecast |
| 2026-04-13 | Trazabilidad: tabla mes × cohortes_hasta × num × den × NOR × NRR en cb_nor.py |
| 2026-04-13 | KPI variants: verde (≥100%), naranja (90–99%), muted (<90%) |
| 2026-04-14 | NOR filtros reestructurados en dos bloques: Generales (País, Moneda, Segmento) y Adicionales (Métrica, Churn, Cohortes, Corte base, Forecast, Vista) |
| 2026-04-14 | Segmento en NOR: pills (Checklist) siempre visibles, toggle on/off por pill, sincronizados con clientside_callback. Tiny incluido en Starter a nivel SQL (_SEGMENT_ALIASES en data_loader.py) |
| 2026-04-14 | "Base madura" → "Base" en radio Cohortes; "Universo" → "Cohortes" como label |
| 2026-04-14 | Corte base: reemplazado dcc.Input por dcc.DatePickerSingle (MMM YYYY, 2022–2026) |
| 2026-04-14 | Gráfico NOR/NRR: etiquetas en negrilla (Arial Black), mensual (dtick=M1), padding 3 semanas en bordes, eje Y 50%–max(200%, data_max), hover con smooth_num + smooth_den + ratio |
| 2026-04-14 | Forecast trace: color naranja #F97316 (distinto del morado #4827BE de actuals), línea punteada + etiquetas + hover completo |
| 2026-04-14 | Conexión actuals↔forecast: traza "puente" invisible (hoverinfo=skip, showlegend=False) + traza forecast separada desde Abril. Evita duplicación de hover en el mes de corte |
| 2026-04-14 | Toggle Vista (% Ratio / Absoluto): en Absoluto el gráfico muestra smooth_num (valor T del período) en lugar del ratio. Eje Y en unidades, sin línea 100%. Hover muestra T, T-12 y ratio calculado (customdata[2]) |
| 2026-04-14 | Bug fix: df_orders y df_rev_p se filtran a <= last_closed ANTES de pasar a calc_retention_series. Evita que un mes parcial en curso (ej. Abril) sea last_actual y deje ese mes en el limbo (excluido de actuals y de forecast) |
| 2026-04-14 | last_closed calculado una sola vez al inicio del callback (movido antes de las cargas de datos) |
| 2026-04-15 | churn_flag: cambiado de churn_date IS NOT NULL a state <> 'Active' en queries 01 y 02 (v4). Sellers que churnearon y volvieron tenían churn_date pero state='Active' |
| 2026-04-15 | Sección Churn en NOR/NRR: bar chart mensual desde Ene 2025 + tabla año→mes→TOP 10 sellers + Otros(N) agrupados. Aplica filtros País, Segmento, Métrica y Moneda/FX |
| 2026-04-15 | Toggle Vista (% Ratio / Absoluto) movido de filtros Adicionales al interior del card del gráfico (top-right, position absolute). Solo aplica al gráfico |
| 2026-04-15 | Título de la hoja NOR/NRR cambiado a "Net Revenue Retention / Net Order Retention"; navegación en sidebar sigue como "NRR/NOR" |
| 2026-04-15 | Vista NDR/ODR implementada: suavizado forward 3 períodos, gráfico curva promedio (ponderado + aritmético), tabla hitos (M1/3/6/12/13/18/24/25), heatmap cohorte × lifecycle_month con colores cuartil |
| 2026-04-15 | calc_cohort_matrix() en transforms.py: smooth(C,Mn) = mean(raw_Mn, raw_Mn+1, raw_Mn+2) usando meses disponibles. Weights = Σ raw(M1..M12) sin suavizar, para el promedio ponderado |
| 2026-04-15 | NDR/ODR: universo = todos los cohortes históricos (sin filtro corte_base). Filtros activos: País, Moneda/FX, Segmentos pills, Churn, Métrica (ODR=órdenes / NDR=revenue) |
| 2026-04-15 | NDR/ODR: heatmap reutiliza clases ct-* de Inputs. M13 y M25 con borde verde y header verde. Filas subtotales: Avg Aritmético (#E8E2F8) y Avg Ponderado (#4827BE) al pie del heatmap |
| 2026-04-15 | ndr_filters() rediseñado: layout dos bloques (Generales/Adicionales) igual que NOR. Segmentos como pills con clientside_callback. Sin corte base |
| 2026-04-16 | NDR/ODR tabla heatmap: agrupada por año (ascendente 2021→2026), cohortes Ene→Dic dentro de cada año, con html.Details/Summary nativo. Años con 1 cohorte usan ct-group-nodrill |
| 2026-04-16 | NDR/ODR: mes actual excluido automáticamente (dato incompleto). Filtro: lifecycle_month ≤ meses_transcurridos desde cohort_month |
| 2026-04-16 | NDR/ODR: hitos expandidos a M13, M25, M37, M49 (borde verde + header verde). _HITOS incluye M36, M37, M48, M49 |
| 2026-04-16 | NDR/ODR: segunda tabla "Ratios NDR/ODR (Mn/M1)" con columna Σ M1-M12 (peso absoluto), ratios en %, filas Avg Aritmético + Avg Ponderado. Avg Ponderado muestra el total de pesos (Σ M1-M12 global) |
| 2026-04-16 | NDR/ODR: exportación Excel única (botón "↓ Exportar Excel") con dos hojas: "Absolutos" y "Ratios NDR-ODR". Columnas: Año, Mes, Cohorte, Σ M1-M12, M1..Mn |
| 2026-04-16 | NDR/ODR: dcc.Store(id="ndr-store") serializa smooth_df, weights y promedios para exportación sin recalcular |
| 2026-04-16 | NDR/ODR: M0 = mes de adquisición (shift lifecycle_month -= 1). Ponderador y ratios desde M1. Tabla "Sin suavizar" encima de la suavizada para verificación |
| 2026-04-16 | NDR/ODR: tabla Sin suavizar con seller drill-down (top 5 + Otros) por Σ M1-M12. Tres niveles: Año → Cohorte (Details) → Sellers (Details) |
| 2026-04-16 | NDR/ODR: Curva Promedio y tabla hitos muestran ratios Mn/M1 (no absolutos). Etiquetas bold en top-center en cada punto. Sin tooltip (hoverinfo=skip) |
| 2026-04-16 | NDR/ODR: pills de años en filtros Adicionales. _MIN_YEAR_WEIGHT_BY_UNIT define umbrales fijos por moneda (K MXN=2000, MM COP=10, K USD=100). Años bajo el umbral arrancan auto-OFF |
| 2026-04-16 | NDR/ODR: update_ratio_section callback separado — reacciona a ndr-store + ndr-year-select. Recalcula promedios solo con años activos; años excluidos se grisan en la tabla de ratios |
| 2026-04-16 | Config /config: página nueva en sidebar (⚙). Override de cohorte por seller: buscar seller, asignar nueva cohorte, tabla con ✕ para eliminar. Persiste en dcc.Store(storage_type="local") |
| 2026-04-16 | apply_cohort_overrides() en transforms.py: cambia cohort_month, recalcula lifecycle_month relativo a la nueva cohorte, descarta filas < M1 (período piloto). Aplica en NDR, NOR, Inputs |

---

## 🚀 INSTRUCCIONES PARA CLAUDE CODE

1. **Leer este CLAUDE.md completo** antes de escribir cualquier código
2. **Leer CLAUDE_BASE.md** para la arquitectura de referencia (SG&A Control)
3. **Glosario:** usar siempre NNR/NNO/NRR/NOR/NDR/ODR con las definiciones de este archivo
4. **El código v4** tiene la lógica base de NDR y NOR — reutilizar sus fórmulas
5. La nueva app obtiene datos de **Redshift**, no del Excel manual
6. **Corte pre/post 2025:** Base (NRR/NOR) vs Nuevos (NDR/ODR)
7. Resaltar **M13 y M25** en los heatmaps
8. Filtros obligatorios: País, Segmento, Churn, FX, Factor estacionalidad

### Reglas de trabajo
- Presentar plan paso a paso antes de ejecutar
- Esperar aprobación explícita
- Si hay dudas, preguntar antes de asumir

---

## 💬 NOTAS DE SESIÓN

### Sesión 2026-04-14
- Gráfico NOR/NRR mejorado: título más alto (margen t=90), etiquetas en negrilla, forecast en naranja (#F97316) con etiquetas y hover completo
- Toggle **Vista: % Ratio / Absoluto** — en Absoluto muestra `smooth_num` (valor T de la base de cohortes por mes). El hover siempre muestra Órdenes (T), Órdenes (T-12) y el ratio % como contexto. Forecast también proyecta el absoluto.
- Traza de forecast refactorizada en dos partes: "puente" invisible (solo línea, sin hover) + traza de datos desde el primer mes de forecast. Resuelve doble hover en mes de corte y ausencia de etiqueta en el primer mes forecast.
- **Bug fix crítico:** `df_orders` y `df_rev_p` se cortan a `last_closed` antes de `calc_retention_series`. Antes, si había órdenes parciales del mes en curso (ej. Abril), ese mes quedaba en el limbo: excluido de actuals (`> last_closed`) y de forecast (`is_forecast=False`). Ahora `last_actual` dentro de la función siempre es el último mes cerrado.
- Filtros NOR reorganizados: Generales (País, Moneda, Segmento-pills) + Adicionales (Métrica, Churn, Cohortes, Corte base, Forecast, **Vista**)
- **Próximos pasos:**
  - [ ] Vista NDR/ODR — implementar cb_ndr.py
  - [ ] Vista NNR/NNO — implementar cb_nnr.py
  - [ ] Warm-up agresivo de cache al arrancar (3 combinaciones país)
  - [ ] Deploy

### Sesión 2026-04-13
- Metodología NOR/NRR alineada y documentada
- `calc_retention_series()` implementada en `transforms.py` — genérica para NOR (order_count) y NRR (display_value)
- `nor_filters()` actualizado: quitado toggle Métrica, agregados Universo (Base madura / Todos) y Forecast (No / Sí)
- `cb_nor.py` implementado: KPIs con colores, gráfico Plotly (NOR violeta + NRR verde + forecast punteado), tabla trazabilidad
- **Próximos pasos:**
  - [ ] Velocidad: warm-up agresivo de las 3 combinaciones al arrancar
  - [ ] Vista NDR/ODR — implementar cb_ndr.py
  - [ ] Vista NNR/NNO — implementar cb_nnr.py
  - [ ] Deploy

### Sesión 2026-04-11
- Vista Inputs completada y verificada con datos reales de Redshift
- Tabla rediseñada: 2 niveles con html.Div flex (sin DataTable) — nivel 1 cohorte-año + Total, nivel 2 drill-down inline al hacer click
- Query 01 simplificado (v3): eliminado JOIN fulfillment_type, D2C+B2B consolidados en SQL
- Filtro order_type eliminado del UI de Inputs (reducción de 9 a 3 combinaciones de cache)
- Unidades corregidas: MEX → K MXN (÷1,000), COL → MM COP (÷1,000,000)
- KPIs: tooltip en NNR/NNO, "Sellers activos" reemplaza "Sellers únicos", eliminado "Cohortes activas"
- Filter bar sticky; Métrica en fila horizontal; filtros alineados a la izquierda; solo año actual abierto por defecto

### Sesión 2026-04-08
- Excel analizado: 12 hojas, datos Dic 2020 a Dic 2025, ~3.735 sellers Colombia
- Código v4 en React documentado (Firebase + SheetJS) — tiene NDR, NOR e Inputs
- Glosario oficial definido: NNR, NNO, NRR, NOR, NDR, ODR, Rolling Forecast
- Corte pre/post 2025 confirmado. ODR = nombre interno para NDR en órdenes
- Preguntas de negocio definidas (ver `Cohortes/research/preguntas_negocio.md`)

### Sesión 2026-04-10
- Bug crítico resuelto: `dash.Dash(__name__)` en `app/__init__.py` buscaba assets en `app/assets/` — corregido con `assets_folder` apuntando a la raíz del proyecto
- Bug crítico resuelto: callbacks stub (cb_nor, cb_ndr, cb_nnr) usaban `raise Exception` en lugar de `raise PreventUpdate` — causaba errores en todas las navegaciones
- Bug corregido: nav item "Inputs" en sidebar apuntaba a `/` en lugar de `/inputs`
- Landing page verificada: logo Melonn, tarjeta "Consolidado" con mes cerrado/parcial, fondo lila
- Scaffold completo verificado: sidebar sticky, routing funcional, navegación sin errores
- Estrategia: construir hoja por hoja (landing ✅ → scaffold ✅ → inputs → NOR → NDR → NNR)
- **Próximos pasos:**
  - [ ] Vista Inputs — conectar cb_inputs.py al run.py
  - [ ] Vista NOR/NRR — implementar
  - [ ] Vista NDR/ODR — implementar
  - [ ] Vista NNR/NNO — implementar
  - [ ] Deploy

### Sesión 2026-04-09
- Schemas Redshift confirmados: core.data_warehouse, core.experience, staging.orbita, staging.profitability, staging.finance
- Fechas inicio del sistema: Feb 2021 (órdenes en staging.orbita); fact_sell_order solo desde Ene 2023 (descartado para órdenes)
- Arquitectura dual-source revenue: histórico (Feb 2021–Dic 2023) en staging.finance.financial_planning_historical_revenue; Redshift (Ene 2024+) desde profitability
- Tabla histórica creada y cargada: 63,862 rows, sellers COL + MEX × 37 meses
- Billing types mapeados: Intereses / Intereses WK → interest_arrears; Alistamiento → external_revenue
- lifecycle_month convenio: M1 = mes de entrada (DATEDIFF + 1)
- Queries 01 (órdenes) y 02 (revenue) validadas end-to-end contra Redshift — D3 OK, D4 OK
- **Próximos pasos:**
  - [ ] PRD completo con pantallas y flujos
  - [ ] Definir factor de estacionalidad NNR
  - [ ] App v2 (Dash + Redshift) — construir
  - [ ] Deploy
