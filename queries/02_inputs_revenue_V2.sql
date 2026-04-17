WITH

sellers AS (
    SELECT
        s.id                                                       AS seller_id,
        s.name                                                     AS seller_name,
        s.segment,
        s.country_id,
        s.country_name,
        DATE_TRUNC('month', s.cohort)::DATE                        AS cohort_month,
        CASE WHEN s.state <> 'Active' THEN 1 ELSE 0 END             AS churn_flag
    FROM core.data_warehouse.dim_seller s
    WHERE s.cohort IS NOT NULL
),

rentabilidad AS (
    SELECT
        rd.seller_id,
        rd.warehouse_id,
        rd.year_month_date,

        COALESCE(fulf.estimated_picking_revenue,                0)
            + COALESCE(fulf.estimated_packaging_revenue,          0)
            + COALESCE(fulf.estimated_payment_on_delivery_revenue,0)
            + COALESCE(fulf.estimated_transport_revenue,          0)
            + COALESCE(fulf.estimated_transport_insurance_revenue,0)
            - COALESCE(fulf.estimated_discount,                   0)   AS fulfillment_revenue,

        COALESCE(fulf.d2c_estimated_picking_revenue,                0)
            + COALESCE(fulf.d2c_estimated_packaging_revenue,          0)
            + COALESCE(fulf.d2c_estimated_payment_on_delivery_revenue,0)
            + COALESCE(fulf.d2c_estimated_transport_revenue,          0)
            + COALESCE(fulf.d2c_estimated_transport_insurance_revenue,0)
            - COALESCE(fulf.d2c_estimated_discount,                   0) AS d2c_fulfillment_revenue,

        COALESCE(fulf.b2b_estimated_picking_revenue,                0)
            + COALESCE(fulf.b2b_estimated_packaging_revenue,          0)
            + COALESCE(fulf.b2b_estimated_payment_on_delivery_revenue,0)
            + COALESCE(fulf.b2b_estimated_transport_revenue,          0)
            + COALESCE(fulf.b2b_estimated_transport_insurance_revenue,0)
            - COALESCE(fulf.b2b_estimated_discount,                   0) AS b2b_fulfillment_revenue,

        COALESCE(ret.anti_picking_charge,  0)
            + COALESCE(ret.anti_shipping_charge, 0)                     AS returns_revenue,

        COALESCE(wr.warehousing_revenue,          edc.estimated_warehousing_revenue,          0)
            + COALESCE(wr.warehousing_insurance_revenue, edc.estimated_warehousing_insurance_revenue, 0)
            - COALESCE(wr.warehousing_discount,     0)                  AS warehousing_revenue,

        COALESCE(ir.inbound_revenue, 0)
            - COALESCE(ir.inbound_discount, 0)                          AS inbound_revenue,

        COALESCE(er.saas, edc.ex_estimated_saas, 0)                   AS saas_revenue,

        COALESCE(er.interest_arrears,        0)
            + COALESCE(er.vas,               0)
            + COALESCE(er.packaging_revenue, 0)
            + COALESCE(er.transport_revenue, 0)
            + COALESCE(er.seller_support_revenue, 0)
            + COALESCE(er.alistamiento_revenue,   0)                    AS external_revenue,

        COALESCE(ar.adjecencies_revenue,   0)                         AS adjecencies_revenue,

        COALESCE(cn.credit_notes_amount,   0)                         AS credit_notes_amount

    FROM (
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

             LEFT JOIN (
        SELECT
            DATE_TRUNC('MONTH', CONVERT_TIMEZONE('UTC', w.timezone_code,
                                                 items_reserved_info.date))::DATE   AS year_month_date,
            so.assigned_warehouse_id               AS warehouse_id,
            so.seller_id,

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

revenue_by_seller AS (
    SELECT
        r.seller_id,
        r.year_month_date AS revenue_month,
        SUM(r.fulfillment_revenue)      AS fulfillment_revenue,
        SUM(r.d2c_fulfillment_revenue)  AS d2c_fulfillment_revenue,
        SUM(r.b2b_fulfillment_revenue)  AS b2b_fulfillment_revenue,
        SUM(r.returns_revenue)          AS returns_revenue,
        SUM(r.warehousing_revenue)      AS warehousing_revenue,
        SUM(r.inbound_revenue)          AS inbound_revenue,
        SUM(r.saas_revenue)             AS saas_revenue,
        SUM(r.external_revenue)         AS external_revenue,
        SUM(r.adjecencies_revenue)      AS adjecencies_revenue,
        SUM(r.credit_notes_amount)      AS credit_notes_amount,
        SUM(
                r.fulfillment_revenue
                    + r.returns_revenue
                    + r.warehousing_revenue
                    + r.inbound_revenue
                    + r.saas_revenue
                    + r.external_revenue
                    + r.adjecencies_revenue
        )                               AS total_revenue
    FROM rentabilidad r
    WHERE r.seller_id IS NOT NULL
      AND r.year_month_date >= '2024-01-01'
    GROUP BY r.seller_id, r.year_month_date
),

revenue_historico AS (
    SELECT
        h.seller_id,
        h.revenue_month,
        h.total_revenue AS fulfillment_revenue,
        0::NUMERIC      AS d2c_fulfillment_revenue,
        0::NUMERIC      AS b2b_fulfillment_revenue,
        0::NUMERIC      AS returns_revenue,
        0::NUMERIC      AS warehousing_revenue,
        0::NUMERIC      AS inbound_revenue,
        0::NUMERIC      AS saas_revenue,
        0::NUMERIC      AS external_revenue,
        0::NUMERIC      AS adjecencies_revenue,
        0::NUMERIC      AS credit_notes_amount,
        h.total_revenue AS total_revenue
    FROM (
             SELECT seller_id, date AS revenue_month, total_revenue, country_id
             FROM staging.finance.financial_planning_historical_revenue
         ) h
    WHERE h.revenue_month < '2024-01-01'
),

revenue_combined AS (
    SELECT * FROM revenue_by_seller
    UNION ALL
    SELECT * FROM revenue_historico
),

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
        r.d2c_fulfillment_revenue,
        r.b2b_fulfillment_revenue,
        r.returns_revenue,
        r.warehousing_revenue,
        r.inbound_revenue,
        r.saas_revenue,
        r.external_revenue,
        r.adjecencies_revenue,
        r.credit_notes_amount,
        r.total_revenue,
        DATEDIFF('month', s.cohort_month, r.revenue_month) + 1 AS lifecycle_month
    FROM sellers s
             JOIN revenue_combined r
                  ON  s.seller_id     = r.seller_id
                      AND r.revenue_month >= s.cohort_month
)

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
    d2c_fulfillment_revenue,
    b2b_fulfillment_revenue,
    returns_revenue,
    warehousing_revenue,
    inbound_revenue,
    saas_revenue,
    external_revenue,
    adjecencies_revenue,
    credit_notes_amount,
    total_revenue
FROM cohort_revenue
ORDER BY
    cohort_month,
    seller_id,
    revenue_month;
