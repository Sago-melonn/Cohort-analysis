-- ============================================================
-- QUERY 2: INPUTS DE REVENUE POR COHORTE (v3 — Dual Source)
-- Proyecto: Cohortes Melonn
-- Propósito: Genera el revenue total P&L por seller × mes,
--            con lifecycle_month para calcular NNR, NRR y NDR.
--
-- FUENTES:
--   Feb 2021 – Dic 2023 → staging.profitability.cohort_revenue_historico
--                          (cargado desde Excel via script 02_load_historical_revenue.py)
--   Ene 2024 – hoy      → Redshift (staging.profitability.* / staging.orbita.*)
--   Resultado final     → UNION ALL de ambas fuentes
--
-- CONVENCIÓN DE MESES (igual que 01_inputs_orders):
--   M1 = mes de entrada del seller (cohort_month) → lifecycle_month = 1
--   M2 = segundo mes                              → lifecycle_month = 2
--   M3 = tercer mes                               → lifecycle_month = 3
--   NNR  = avg(Rev_M2, Rev_M3) → lifecycle_month IN (2, 3)
--   NDR  = Rev_Mn / Rev_M1    → base = lifecycle_month = 1
--   NRR  = cohortes con lifecycle_month >= 13
--
-- FILTROS CONFIGURABLES:
--   order_type_filter    : 'D2C', 'B2B', o NULL (ambos) — solo afecta Redshift (Ene 2024+)
--   segment_filter       : segmentos activos (default: Starter, Plus, Top, Enterprise)
--   include_churn        : TRUE = incluir sellers con churn, FALSE = excluir
--   country_filter       : 1 = COL, 2 = MEX, NULL = ambos
--   include_credit_notes : TRUE = incluye ajuste de credit notes, FALSE = excluye (default)
--
-- LÓGICA REAL vs ESTIMADO (Ene 2024+ desde Redshift):
--   Fulfillment : estimated_* ya aplica COALESCE(real, estimado) A NIVEL DE ORDEN
--   Warehousing : CASE WHEN real IS NOT NULL THEN real ELSE estimado (por bodega × mes)
--   SaaS        : CASE WHEN real IS NOT NULL THEN real ELSE estimado (por bodega × mes)
--   Histórico   : revenue total (sin desglose por componente)
-- ============================================================

WITH

-- ── PARÁMETROS ───────────────────────────────────────────────────────────────
params AS (
    SELECT
        ARRAY['Starter', 'Plus', 'Top', 'Enterprise'] AS segment_filter,
        TRUE                                           AS include_churn,
        NULL::INTEGER                                  AS country_filter,     -- NULL = COL + MEX
        NULL::VARCHAR                                  AS order_type_filter,  -- NULL = D2C + B2B
        FALSE                                          AS include_credit_notes -- default: excluir
),

-- ── SELLERS ELEGIBLES ────────────────────────────────────────────────────────
sellers AS (
    SELECT
        s.id                                                       AS seller_id,
        s.name                                                     AS seller_name,
        s.segment,
        s.country_id,
        s.country_name,
        DATE_TRUNC('month', s.cohort)::DATE                        AS cohort_month,
        CASE WHEN s.churn_date IS NOT NULL THEN 1 ELSE 0 END       AS churn_flag
    FROM core.data_warehouse.dim_seller s
    CROSS JOIN params p
    WHERE
        s.segment = ANY(p.segment_filter)
        AND (p.country_filter IS NULL OR s.country_id = p.country_filter)
        AND (p.include_churn  OR s.churn_date IS NULL)
        AND s.cohort IS NOT NULL
),

