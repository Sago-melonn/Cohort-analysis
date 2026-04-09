-- Profitability_master
SELECT
-- Agrupadores
reference_data.year_month_date,
reference_data.seller_id,
reference_data.warehouse_id,
reference_data.seller_name,
reference_data.warehouse_name,
reference_data.country,
reference_data.seller_category                                            AS seller_category_archi,
---------------------- Joaqs & Mario ----------------------------------------------------
hub.product_category                                                      AS product_category,
hub.kam                                                                   AS kam,
hub.tier                                                                  AS tier,
hub.active_date                                                           AS hub_active_date,
-------------------------------------------------------------------------------------------
sseg.segment                                                              AS seller_segment,


(CASE
     WHEN first_item.creation_date IS NOT NULL THEN CONVERT_TIMEZONE(reference_data.warehouse_timezone_code,
                                                                     first_item.creation_date::TIMESTAMP)
    END)                                                                  AS fecha_ingreso_primer_item,
-- profit_ordenes_items_reservados.product_category,
-- profit_ordenes_items_reservados.kam,
-- profit_ordenes_items_reservados.tier,

-- Órdenes items reservados
profit_ordenes_items_reservados.picking_revenue                           AS ir_picking_revenue,
profit_ordenes_items_reservados.packaging_revenue                         AS ir_packaging_revenue,
profit_ordenes_items_reservados.estimated_picking_revenue                 AS ir_estimated_picking_revenue,
profit_ordenes_items_reservados.estimated_packaging_revenue               AS ir_estimated_packaging_revenue,
profit_ordenes_items_reservados.packaging_cost                            AS ir_packaging_cost,
--JOACO ESTIMATED PACKAGING
profit_ordenes_items_reservados.estimated_packaging_cost                  AS ir_estimated_packaging_cost,
--JOACO ESTIMATED PACKAGING
profit_ordenes_items_reservados.payment_on_delivery_revenue               AS ir_payment_on_delivery_revenue,
profit_ordenes_items_reservados.transport_revenue                         AS ir_transport_revenue,
profit_ordenes_items_reservados.transport_insurance_revenue               AS ir_transport_insurance_revenue,
profit_ordenes_items_reservados.estimated_payment_on_delivery_revenue     AS ir_estimated_payment_on_delivery_revenue,
profit_ordenes_items_reservados.estimated_transport_revenue               AS ir_estimated_transport_revenue,
profit_ordenes_items_reservados.estimated_transport_insurance_revenue     AS ir_estimated_transport_insurance_revenue,
profit_ordenes_items_reservados.discount                                  AS ir_discount,
profit_ordenes_items_reservados.estimated_discount                        AS ir_estimated_discount,
profit_ordenes_items_reservados.courier_cost                              AS ir_courier_cost,
profit_ordenes_items_reservados.estimated_courier_cost                    AS ir_estimated_courier_cost,
profit_ordenes_items_reservados.courier_pod_cost                          AS ir_courier_pod_cost,
profit_ordenes_items_reservados.local_last_mile_cost                      AS ir_local_last_mile_cost,
profit_ordenes_items_reservados.estimated_local_last_mile_cost            AS ir_estimated_local_last_mile_cost,

profit_ordenes_items_reservados.picking_assigned_cost                     AS ir_picking_assigned_cost,
profit_ordenes_items_reservados.picking_cost                              AS ir_picking_cost,
profit_ordenes_items_reservados.estimated_picking_assigned_cost           AS ir_estimated_picking_assigned_cost,
profit_ordenes_items_reservados.estimated_picking_cost                    AS ir_estimated_picking_cost,

profit_ordenes_items_reservados.packing_assigned_cost                     AS ir_packing_assigned_cost,
profit_ordenes_items_reservados.packing_cost                              AS ir_packing_cost,
profit_ordenes_items_reservados.estimated_packing_assigned_cost           AS ir_estimated_packing_assigned_cost,
profit_ordenes_items_reservados.estimated_packing_cost                    AS ir_estimated_packing_cost,



profit_ordenes_items_reservados.d2c_picking_revenue                       AS d2c_ir_picking_revenue,
profit_ordenes_items_reservados.d2c_packaging_revenue                     AS d2c_ir_packaging_revenue,
profit_ordenes_items_reservados.d2c_estimated_picking_revenue             AS d2c_ir_estimated_picking_revenue,
profit_ordenes_items_reservados.d2c_estimated_packaging_revenue           AS d2c_ir_estimated_packaging_revenue,
profit_ordenes_items_reservados.d2c_packaging_cost                        AS d2c_ir_packaging_cost,
profit_ordenes_items_reservados.d2c_payment_on_delivery_revenue           AS d2c_ir_payment_on_delivery_revenue,
profit_ordenes_items_reservados.d2c_transport_revenue                     AS d2c_ir_transport_revenue,
profit_ordenes_items_reservados.d2c_transport_insurance_revenue           AS d2c_ir_transport_insurance_revenue,
profit_ordenes_items_reservados.d2c_estimated_payment_on_delivery_revenue AS d2c_ir_estimated_payment_on_delivery_revenue,
profit_ordenes_items_reservados.d2c_estimated_transport_revenue           AS d2c_ir_estimated_transport_revenue,
profit_ordenes_items_reservados.d2c_estimated_transport_insurance_revenue AS d2c_ir_estimated_transport_insurance_revenue,
profit_ordenes_items_reservados.d2c_discount                              AS d2c_ir_discount,
profit_ordenes_items_reservados.d2c_estimated_discount                    AS d2c_ir_estimated_discount,
profit_ordenes_items_reservados.d2c_courier_cost                          AS d2c_ir_courier_cost,
profit_ordenes_items_reservados.d2c_estimated_courier_cost                AS d2c_ir_estimated_courier_cost,
profit_ordenes_items_reservados.d2c_courier_pod_cost                      AS d2c_ir_courier_pod_cost,
profit_ordenes_items_reservados.d2c_local_last_mile_cost                  AS d2c_ir_local_last_mile_cost,
profit_ordenes_items_reservados.d2c_estimated_local_last_mile_cost        AS d2c_ir_estimated_local_last_mile_cost,

profit_ordenes_items_reservados.d2c_picking_assigned_cost                 AS d2c_ir_picking_assigned_cost,
profit_ordenes_items_reservados.d2c_picking_cost                          AS d2c_ir_picking_cost,
profit_ordenes_items_reservados.d2c_estimated_picking_assigned_cost       AS d2c_ir_estimated_picking_assigned_cost,
profit_ordenes_items_reservados.d2c_estimated_picking_cost                AS d2c_ir_estimated_picking_cost,


profit_ordenes_items_reservados.d2c_packing_assigned_cost                 AS d2c_ir_packing_assigned_cost,
profit_ordenes_items_reservados.d2c_packing_cost                          AS d2c_ir_packing_cost,
profit_ordenes_items_reservados.d2c_estimated_packing_assigned_cost       AS d2c_ir_estimated_packing_assigned_cost,
profit_ordenes_items_reservados.d2c_estimated_packing_cost                AS d2c_ir_estimated_packing_cost,

profit_ordenes_items_reservados.total_count_d2c                           AS d2c_ir_total_count,

