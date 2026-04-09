-- ============================================================
-- QUERY 1: INPUTS DE ÓRDENES POR COHORTE (v2 — Orbita full history)
-- Proyecto: Cohortes Melonn
-- Propósito: Genera la tabla de órdenes por seller × mes,
--            con lifecycle_month para calcular NNO, NOR y ODR.
--
-- FUENTE: staging.orbita.sell_order (historia completa desde Feb 2021)
--         La fecha de referencia se toma de sell_order_log (state_id=2)
--         que captura el momento en que los ítems fueron reservados.
--         staging.orbita.fulfillment_type para order_type (D2C / B2B).
--
-- CONVENCIÓN DE MESES:
--   M1 = mes de entrada del seller (cohort_month) → lifecycle_month = 1
--   M2 = segundo mes                              → lifecycle_month = 2
--   M3 = tercer mes                               → lifecycle_month = 3
--   NNO  = avg(orders_M2, orders_M3) → lifecycle_month IN (2, 3)
--   ODR  = orders_Mn / orders_M1    → base = lifecycle_month = 1
--   NOR  = cohortes con lifecycle_month >= 13
--
-- FILTROS CONFIGURABLES:
--   order_type_filter : 'D2C', 'B2B', o NULL (ambos)
--   segment_filter    : segmentos activos (default: Starter, Plus, Top, Enterprise)
--   include_churn     : TRUE = incluir sellers con churn, FALSE = excluir
--   country_filter    : 1 = COL, 2 = MEX, NULL = ambos
-- ============================================================

WITH

-- ── PARÁMETROS ───────────────────────────────────────────────────────────────
params AS (
    SELECT
        ARRAY['Starter', 'Plus', 'Top', 'Enterprise'] AS segment_filter,
        TRUE                                           AS include_churn,
        NULL::INTEGER                                  AS country_filter,    -- NULL = ambos
        NULL::VARCHAR                                  AS order_type_filter  -- NULL = D2C+B2B
),

-- ── SELLERS ELEGIBLES ────────────────────────────────────────────────────────
sellers AS (
    SELECT
        s.id                                                 AS seller_id,
        s.name                                               AS seller_name,
        s.segment,
        s.country_id,
        s.country_name,
        DATE_TRUNC('month', s.cohort)::DATE                  AS cohort_month,
        CASE WHEN s.churn_date IS NOT NULL THEN 1 ELSE 0 END AS churn_flag
    FROM core.data_warehouse.dim_seller s
    CROSS JOIN params p
    WHERE
        s.segment         = ANY(p.segment_filter)
        AND (p.country_filter IS NULL OR s.country_id = p.country_filter)
        AND (p.include_churn  OR s.churn_date IS NULL)
        AND s.cohort IS NOT NULL
),

-- ── ÓRDENES DESDE ORBITA (historia completa) ─────────────────────────────────
-- Fecha de referencia: MIN(action_date) del sell_order_log con state_id = 2
-- (momento en que los ítems fueron reservados = items_reservation_date)
-- Se convierte a timezone de la bodega para agrupar por mes correctamente.
orders AS (
    SELECT
        so.seller_id,
        DATE_TRUNC('month',
            CONVERT_TIMEZONE('UTC', w.timezone_code, iri.date)
        )::DATE                                              AS order_month,
        ft.order_type,                                       -- 'D2C' | 'B2B'
        COUNT(so.id)                                         AS order_count
    FROM staging.orbita.sell_order AS so
    INNER JOIN staging.orbita.fulfillment_type AS ft
        ON so.fulfillment_type_id = ft.id
    INNER JOIN staging.orbita.warehouse AS w
        ON so.assigned_warehouse_id = w.id
    INNER JOIN (
        SELECT sell_order_id, MIN(action_date) AS date
        FROM staging.orbita.sell_order_log
        WHERE sell_order_state_id = 2
        GROUP BY sell_order_id
    ) AS iri
        ON so.id = iri.sell_order_id
    CROSS JOIN params p
    WHERE
        w.operated_by_melonn = 1
        AND iri.date IS NOT NULL
        AND (p.order_type_filter IS NULL OR ft.order_type = p.order_type_filter)
    GROUP BY
        so.seller_id,
        order_month,
        ft.order_type
),

-- ── UNIR SELLERS CON ÓRDENES Y CALCULAR MES DE VIDA ──────────────────────────
cohort_orders AS (
    SELECT
        s.seller_id,
        s.seller_name,
        s.segment,
        s.country_id,
        s.country_name,
        s.cohort_month,
        s.churn_flag,
        o.order_month,
        o.order_type,
        o.order_count,
        -- M1 = mes de entrada, M2 = siguiente, M3 = ...
        -- DATEDIFF da 0 en el mes de entrada → sumamos 1
        DATEDIFF('month', s.cohort_month, o.order_month) + 1 AS lifecycle_month
    FROM sellers s
    JOIN orders o
        ON  s.seller_id   = o.seller_id
        AND o.order_month >= s.cohort_month   -- solo desde el ingreso
)

-- ── RESULTADO FINAL ───────────────────────────────────────────────────────────
SELECT
    seller_id,
    seller_name,
    segment,
    country_id,
    country_name,
    cohort_month,
    churn_flag,
    order_month,
    order_type,
    lifecycle_month,
    order_count
FROM cohort_orders
ORDER BY
    cohort_month,
    seller_id,
    order_month;

-- ============================================================
-- NOTAS DE USO:
--   NNO  → lifecycle_month IN (2, 3), AVG(order_count) por cohorte
--   NOR  → agregar por order_month, filtrar lifecycle_month >= 13
--   ODR  → base = lifecycle_month = 1, curva M1→Mn por cohort_month
--
-- FUENTE vs VERSIÓN ANTERIOR:
--   v1 usaba core.data_warehouse.fact_sell_order (solo desde Ene 2023)
--   v2 usa staging.orbita.sell_order (historia completa desde Feb 2021)
-- ============================================================
