-- ============================================================
-- SCRIPT DE VALIDACIÓN — Redshift
-- Proyecto: Cohortes Melonn
-- Propósito: Confirmar existencia de tablas, columnas y
--            datos relevantes antes de ejecutar los queries
--            de inputs (01 y 02).
--
-- Instrucciones:
--   1. Correr cada bloque por separado en tu cliente SQL
--   2. Si alguna query falla → identificar nombre real
--   3. Reportar resultados para actualizar los queries
-- ============================================================


-- ============================================================
-- SECCIÓN A: TABLAS DE REFERENCIA (dim_seller, fact_sell_order)
-- ============================================================


-- A3: ¿Qué países existen (country_id y country_name)?
SELECT DISTINCT country_id, country_name
FROM core.data_warehouse.dim_seller
ORDER BY country_id;

-- A4: ¿El campo cohort es TIMESTAMP o DATE? ¿Hay sellers sin cohorte?
SELECT
    COUNT(*)                        AS total_sellers,
    COUNT(cohort)                   AS con_cohorte,
    MIN(DATE_TRUNC('month', cohort)) AS cohorte_mas_antigua,
    MAX(DATE_TRUNC('month', cohort)) AS cohorte_mas_reciente
FROM core.data_warehouse.dim_seller
WHERE segment IN ('Starter', 'Plus', 'Top', 'Enterprise');

-- A5: fact_sell_order — ¿columnas y filtros de fecha disponibles?
SELECT
    seller_id,
    items_reservation_date,   -- ← confirmar nombre exacto
    order_type,               -- ← confirmar: 'D2C' / 'B2B'?
    id
FROM core.data_warehouse.fact_sell_order
LIMIT 5;

-- A6: ¿Qué valores tiene order_type en fact_sell_order?
SELECT DISTINCT order_type, COUNT(*) AS orders
FROM core.data_warehouse.fact_sell_order
GROUP BY order_type;


-- ============================================================
-- SECCIÓN B: TABLAS ORBITA (base de Rentabilidad_master)
-- ============================================================

-- B1: orbita.warehouse — ¿existe? ¿columnas clave?
SELECT id, name, operated_by_melonn, timezone_code, country
FROM staging.orbita.warehouse
LIMIT 5;

-- B2: Warehouses activos Melonn (expected: Medellín, Bogotá, CDMX, etc.)
SELECT id, name, country, operated_by_melonn
FROM staging.orbita.warehouse
WHERE operated_by_melonn = 1 OR id IN (3, 8)
ORDER BY id;

-- B3: orbita.seller — ¿columna seller_state_id?
SELECT id, name, seller_state_id
FROM staging.orbita.seller
LIMIT 5;

-- B4: ¿Qué valores tiene seller_state_id? (esperados: 2, 3, 9, 10 = activos)
SELECT seller_state_id, COUNT(*) AS sellers
FROM staging.orbita.seller
GROUP BY seller_state_id
ORDER BY seller_state_id;

-- B5: orbita.seller_warehouse_configuration — ¿existe y tiene el join correcto?
SELECT warehouse_id, seller_id
FROM staging.orbita.seller_warehouse_configuration
LIMIT 5;

-- B6: orbita.warehouse_calendar — ¿tiene fechas desde 2020-12-01?
SELECT
    MIN(date) AS fecha_min,
    MAX(date) AS fecha_max,
    COUNT(*)  AS total_dias
FROM staging.orbita.warehouse_calendar;

-- B7: orbita.sell_order — columnas clave
SELECT
    id,
    internal_order_number,
    seller_id,
    assigned_warehouse_id,
    fulfillment_type_id,
    sell_order_state_id
FROM staging.orbita.sell_order
LIMIT 5;

-- B8: orbita.sell_order_log — ¿state_id 2 = items_reservados?
SELECT DISTINCT sell_order_state_id, COUNT(*) AS logs
FROM staging.orbita.sell_order_log
GROUP BY sell_order_state_id
ORDER BY sell_order_state_id;

