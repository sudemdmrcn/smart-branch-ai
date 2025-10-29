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
DB_NAME = "postgres" # Küçük harf, doğru isim
DB_USER = "postgres"  
DB_PASS = "Sudem12345" # <-- Kendi şifreniz, Türkçe karakter olmamalı

# ----------------- 2. VERITABANI BAĞLANTI FONKSIYONU (YENİ) -----------------
def create_db_engine():
    """SQLAlchemy motoru (engine) oluşturur."""
    try:
        # PostgreSQL bağlantı dizesi: Host, User, Pass ve DB_NAME'i kullanır
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


# ----------------- 3. ÖRNEK VERI ÜRETME FONKSIYONLARI BURAYA GELECEK! -----------------

def generate_branch_data(num_branches=5):
    """Branches tablosu için statik şube verisi üretir."""
    branch_list = []
    # Şube açılış tarihleri için bir başlangıç tarihi tanımlıyoruz
    start_date = datetime(2020, 1, 1) 

    for i in range(1, num_branches + 1):
        city = FAKE.city()
        branch_list.append({
            # Tablo yapımızdaki sütun adlarını kullanıyoruz:
            # 'branch_id': i, 
            'branch_name': f"{city} Şubesi",
            'city': city,
            'address': FAKE.address(),
            'opening_date': start_date + timedelta(days=random.randint(100, 1000))
        })
    return pd.DataFrame(branch_list)
# -------------------------------------------------------------------------------------
# ----------------- 4. ANA ÇALIŞTIRMA BLOĞU -----------------

if __name__ == "__main__":
    
    # 1. SQLAlchemy Motorunu Dene
    engine = create_db_engine() # <-- ARTIK BU ÇAĞRILIYOR
    
    if engine is None:
        print("\n[DURDURULDU] Motor hatası nedeniyle veri üretimi başlatılamadı.")
    else:
        print("\n-> BAĞLANTI BAŞARILI. Veri üretimi ve yükleme başlıyor...")
        
        # 1. ŞUBE VERİSİ ÜRETİMİ VE YÜKLEMESİ
        branches_df = generate_branch_data(num_branches=5)
        
        try:
            # YENİ YÜKLEME KODU: engine kullanılıyor ve 'commit' gerekmiyor
            branches_df.to_sql('branches', engine, schema='public', if_exists='append', index=False)
            
            print(f"-> {len(branches_df)} adet şube verisi başarıyla yüklendi.")
            
        except Exception as e:
            print(f"!!! [YÜKLEME HATASI] 'branches' tablosuna yükleme başarısız: {e}")
            
        print("\n[TAMAMLANDI] Tüm işlemler bitti.")