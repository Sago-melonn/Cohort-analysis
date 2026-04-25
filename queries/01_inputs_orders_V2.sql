-- ============================================================
-- QUERY 1 V2: INPUTS DE ÓRDENES POR COHORTE (sin filtros — carga completa)
-- Proyecto: Cohortes Melonn
-- Propósito: Órdenes totales por seller × mes (D2C + B2B consolidados).
--            Sin params CTE — todos los filtros se aplican en Python
--            por data_loader._load_orders_raw() → load_orders().
--
-- FUENTE: staging.orbita.sell_order (historia completa desde Feb 2021)
--         Fecha de referencia: MIN(action_date) en sell_order_log (state_id=2)
--         = items_reservation_date, convertida al timezone de la bodega.
--
-- CONVENCIÓN DE MESES:
--   M1 = mes de entrada del seller (cohort_month) → lifecycle_month = 1
--   M2 = segundo mes                              → lifecycle_month = 2
--
-- Filtros aplicados en Python (data_loader.py):
--   segments      : df[df["segment"].isin(expanded)]
--   country_id    : df[df["country_id"] == country_id]
--   include_churn : df[df["churn_flag"] == 0]
-- ============================================================

WITH

-- ── SELLERS (sin filtros — todos con cohorte asignada) ───────────────────────
sellers AS (
    SELECT
        s.id                                                 AS seller_id,
        s.name                                               AS seller_name,
        s.segment,
        s.country_id,
        s.country_name,
        DATE_TRUNC('month', s.cohort)::DATE                  AS cohort_month,
        CASE WHEN s.state <> 'Active' THEN 1 ELSE 0 END      AS churn_flag
    FROM core.data_warehouse.dim_seller s
    WHERE s.cohort IS NOT NULL
),

-- ── ÓRDENES TOTALES (D2C + B2B consolidadas) ─────────────────────────────────
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
