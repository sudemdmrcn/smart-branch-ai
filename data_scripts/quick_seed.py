"""
Küçük veri yükleme scripti (hafif POC):
- 1 şube, 5 çalışan, 10 ürün
- Son 14 güne ait günlük 20 satış (toplam ~280 kayıt)
Uyarı: Var olan tablolara veri ekler; şema yoksa önce oluşturmanız gerekir.
"""

import random
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import create_engine

# ----------------- DB AYARLARI -----------------
DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Sudem12345"

def create_db_engine():
    engine_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    return create_engine(engine_url)


def load_data(engine, df, table_name):
    df.to_sql(table_name, engine, schema="public", if_exists="append", index=False)
    print(f"[OK] {len(df)} satır {table_name} tablosuna eklendi.")


def main():
    engine = create_db_engine()
    today = datetime.now().date()

    # Şube
    branches_df = pd.DataFrame(
        [{"branch_id": 1, "branch_name": "Merkez", "city": "İstanbul", "address": "Merkez", "opening_date": today - timedelta(days=365)}]
    )

    # Çalışan
    employees_df = pd.DataFrame(
        [
            {"employee_id": i + 1, "first_name": f"Emp{i+1}", "last_name": "Test", "job_title": "Satış", "hourly_wage": 200 + i * 5, "branch_id": 1}
            for i in range(5)
        ]
    )

    # Ürün
    products = []
    categories = ["Süt", "Bakliyat", "Atıştırmalık", "İçecek", "Temizlik"]
    for i in range(10):
        cat = random.choice(categories)
        cost = round(random.uniform(5, 50), 2)
        products.append(
            {
                "product_id": i + 1,
                "product_name": f"{cat} Ürün {i+1}",
                "sku": f"SKU-{1000+i}",
                "category": cat,
                "current_stock_level": random.randint(30, 120),
                "unit_cost": cost,
                "selling_price": round(cost * random.uniform(1.3, 1.8), 2),
                "reorder_point": random.randint(10, 40),
            }
        )
    products_df = pd.DataFrame(products)

    # Satışlar (son 14 gün, günde ~20 satış)
    sales = []
    start_date = today - timedelta(days=13)
    for day_offset in range(14):
        sale_date = start_date + timedelta(days=day_offset)
        for _ in range(20):
            prod = products_df.sample(1).iloc[0]
            qty = random.randint(1, 4)
            total_amount = round(qty * prod["selling_price"], 2)
            sales.append(
                {
                    "sale_datetime": datetime.combine(sale_date, datetime.min.time()) + timedelta(hours=random.randint(9, 21), minutes=random.randint(0, 59)),
                    "branch_id": 1,
                    "product_id": int(prod["product_id"]),
                    "quantity": qty,
                    "unit_price_at_sale": prod["selling_price"],
                    "total_sale_amount": total_amount,
                    "employee_id": random.randint(1, 5),
                }
            )
    sales_df = pd.DataFrame(sales)

    # Yükleme sırası: branches -> employees -> products -> sales
    load_data(engine, branches_df, "branches")
    load_data(engine, employees_df, "employees")
    load_data(engine, products_df, "products")
    load_data(engine, sales_df, "sales")

    print("\nBitti. Küçük veri seti yüklendi.")


if __name__ == "__main__":
    main()