-- B9: orbita.fulfillment_type — ¿order_type = 'D2C' / 'B2B'?
SELECT DISTINCT id, order_type
FROM staging.orbita.fulfillment_type;

-- B10: orbita.buyer_return_order — para devoluciones
SELECT id, assigned_warehouse_id, seller_id
FROM staging.orbita.buyer_return_order
LIMIT 5;

-- B11: orbita.supplier_order — para inbound
SELECT internal_order_number, destination_warehouse_id, seller_id
FROM staging.orbita.supplier_order
LIMIT 5;


-- ============================================================
-- SECCIÓN C: TABLAS PROFITABILITY (Rentabilidad_master)
-- ============================================================


-- C1: revenue real por orden
SELECT internal_order_number, picking_charge, packing_charge,
       estimated_picking_revenue  -- ← confirmar que existe este campo
FROM staging.profitability.sell_order_revenue
LIMIT 3;

SELECT *
FROM staging.profitability.estimated_sell_order_revenue
LIMIT 1;

-- C3: profitability.returns_revenue — devoluciones
SELECT
    date_of_billing,
    internal_order_number,
    anti_picking_charge,
    anti_shipping_charge
FROM staging.profitability.returns_revenue
LIMIT 3;

-- C4: profitability.warehousing_revenue — warehousing real
SELECT
    date_of_billing,
    warehouse_id,
    seller_id,
    storage_charge,
    revenue_space,
    storage_insurance_charge,
    storage_charge_discount
FROM staging.profitability.warehousing_revenue
LIMIT 3;

-- C5: profitability.inbound_revenue — inbound real
SELECT
    date_of_billing,
    internal_order_number,
    supplier_order_charge,
    supplier_order_discount
FROM staging.profitability.inbound_revenue
LIMIT 3;

-- C6: profitability.estimated_daily_charges — fallback warehousing + saas
SELECT
    date,
    warehouse_id,
    seller_id,
    estimated_net_charge_storage,
    estimated_net_charge_storage_coverage,
    estimated_net_charge_fee
FROM staging.profitability.estimated_daily_charges
LIMIT 3;

-- C7: profitability.external_revenue — SaaS real, VAS, intereses
SELECT DISTINCT billing_type
FROM staging.profitability.external_revenue
ORDER BY billing_type;
-- Expected: 'Intereses mora', 'Servicios adicionales', 'Empaque',
--           'Transporte', 'Seller support', 'Facturacion Minima', 'Fee Mensual'

-- C8: profitability.adjecencies_revenue
SELECT
    date,
    warehouse_id,
    seller_id,
    adjecencies_charge
FROM staging.profitability.adjecencies_revenue
LIMIT 3;

-- C9: profitability.credit_notes
SELECT
    date_of_billing,
    warehouse_id,
    seller_id,
    amount
FROM staging.profitability.credit_notes
LIMIT 3;


-- ============================================================
-- SECCIÓN D: VALIDACIÓN DE DATOS (end-to-end liviano)
-- ============================================================

-- D1: ¿Cuántos sellers elegibles hay por país y segmento?
SELECT
    country_id,
    country_name,
    segment,
    COUNT(*)                        AS total_sellers,
    MIN(DATE_TRUNC('month', cohort)) AS primera_cohorte,
    MAX(DATE_TRUNC('month', cohort)) AS ultima_cohorte
FROM core.data_warehouse.dim_seller
WHERE segment IN ('Starter', 'Plus', 'Top', 'Enterprise')
  AND cohort IS NOT NULL
GROUP BY country_id, country_name, segment
ORDER BY country_id, segment;

-- D2: ¿Hay órdenes en fact_sell_order desde Dic 2020?
SELECT
    DATE_TRUNC('month', items_reservation_date)::DATE AS mes,
    COUNT(*) AS ordenes
FROM core.data_warehouse.fact_sell_order
WHERE mes = '2023-01-01'
  -- AND items_reservation_date IS NOT NULL
GROUP BY mes
ORDER BY mes asc
LIMIT 100;

-- D3: Join dim_seller ↔ orbita.sell_order (historia completa desde Feb 2021)
SELECT
    s.id            AS seller_id,
    s.segment,
    DATE_TRUNC('month', s.cohort)::DATE AS cohort_month,
    COUNT(so.id)    AS total_orders