-- ============================================================
-- SUBQUERY RENTABILIDAD OPTIMIZADO
-- Solo componentes de revenue — sin JOINs de costo.
-- Granularidad: seller_id × warehouse_id × year_month_date
-- ============================================================
rentabilidad AS (
    SELECT
        rd.seller_id,
        rd.warehouse_id,
        rd.year_month_date,

        -- ── FULFILLMENT ──────────────────────────────────────────────────────
        -- Los campos estimated_* ya aplican COALESCE(real, estimado) a nivel de orden
        -- dentro del subquery de profitability.sell_order_revenue / estimated_sell_order_revenue.
        -- NO se re-aplica COALESCE aquí: se usan los campos estimated_* directamente.

        -- Total (D2C + B2B)
        COALESCE(fulf.estimated_picking_revenue,                0)
          + COALESCE(fulf.estimated_packaging_revenue,          0)
          + COALESCE(fulf.estimated_payment_on_delivery_revenue,0)
          + COALESCE(fulf.estimated_transport_revenue,          0)
          + COALESCE(fulf.estimated_transport_insurance_revenue,0)
          - COALESCE(fulf.estimated_discount,                   0)   AS fulfillment_revenue,

        -- Solo D2C (para filtro order_type_filter = 'D2C')
        COALESCE(fulf.d2c_estimated_picking_revenue,                0)
          + COALESCE(fulf.d2c_estimated_packaging_revenue,          0)
          + COALESCE(fulf.d2c_estimated_payment_on_delivery_revenue,0)
          + COALESCE(fulf.d2c_estimated_transport_revenue,          0)
          + COALESCE(fulf.d2c_estimated_transport_insurance_revenue,0)
          - COALESCE(fulf.d2c_estimated_discount,                   0) AS d2c_fulfillment_revenue,

        -- Solo B2B (para filtro order_type_filter = 'B2B')
        COALESCE(fulf.b2b_estimated_picking_revenue,                0)
          + COALESCE(fulf.b2b_estimated_packaging_revenue,          0)
          + COALESCE(fulf.b2b_estimated_payment_on_delivery_revenue,0)
          + COALESCE(fulf.b2b_estimated_transport_revenue,          0)
          + COALESCE(fulf.b2b_estimated_transport_insurance_revenue,0)
          - COALESCE(fulf.b2b_estimated_discount,                   0) AS b2b_fulfillment_revenue,

        -- ── DEVOLUCIONES ─────────────────────────────────────────────────────
        COALESCE(ret.anti_picking_charge,  0)
          + COALESCE(ret.anti_shipping_charge, 0)                     AS returns_revenue,

        -- ── WAREHOUSING (real → estimado por bodega × mes) ───────────────────
        -- Warehousing revenue: CASE WHEN real IS NOT NULL THEN real ELSE estimado
        COALESCE(wr.warehousing_revenue,          edc.estimated_warehousing_revenue,          0)
          + COALESCE(wr.warehousing_insurance_revenue, edc.estimated_warehousing_insurance_revenue, 0)
          - COALESCE(wr.warehousing_discount,     0)                  AS warehousing_revenue,

        -- ── INBOUND ──────────────────────────────────────────────────────────
        COALESCE(ir.inbound_revenue, 0)
          - COALESCE(ir.inbound_discount, 0)                          AS inbound_revenue,

        -- ── SAAS (real → estimado por bodega × mes) ──────────────────────────
        COALESCE(er.saas, edc.ex_estimated_saas, 0)                   AS saas_revenue,

        -- ── EXTERNOS Y ADYACENCIAS ───────────────────────────────────────────
        COALESCE(er.interest_arrears,        0)
          + COALESCE(er.vas,               0)
          + COALESCE(er.packaging_revenue, 0)
          + COALESCE(er.transport_revenue, 0)
          + COALESCE(er.seller_support_revenue, 0)
          + COALESCE(er.alistamiento_revenue,   0)                    AS external_revenue,

        COALESCE(ar.adjecencies_revenue,   0)                         AS adjecencies_revenue,

        -- ── CREDIT NOTES ─────────────────────────────────────────────────────
        COALESCE(cn.credit_notes_amount,   0)                         AS credit_notes_amount

    FROM (
        -- ── BASE: seller × warehouse × mes ──────────────────────────────────
        -- Grid completo para preservar meses con Warehousing/SaaS pero sin órdenes.
        SELECT
            w.id    AS warehouse_id,
            s.id    AS seller_id,
            DATE_TRUNC('MONTH', wc.date)::DATE AS year_month_date
        FROM staging.orbita.warehouse AS w
        CROSS JOIN staging.orbita.seller AS s
        INNER JOIN staging.orbita.seller_warehouse_configuration AS swc
            ON (w.id = swc.warehouse_id OR w.id IN (3, 8))
            AND s.id = swc.seller_id
        CROSS JOIN (
            SELECT DATE_TRUNC('MONTH', wc.date)::DATE AS date
            FROM staging.orbita.warehouse_calendar AS wc
            WHERE wc.date >= '2020-12-01'
            GROUP BY 1
        ) AS wc
        WHERE s.seller_state_id IN (2, 3, 9, 10)
          AND (w.operated_by_melonn = 1 OR w.id IN (3, 8))
        GROUP BY w.id, s.id, wc.date
    ) AS rd

    -- ── JOIN: FULFILLMENT ────────────────────────────────────────────────────
    -- Órdenes con items_reservation_date; estimated_* ya aplica real→estimado.
    LEFT JOIN (
        SELECT
            DATE_TRUNC('MONTH', CONVERT_TIMEZONE('UTC', w.timezone_code,
                items_reserved_info.date))::DATE   AS year_month_date,
            so.assigned_warehouse_id               AS warehouse_id,
            so.seller_id,

            -- Total estimated (real OR estimado a nivel orden, sin COALESCE extra)
            SUM(CASE WHEN sor.internal_order_number IS NOT NULL
                     THEN sor.picking_charge
                     ELSE COALESCE(esor.picking_revenue,              0) END) AS estimated_picking_revenue,
            SUM(CASE WHEN sor.internal_order_number IS NOT NULL
                     THEN sor.packing_charge
                     ELSE COALESCE(esor.packaging_revenue,            0) END) AS estimated_packaging_revenue,
            SUM(CASE WHEN sor.internal_order_number IS NOT NULL
                     THEN sor.payment_on_delivery_charge
                     ELSE COALESCE(esor.payment_on_delivery_revenue,  0) END) AS estimated_payment_on_delivery_revenue,
            SUM(CASE WHEN sor.internal_order_number IS NOT NULL
                     THEN sor.shipping_charge + sor.retry_charge
                          + sor.returns_charge + sor.cancelation_charge
                     ELSE COALESCE(esor.transport_revenue,            0) END) AS estimated_transport_revenue,
            SUM(CASE WHEN sor.internal_order_number IS NOT NULL
                     THEN sor.transport_insurance_charge
                     ELSE COALESCE(esor.transport_insurance_revenue,  0) END) AS estimated_transport_insurance_revenue,
            SUM(CASE WHEN sor.internal_order_number IS NOT NULL
                     THEN sor.picking_discount + sor.shipping_discount
                     ELSE COALESCE(esor.picking_discount + esor.shipping_discount, 0) END) AS estimated_discount,

            -- D2C estimated
            SUM(CASE WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL
                     THEN sor.picking_charge
                     WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                     THEN esor.picking_revenue                        ELSE 0 END) AS d2c_estimated_picking_revenue,
            SUM(CASE WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL
                     THEN sor.packing_charge
                     WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                     THEN esor.packaging_revenue                      ELSE 0 END) AS d2c_estimated_packaging_revenue,
            SUM(CASE WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL
                     THEN sor.payment_on_delivery_charge
                     WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                     THEN esor.payment_on_delivery_revenue            ELSE 0 END) AS d2c_estimated_payment_on_delivery_revenue,
            SUM(CASE WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL
                     THEN sor.shipping_charge + sor.retry_charge
                          + sor.returns_charge + sor.cancelation_charge
                     WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                     THEN esor.transport_revenue                      ELSE 0 END) AS d2c_estimated_transport_revenue,
            SUM(CASE WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL
                     THEN sor.transport_insurance_charge
                     WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                     THEN esor.transport_insurance_revenue            ELSE 0 END) AS d2c_estimated_transport_insurance_revenue,
            SUM(CASE WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL
                     THEN sor.picking_discount + sor.shipping_discount
                     WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                     THEN esor.picking_discount + esor.shipping_discount ELSE 0 END) AS d2c_estimated_discount,

            -- B2B estimated
            SUM(CASE WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL
                     THEN sor.picking_charge
                     WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                     THEN esor.picking_revenue                        ELSE 0 END) AS b2b_estimated_picking_revenue,
            SUM(CASE WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL
                     THEN sor.packing_charge
                     WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                     THEN esor.packaging_revenue                      ELSE 0 END) AS b2b_estimated_packaging_revenue,
            SUM(CASE WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL
                     THEN sor.payment_on_delivery_charge
                     WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                     THEN esor.payment_on_delivery_revenue            ELSE 0 END) AS b2b_estimated_payment_on_delivery_revenue,
            SUM(CASE WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL
                     THEN sor.shipping_charge + sor.retry_charge
                          + sor.returns_charge + sor.cancelation_charge
                     WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                     THEN esor.transport_revenue                      ELSE 0 END) AS b2b_estimated_transport_revenue,
            SUM(CASE WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL
                     THEN sor.transport_insurance_charge
                     WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                     THEN esor.transport_insurance_revenue            ELSE 0 END) AS b2b_estimated_transport_insurance_revenue,
            SUM(CASE WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL
                     THEN sor.picking_discount + sor.shipping_discount
                     WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                     THEN esor.picking_discount + esor.shipping_discount ELSE 0 END) AS b2b_estimated_discount

        FROM staging.orbita.sell_order AS so
        INNER JOIN staging.orbita.sell_order_state AS sos
            ON so.sell_order_state_id = sos.id
        INNER JOIN staging.orbita.fulfillment_type AS ft
            ON so.fulfillment_type_id = ft.id
        INNER JOIN (
            SELECT sol.sell_order_id, MIN(sol.action_date) AS date
            FROM staging.orbita.sell_order_log AS sol
            WHERE sol.sell_order_state_id = 2
            GROUP BY sol.sell_order_id
        ) AS items_reserved_info
            ON so.id = items_reserved_info.sell_order_id
        INNER JOIN staging.orbita.warehouse AS w
            ON so.assigned_warehouse_id = w.id
        LEFT JOIN staging.profitability.estimated_sell_order_revenue AS esor
            ON so.internal_order_number = esor.internal_order_number
        LEFT JOIN staging.profitability.sell_order_revenue AS sor
            ON so.internal_order_number = sor.internal_order_number
        WHERE w.operated_by_melonn = 1
          AND items_reserved_info.date >= '2020-12-01'
        GROUP BY
            year_month_date,
            so.seller_id,
            so.assigned_warehouse_id
    ) AS fulf
        ON  rd.warehouse_id    = fulf.warehouse_id
        AND rd.seller_id       = fulf.seller_id
        AND rd.year_month_date = fulf.year_month_date

    -- ── JOIN: DEVOLUCIONES ───────────────────────────────────────────────────
    LEFT JOIN (
        SELECT
            rr.date_of_billing           AS year_month_date,
            bro.assigned_warehouse_id    AS warehouse_id,
            bro.seller_id,
            SUM(rr.anti_picking_charge)  AS anti_picking_charge,
            SUM(rr.anti_shipping_charge) AS anti_shipping_charge
        FROM staging.profitability.returns_revenue AS rr
        LEFT JOIN staging.orbita.buyer_return_order AS bro ON bro.id = rr.internal_order_number
        LEFT JOIN staging.orbita.warehouse AS w ON bro.assigned_warehouse_id = w.id
        WHERE w.operated_by_melonn = 1
        GROUP BY year_month_date, bro.assigned_warehouse_id, bro.seller_id
    ) AS ret
        ON  rd.warehouse_id    = ret.warehouse_id
        AND rd.seller_id       = ret.seller_id
        AND rd.year_month_date = ret.year_month_date

    -- ── JOIN: WAREHOUSING REVENUE (real) ─────────────────────────────────────
    LEFT JOIN (
        SELECT
            wgr.date_of_billing                  AS year_month_date,
            wgr.warehouse_id,
            wgr.seller_id,
            SUM(wgr.storage_charge)              AS warehousing_revenue,
            SUM(wgr.storage_insurance_charge)    AS warehousing_insurance_revenue,
            SUM(wgr.storage_charge_discount)     AS warehousing_discount
        FROM staging.profitability.warehousing_revenue AS wgr
        INNER JOIN staging.orbita.warehouse AS w ON wgr.warehouse_id = w.id
        WHERE w.operated_by_melonn = 1
          AND wgr.date_of_billing >= '2020-12-01'
        GROUP BY year_month_date, wgr.warehouse_id, wgr.seller_id
    ) AS wr
        ON  rd.warehouse_id    = wr.warehouse_id
        AND rd.seller_id       = wr.seller_id
        AND rd.year_month_date = wr.year_month_date

    -- ── JOIN: INBOUND REVENUE ────────────────────────────────────────────────
    LEFT JOIN (
        SELECT
            spor.date_of_billing              AS year_month_date,
            spo.destination_warehouse_id      AS warehouse_id,
            spo.seller_id,
            SUM(spor.supplier_order_charge)   AS inbound_revenue,
            SUM(spor.supplier_order_discount) AS inbound_discount
        FROM staging.profitability.inbound_revenue AS spor
        INNER JOIN staging.orbita.supplier_order AS spo
            ON spo.internal_order_number = spor.internal_order_number
        INNER JOIN staging.orbita.warehouse AS w
            ON spo.destination_warehouse_id = w.id
        WHERE w.operated_by_melonn = 1
          AND spor.date_of_billing >= '2020-12-01'
        GROUP BY year_month_date, spo.destination_warehouse_id, spo.seller_id
    ) AS ir
        ON  rd.warehouse_id    = ir.warehouse_id
        AND rd.seller_id       = ir.seller_id
        AND rd.year_month_date = ir.year_month_date

    -- ── JOIN: ESTIMATED DAILY CHARGES (fallback Warehousing + SaaS) ─────────
    LEFT JOIN (
        SELECT
            edc.date            AS year_month_date,
            edc.warehouse_id,
            edc.seller_id,
            SUM(edc.estimated_net_charge_storage)          AS estimated_warehousing_revenue,
            SUM(edc.estimated_net_charge_storage_coverage) AS estimated_warehousing_insurance_revenue,
            SUM(edc.estimated_net_charge_fee)              AS ex_estimated_saas
        FROM staging.profitability.estimated_daily_charges AS edc
        INNER JOIN staging.orbita.warehouse AS w ON edc.warehouse_id = w.id
        WHERE w.operated_by_melonn = 1
        GROUP BY edc.date, edc.warehouse_id, edc.seller_id
    ) AS edc
        ON  rd.warehouse_id    = edc.warehouse_id
        AND rd.seller_id       = edc.seller_id
        AND rd.year_month_date = edc.year_month_date

    -- ── JOIN: EXTERNAL REVENUE (SaaS real, VAS, intereses, etc.) ────────────
    LEFT JOIN (
        SELECT
            er.date_of_billing  AS year_month_date,
            er.warehouse_id,
            er.seller_id,
            SUM(CASE WHEN er.billing_type IN ('Intereses mora',
                                             'Intereses',
                                             'Intereses WK')          THEN er.charge ELSE 0 END) AS interest_arrears,
            SUM(CASE WHEN er.billing_type = 'Servicios adicionales'   THEN er.charge ELSE 0 END) AS vas,
            SUM(CASE WHEN er.billing_type = 'Empaque'                 THEN er.charge ELSE 0 END) AS packaging_revenue,
            SUM(CASE WHEN er.billing_type = 'Transporte'              THEN er.charge ELSE 0 END) AS transport_revenue,
            SUM(CASE WHEN er.billing_type = 'Seller support'          THEN er.charge ELSE 0 END) AS seller_support_revenue,
            SUM(CASE WHEN er.billing_type IN ('Facturacion Minima',
                                             'Fee Mensual')            THEN er.charge ELSE 0 END) AS saas,
            SUM(CASE WHEN er.billing_type = 'Alistamiento'            THEN er.charge ELSE 0 END) AS alistamiento_revenue
        FROM staging.profitability.external_revenue AS er
        INNER JOIN staging.orbita.warehouse AS w ON er.warehouse_id = w.id
        WHERE w.operated_by_melonn = 1
          AND er.date_of_billing >= '2020-12-01'
        GROUP BY er.date_of_billing, er.warehouse_id, er.seller_id
    ) AS er
        ON  rd.warehouse_id    = er.warehouse_id
        AND rd.seller_id       = er.seller_id
        AND rd.year_month_date = er.year_month_date

    -- ── JOIN: ADYACENCIAS REVENUE ────────────────────────────────────────────
    LEFT JOIN (
        SELECT
            ar.date            AS year_month_date,
            ar.warehouse_id,
            ar.seller_id,
            SUM(ar.adjecencies_charge) AS adjecencies_revenue
        FROM staging.profitability.adjecencies_revenue AS ar
        INNER JOIN staging.orbita.warehouse AS w ON ar.warehouse_id = w.id
        WHERE (w.operated_by_melonn = 1 OR w.id IN (3, 8))
          AND ar.date >= '2020-12-01'
        GROUP BY ar.date, ar.warehouse_id, ar.seller_id
    ) AS ar
        ON  rd.warehouse_id    = ar.warehouse_id
        AND rd.seller_id       = ar.seller_id
        AND rd.year_month_date = ar.year_month_date

    -- ── JOIN: CREDIT NOTES (flag configurable) ───────────────────────────────
    LEFT JOIN (
        SELECT
            cn.date_of_billing AS year_month_date,
            cn.warehouse_id,
            cn.seller_id,
            SUM(cn.amount)     AS credit_notes_amount
        FROM staging.profitability.credit_notes AS cn
        GROUP BY cn.date_of_billing, cn.warehouse_id, cn.seller_id
    ) AS cn
        ON  rd.year_month_date = cn.year_month_date
        AND rd.warehouse_id    = cn.warehouse_id
        AND rd.seller_id       = cn.seller_id
),

