-- =============================================================
-- 03_inputs_forecast.sql
-- Forecast de órdenes por seller × mes
-- Fuente: core.forecast.official_forecast_temp
-- Granularidad output: seller_id × forecast_month
--
-- NOTA: la tabla ya refleja el forecast oficial vigente.
--       No se filtra por version_id — las versiones son control
--       interno y no deben afectar la lectura de datos.
--
-- NOTA: cohort_month viene de dim_seller (no del forecast)
--       para que ajustes administrativos de cohorte apliquen
--       automáticamente sin modificar el forecast.
--
-- Validado: D5 OK (2026-04-09)
-- =============================================================

WITH params AS (
    SELECT
        NULL::INTEGER  AS country_filter,   -- 1=COL, 2=MEX, NULL=ambos
        NULL::VARCHAR  AS segment_filter    -- 'Starter','Plus','Top','Enterprise', NULL=todos
),

forecast_monthly AS (
    SELECT
        seller_id,
        DATE_TRUNC('month', date)::DATE   AS forecast_month,
        SUM(forecasted_orders)            AS forecasted_orders
    FROM core.forecast.official_forecast_temp
    GROUP BY seller_id, DATE_TRUNC('month', date)::DATE
)

SELECT
    s.id                                        AS seller_id,
    DATE_TRUNC('month', s.cohort)::DATE         AS cohort_month,
    s.segment,
    s.country_id,
    DATEDIFF('month',
        DATE_TRUNC('month', s.cohort)::DATE,
        fm.forecast_month
    ) + 1                                       AS lifecycle_month,
    fm.forecast_month,
    fm.forecasted_orders
FROM forecast_monthly fm
INNER JOIN core.data_warehouse.dim_seller s
    ON fm.seller_id = s.id
CROSS JOIN params p
WHERE s.segment IN ('Starter', 'Plus', 'Top', 'Enterprise')
  AND (p.country_filter IS NULL OR s.country_id = p.country_filter)
  AND (p.segment_filter IS NULL OR s.segment = p.segment_filter)
  AND fm.forecast_month <= '2026-12-01'
ORDER BY cohort_month, seller_id, forecast_month;