FROM core.data_warehouse.dim_seller s
         JOIN staging.orbita.sell_order so
              ON s.id = so.seller_id
         INNER JOIN staging.orbita.warehouse w
                    ON so.assigned_warehouse_id = w.id
         INNER JOIN (
    SELECT sell_order_id, MIN(action_date) AS date
    FROM staging.orbita.sell_order_log
    WHERE sell_order_state_id = 2
    GROUP BY sell_order_id
) iri ON so.id = iri.sell_order_id
WHERE s.segment IN ('Starter', 'Plus', 'Top', 'Enterprise')
  AND w.operated_by_melonn = 1
  AND iri.date IS NOT NULL
GROUP BY s.id, s.segment, cohort_month
ORDER BY total_orders DESC
LIMIT 10;


-- D3: ¿El join dim_seller ↔ fact_sell_order funciona?
SELECT
    s.id            AS seller_id,
    s.segment,
    DATE_TRUNC('month', s.cohort)::DATE AS cohort_month,
    COUNT(o.id)     AS total_orders
FROM core.data_warehouse.dim_seller s
JOIN core.data_warehouse.fact_sell_order o ON s.id = o.seller_id
WHERE s.segment IN ('Starter', 'Plus', 'Top', 'Enterprise')
  AND o.items_reservation_date >= '2020-12-01'
  AND o.items_reservation_date IS NOT NULL
GROUP BY s.id, s.segment, cohort_month
ORDER BY total_orders DESC
LIMIT 10;

-- D4: Mini-test de revenue — ¿hay datos en sell_order_revenue o estimated?
-- (para un mes reciente conocido, ej. 2025-11-01)
SELECT
    DATE_TRUNC('month', CONVERT_TIMEZONE('UTC', w.timezone_code,
        iri.date))::DATE            AS mes,
    so.seller_id,
    COUNT(so.id)                    AS ordenes,
    SUM(CASE WHEN sor.internal_order_number IS NOT NULL
             THEN sor.picking_charge
             ELSE COALESCE(esor.picking_revenue, 0) END) AS picking_rev_estimado
FROM staging.orbita.sell_order so
INNER JOIN staging.orbita.sell_order_state sos ON so.sell_order_state_id = sos.id
INNER JOIN (
    SELECT sell_order_id, MIN(action_date) AS date
    FROM staging.orbita.sell_order_log
    WHERE sell_order_state_id = 2
    GROUP BY sell_order_id
) iri ON so.id = iri.sell_order_id
INNER JOIN staging.orbita.warehouse w ON so.assigned_warehouse_id = w.id
LEFT JOIN staging.profitability.sell_order_revenue sor
    ON so.internal_order_number = sor.internal_order_number
LEFT JOIN staging.profitability.estimated_sell_order_revenue esor
    ON so.internal_order_number = esor.internal_order_number
WHERE w.operated_by_melonn = 1
  AND iri.date >= '2025-10-01'
  AND iri.date <  '2025-12-01'
GROUP BY mes, so.seller_id
ORDER BY picking_rev_estimado DESC
LIMIT 10;

-- ============================================================
-- SECCIÓN E: POSIBLES ISSUES A CONFIRMAR
-- ============================================================

-- E1: ¿dim_seller.cohort se puede hacer DATE_TRUNC('month', ...)?
--     (falla si el campo es VARCHAR — necesitaría ::TIMESTAMP)
SELECT DATE_TRUNC('month', cohort)::DATE AS cohort_month
FROM core.data_warehouse.dim_seller
WHERE cohort IS NOT NULL
LIMIT 1;

-- E2: ¿items_reservation_date en fact_sell_order es TIMESTAMP o DATE?
SELECT
    items_reservation_date,
    pg_typeof(items_reservation_date) AS tipo
FROM core.data_warehouse.fact_sell_order
WHERE items_reservation_date IS NOT NULL
LIMIT 1;