profit_ordenes_items_reservados.b2b_picking_revenue                       AS b2b_ir_picking_revenue,
profit_ordenes_items_reservados.b2b_packaging_revenue                     AS b2b_ir_packaging_revenue,
profit_ordenes_items_reservados.b2b_estimated_picking_revenue             AS b2b_ir_estimated_picking_revenue,
profit_ordenes_items_reservados.b2b_estimated_packaging_revenue           AS b2b_ir_estimated_packaging_revenue,
profit_ordenes_items_reservados.b2b_packaging_cost                        AS b2b_ir_packaging_cost,
profit_ordenes_items_reservados.b2b_payment_on_delivery_revenue           AS b2b_ir_payment_on_delivery_revenue,
profit_ordenes_items_reservados.b2b_transport_revenue                     AS b2b_ir_transport_revenue,
profit_ordenes_items_reservados.b2b_transport_insurance_revenue           AS b2b_ir_transport_insurance_revenue,
profit_ordenes_items_reservados.b2b_estimated_payment_on_delivery_revenue AS b2b_ir_estimated_payment_on_delivery_revenue,
profit_ordenes_items_reservados.b2b_estimated_transport_revenue           AS b2b_ir_estimated_transport_revenue,
profit_ordenes_items_reservados.b2b_estimated_transport_insurance_revenue AS b2b_ir_estimated_transport_insurance_revenue,
profit_ordenes_items_reservados.b2b_discount                              AS b2b_ir_discount,
profit_ordenes_items_reservados.b2b_estimated_discount                    AS b2b_ir_estimated_discount,
profit_ordenes_items_reservados.b2b_courier_cost                          AS b2b_ir_courier_cost,
profit_ordenes_items_reservados.b2b_estimated_courier_cost                AS b2b_ir_estimated_courier_cost,
profit_ordenes_items_reservados.b2b_courier_pod_cost                      AS b2b_ir_courier_pod_cost,
profit_ordenes_items_reservados.b2b_local_last_mile_cost                  AS b2b_ir_local_last_mile_cost,
profit_ordenes_items_reservados.b2b_estimated_local_last_mile_cost        AS b2b_ir_estimated_local_last_mile_cost,

profit_ordenes_items_reservados.b2b_picking_assigned_cost                 AS b2b_ir_picking_assigned_cost,
profit_ordenes_items_reservados.b2b_picking_cost                          AS b2b_ir_picking_cost,
profit_ordenes_items_reservados.b2b_estimated_picking_assigned_cost       AS b2b_ir_estimated_picking_assigned_cost,
profit_ordenes_items_reservados.b2b_estimated_picking_cost                AS b2b_ir_estimated_picking_cost,


profit_ordenes_items_reservados.b2b_packing_assigned_cost                 AS b2b_ir_packing_assigned_cost,
profit_ordenes_items_reservados.b2b_packing_cost                          AS b2b_ir_packing_cost,
profit_ordenes_items_reservados.b2b_estimated_packing_assigned_cost       AS b2b_ir_estimated_packing_assigned_cost,
profit_ordenes_items_reservados.b2b_estimated_packing_cost                AS b2b_ir_estimated_packing_cost,

profit_ordenes_items_reservados.total_count_b2b                           AS b2b_ir_total_count,


profit_ordenes_items_reservados.attempts_quantity                         AS ir_attempts_quantity,
profit_ordenes_items_reservados.courier_quantity                          AS ir_courier_quantity,
profit_ordenes_items_reservados.last_mile_quantity                        AS ir_last_mile_quantity,
profit_ordenes_items_reservados.fulfillment_flag                          AS ir_fulfillment_flag,
profit_ordenes_items_reservados.total_count                               AS ir_total_count,


-- Seller y Bodega
CASE WHEN
    external_revenue.saas IS NOT NULL THEN external_revenue.saas
    ELSE estimated_daily_charges.ex_estimated_saas END                                AS revenue_estimated_saas,
CASE WHEN
    warehousing_revenue.warehousing_revenue IS NOT NULL THEN warehousing_revenue.warehousing_revenue
    ELSE estimated_daily_charges.estimated_warehousing_revenue END                    AS estimated_revenue_warehousing_revenue,
CASE WHEN
    warehousing_revenue.revenue_space IS NOT NULL THEN warehousing_revenue.revenue_space/4
    ELSE estimated_daily_charges.average_used_m3 END                                  AS estimated_average_used_m3,
CASE WHEN
    warehousing_revenue.warehousing_insurance_revenue IS NOT NULL THEN warehousing_revenue.warehousing_insurance_revenue
    ELSE estimated_daily_charges.estimated_warehousing_insurance_revenue END          AS estimated_revenue_warehousing_insurance_revenue,
CASE WHEN
    warehousing_cost.warehousing_total_cost IS NOT NULL THEN warehousing_cost.warehousing_total_cost
    ELSE estimated_daily_charges.estimated_warehousing_total_cost END                 AS estimated_warehousing_total_cost,
CASE WHEN
    warehousing_cost.warehousing_assigned_cost IS NOT NULL THEN warehousing_cost.warehousing_assigned_cost
    ELSE estimated_daily_charges.estimated_warehousing_assigned_cost END               AS estimated_warehousing_assigned_cost,
CASE WHEN
    saas_cost.saas_cost IS NOT NULL THEN saas_cost.saas_cost
    ELSE estimated_daily_charges.estimated_saas_cost END                               AS estimated_saas_cost,
CASE WHEN warehousing_cost.warehousing_insurance_cost IS NOT NULL THEN warehousing_cost.warehousing_insurance_cost
    ELSE estimated_daily_charges.estimated_insurance_cost END                          AS estimated_insurance_cost,
CASE WHEN inbound_cost.inbound_assigned_cost IS NOT NULL THEN inbound_cost.inbound_assigned_cost
    ELSE estimated_inbound_cost.estimated_inbound_assigned_cost END                    AS estimated_inbound_assigned_cost,
CASE WHEN inbound_cost.inbound_total_cost IS NOT NULL THEN inbound_cost.inbound_total_cost
    ELSE estimated_inbound_cost.estimated_inbound_total_cost END                       AS estimated_inbound_total_cost,
return_orders_revenue.anti_picking_charge                                 AS anti_picking_charge,
return_orders_revenue.anti_shipping_charge                                AS anti_shipping_charge,
return_orders_cost.returns_total_assigned_cost,
return_orders_cost.returns_total_cost,
return_orders_cost.returns_transport_cost,
warehousing_cost.warehousing_insurance_cost,
warehousing_cost.warehousing_assigned_cost                                AS warehousing_assigned_cost,
warehousing_cost.warehousing_total_cost                                   AS warehousing_total_cost,
warehousing_revenue.warehousing_discount                                  AS warehousing_discount,
seller_support.seller_support_cost,
warehousing_revenue.warehousing_insurance_revenue                         AS warehousing_insurance_revenue,
warehousing_revenue.warehousing_revenue                                   AS warehousing_revenue,
warehousing_revenue.revenue_space/4                                       AS revenue_space,
adjecencies_revenue.adjecencies_revenue,
adjecencies_cost.adjecencies_cost,
inventory_adjustments.inventory_adjustment,
inbound_revenue.inbound_revenue,
inbound_revenue.inbound_discount,
inbound_cost.inbound_assigned_cost,
inbound_cost.inbound_total_cost,
transport_ftes.transport_ftes,
CASE WHEN
    transport_ftes.transport_ftes IS NOT NULL THEN transport_ftes.transport_ftes
    ELSE estimated_transport_ftes.estimated_transport_ftes END            AS estimated_transport_ftes,
transport_ftes.pod_ftes,
CASE WHEN
    transport_ftes.pod_ftes IS NOT NULL THEN transport_ftes.pod_ftes
    ELSE estimated_transport_ftes.estimated_pod_ftes END                  AS estimated_transport_ftes_pod,