-- ── AGREGAR A SELLER × MES — FUENTE REDSHIFT (Ene 2024+) ────────────────────
-- order_type_filter aplica solo a Fulfillment; Warehousing/SaaS/Inbound no aplica.
revenue_by_seller AS (
    SELECT
        r.seller_id,
        r.year_month_date AS revenue_month,
        SUM(
            CASE
                WHEN p.order_type_filter = 'D2C' THEN r.d2c_fulfillment_revenue
                WHEN p.order_type_filter = 'B2B' THEN r.b2b_fulfillment_revenue
                ELSE r.fulfillment_revenue
            END
        )                               AS fulfillment_revenue,
        SUM(r.returns_revenue)          AS returns_revenue,
        SUM(r.warehousing_revenue)      AS warehousing_revenue,
        SUM(r.inbound_revenue)          AS inbound_revenue,
        SUM(r.saas_revenue)             AS saas_revenue,
        SUM(r.external_revenue)         AS external_revenue,
        SUM(r.adjecencies_revenue)      AS adjecencies_revenue,
        SUM(
            CASE
                WHEN p.include_credit_notes = TRUE THEN - r.credit_notes_amount
                ELSE 0
            END
        )                               AS credit_notes_adjustment,
        SUM(
            CASE
                WHEN p.order_type_filter = 'D2C' THEN r.d2c_fulfillment_revenue
                WHEN p.order_type_filter = 'B2B' THEN r.b2b_fulfillment_revenue
                ELSE r.fulfillment_revenue
            END
            + r.returns_revenue
            + r.warehousing_revenue
            + r.inbound_revenue
            + r.saas_revenue
            + r.external_revenue
            + r.adjecencies_revenue
            + CASE WHEN p.include_credit_notes = TRUE THEN - r.credit_notes_amount ELSE 0 END
        )                               AS total_revenue
    FROM rentabilidad r
    CROSS JOIN params p
    WHERE r.seller_id IS NOT NULL
      AND r.year_month_date >= '2024-01-01'   -- ← solo Redshift desde Ene 2024
    GROUP BY r.seller_id, r.year_month_date
),

