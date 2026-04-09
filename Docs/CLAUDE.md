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

**Fórmula:**
```
NRR(mes_t) = Σ Revenue(cohortes entrada ≤ mes_t - 12 meses, en mes_t)
             / Σ Revenue(cohortes entrada ≤ mes_t - 13 meses, en mes_t - 12)
```
- Ejemplo para Dic 2025: num = revenue en Dic 2025 de cohortes que entraron ≤ Dic 2024; den = revenue en Dic 2024 de esas mismas cohortes
- Resultado tipo 110% = clientes crecen YoY

**Aplica a:** Clientes **pre-2025** ("Base")

**Nota:** NRR puede estar inflado por aumentos de precio, nuevos servicios cobrados, cambios de comportamiento. Por eso se complementa con NOR.

---

### NOR — Net Order Retention
**Qué es:** Igual que NRR pero en órdenes. Métrica preferida por ser más limpia.

**Fórmula:**
```
NOR(mes_t) = Σ Orders_smooth(cohortes edad > 12m, en mes_t)
             / Σ Orders_smooth(cohortes edad > 12m, en mes_t - 12)
```
- Aplica **suavizado de 3 períodos** antes del cálculo (promedio de los últimos 3 meses con valor > 0)
- Solo cohortes con ≥13 meses de historia

**Aplica a:** Clientes **pre-2025** ("Base")

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
| `churn_date` | `IS NOT NULL` → churn_flag = 1 |

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
| App v2 (Dash + Redshift) | 🔴 Pendiente | |
| Deploy | 🔴 Pendiente | |

---

## 📝 DECISIONES TOMADAS

| Fecha | Decisión |
|---|---|
| 2026-04-08 | Cohorte = mes de primera facturación del seller |
| 2026-04-08 | Segmentos activos: Starter, Plus, Top, Enterprise (Tiny excluido por default) |
| 2026-04-08 | Hitos de retención clave: M13 y M25 |
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

### Sesión 2026-04-08
- Excel analizado: 12 hojas, datos Dic 2020 a Dic 2025, ~3.735 sellers Colombia
- Código v4 en React documentado (Firebase + SheetJS) — tiene NDR, NOR e Inputs
- Glosario oficial definido: NNR, NNO, NRR, NOR, NDR, ODR, Rolling Forecast
- Corte pre/post 2025 confirmado. ODR = nombre interno para NDR en órdenes
- Preguntas de negocio definidas (ver `Cohortes/research/preguntas_negocio.md`)

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
