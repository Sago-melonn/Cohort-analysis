-- ============================================================
-- QUERY 1: INPUTS DE ÓRDENES POR COHORTE (v3 — sin distinción D2C/B2B)
-- Proyecto: Cohortes Melonn
-- Propósito: Órdenes totales por seller × mes (D2C + B2B consolidados).
--            lifecycle_month para calcular NNO, NOR y ODR.
--
-- FUENTE: staging.orbita.sell_order (historia completa desde Feb 2021)
--         Fecha de referencia: MIN(action_date) en sell_order_log (state_id=2)
--         = items_reservation_date, convertida al timezone de la bodega.
--
-- CONVENCIÓN DE MESES:
--   M1 = mes de entrada del seller (cohort_month) → lifecycle_month = 1
--   M2 = segundo mes                              → lifecycle_month = 2
--   NNO  = avg(orders_M2, orders_M3)
--   ODR  = orders_Mn / orders_M1
--   NOR  = cohortes con lifecycle_month >= 13
--
-- FILTROS CONFIGURABLES (inyectados por data_loader._inject_filters):
--   segment_filter : segmentos activos (default: Starter, Plus, Top, Enterprise)
--   include_churn  : TRUE = incluir sellers con churn, FALSE = excluir
--   country_filter : 1 = COL, 2 = MEX, NULL = ambos
-- ============================================================

WITH

-- ── PARÁMETROS ───────────────────────────────────────────────────────────────
params AS (
    SELECT
        ARRAY['Starter', 'Plus', 'Top', 'Enterprise'] AS segment_filter,
        TRUE          AS include_churn,
        NULL::INTEGER AS country_filter
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
        CASE WHEN s.state <> 'Active' THEN 1 ELSE 0 END AS churn_flag
    FROM core.data_warehouse.dim_seller s
    CROSS JOIN params p
    WHERE
        s.segment         = ANY(p.segment_filter)
        AND (p.country_filter IS NULL OR s.country_id = p.country_filter)
        AND (p.include_churn  OR s.state = 'Active')
        AND s.cohort IS NOT NULL
),

-- ── ÓRDENES TOTALES (D2C + B2B consolidadas) ─────────────────────────────────
-- Se elimina el JOIN con fulfillment_type — se cuentan todas las órdenes
-- sin distinguir tipo. Fecha de referencia: items_reservation_date.
orders AS (
    SELECT
        so.seller_id,
        DATE_TRUNC('month',
            CONVERT_TIMEZONE('UTC', w.timezone_code, iri.date)
        )::DATE      AS order_month,
        COUNT(so.id) AS order_count
    FROM staging.orbita.sell_order AS so
    INNER JOIN staging.orbita.warehouse AS w
        ON so.assigned_warehouse_id = w.id
    INNER JOIN (
        SELECT sell_order_id, MIN(action_date) AS date
        FROM staging.orbita.sell_order_log
        WHERE sell_order_state_id = 2
        GROUP BY sell_order_id
    ) AS iri
        ON so.id = iri.sell_order_id
    WHERE
        w.operated_by_melonn = 1
        AND iri.date IS NOT NULL
    GROUP BY
        so.seller_id,
        order_month
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
        o.order_count,
        DATEDIFF('month', s.cohort_month, o.order_month) + 1 AS lifecycle_month
    FROM sellers s
    JOIN orders o
        ON  s.seller_id   = o.seller_id
        AND o.order_month >= s.cohort_month
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
    lifecycle_month,
    order_count
FROM cohort_orders
ORDER BY
    cohort_month,
    seller_id,
    order_month;

-- ============================================================
-- NOTAS:
--   v4 (2026-04-15): churn_flag y filtro include_churn usan s.state <> 'Active'
--                    en lugar de churn_date IS NOT NULL. Sellers que volvieron
--                    (churn_date poblada pero state = 'Active') ya no cuentan como churn.
--   v3 (2026-04-11): eliminado JOIN fulfillment_type y columna order_type.
--                    Órdenes D2C + B2B consolidadas en SQL.
--   v2: usaba staging.orbita.sell_order (historia completa desde Feb 2021)
--   v1: usaba core.data_warehouse.fact_sell_order (solo desde Ene 2023)
-- ============================================================
