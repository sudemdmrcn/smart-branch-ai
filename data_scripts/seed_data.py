import psycopg2
from psycopg2 import sql
import pandas as pd
from faker import Faker
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
FAKE = Faker('tr_TR')

# ----------------- 1. YAPILANDIRMA AYARLARI -----------------
DB_HOST = "localhost"
DB_NAME = "postgres"  
DB_USER = "postgres"
DB_PASS = "Sudem12345" # <-- Kendi şifreniz, Türkçe karakter olmamalı

# ----------------- 2. VERITABANI MOTORU OLUŞTURMA -----------------
def create_db_engine():
    """SQLAlchemy motoru (engine) oluşturur."""
    try:
        engine_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
        engine = create_engine(engine_url)
        print("\n[BAŞARILI] SQLAlchemy Motoru oluşturuldu.")
        
        # Basit bir test bağlantısı yapalım
        with engine.connect() as conn:
            conn.close()
        print("-> Veritabanı bağlantı testi başarılı.")
        return engine
    except Exception as e:
        print(f"\n[HATA] Veritabanı motoru oluşturulamadı!")
        print(f"SQLAlchemy Hatası: {e}")
        return None


# ----------------- 3. ÖRNEK VERI ÜRETME FONKSIYONLARI -----------------

def generate_branch_data(num_branches=5):
    """Branches tablosu için statik şube verisi üretir."""
    branch_list = []
    start_date = datetime(2020, 1, 1) 
    for i in range(1, num_branches + 1):
        city = FAKE.city()
        branch_list.append({
            'branch_name': f"{city} Şubesi",
            'city': city,
            'address': FAKE.address(),
            'opening_date': start_date + timedelta(days=random.randint(100, 1000))
        })
    return pd.DataFrame(branch_list)


def generate_employee_data(branches_df, num_employees_per_branch=8):
    """Her şubeye belirli sayıda personel atayarak veri üretir."""
    employee_list = []
    employee_count = 1 
    job_titles = ['Kasiyer', 'Satış Temsilcisi', 'Vardiya Müdürü', 'Depo Görevlisi']
    
    for branch_id in branches_df['branch_id']:
        for _ in range(num_employees_per_branch):
            employee_list.append({
                'employee_id': employee_count,
                'first_name': FAKE.first_name(),
                'last_name': FAKE.last_name(),
                'job_title': random.choice(job_titles),
                'hourly_wage': round(random.uniform(150, 400), 2),
                'branch_id': branch_id 
            })
            employee_count += 1
    return pd.DataFrame(employee_list)
    

def generate_product_data(num_products=100):
    """100 adet sahte ürün verisi üretir."""
    product_list = []
    categories = ['Süt Ürünleri', 'Bakliyat', 'Elektronik', 'Temizlik', 'Meyve&Sebze', 'Fırın Ürünleri']
    
    for i in range(1, num_products + 1):
        category = random.choice(categories)
        if category in ['Süt Ürünleri', 'Fırın Ürünleri', 'Meyve&Sebze']:
            cost = round(random.uniform(5, 50), 2)
        else:
            cost = round(random.uniform(100, 500), 2)
            
        product_list.append({
            'product_name': f"{category} - {FAKE.word().capitalize()}",
            'sku': FAKE.unique.numerify('SKU-######'),
            'category': category,
            'current_stock_level': random.randint(50, 500),
            'unit_cost': cost,
            'selling_price': round(cost * random.uniform(1.2, 1.8), 2),
            'reorder_point': random.randint(10, 50)
        })
    return pd.DataFrame(product_list)



# -------belirli tarih aralıgında rastgele satış verileri