-- E3: ¿sell_order_log.action_date es TIMESTAMP?
SELECT
    action_date,
    pg_typeof(action_date) AS tipo
FROM staging.orbita.sell_order_log
LIMIT 1;

-- E4: ¿warehousing_revenue.date_of_billing coincide en formato
--     con estimated_daily_charges.date?
SELECT 'warehousing_revenue'   AS tabla, MAX(date_of_billing) AS fecha_max FROM staging.profitability.warehousing_revenue
UNION ALL
SELECT 'estimated_daily_charges', MAX(date)          AS fecha_max FROM staging.profitability.estimated_daily_charges
UNION ALL
SELECT 'external_revenue',         MAX(date_of_billing) AS fecha_max FROM staging.profitability.external_revenue;

sql
SELECT
    MIN(date_of_billing) AS revenue_desde,
    MAX(date_of_billing) AS revenue_hasta
FROM staging.profitability.warehousing_revenue;


-- D4: Mini-test revenue — histórico vs Redshift
-- Histórico (pre-2024)
SELECT
    'historico'         AS fuente,
    h.date              AS mes,
    COUNT(DISTINCT h.seller_id) AS sellers,
    ROUND(SUM(h.total_revenue) / 1e6, 2) AS revenue_MM
FROM staging.finance.financial_planning_historical_revenue h
WHERE h.date BETWEEN '2023-10-01' AND '2023-12-01'
GROUP BY h.date
ORDER BY h.date

    UNION ALL

-- Redshift (post-2024, usando sell_order_revenue + estimated como fallback)
SELECT
    'redshift'          AS fuente,
    DATE_TRUNC('month', CONVERT_TIMEZONE('UTC', w.timezone_code, iri.date))::DATE AS mes,
    COUNT(DISTINCT so.seller_id) AS sellers,
    ROUND(SUM(
                  COALESCE(sor.picking_charge, esor.picking_revenue, 0)
          ) / 1e6, 2) AS revenue_MM   -- solo picking como proxy rápido
FROM staging.orbita.sell_order so
         INNER JOIN staging.orbita.warehouse w ON so.assigned_warehouse_id = w.id
         INNER JOIN (
    SELECT sell_order_id, MIN(action_date) AS date
    FROM staging.orbita.sell_order_log
    WHERE sell_order_state_id = 2
    GROUP BY sell_order_id
) iri ON so.id = iri.sell_order_id
         LEFT JOIN staging.profitability.sell_order_revenue sor
                   ON so.internal_order_number = sor.internal_order_number
         LEFT JOIN staging.profitability.estimated_sell_order_revenue esor
                   ON so.internal_order_number = esor.internal_order_number
WHERE w.operated_by_melonn = 1
  AND iri.date BETWEEN '2024-01-01' AND '2024-03-31'
GROUP BY mes
ORDER BY mes;

-- D5: Verificar forecast — top sellers por órdenes forecasted
WITH latest_version AS (
    SELECT MAX(version_id) AS version_id
    FROM core.forecast.official_forecast_temp
),

     forecast_monthly AS (
         SELECT
             f.seller_id,
             DATE_TRUNC('month', f.date)::DATE AS forecast_month,
             SUM(f.forecasted_orders)          AS forecasted_orders
         FROM core.forecast.official_forecast_temp f
                  INNER JOIN latest_version lv ON f.version_id = lv.version_id
         GROUP BY f.seller_id, DATE_TRUNC('month', f.date)::DATE
     )

SELECT
    fm.seller_id,
    DATE_TRUNC('month', s.cohort)::DATE AS cohort_month,
    s.segment,
    SUM(fm.forecasted_orders)           AS total_forecast_orders,
    COUNT(DISTINCT fm.forecast_month)   AS meses_con_forecast
FROM forecast_monthly fm
         INNER JOIN core.data_warehouse.dim_seller s
                    ON fm.seller_id = s.id
WHERE s.segment IN ('Starter', 'Plus', 'Top', 'Enterprise')
GROUP BY fm.seller_id, DATE_TRUNC('month', s.cohort)::DATE, s.segment
ORDER BY total_forecast_orders DESC
LIMIT 10;