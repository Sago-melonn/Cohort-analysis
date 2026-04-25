-- =============================================================
-- 03_inputs_forecast_V2.sql
-- Forecast de órdenes por seller × mes (sin filtros — carga completa)
-- Fuente: core.forecast.official_forecast_temp
--
-- Sin params CTE — todos los filtros se aplican en Python
-- por data_loader._load_forecast_raw() → load_forecast().
--
-- Filtros aplicados en Python (data_loader.py):
--   segments   : df[df["segment"].isin(expanded)]
--   country_id : df[df["country_id"] == country_id]
--
-- NOTA: la tabla ya refleja el forecast oficial vigente.
--       No se filtra por version_id — las versiones son control interno.
-- NOTA: cohort_month viene de dim_seller para que ajustes administrativos
--       de cohorte apliquen automáticamente.
-- =============================================================

WITH

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
    s.name                                      AS seller_name,
    DATE_TRUNC('month', s.cohort)::DATE         AS cohort_month,
    s.segment,
    s.country_id,
    CASE WHEN s.state <> 'Active' THEN 1 ELSE 0 END AS churn_flag,
    DATEDIFF('month',
        DATE_TRUNC('month', s.cohort)::DATE,
        fm.forecast_month
    ) + 1                                       AS lifecycle_month,
    fm.forecast_month,
    fm.forecasted_orders
FROM forecast_monthly fm
INNER JOIN core.data_warehouse.dim_seller s
    ON fm.seller_id = s.id
WHERE s.cohort IS NOT NULL
  AND fm.forecast_month <= '2026-12-01'
ORDER BY cohort_month, seller_id, forecast_month;
