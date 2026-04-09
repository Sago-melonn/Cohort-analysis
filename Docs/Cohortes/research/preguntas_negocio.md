# Preguntas de Negocio — App de Cohortes Melonn
> Estas preguntas definen las vistas y funcionalidades que debe tener la app.
> Sesión: 2026-04-08

---

## Pregunta 1 — NNR / NNO histórico

**¿Cuánto revenue nuevo y cuántas órdenes nuevas entraron cada mes?**

### Qué debe mostrar la app
- **Serie histórica de NNR** por mes de cohorte: cuánto revenue nuevo (avg M2+M3) trajo cada cohorte al negocio
- **Serie histórica de NNO** por mes de cohorte: ídem en órdenes
- **Run rate trimestral de NNR:** agrupación por trimestre del NNR acumulado — formato para informes de junta

### Usuario principal
Finance / Junta directiva

### Frecuencia de uso
Trimestral (informes de junta) + mensual (seguimiento interno)

### Filtros relevantes
País (COL / MEX / Consolidado), Segmento, Factor de estacionalidad

### Formato esperado
- Gráfico de barras: NNR por mes de cohorte (USD y moneda local)
- Tabla trimestral con run rate
- KPI destacado: NNR del último trimestre vs trimestre anterior

---

## Pregunta 2 — NRR / NOR: ¿están creciendo los clientes?

**¿Cuánto están creciendo YoY los clientes activos de Melonn?**

### Dos modos de análisis (toggle en la app)

#### Modo A — Rolling Agregado (default)
- Compara el mes actual T contra T-12, para todas las cohortes activas con ≥13 meses de vida
- **Default:** corte "Base" = Dic 2024 (configurable por el usuario)
- Ejemplo: en Mar 2026 → NOR = órdenes Mar 2026 de cohortes maduras / órdenes Mar 2025 de esas mismas cohortes
- El corte se puede mover: en 2027 podría ser "hasta Dic 2025"
- Funciona para: COL, MEX, Consolidado

#### Modo B — Análisis de Base Fija
- Fija un grupo específico de cohortes (ej. todos los sellers pre-2025) y analiza su comportamiento
- Usado para construir inputs del modelo financiero
- Permite ver la evolución de NRR y NOR de ese grupo a lo largo del tiempo

### Qué debe mostrar la app
- Línea de tiempo de NOR (y NRR) mensual, con indicación si > o < 100%
- Toggle: Modo Rolling / Modo Base Fija
- Selector de fecha de corte para la "Base"
- Vista por país (COL / MEX / Consolidado)

### Formato esperado
- Gráfico de línea: NOR % mensual (eje Y = %, línea de referencia en 100%)
- Card KPI: NOR último mes disponible
- Tabla de detalle: cohortes incluidas en el cálculo

---

## Pregunta 3 — Insights del Forecast

**¿El forecast actual tiene sentido? ¿Qué NRR / NDR implicaría si se cumple?**

### Qué debe mostrar la app
- Visualización unificada: datos **reales** (histórico) + datos **proyectados** (forecast) en la misma línea de tiempo
- Para clientes **pre-2025 (Base):** cómo se comportaría su NOR/NRR si el forecast se cumple mes a mes
- Para clientes **post-2025 (Nuevos):** cómo sería su ODR si el forecast se cumple
- **Señales de alerta:** si el forecast implica un NOR/NDR inconsistente con patrones históricos, marcarlo visualmente

### Casos de uso específicos
1. **Validar el forecast:** ¿el crecimiento proyectado en órdenes es consistente con la retención histórica?
2. **Pushback informado:** si el NOR implícito del forecast es 130% cuando históricamente es 105%, hay que cuestionar el forecast
3. **Sugerir inputs al modelo financiero:** con base en NOR/ODR histórico, proponer rangos razonables para el forecast

### Qué necesita la app para esto
- Acceso al forecast de órdenes por cliente hasta Dic 2026 (tabla Redshift)
- Join con datos históricos por seller para completar la serie temporal
- Mismo cálculo de NOR/ODR pero aplicado a datos forecast

### Formato esperado
- Gráfico de área / línea: real (sólido) + proyectado (punteado)
- Indicador: "NOR implícito del forecast: X% vs histórico: Y%"
- Alerta visual si la diferencia supera un umbral configurable

---

## Resumen de vistas de la app

| Vista | Métrica principal | Usuario | Toggle |
|---|---|---|---|
| NNR / NNO histórico | NNR, NNO por cohorte | Finance, Junta | País |
| NRR / NOR retención | NOR, NRR % mensual | Revenue Ops, Finance | Rolling vs Base Fija / País |
| NDR / ODR curvas | ODR, NDR por cohorte (heatmap) | Revenue Ops | País |
| Forecast insights | NOR/ODR proyectado vs real | Finance, Revenue Ops | País |
| Inputs (raw data) | Revenue/órdenes por cohorte | Analistas | País |