external_revenue.packaging_revenue                                        AS ex_packaging_revenue,
external_revenue.transport_revenue                                        AS ex_transport_revenue,
external_revenue.seller_support_revenue                                   AS ex_seller_support_revenue,
external_revenue.saas                                                     AS ex_saas,
external_revenue.interest_arrears                                         AS interest_arrears,
external_revenue.vas                                                      AS vas,
saas_cost.saas_cost,
disc.insurance_discount                                                   AS insurance_discount,
stock_counts_cost.stock_counts_assigned_cost,
stock_counts_cost.stock_counts_total_cost,
cancelled_orders_cost.cancelled_assigned_cost,
cancelled_orders_cost.cancelled_total_cost,
gmv.total_d2c                                                             AS gmv_total_d2c,
gmv.total_b2b                                                             AS gmv_total_b2b,
gmv.total                                                                 AS gmv_total,
credit_notes.credit_notes_amount,
missmatch_transport.mismatch_transport_cost
FROM (SELECT
          w.id               AS warehouse_id,
          w.name             AS warehouse_name,
          w.country,
          w.timezone_code    AS warehouse_timezone_code,
          s.id               AS seller_id,
          s.name             AS seller_name,
          soin.products_type AS seller_category,
          calendar_info.year_month_date
      FROM orbita.warehouse AS w
      CROSS JOIN orbita.seller AS s
      LEFT JOIN  orbita.seller_operations_information AS soin
                     ON s.id = soin.seller_id
      INNER JOIN orbita.seller_warehouse_configuration AS swc
                     ON (w.id = swc.warehouse_id OR w.id IN (3,8)) AND s.id = swc.seller_id --AND swc.active = 1
      CROSS JOIN(SELECT
                     DATE_TRUNC('MONTH', wc.date) AS year_month_date
                 FROM orbita.warehouse_calendar AS wc
                 WHERE wc.date > '2023-05-31'
                 GROUP BY year_month_date) AS calendar_info
      WHERE s.seller_state_id IN (2, 3, 9, 10)
        AND (w.operated_by_melonn = 1 OR w.id IN (3,8))
      GROUP BY w.id, w.name, w.country, w.timezone_code, s.id, s.name, soin.products_type,
               calendar_info.year_month_date) AS reference_data
