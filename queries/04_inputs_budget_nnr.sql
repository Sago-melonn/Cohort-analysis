-- Budget NNR / NNO 2026
-- Fuente: staging.finance.financial_planning_budget_nnr
--
-- Columnas:
--   date             : primer día del mes presupuestado
--   country_id       : 1 = COL, 2 = MEX
--   budget_nnr_base  : NNR objetivo ("Junta")  — en USD brutos
--   budget_nno_base  : NNO objetivo ("Junta")  — en órdenes
--   budget_nnr_bear  : NNR escenario conservador — en USD brutos
--   budget_nno_bear  : NNO escenario conservador — en órdenes

SELECT
    date,
    country_id,
    budget_nnr_base,
    budget_nno_base,
    budget_nnr_bear,
    budget_nno_bear
FROM staging.finance.financial_planning_budget_nnr
ORDER BY date, country_id