-- ── FUENTE HISTÓRICA (Dic 2020 – Dic 2023) ───────────────────────────────────
-- Cargado desde Excel "Insumos COL & MEX Cohortes (Revenue historico).xlsx"
-- via script 02_load_historical_revenue.py → historical_revenue.csv → Redshift.
-- Revenue total en moneda local (COP o MXN), sin desglose por componente.
revenue_historico AS (
    SELECT
        h.seller_id,
        h.revenue_month,
        h.total_revenue AS fulfillment_revenue,   -- total consolidado en columna de fulfillment
        0::NUMERIC      AS returns_revenue,
        0::NUMERIC      AS warehousing_revenue,
        0::NUMERIC      AS inbound_revenue,
        0::NUMERIC      AS saas_revenue,
        0::NUMERIC      AS external_revenue,
        0::NUMERIC      AS adjecencies_revenue,
        0::NUMERIC      AS credit_notes_adjustment,
        h.total_revenue AS total_revenue
    FROM staging.finance.financial_planning_historical_revenue h
    CROSS JOIN params p
    WHERE h.date < '2024-01-01'
      AND (p.country_filter IS NULL OR h.country_id = p.country_filter)
),

-- ── UNIÓN DE AMBAS FUENTES ────────────────────────────────────────────────────
revenue_combined AS (
    SELECT * FROM revenue_by_seller
    UNION ALL
    SELECT * FROM revenue_historico
),