LEFT JOIN (SELECT
               DATE_TRUNC('MONTH',
                          CONVERT_TIMEZONE('UTC', w.timezone_code, items_reserved_info.date)) AS year_month_date,
               so.assigned_warehouse_id                                                       AS warehouse_id,
               so.seller_id,
               s.name                                                                         AS seller_name,
               w.name                                                                         AS warehouse_name,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.picking_charge
                       ELSE 0 END)                                                            AS picking_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.picking_charge
                       ELSE COALESCE(esor.picking_revenue, 0) END)                            AS estimated_picking_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.packing_charge
                       ELSE 0 END)                                                            AS packaging_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.packing_charge
                       ELSE COALESCE(esor.packaging_revenue, 0) END)                          AS estimated_packaging_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.payment_on_delivery_charge
                       ELSE 0 END)                                                            AS payment_on_delivery_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.payment_on_delivery_charge
                       ELSE COALESCE(esor.payment_on_delivery_revenue, 0) END)                AS estimated_payment_on_delivery_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.shipping_charge + sor.retry_charge +
                                                                       sor.returns_charge + sor.cancelation_charge
                       ELSE 0 END)                                                            AS transport_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.shipping_charge + sor.retry_charge +
                                                                       sor.returns_charge + sor.cancelation_charge
                       ELSE COALESCE(esor.transport_revenue, 0) END)                          AS estimated_transport_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.transport_insurance_charge
                       ELSE 0 END)                                                            AS transport_insurance_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.transport_insurance_charge
                       ELSE COALESCE(esor.transport_insurance_revenue, 0) END)                AS estimated_transport_insurance_revenue,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.picking_discount + sor.shipping_discount
                       ELSE 0 END)                                                            AS discount,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL THEN sor.picking_discount + sor.shipping_discount
                       ELSE COALESCE(esor.picking_discount + esor.shipping_discount, 0) END)  AS estimated_discount,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.picking_charge
                       ELSE 0 END)                                                            AS d2c_picking_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.picking_charge
                       WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL THEN esor.picking_revenue
                       ELSE 0 END)                                                            AS d2c_estimated_picking_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.packing_charge
                       ELSE 0 END)                                                            AS d2c_packaging_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.packing_charge
                       WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL THEN esor.packaging_revenue
                       ELSE 0 END)                                                            AS d2c_estimated_packaging_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.payment_on_delivery_charge
                       ELSE 0 END)                                                            AS d2c_payment_on_delivery_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.payment_on_delivery_charge
                       WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                           THEN esor.payment_on_delivery_revenue
                       ELSE 0 END)                                                            AS d2c_estimated_payment_on_delivery_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.shipping_charge +
                                                                                         sor.retry_charge +
                                                                                         sor.returns_charge +
                                                                                         sor.cancelation_charge
                       ELSE 0 END)                                                            AS d2c_transport_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.shipping_charge +
                                                                                         sor.retry_charge +
                                                                                         sor.returns_charge +
                                                                                         sor.cancelation_charge
                       WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL THEN esor.transport_revenue
                       ELSE 0 END)                                                            AS d2c_estimated_transport_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.transport_insurance_charge
                       ELSE 0 END)                                                            AS d2c_transport_insurance_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL THEN sor.transport_insurance_charge
                       WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                           THEN esor.transport_insurance_revenue
                       ELSE 0 END)                                                            AS d2c_estimated_transport_insurance_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL
                           THEN sor.picking_discount + sor.shipping_discount
                       ELSE 0 END)                                                            AS d2c_discount,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND sor.internal_order_number IS NOT NULL
                           THEN sor.picking_discount + sor.shipping_discount
                       WHEN ft.order_type = 'D2C' AND esor.internal_order_number IS NOT NULL
                           THEN esor.picking_discount + esor.shipping_discount
                       ELSE 0 END)                                                            AS d2c_estimated_discount,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.picking_charge
                       ELSE 0 END)                                                            AS b2b_picking_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.picking_charge
                       WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL THEN esor.picking_revenue
                       ELSE 0 END)                                                            AS b2b_estimated_picking_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.packing_charge
                       ELSE 0 END)                                                            AS b2b_packaging_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.packing_charge
                       WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL THEN esor.packaging_revenue
                       ELSE 0 END)                                                            AS b2b_estimated_packaging_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.payment_on_delivery_charge
                       ELSE 0 END)                                                            AS b2b_payment_on_delivery_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.payment_on_delivery_charge
                       WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                           THEN esor.payment_on_delivery_revenue
                       ELSE 0 END)                                                            AS b2b_estimated_payment_on_delivery_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.shipping_charge +
                                                                                         sor.retry_charge +
                                                                                         sor.returns_charge +
                                                                                         sor.cancelation_charge
                       ELSE 0 END)                                                            AS b2b_transport_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.shipping_charge +
                                                                                         sor.retry_charge +
                                                                                         sor.returns_charge +
                                                                                         sor.cancelation_charge
                       WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL THEN esor.transport_revenue
                       ELSE 0 END)                                                            AS b2b_estimated_transport_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.transport_insurance_charge
                       ELSE 0 END)                                                            AS b2b_transport_insurance_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL THEN sor.transport_insurance_charge
                       WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                           THEN esor.transport_insurance_revenue
                       ELSE 0 END)                                                            AS b2b_estimated_transport_insurance_revenue,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL
                           THEN sor.picking_discount + sor.shipping_discount
                       ELSE 0 END)                                                            AS b2b_discount,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND sor.internal_order_number IS NOT NULL
                           THEN sor.picking_discount + sor.shipping_discount
                       WHEN ft.order_type = 'B2B' AND esor.internal_order_number IS NOT NULL
                           THEN esor.picking_discount + esor.shipping_discount
                       ELSE 0 END)                                                            AS b2b_estimated_discount,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN COALESCE(attempts_info.quantity, 0) -
                            (COALESCE(courier_info.quantity, 0) + COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN courier_info.cost
                       ELSE 0 END)                                                            AS courier_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN COALESCE(attempts_info.quantity, 0) -
                            (COALESCE(courier_info.quantity, 0) + COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN CASE
                                    WHEN courier_info.cost IS NULL OR courier_info.cost = 0
                                        THEN etc.estimated_courier_cost
                                    ELSE courier_info.cost END
                       ELSE COALESCE(etc.estimated_courier_cost, 0) END)                      AS estimated_courier_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN COALESCE(attempts_info.quantity, 0) -
                            (COALESCE(courier_info.quantity, 0) + COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN courier_info.pod_cost
                       ELSE 0 END)                                                            AS courier_pod_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN COALESCE(attempts_info.quantity, 0) -
                            (COALESCE(courier_info.quantity, 0) + COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN last_mile_info.total_cost
                       ELSE 0 END)                                                            AS local_last_mile_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN COALESCE(attempts_info.quantity, 0) -
                            (COALESCE(courier_info.quantity, 0) + COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN CASE
                                    WHEN last_mile_info.total_cost IS NULL OR last_mile_info.total_cost = 0
                                        THEN etc.estimated_local_last_mile_cost
                                    ELSE last_mile_info.total_cost END
                       ELSE COALESCE(etc.estimated_local_last_mile_cost, 0) END)              AS estimated_local_last_mile_cost,
               SUM(CASE
                       WHEN pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_assigned_cost
                       ELSE 0 END)                                                            AS picking_assigned_cost,
               SUM(CASE
                       WHEN pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_cost
                       ELSE 0 END)                                                            AS picking_cost,
               SUM(CASE
                       WHEN pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_assigned_cost
                       ELSE 0 END)                                                            AS packing_assigned_cost,
               SUM(CASE
                       WHEN pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_cost
                       ELSE 0 END)                                                            AS packing_cost,
               SUM(CASE
                       WHEN pkg.internal_order_number IS NOT NULL THEN pkg.total_cost
                       ELSE 0 END)                                                            AS packaging_cost,
               --JOACO ESTIMATED PACKAGING
               SUM(CASE
                       WHEN pkg.internal_order_number IS NOT NULL THEN pkg.total_cost
                            ELSE epkg.total_cost END)                                          AS estimated_packaging_cost,
               --JOACO ESTIMATED PACKAGING
               SUM(CASE
                       WHEN pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_assigned_cost
                            ELSE estimated_pick_cost.estimated_opex_assigned_cost END)        AS estimated_picking_assigned_cost,
               SUM(CASE
                       WHEN pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_cost
                            ELSE estimated_pick_cost.estimated_opex_total_cost END)           AS estimated_picking_cost,
               SUM(CASE
                       WHEN pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_cost
                            ELSE estimated_pack_cost.estimated_opex_total_cost END)           AS estimated_packing_cost,
               SUM(CASE
                       WHEN pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_assigned_cost
                            ELSE estimated_pack_cost.estimated_opex_assigned_cost END)        AS estimated_packing_assigned_cost,

               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'D2C' AND COALESCE(attempts_info.quantity, 0) -
                                              (COALESCE(courier_info.quantity, 0) +
                                               COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN courier_info.cost
                       ELSE 0 END)                                                            AS d2c_courier_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'D2C' THEN
                           CASE
                               WHEN COALESCE(attempts_info.quantity, 0) -
                                    (COALESCE(courier_info.quantity, 0) +
                                     COALESCE(last_mile_info.quantity, 0)) <= 0
                                   THEN CASE
                                            WHEN courier_info.cost IS NULL OR courier_info.cost = 0
                                                THEN etc.estimated_courier_cost
                                            ELSE courier_info.cost END
                               ELSE COALESCE(etc.estimated_courier_cost, 0)
                               END
                       ELSE 0 END)                                                            AS d2c_estimated_courier_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'D2C' AND COALESCE(attempts_info.quantity, 0) -
                                              (COALESCE(courier_info.quantity, 0) +
                                               COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN courier_info.pod_cost
                       ELSE 0 END)                                                            AS d2c_courier_pod_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'D2C' AND COALESCE(attempts_info.quantity, 0) -
                                              (COALESCE(courier_info.quantity, 0) +
                                               COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN last_mile_info.total_cost
                       ELSE 0 END)                                                            AS d2c_local_last_mile_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'D2C' THEN
                           CASE
                               WHEN COALESCE(attempts_info.quantity, 0) -
                                    (COALESCE(courier_info.quantity, 0) +
                                     COALESCE(last_mile_info.quantity, 0)) <= 0
                                   THEN CASE
                                            WHEN last_mile_info.total_cost IS NULL OR last_mile_info.total_cost = 0
                                                THEN etc.estimated_local_last_mile_cost
                                            ELSE last_mile_info.total_cost END
                               ELSE COALESCE(etc.estimated_local_last_mile_cost, 0) END
                       ELSE 0 END)                                                            AS d2c_estimated_local_last_mile_cost,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pick_cost.internal_order_number IS NOT NULL
                           THEN pick_cost.total_assigned_cost
                       ELSE 0 END)                                                            AS d2c_picking_assigned_cost,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_cost
                       ELSE 0 END)                                                            AS d2c_picking_cost,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pack_cost.internal_order_number IS NOT NULL
                           THEN pack_cost.total_assigned_cost
                       ELSE 0 END)                                                            AS d2c_packing_assigned_cost,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_cost
                       ELSE 0 END)                                                            AS d2c_packing_cost,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pkg.internal_order_number IS NOT NULL THEN pkg.total_cost
                       ELSE 0 END)                                                            AS d2c_packaging_cost,

                SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_assigned_cost
                       WHEN ft.order_type = 'D2C' AND pick_cost.internal_order_number IS NULL THEN
                           estimated_pick_cost.estimated_opex_assigned_cost END)        AS d2c_estimated_picking_assigned_cost,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_cost
                       WHEN ft.order_type = 'D2C' AND pick_cost.internal_order_number IS NULL THEN
                            estimated_pick_cost.estimated_opex_total_cost END)           AS d2c_estimated_picking_cost,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_cost
                       WHEN ft.order_type = 'D2C' AND pack_cost.internal_order_number IS NULL  THEN
                            estimated_pack_cost.estimated_opex_total_cost END)           AS d2c_estimated_packing_cost,
               SUM(CASE
                       WHEN ft.order_type = 'D2C' AND pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_assigned_cost
                       WHEN ft.order_type = 'D2C' AND pack_cost.internal_order_number IS NULL THEN
                            estimated_pack_cost.estimated_opex_assigned_cost END)        AS d2c_estimated_packing_assigned_cost,

               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'B2B' AND COALESCE(attempts_info.quantity, 0) -
                                              (COALESCE(courier_info.quantity, 0) +
                                               COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN courier_info.cost
                       ELSE 0 END)                                                            AS b2b_courier_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'B2B' THEN
                           CASE
                               WHEN COALESCE(attempts_info.quantity, 0) -
                                    (COALESCE(courier_info.quantity, 0) +
                                     COALESCE(last_mile_info.quantity, 0)) <= 0
                                   THEN CASE
                                            WHEN courier_info.cost IS NULL OR courier_info.cost = 0
                                                THEN etc.estimated_courier_cost
                                            ELSE courier_info.cost END
                               ELSE COALESCE(etc.estimated_courier_cost, 0) END
                       ELSE 0 END)                                                            AS b2b_estimated_courier_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'B2B' AND COALESCE(attempts_info.quantity, 0) -
                                              (COALESCE(courier_info.quantity, 0) +
                                               COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN courier_info.pod_cost
                       ELSE 0 END)                                                            AS b2b_courier_pod_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'B2B' AND COALESCE(attempts_info.quantity, 0) -
                                              (COALESCE(courier_info.quantity, 0) +
                                               COALESCE(last_mile_info.quantity, 0)) <= 0
                           THEN last_mile_info.total_cost
                       ELSE 0 END)                                                            AS b2b_local_last_mile_cost,
               SUM(CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                       WHEN ft.order_type = 'B2B' THEN
                           CASE
                               WHEN COALESCE(attempts_info.quantity, 0) -
                                    (COALESCE(courier_info.quantity, 0) +
                                     COALESCE(last_mile_info.quantity, 0)) <= 0
                                   THEN CASE
                                            WHEN last_mile_info.total_cost IS NULL OR last_mile_info.total_cost = 0
                                                THEN etc.estimated_local_last_mile_cost
                                            ELSE last_mile_info.total_cost END
                               ELSE COALESCE(etc.estimated_local_last_mile_cost, 0) END
                       ELSE 0 END)                                                            AS b2b_estimated_local_last_mile_cost,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pick_cost.internal_order_number IS NOT NULL
                           THEN pick_cost.total_assigned_cost
                       ELSE 0 END)                                                            AS b2b_picking_assigned_cost,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_cost
                       ELSE 0 END)                                                            AS b2b_picking_cost,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pack_cost.internal_order_number IS NOT NULL
                           THEN pack_cost.total_assigned_cost
                       ELSE 0 END)                                                            AS b2b_packing_assigned_cost,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_cost
                       ELSE 0 END)                                                            AS b2b_packing_cost,

                SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_assigned_cost
                       WHEN ft.order_type = 'B2B' AND pick_cost.internal_order_number IS NULL THEN
                            estimated_pick_cost.estimated_opex_assigned_cost END)             AS b2b_estimated_picking_assigned_cost,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pick_cost.internal_order_number IS NOT NULL THEN pick_cost.total_cost
                       WHEN ft.order_type = 'B2B' AND pick_cost.internal_order_number IS NULL THEN
                            estimated_pick_cost.estimated_opex_total_cost END)                AS b2b_estimated_picking_cost,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_cost
                       WHEN ft.order_type = 'B2B' AND pack_cost.internal_order_number IS NULL THEN
                            estimated_pack_cost.estimated_opex_total_cost END)               AS b2b_estimated_packing_cost,
               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pack_cost.internal_order_number IS NOT NULL THEN pack_cost.total_assigned_cost
                       WHEN ft.order_type = 'B2B' AND pack_cost.internal_order_number IS NULL THEN
                            estimated_pack_cost.estimated_opex_assigned_cost END)            AS b2b_estimated_packing_assigned_cost,

               SUM(CASE
                       WHEN ft.order_type = 'B2B' AND pkg.internal_order_number IS NOT NULL THEN pkg.total_cost
                       ELSE 0 END)                                                            AS b2b_packaging_cost,
               SUM(COALESCE(attempts_info.quantity, 0))                                       AS attempts_quantity,
               SUM(COALESCE(courier_info.quantity, 0))                                        AS courier_quantity,
               SUM(COALESCE(last_mile_info.quantity, 0))                                      AS last_mile_quantity,
               SUM(CASE WHEN sor.internal_order_number IS NOT NULL THEN 1 ELSE 0 END)         AS revenue_flag,
               SUM(CASE
                       WHEN pick_cost.internal_order_number IS NOT NULL
                           OR pack_cost.internal_order_number IS NOT NULL THEN 1
                       ELSE 0 END)                                                            AS handling_cost_flag,
               SUM(CASE WHEN pkg.internal_order_number IS NOT NULL THEN 1 ELSE 0 END)         AS packaging_cost_flag,
              --JOACO ESTIMATED PACKAGING
              SUM(CASE WHEN epkg.internal_order_number IS NOT NULL THEN 1 ELSE 0 END)         AS estimated_packaging_cost_flag,
               --JOACO ESTIMATED PACKAGING

               SUM(
                       CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                           WHEN attempts_info.rc_fedex > 0 THEN 1
                           WHEN COALESCE(attempts_info.quantity, 0) -
                                (COALESCE(courier_info.quantity, 0) + COALESCE(last_mile_info.quantity, 0)) > 0
                               THEN 0
                           ELSE 1
                           END
               )                                                                              AS transport_flag,
               SUM(CASE
                       WHEN sor.internal_order_number IS NOT NULL
                           AND (pick_cost.internal_order_number IS NOT NULL
                               OR pack_cost.internal_order_number IS NOT NULL)
--                                 AND pkg.internal_order_number IS NOT NULL
                           AND CASE
--                                 WHEN so.closed_date < DATEADD('MONTH', -3, CURRENT_TIMESTAMP::TIMESTAMP) THEN 1
                                   WHEN attempts_info.rc_fedex > 0 THEN TRUE
                                   WHEN COALESCE(attempts_info.quantity, 0) -
                                        (COALESCE(courier_info.quantity, 0) +
                                         COALESCE(last_mile_info.quantity, 0)) > 0
                                       THEN FALSE
                                   ELSE TRUE
                                END
                           THEN 1
                       ELSE 0 END
               )                                                                              AS fulfillment_flag,
               COUNT(CASE WHEN ft.order_type = 'D2C' THEN so.id END)                                  AS total_count_d2c,
               COUNT(CASE WHEN ft.order_type = 'B2B' THEN so.id END)                                  AS total_count_b2b,
               COUNT(so.id)                                                                   AS total_count
           FROM orbita.sell_order AS so
           INNER JOIN orbita.sell_order_state AS sos
                          ON so.sell_order_state_id = sos.id
           INNER JOIN orbita.fulfillment_type AS ft
                            ON so.fulfillment_type_id = ft.id
           INNER JOIN (SELECT
                           sol.sell_order_id,
                           MIN(sol.action_date) AS date
                       FROM orbita.sell_order_log AS sol
                       WHERE sol.sell_order_state_id = 2
                       GROUP BY sol.sell_order_id) AS items_reserved_info
                          ON so.id = items_reserved_info.sell_order_id
           INNER JOIN orbita.seller s
                          ON so.seller_id = s.id
           INNER JOIN orbita.shipping_method AS sm
                          ON so.shipping_method_id = sm.id
           INNER JOIN orbita.warehouse AS w
                          ON so.assigned_warehouse_id = w.id
           LEFT JOIN  (SELECT
                           etc.internal_order_number,
                           SUM(etc.estimated_local_last_mile_cost) AS estimated_local_last_mile_cost,
                           SUM(etc.estimated_courier_cost)         AS estimated_courier_cost
                       FROM profitability.estimated_transport_cost AS etc
                       GROUP BY etc.internal_order_number) AS etc
                          ON so.internal_order_number = etc.internal_order_number
           LEFT JOIN  profitability.estimated_sell_order_revenue AS esor
                          ON so.internal_order_number = esor.internal_order_number
           LEFT JOIN  profitability.sell_order_revenue AS sor
                          ON so.internal_order_number = sor.internal_order_number
           LEFT JOIN  (SELECT
                           ccc.internal_number,
                           SUM(
                                   COALESCE(ccc.shipping_cost, 0) +
                                   COALESCE(ccc.insurance_cost, 0) +
                                   COALESCE(ccc.fuel_cost, 0) +
                                   COALESCE(ccc.additional_cost, 0)
                           )        AS cost,
                           SUM(
                                   COALESCE(ccc.payment_on_delivery_cost, 0)
                           )        AS pod_cost,
                           COUNT(1) AS quantity
                       FROM profitability.courier_companies_cost AS ccc
                       GROUP BY ccc.internal_number) AS courier_info
                          ON so.internal_order_number = courier_info.internal_number
           LEFT JOIN  (SELECT
                           llm.internal_order_number,
                           SUM(llm.total_cost) AS total_cost,
                           COUNT(1)            AS quantity
                       FROM profitability.local_last_mile AS llm
                       GROUP BY llm.internal_order_number) AS last_mile_info
                          ON so.internal_order_number = last_mile_info.internal_order_number
           LEFT JOIN  profitability.picking_cost AS pick_cost
                          ON so.internal_order_number = pick_cost.internal_order_number
           LEFT JOIN  profitability.packing_cost AS pack_cost
                          ON so.internal_order_number = pack_cost.internal_order_number

           LEFT JOIN profitability.estimated_picking_cost AS estimated_pick_cost
                          ON so.internal_order_number = estimated_pick_cost.internal_order_number
           LEFT JOIN profitability.estimated_packing_cost AS estimated_pack_cost
                          ON so.internal_order_number = estimated_pack_cost.internal_order_number

           LEFT JOIN  (SELECT
                           pkg.internal_order_number,
                           SUM(pkg.total_cost) AS total_cost
                       FROM profitability.packaging AS pkg
                       GROUP BY pkg.internal_order_number) AS pkg
                          ON so.internal_order_number = pkg.internal_order_number
           --JOACO ESTIMATED PACKAGING
           LEFT JOIN(SELECT
                         epkg.internal_order_number,
                         SUM(epkg.estimated_cost) AS total_cost
                     FROM profitability.estimated_packaging_cost AS epkg
                     GROUP BY epkg.internal_order_number) AS epkg
                        ON so.internal_order_number = epkg.internal_order_number
           --JOACO ESTIMATED PACKAGING
           LEFT JOIN  (SELECT
                           soa.sell_order_id,
                           COUNT(CASE
                                     WHEN cc.id NOT IN (104, 172, 164) AND so.fulfillment_type_id NOT IN (3,7)
                                         THEN soa.id END) AS quantity,
                           COUNT(CASE
                                     WHEN (cc.id IN (104, 172, 164) OR so.fulfillment_type_id IN (3,7))
                                         AND w.country <> 'Colombia'
                                         THEN soa.id END) AS rc_fedex
                       FROM orbita.sell_order_attempt AS soa
                       INNER JOIN orbita.sell_order AS so
                                      ON soa.sell_order_id = so.id
                       INNER JOIN orbita.warehouse AS w
                                      ON so.assigned_warehouse_id = w.id
                       INNER JOIN orbita.delivery_service ds
                                      ON soa.id = ds.sell_order_attempt_id
                       INNER JOIN orbita.transport_service AS ts
                                      ON ds.transport_service_id = ts.id
                       INNER JOIN orbita.courier_company AS cc
                                      ON ts.courier_company_id = cc.id
                       WHERE ds.delivery_service_state_id NOT IN (1, 2, 3, 8)
                       GROUP BY soa.sell_order_id) AS attempts_info
                          ON attempts_info.sell_order_id = so.id
           WHERE w.operated_by_melonn = 1
             AND items_reserved_info.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, so.seller_id, s.name, w.name,
                    so.assigned_warehouse_id) AS profit_ordenes_items_reservados
              ON
              reference_data.warehouse_id = profit_ordenes_items_reservados.warehouse_id
                  AND reference_data.seller_id = profit_ordenes_items_reservados.seller_id
                  AND reference_data.year_month_date = profit_ordenes_items_reservados.year_month_date
