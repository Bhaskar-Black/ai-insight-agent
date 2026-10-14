import datetime
import json
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

OUTPUT_PATH = os.path.join("src", "dashboard_snapshot.json")


def normalize_db_url(url):
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def main():
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not found. Add it to your .env file first.")

    engine = create_engine(normalize_db_url(url), connect_args={"connect_timeout": 15})

    print("Running aggregate queries (this can take a little while on the free tier)...")
    kpis = pd.read_sql_query(
        "SELECT COUNT(DISTINCT order_id) AS total_orders, COUNT(DISTINCT product_id) AS total_products, "
        "AVG(reordered) AS reorder_rate FROM order_products_full", engine).iloc[0]
    dept = pd.read_sql_query(
        "SELECT department, COUNT(*) AS order_count, AVG(reordered) AS reorder_rate "
        "FROM order_products_full GROUP BY department", engine)

    payload = {
        "created": datetime.date.today().isoformat(),
        "kpis": {"total_orders": int(kpis["total_orders"]),
                 "total_products": int(kpis["total_products"]),
                 "reorder_rate": float(kpis["reorder_rate"])},
        "departments": [{"department": str(r["department"]),
                         "order_count": int(r["order_count"]),
                         "reorder_rate": float(r["reorder_rate"])} for _, r in dept.iterrows()],
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Saved {OUTPUT_PATH}: {payload['kpis']['total_orders']:,} orders, "
          f"{len(payload['departments'])} departments.")


if __name__ == "__main__":
    main()