def generate_sales_data(engine, start_date, end_date, sales_per_day_per_branch=150):
    """Belirli bir tarih aralığında rastgele satış verileri üretir ve yükler."""
    
    # Veritabanından gerekli ID'leri çekiyoruz:
    branches_in_db = pd.read_sql_table('branches', engine, schema='public', columns=['branch_id'])
    products_in_db = pd.read_sql_table('products', engine, schema='public', columns=['product_id', 'selling_price', 'unit_cost'])
    employees_in_db = pd.read_sql_table('employees', engine, schema='public', columns=['employee_id', 'branch_id'])
    
    sales_list = []
    current_date = start_date
    
    # Hızlı döngü için ID listelerini hazırlama
    branch_ids = branches_in_db['branch_id'].tolist()
    product_ids = products_in_db['product_id'].tolist()
    
    print(f"\n-> Satış hareketleri simülasyonu başlatılıyor ({start_date} - {end_date})...")

    while current_date <= end_date:
        # Her şube ve her gün için satış simülasyonu
        for branch_id in branch_ids:
            
            # O şubede o gün çalışan personelleri filtrele
            # Şimdilik basitleştirelim: o şubede kayıtlı olan tüm personellerden rastgele seçelim.
            employees_at_branch = employees_in_db[employees_in_db['branch_id'] == branch_id]['employee_id'].tolist()
            
            if not employees_at_branch:
                continue # Çalışan yoksa satış da yok
            
            for _ in range(sales_per_day_per_branch):
                
                product_row = products_in_db.sample(n=1).iloc[0]
                
                # Rastgele saat ve dakika oluşturma (8:00 - 22:00 arası)
                sale_time = datetime(current_date.year, current_date.month, current_date.day, 
                                     random.randint(8, 22), random.randint(0, 59), random.randint(0, 59))
                
                quantity = random.randint(1, 5)
                unit_price = product_row['selling_price']
                total_amount = round(quantity * unit_price, 2)
                
                sales_list.append({
                    'sale_datetime': sale_time,
                    'branch_id': branch_id,
                    'product_id': product_row['product_id'],
                    'quantity': quantity,
                    'unit_price_at_sale': unit_price,
                    'total_sale_amount': total_amount,
                    'employee_id': random.choice(employees_at_branch)
                })
        
        current_date += timedelta(days=1)
    
    sales_df = pd.DataFrame(sales_list)
    return sales_df

# ----------------- 4. ANA ÇALIŞTIRMA BLOĞU -----------------
def load_data(engine, df, table_name):
    """Veriyi veritabanına yükler ve sonucu yazdırır."""
    try:
        # Pandas to_sql ile yükleme
        df.to_sql(table_name, engine, schema='public', if_exists='append', index=False)
        print(f"-> {len(df)} adet {table_name} verisi başarıyla yüklendi.")
        return True
    except Exception as e:
        # PostgreSQL'de tablo boş değilse ve Primary Key hatası varsa uyarı ver.
        if "duplicate key value violates unique constraint" in str(e):
             print(f"!!! [YÜKLEME HATASI] '{table_name}' zaten dolu. Yeni veri yüklenmedi.")
        else:
            print(f"!!! [YÜKLEME HATASI] '{table_name}' tablosuna yükleme başarısız: {e}")
        return False

if __name__ == "__main__":
    
    engine = create_db_engine()
    
    if engine is None:
        print("\n[DURDURULDU] Motor hatası nedeniyle veri üretimi başlatılamadı.")
    else:
        print("\n-> BAĞLANTI BAŞARILI. Veri üretimi ve yükleme başlıyor...")
        
        # 1. ŞUBE VERİSİ YÜKLEMESİ
        branches_df = generate_branch_data(num_branches=5)
        load_data(engine, branches_df, 'branches')
        
        # 2. PERSONEL VERİSİ YÜKLEMESİ
        try:
            # Personel ataması için veritabanındaki şube ID'lerini çek
            branches_in_db = pd.read_sql_table('branches', engine, schema='public', columns=['branch_id'])
            employees_df = generate_employee_data(branches_df=branches_in_db, num_employees_per_branch=8)
            load_data(engine, employees_df, 'employees')
            
        except Exception as e:
             print(f"!!! [VERİ OKUMA HATASI] Employees yüklenemedi. Önce branches tablosu dolu olmalı: {e}")

        # 3. ÜRÜN VERİSİ YÜKLEMESİ
        products_df = generate_product_data(num_products=100)
        load_data(engine, products_df, 'products')
        
        print("\n[TAMAMLANDI] Tüm işlemler bitti. Artık sales verisine geçebiliriz!")
        