LEFT JOIN (SELECT
               rr.date_of_billing           AS year_month_date,
               bro.assigned_warehouse_id    AS warehouse_id,
               bro.seller_id,
               SUM(rr.anti_picking_charge)  AS anti_picking_charge,
               SUM(rr.anti_shipping_charge) AS anti_shipping_charge
           FROM profitability.returns_revenue AS rr
           LEFT JOIN orbita.buyer_return_order AS bro
                         ON bro.id = rr.internal_order_number
           LEFT JOIN orbita.warehouse AS w
                         ON bro.assigned_warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
           -- AND w.country = 'Colombia'
           GROUP BY year_month_date, bro.assigned_warehouse_id, bro.seller_id) AS return_orders_revenue
              ON reference_data.warehouse_id = return_orders_revenue.warehouse_id AND
                 reference_data.seller_id = return_orders_revenue.seller_id
              AND reference_data.year_month_date = return_orders_revenue.year_month_date
LEFT JOIN (SELECT
               rc.date                     AS year_month_date,
               bro.assigned_warehouse_id   AS warehouse_id,
               bro.seller_id,
               SUM(rc.total_assigned_cost) AS returns_total_assigned_cost,
               SUM(rc.total_cost)          AS returns_total_cost,
               TRUNC(
                       SUM(COALESCE(ccc.shipping_cost, 0)
                           + COALESCE(ccc.payment_on_delivery_cost, 0)
                           + COALESCE(ccc.insurance_cost, 0)
                           + COALESCE(ccc.fuel_cost, 0)
                           + COALESCE(ccc.additional_cost, 0))
                   , 6)                    AS returns_transport_cost
           FROM profitability.returns_cost AS rc
           LEFT JOIN orbita.buyer_return_order AS bro
                         ON bro.id = rc.internal_order_number
           LEFT JOIN orbita.warehouse AS w
                         ON bro.assigned_warehouse_id = w.id
           LEFT JOIN profitability.courier_companies_cost AS ccc
                         ON rc.internal_order_number = ccc.internal_number
           WHERE w.operated_by_melonn = 1
           -- AND w.country = 'Colombia'
           GROUP BY year_month_date, bro.assigned_warehouse_id, bro.seller_id) AS return_orders_cost
              ON reference_data.warehouse_id = return_orders_cost.warehouse_id AND
                 reference_data.seller_id = return_orders_cost.seller_id
              AND reference_data.year_month_date = return_orders_cost.year_month_date
