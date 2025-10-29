# tüm şubelerin günlük toplam satış miktarını tahmin etmeye odaklanacaktır.

import pandas as pd
from sqlalchemy import create_engine
from prophet import Prophet
from datetime import datetime

# ----------------- 1. YAPILANDIRMA AYARLARI (seed_data.py ile aynı) -----------------
DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Sudem12345" # <-- Şifrenizi kontrol edin

def create_db_engine():
    """SQLAlchemy motorunu oluşturur."""
    engine_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    return create_engine(engine_url)

def get_data_for_prediction(engine):
    """Veritabanından tahmin için gerekli veriyi çeker ve hazırlar."""
    print("-> Veritabanından veriler çekiliyor ve günlük toplam satışa dönüştürülüyor...")
    
    # Tüm şubelerden, tüm tarihlerdeki günlük toplam satış miktarını çeken SQL sorgusu
    query = """
    SELECT 
        DATE(sale_datetime) as ds,  -- Prophet için tarih sütunu 'ds' olmalı
        SUM(total_sale_amount) as y  -- Prophet için tahmin edilecek değer 'y' olmalı
    FROM sales
    GROUP BY DATE(sale_datetime)
    ORDER BY ds;
    """
    
    # Pandas ile veriyi çekme
    df = pd.read_sql(query, engine)
    
    # Tarih formatını kontrol etme
    df['ds'] = pd.to_datetime(df['ds'])
    
    print(f"-> Tahmin için {len(df)} günlük veri seti hazırlandı.")
    return df

def train_and_predict(df, periods=7):
    """Prophet modelini eğitir ve ileriye dönük tahmin yapar."""
    print(f"-> Prophet modeli eğitiliyor...")
    
    # 1. Modeli Tanımlama (Günlük veriye uygun)
    model = Prophet(
        yearly_seasonality=True, # Yıllık trendleri yakala
        weekly_seasonality=True, # Haftalık trendleri yakala
        daily_seasonality=False # Günlük bazda toplama yaptığımız için bu gerekli değil
    )
    
    # 2. Modeli Eğitme
    model.fit(df)
    print("-> Model eğitimi tamamlandı.")

    # 3. Gelecekteki 7 günü belirleme
    future = model.make_future_dataframe(periods=periods)
    
    # 4. Tahmin yapma
    forecast = model.predict(future)
    
    # Sadece gelecek 7 günün tahminlerini al
    prediction = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    
    print(f"-> Önümüzdeki {periods} gün için tahmin başarıyla yapıldı.")
    return prediction

# ----------------- ANA ÇALIŞTIRMA BLOĞU -----------------
if __name__ == "__main__":
    engine = create_db_engine()
    
    if engine:
        # 1. Veriyi çek
        sales_df = get_data_for_prediction(engine)
        
        # 2. Modeli eğit ve 7 günlük tahmin yap
        predictions_7_days = train_and_predict(sales_df, periods=7)
        
        # 3. Sonuçları yazdır
        print("\n================================================")
        print("🚀 ÖNÜMÜZDEKİ 7 GÜN İÇİN TOPLAM SATIŞ TAHMİNİ 🚀")
        print("================================================")
        print(predictions_7_days.to_string(index=False))
        print("\n* yhat: Tahmin edilen ortalama satış miktarı")
        print("* yhat_lower/upper: %80 güven aralığı")
        
    else:
        print("\n[DURDURULDU] Veritabanı bağlantısı kurulamadığı için tahmin yapılamadı.")

    # prediction_engine.py dosyasında, main bloğunun en altı

# 4. Tahmin Sonuçlarını Veritabanına Kaydetme
try:
    print("-> Tahmin sonuçları veritabanına kaydediliyor...")
    
    # Veritabanına kaydetmeden önce sütun adlarını düzenleyelim
    predictions_to_save = predictions_7_days.rename(columns={'ds': 'prediction_date', 'yhat': 'predicted_sales', 'yhat_lower': 'lower_bound', 'yhat_upper': 'upper_bound'})
    
    # Tüm şube toplamı olduğu için branch_id'yi 0 olarak ayarlayalım
    predictions_to_save['branch_id'] = 0 
    
    # Sadece gerekli sütunları alalım
    final_df = predictions_to_save[['branch_id', 'prediction_date', 'predicted_sales', 'lower_bound', 'upper_bound']]

    # Veriyi kaydetme (Artık SQLAlchemy kullanıyoruz)
    final_df.to_sql('prediction_results', engine, schema='public', if_exists='append', index=False)
    
    print("-> Tahmin sonuçları başarıyla 'prediction_results' tablosuna yüklendi.")
    
except Exception as e:
    print(f"!!! [KAYIT HATASI] Tahmin sonuçları yüklenemedi: {e}")