"""
ETL: Carga de historical_revenue.csv → Redshift
================================================
Proyecto : Cohortes Melonn
Tabla     : staging.finance.financial_planning_historical_revenue
Columnas  : date | seller_id | total_revenue | country_id

El CSV fue generado a partir de:
    "Insumos COL & MEX Cohortes (Revenue historico).xlsx"
    Hojas COL (country_id=1, COP) y MEX (country_id=2, MXN)
    37 meses: Dic 2020 – Dic 2023
    63,862 filas | 1,726 sellers únicos

Requisitos:
    pip install pandas sqlalchemy psycopg2-binary

Pasos:
    1. Llenar credenciales en la sección CONFIG
    2. python 02_load_historical_revenue.py
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(__file__), "historical_revenue.csv")

# Credenciales Redshift (igual que connection.py del SG&A Control)
REDSHIFT_HOST     = "your-cluster.redshift.amazonaws.com"
REDSHIFT_PORT     = 5439
REDSHIFT_DB       = "your_database"
REDSHIFT_USER     = "your_user"
REDSHIFT_PASSWORD = "your_password"

TARGET_SCHEMA     = "finance"
TARGET_TABLE      = "financial_planning_historical_revenue"
TRUNCATE_BEFORE   = True
# ─────────────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("ETL: historical_revenue.csv → Redshift")
    print(f"Destino: staging.{TARGET_SCHEMA}.{TARGET_TABLE}")
    print("=" * 60)

    # 1. Leer CSV y renombrar columnas para que coincidan con la tabla
    print(f"\n Leyendo {CSV_PATH} ...")
    df = pd.read_csv(CSV_PATH, parse_dates=["revenue_month"])

    df = df.rename(columns={"revenue_month": "date"})
    df["date"]          = df["date"].dt.date
    df["seller_id"]     = df["seller_id"].astype(int)
    df["country_id"]    = df["country_id"].astype(int)
    df["total_revenue"] = df["total_revenue"].round(2)

    # Orden exacto de columnas de la tabla
    df = df[["date", "seller_id", "total_revenue", "country_id"]]

    print(f"  {len(df):,} filas | {df['seller_id'].nunique():,} sellers únicos")
    print(f"  Rango: {df['date'].min()} → {df['date'].max()}")
    print(f"  COL (country_id=1): {(df.country_id==1).sum():,} filas")
    print(f"  MEX (country_id=2): {(df.country_id==2).sum():,} filas")
    print("\n  Preview:")
    print(df.head(3).to_string(index=False))

    # 2. Conectar a Redshift
    print("\n Conectando a Redshift ...")
    conn_str = (
        f"postgresql+psycopg2://{REDSHIFT_USER}:{REDSHIFT_PASSWORD}"
        f"@{REDSHIFT_HOST}:{REDSHIFT_PORT}/{REDSHIFT_DB}"
    )
    engine = create_engine(conn_str, connect_args={"sslmode": "require"})
    print("  Conexión OK.")

    # 3. Truncar
    with engine.begin() as conn:
        if TRUNCATE_BEFORE:
            print(f"\n Truncando {TARGET_SCHEMA}.{TARGET_TABLE} ...")
            conn.execute(text(f"TRUNCATE TABLE {TARGET_SCHEMA}.{TARGET_TABLE}"))

    # 4. Insertar en lotes
    print(f"\n Cargando {len(df):,} filas ...")
    df.to_sql(
        name=TARGET_TABLE,
        con=engine,
        schema=TARGET_SCHEMA,
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi"
    )

    # 5. Validar
    print("\n── VALIDACIÓN ──────────────────────────────────────────")
    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT
                country_id,
                MIN(date)             AS desde,
                MAX(date)             AS hasta,
                COUNT(DISTINCT seller_id) AS sellers,
                COUNT(*)              AS filas,
                ROUND(SUM(total_revenue)) AS revenue_total
            FROM {TARGET_SCHEMA}.{TARGET_TABLE}
            GROUP BY country_id ORDER BY country_id
        """))
        rows = result.fetchall()
        print(f"  {'pais':>6} {'desde':>12} {'hasta':>12} "
              f"{'sellers':>8} {'filas':>8} {'revenue_total':>15}")
        print("  " + "-" * 67)
        for r in rows:
            pais = "COL" if r[0] == 1 else "MEX"
            print(f"  {pais:>6} {str(r[1]):>12} {str(r[2]):>12} "
                  f"{r[3]:>8,} {r[4]:>8,} {r[5]:>15,.0f}")

    print("\n ETL completado exitosamente.")


if __name__ == "__main__":
    main()