LEFT JOIN (SELECT
               wg.date                    AS year_month_date,
               wg.warehouse_id,
               wg.seller_id,
               SUM(wg.insurance_cost)     AS warehousing_insurance_cost,
               SUM(wg.adjusted_opex_cost) AS warehousing_assigned_cost,
               SUM(wg.total_opex_cost)    AS warehousing_total_cost
           FROM profitability.warehousing AS wg
           INNER JOIN orbita.warehouse AS w
                          ON wg.warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
           -- AND w.country = 'Colombia'
           GROUP BY year_month_date, wg.warehouse_id, wg.seller_id) AS warehousing_cost
              ON reference_data.warehouse_id = warehousing_cost.warehouse_id AND
                 reference_data.seller_id = warehousing_cost.seller_id
              AND reference_data.year_month_date = warehousing_cost.year_month_date
LEFT JOIN (SELECT
               wgr.date_of_billing               AS year_month_date,
               wgr.warehouse_id,
               wgr.seller_id,
               SUM(wgr.storage_charge)           AS warehousing_revenue,
               SUM(wgr.revenue_space)            AS revenue_space,
               SUM(wgr.storage_insurance_charge) AS warehousing_insurance_revenue,
               SUM(wgr.storage_charge_discount)  AS warehousing_discount
           FROM profitability.warehousing_revenue AS wgr
           INNER JOIN orbita.warehouse AS w
                          ON wgr.warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
             AND wgr.date_of_billing >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, wgr.warehouse_id, wgr.seller_id) AS warehousing_revenue
              ON reference_data.warehouse_id = warehousing_revenue.warehouse_id AND
                 reference_data.seller_id = warehousing_revenue.seller_id
              AND reference_data.year_month_date = warehousing_revenue.year_month_date

LEFT JOIN (SELECT
               spor.date_of_billing              AS year_month_date,
               spo.destination_warehouse_id      AS warehouse_id,
               spo.seller_id,
               SUM(spor.supplier_order_charge)   AS inbound_revenue,
               SUM(spor.supplier_order_discount) AS inbound_discount
           FROM profitability.inbound_revenue AS spor
           INNER JOIN orbita.supplier_order AS spo
                          ON spo.internal_order_number = spor.internal_order_number
           INNER JOIN orbita.warehouse AS w
                          ON spo.destination_warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
             AND spor.date_of_billing >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, warehouse_id, spo.seller_id) AS inbound_revenue
              ON reference_data.warehouse_id = inbound_revenue.warehouse_id AND
                 reference_data.seller_id = inbound_revenue.seller_id
              AND reference_data.year_month_date = inbound_revenue.year_month_date