-- ── UNIR CON SELLERS Y CALCULAR MES DE VIDA ──────────────────────────────────
cohort_revenue AS (
    SELECT
        s.seller_id,
        s.seller_name,
        s.segment,
        s.country_id,
        s.country_name,
        s.cohort_month,
        s.churn_flag,
        r.revenue_month,
        r.fulfillment_revenue,
        r.returns_revenue,
        r.warehousing_revenue,
        r.inbound_revenue,
        r.saas_revenue,
        r.external_revenue,
        r.adjecencies_revenue,
        r.credit_notes_adjustment,
        r.total_revenue,
        -- M1 = mes de entrada, M2 = siguiente, M3 = ...
        -- DATEDIFF da 0 en el mes de entrada → sumamos 1
        DATEDIFF('month', s.cohort_month, r.revenue_month) + 1 AS lifecycle_month
    FROM sellers s
    JOIN revenue_combined r
        ON  s.seller_id     = r.seller_id
        AND r.revenue_month >= s.cohort_month   -- solo desde el ingreso
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
    revenue_month,
    lifecycle_month,
    fulfillment_revenue,
    returns_revenue,
    warehousing_revenue,
    inbound_revenue,
    saas_revenue,
    external_revenue,
    adjecencies_revenue,
    credit_notes_adjustment,
    total_revenue
FROM cohort_revenue
ORDER BY
    cohort_month,
    seller_id,
    revenue_month;

-- ============================================================
-- FUENTES:
--   Dic 2020 – Dic 2023 : staging.finance.financial_planning_historical_revenue
--                         (Excel → Python ETL → Redshift)
--                         columnas: date | seller_id | total_revenue | country_id
--   Ene 2024 – hoy      : Redshift (staging.profitability.* / staging.orbita.*)
--                         revenue completo con todos los componentes
--
-- NOTAS DE USO:
--   NNR → lifecycle_month IN (2, 3), AVG(total_revenue) por cohorte
--   NRR → agregar por revenue_month, filtrar lifecycle_month >= 13
--   NDR → base = lifecycle_month = 1, curva M1→Mn por cohort_month
--   credit_notes_adjustment = 0 para histórico y cuando include_credit_notes = FALSE
--
-- CONVERSIÓN FX:
--   COP → USD: dividir por 3800
--   MXN → USD: dividir por 17.5
-- ============================================================
