-- ============================================================
-- DDL: historical_revenue
-- Proyecto: Cohortes Melonn
-- Propósito: Revenue histórico Dic 2020 – Dic 2023 en moneda local,
--            cargado desde "Insumos COL & MEX Cohortes (Revenue historico).xlsx"
--            Fuente: 1,726 sellers × 37 meses = 63,862 filas
--
-- COL: 1,242 sellers (revenue en COP)
-- MEX:   484 sellers (revenue en MXN)
--
-- Correr ANTES de hacer COPY / INSERT desde el CSV.
-- ============================================================

CREATE TABLE IF NOT EXISTS staging.profitability.historical_revenue (
    seller_id       INTEGER      NOT NULL,
    country_id      INTEGER      NOT NULL,   -- 1 = COL (COP), 2 = MEX (MXN)
    revenue_month   DATE         NOT NULL,   -- primer día del mes, ej. 2021-02-01
    total_revenue   NUMERIC(18,2) NOT NULL   -- moneda local (COP o MXN)
)
DISTKEY(seller_id)
SORTKEY(revenue_month, seller_id);

COMMENT ON TABLE staging.profitability.historical_revenue IS
    'Revenue histórico Dic 2020–Dic 2023 en moneda local. '
    'Fuente: Insumos COL & MEX Cohortes (Revenue historico).xlsx. '
    'COL=COP, MEX=MXN. Usar para UNION con datos Redshift desde Ene 2024.';