LEFT JOIN (SELECT
               edc.date                                       AS year_month_date,
               edc.warehouse_id,
               edc.seller_id,
               SUM(edc.estimated_net_charge_storage)          AS estimated_warehousing_revenue,
               SUM(edc.estimated_net_charge_fee)              AS ex_estimated_saas,
               SUM(edc.estimated_net_charge_storage_coverage) AS estimated_warehousing_insurance_revenue,
               SUM(edc.opex_total_cost)                       AS estimated_warehousing_total_cost,
               SUM(edc.opex_assigned_cost)                    AS estimated_warehousing_assigned_cost,
               SUM(edc.average_used_m3)                       AS average_used_m3,
               SUM(edc.total_fee_cost)                        AS estimated_saas_cost,
               SUM(edc.total_insurance_cost)                  AS estimated_insurance_cost
           FROM profitability.estimated_daily_charges edc
           INNER JOIN orbita.warehouse AS w
                          ON edc.warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
           -- AND w.country = 'Colombia')
           -- AND edc.date_month >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, warehouse_id, edc.seller_id) AS estimated_daily_charges
              ON reference_data.warehouse_id = estimated_daily_charges.warehouse_id AND
                 reference_data.seller_id = estimated_daily_charges.seller_id
              AND reference_data.year_month_date = estimated_daily_charges.year_month_date

LEFT JOIN (SELECT
             eic.date                           AS year_month_date,
             eic.warehouse_id,
             eic.seller_id,
             SUM(eic.estimated_opex_assigned_cost) AS estimated_inbound_assigned_cost,
             SUM(eic.estimated_opex_total_cost) AS estimated_inbound_total_cost
           FROM profitability.estimated_inbound_cost AS eic
           INNER JOIN orbita.warehouse AS w
                 ON eic.warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
           GROUP BY year_month_date, warehouse_id, seller_id) AS estimated_inbound_cost
              ON reference_data.warehouse_id = estimated_inbound_cost.warehouse_id
                AND reference_data.seller_id = estimated_inbound_cost.seller_id
                AND reference_data.year_month_date = estimated_inbound_cost.year_month_date

LEFT JOIN (SELECT
               spoc.date                     AS year_month_date,
               spo.destination_warehouse_id  AS warehouse_id,
               spo.seller_id,
               SUM(spoc.total_assigned_cost) AS inbound_assigned_cost,
               SUM(spoc.total_cost)          AS inbound_total_cost
           FROM profitability.inbound_cost AS spoc
           INNER JOIN orbita.supplier_order AS spo
                          ON spo.internal_order_number = spoc.internal_order_number
           INNER JOIN orbita.warehouse AS w
                          ON spo.destination_warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
             AND spoc.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, warehouse_id, spo.seller_id) AS inbound_cost
              ON reference_data.warehouse_id = inbound_cost.warehouse_id AND
                 reference_data.seller_id = inbound_cost.seller_id
              AND reference_data.year_month_date = inbound_cost.year_month_date
LEFT JOIN (SELECT
               er.date_of_billing                                                          AS year_month_date,
               er.warehouse_id                                                             AS warehouse_id,
               er.seller_id,
               SUM(CASE WHEN er.billing_type = 'Intereses mora' THEN er.charge ELSE 0 END) AS interest_arrears,
               SUM(CASE WHEN er.billing_type = 'Servicios adicionales' THEN er.charge ELSE 0 END) AS vas,
               SUM(CASE WHEN er.billing_type = 'Empaque' THEN er.charge ELSE 0 END)        AS packaging_revenue,
               SUM(CASE WHEN er.billing_type = 'Transporte' THEN er.charge ELSE 0 END)     AS transport_revenue,
               SUM(CASE WHEN er.billing_type = 'Seller support' THEN er.charge ELSE 0 END) AS seller_support_revenue,
               SUM(CASE
                       WHEN er.billing_type IN ('Facturacion Minima', 'Fee Mensual') THEN er.charge
                       ELSE 0 END)                                                         AS SaaS
           FROM profitability.external_revenue AS er
           INNER JOIN orbita.warehouse AS w
                          ON er.warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
             AND er.date_of_billing >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, er.warehouse_id, er.seller_id) AS external_revenue
              ON reference_data.warehouse_id = external_revenue.warehouse_id AND
                 reference_data.seller_id = external_revenue.seller_id
              AND reference_data.year_month_date = external_revenue.year_month_date
LEFT JOIN (SELECT
               ss.warehouse_id    AS warehouse_id,
               ss.seller_id,
               SUM(ss.total_cost) AS seller_support_cost,
               ss.date            AS year_month_date
           FROM profitability.seller_support AS ss
           GROUP BY year_month_date, warehouse_id, ss.seller_id) AS seller_support
              ON reference_data.warehouse_id = seller_support.warehouse_id AND
                 reference_data.seller_id = seller_support.seller_id
              AND reference_data.year_month_date = seller_support.year_month_date
LEFT JOIN (SELECT
               ar.date                    AS year_month_date,
               ar.warehouse_id            AS warehouse_id,
               ar.seller_id,
               SUM(ar.adjecencies_charge) AS adjecencies_revenue
           FROM profitability.adjecencies_revenue AS ar
           INNER JOIN orbita.warehouse AS w
                          ON ar.warehouse_id = w.id
           WHERE (w.operated_by_melonn = 1 OR w.id IN (3,8))
             -- AND w.country = 'Colombia'
             AND ar.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, ar.warehouse_id, ar.seller_id) AS adjecencies_revenue
              ON reference_data.warehouse_id = adjecencies_revenue.warehouse_id AND
                 reference_data.seller_id = adjecencies_revenue.seller_id
              AND reference_data.year_month_date = adjecencies_revenue.year_month_date
LEFT JOIN (SELECT
               ac.date         AS year_month_date,
               ac.warehouse_id AS warehouse_id,
               ac.seller_id,
               SUM(ac.cost)    AS adjecencies_cost
           FROM profitability.adjecencies_cost AS ac
           INNER JOIN orbita.warehouse AS w
                          ON ac.warehouse_id = w.id
           WHERE (w.operated_by_melonn = 1 OR w.id IN (3,8))
             -- AND w.country = 'Colombia'
             AND ac.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, ac.warehouse_id, ac.seller_id) AS adjecencies_cost
              ON reference_data.warehouse_id = adjecencies_cost.warehouse_id AND
                 reference_data.seller_id = adjecencies_cost.seller_id
              AND reference_data.year_month_date = adjecencies_cost.year_month_date
LEFT JOIN (SELECT
               saas.date                   AS year_month_date,
               saas.warehouse_id           AS warehouse_id,
               saas.seller_id,
               COALESCE(SUM(saas.cost), 0) AS saas_cost
           FROM profitability.saas
           INNER JOIN orbita.warehouse AS w
                          ON saas.warehouse_id = w.id
           WHERE (w.operated_by_melonn = 1 OR w.id IN (3,8))
             -- AND w.country = 'Colombia'
             AND saas.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, saas.warehouse_id, saas.seller_id) AS saas_cost
              ON reference_data.warehouse_id = saas_cost.warehouse_id AND
                 reference_data.seller_id = saas_cost.seller_id
              AND reference_data.year_month_date = saas_cost.year_month_date
LEFT JOIN (SELECT
               dis.date                     AS year_month_date,
               dis.warehouse_id             AS warehouse_id,
               dis.seller_id,
               COALESCE(SUM(dis.charge), 0) AS insurance_discount
           FROM profitability.discounts dis
           INNER JOIN orbita.warehouse AS w
                          ON dis.warehouse_id = w.id
           WHERE (w.operated_by_melonn = 1 OR w.id IN (3,8))
             -- AND w.country = 'Colombia'
             AND dis.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, dis.warehouse_id, dis.seller_id) AS disc
              ON reference_data.warehouse_id = disc.warehouse_id AND
                 reference_data.seller_id = disc.seller_id
              AND reference_data.year_month_date = disc.year_month_date
LEFT JOIN (SELECT
               scc.date                     AS year_month_date,
               scc.warehouse_id             AS warehouse_id,
               scc.seller_id,
               SUM(scc.total_assigned_cost) AS stock_counts_assigned_cost,
               SUM(scc.total_cost)          AS stock_counts_total_cost
           FROM profitability.stock_counts_cost AS scc
           INNER JOIN orbita.warehouse AS w
                          ON scc.warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
             AND scc.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, warehouse_id, scc.seller_id) AS stock_counts_cost
              ON reference_data.warehouse_id = stock_counts_cost.warehouse_id AND
                 reference_data.seller_id = stock_counts_cost.seller_id
              AND reference_data.year_month_date = stock_counts_cost.year_month_date
LEFT JOIN (SELECT
               cldc.date                     AS year_month_date,
               cldc.warehouse_id             AS warehouse_id,
               cldc.seller_id,
               SUM(cldc.total_assigned_cost) AS cancelled_assigned_cost,
               SUM(cldc.total_cost)          AS cancelled_total_cost
           FROM profitability.cancelled_cost AS cldc
           INNER JOIN orbita.warehouse AS w
                          ON cldc.warehouse_id = w.id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
             AND cldc.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, warehouse_id, cldc.seller_id) AS cancelled_orders_cost
              ON reference_data.warehouse_id = cancelled_orders_cost.warehouse_id AND
                 reference_data.seller_id = cancelled_orders_cost.seller_id
              AND reference_data.year_month_date = cancelled_orders_cost.year_month_date
LEFT JOIN (SELECT
               ia.date                      AS year_month_date,
               ia.warehouse_id              AS warehouse_id,
               ia.seller_id,
               SUM(ia.inventory_adjustment) AS inventory_adjustment
           FROM profitability.inventory_adjustments AS ia
           INNER JOIN orbita.warehouse AS w
                          ON ia.warehouse_id = w.id
           WHERE (w.operated_by_melonn = 1 OR w.id IN (3,8))
             -- AND w.country = 'Colombia'
             AND ia.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, ia.warehouse_id, ia.seller_id) AS inventory_adjustments
              ON reference_data.warehouse_id = inventory_adjustments.warehouse_id AND
                 reference_data.seller_id = inventory_adjustments.seller_id
              AND reference_data.year_month_date = inventory_adjustments.year_month_date
LEFT JOIN (SELECT
               tftes.date               AS year_month_date,
               so.assigned_warehouse_id AS warehouse_id,
               so.seller_id,
               SUM(tftes.cost)          AS transport_ftes,
               SUM(tftes.pod_cost)      AS pod_ftes
           FROM profitability.transport_ftes AS tftes
           INNER JOIN orbita.sell_order AS so
                          ON tftes.internal_order_number = so.internal_order_number
           INNER JOIN orbita.warehouse AS w
                          ON w.id = so.assigned_warehouse_id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
             AND tftes.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, warehouse_id, so.seller_id) AS transport_ftes
              ON reference_data.warehouse_id = transport_ftes.warehouse_id AND
                 reference_data.seller_id = transport_ftes.seller_id
              AND reference_data.year_month_date = transport_ftes.year_month_date
--- JOACO
LEFT JOIN (SELECT
               etftes.date AS year_month_date,
               etftes.warehouse_id,
               so.seller_id,
               SUM(etftes.total_transport_cost) AS estimated_transport_ftes,
               SUM(etftes.pud_cost)       AS estimated_pod_ftes
           FROM profitability.estimated_transport_fte AS etftes
           INNER JOIN orbita.sell_order AS so
                          ON etftes.internal_order_number = so.internal_order_number
           INNER JOIN orbita.warehouse AS w
                          ON w.id = so.assigned_warehouse_id
           WHERE w.operated_by_melonn = 1
             -- AND w.country = 'Colombia'
             AND etftes.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, warehouse_id, so.seller_id) AS estimated_transport_ftes
              ON reference_data.warehouse_id = estimated_transport_ftes.warehouse_id AND
                 reference_data.seller_id = estimated_transport_ftes.seller_id
              AND reference_data.year_month_date = estimated_transport_ftes.year_month_date
--- JOACO
LEFT JOIN (SELECT
               gmv.date                        AS year_month_date,
               gmv.warehouse_id                AS warehouse_id,
               gmv.seller_id,
               SUM(gmv.total_col_d2c + gmv.total_mex_d2c)          AS total_d2c,
               SUM(gmv.total_col_b2b + gmv.total_mex_b2b)          AS total_b2b,
               SUM(CASE
                       WHEN w.country = 'Colombia'
                           THEN gmv.total_col
                       ELSE gmv.total_mex END) AS total
           FROM profitability.gmv
           INNER JOIN orbita.warehouse AS w
                          ON gmv.warehouse_id = w.id
           WHERE (w.operated_by_melonn = 1 OR w.id IN (3,8))
             -- AND w.country = 'Colombia'
             AND gmv.date >= '2023-06-01 00:00:00'
           GROUP BY year_month_date, gmv.warehouse_id, gmv.seller_id) AS gmv
              ON reference_data.warehouse_id = gmv.warehouse_id AND
                 reference_data.seller_id = gmv.seller_id
              AND reference_data.year_month_date = gmv.year_month_date
LEFT JOIN (SELECT
               DATE_TRUNC('MONTH', ccc.transport_service_date) AS year_month_date,
               CASE
                   WHEN ccc.country_id = 1 THEN 6
                   ELSE 5 END                                  AS warehouse_id,
               CASE
                   WHEN ccc.country_id = 1 THEN 1050
                   ELSE 1436 END                               AS seller_id,
               TRUNC(
                       SUM(COALESCE(ccc.shipping_cost, 0)
                           + COALESCE(ccc.payment_on_delivery_cost, 0)
                           + COALESCE(ccc.insurance_cost, 0)
                           + COALESCE(ccc.fuel_cost, 0)
                           + COALESCE(ccc.additional_cost, 0))
                   , 6)                                        AS mismatch_transport_cost
           FROM profitability.courier_companies_cost AS ccc
           WHERE match_method IS NULL
           GROUP BY year_month_date,
                    warehouse_id,
                    seller_id) AS missmatch_transport
              ON reference_data.warehouse_id = missmatch_transport.warehouse_id AND
                 reference_data.seller_id = missmatch_transport.seller_id
              AND reference_data.year_month_date = missmatch_transport.year_month_date
    ---------------------------- Joqs & Mario -------------------------------------------------
LEFT JOIN
          (SELECT
               ds.id             AS seller_id,
               'Tier'            AS tier,
               ds.kam_id         AS kam,
               ds.activation_date      AS active_date,
               ds.products_category AS product_category
           FROM core.data_warehouse.dim_seller ds
           WHERE id IS NOT NULL
           ) AS hub
              ON reference_data.seller_id = hub.seller_id

    -------------------------------- Join Hub Viejo----------------------------------------------
--LEFT JOIN
--          (SELECT
--               d.orbita_id             AS seller_id,
 --              MAX(d.tiers)            AS tier,
--               MAX(d.kam_am)           AS kam,
--               MAX(d.active_date)      AS active_date,
--               MAX(d.product_category) AS product_category
--           FROM hubspot.deal d
--           WHERE orbita_id IS NOT NULL
--           GROUP BY seller_id) AS hub
--              ON reference_data.seller_id = hub.seller_id
    ---------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------
LEFT JOIN experience.seller_segmentation sseg
              ON sseg.seller_id = reference_data.seller_id
LEFT JOIN
          ( -- Fecha ingreso de primer item
              SELECT
                  it.owner_seller_id    AS seller_id,
                  MIN(it.creation_date) AS creation_date
              FROM orbita.item AS it
              WHERE it.owner_seller_id NOT IN (26, 80, 81, 797, 1050)
              GROUP BY it.owner_seller_id) AS first_item
              ON first_item.seller_id = reference_data.seller_id
LEFT JOIN (SELECT
               cn.date_of_billing AS year_month_date,
               cn.warehouse_id,
               cn.seller_id,
               SUM(cn.amount)     AS credit_notes_amount
           FROM profitability.credit_notes AS cn
           GROUP BY cn.date_of_billing, cn.warehouse_id, cn.seller_id) AS credit_notes
              ON reference_data.year_month_date = credit_notes.year_month_date
              AND reference_data.warehouse_id = credit_notes.warehouse_id
              AND reference_data.seller_id = credit_notes.seller_id