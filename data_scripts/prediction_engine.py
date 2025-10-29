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

# prediction_engine.py dosyasındaki fonksiyonları değiştirin

def get_data_for_prediction(engine, branch_id=None):
    """Belirli bir şube veya tüm şubeler için günlük toplam satış verisini çeker."""
    
    # 0 = Tüm şubeler. branch_id verilirse o şube için filtreleme yapılır.
    if branch_id and branch_id != 0:
        filter_clause = f"WHERE branch_id = {branch_id}"
        print(f"-> Veri çekiliyor: Sadece Şube {branch_id}")
    else:
        filter_clause = ""
        print("-> Veri çekiliyor: Tüm Şubeler Toplamı")

    query = f"""
    SELECT 
        DATE(sale_datetime) as ds,  -- Prophet için tarih
        SUM(total_sale_amount) as y  -- Tahmin edilecek değer
    FROM sales
    {filter_clause}
    GROUP BY DATE(sale_datetime)
    ORDER BY ds;
    """
    
    df = pd.read_sql(query, engine)
    df['ds'] = pd.to_datetime(df['ds'])
    
    return df

def train_and_predict(df, branch_id, periods=7):
    """Prophet modelini eğitir, tahmin yapar ve sonucu kaydetmeye hazırlar."""
    
    # Veri setinde yeterli veri yoksa tahmin yapma (Örn: yeni şubeler)
    if len(df) < 30:
        print(f"!!! Şube {branch_id}: Tahmin için yeterli veri yok (Minimum 30 gün gerekli).")
        return None
        
    print(f"-> Şube {branch_id}: Model eğitiliyor...")
    
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False
    )
    
    model.fit(df)
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)

    prediction = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods).copy()
    
    # Sütun adlarını veritabanına uyarlıyoruz
    prediction.rename(columns={'ds': 'prediction_date', 'yhat': 'predicted_sales', 'yhat_lower': 'lower_bound', 'yhat_upper': 'upper_bound'}, inplace=True)
    
    # Hangi şube için tahmin yapıldığını ekliyoruz
    prediction['branch_id'] = branch_id 
    
    return prediction
# ----------------- ANA ÇALIŞTIRMA BLOĞU -----------------
# prediction_engine.py dosyasında, main bloğunun içini değiştirin

if __name__ == "__main__":
    engine = create_db_engine()
    
    if engine:
        
        # 0. Veritabanından mevcut şube ID'lerini çek
        try:
            branch_ids_in_db = pd.read_sql_table('branches', engine, schema='public', columns=['branch_id'])['branch_id'].tolist()
        except Exception:
            print("!!! HATA: 'branches' tablosu bulunamadı. Lütfen seed_data.py'yi çalıştırın.")
            branch_ids_in_db = []
            
        # Tahmin sonuçlarını kaydetmek için boş bir liste oluştur
        all_predictions = []
        
        # 1. Tüm Şubeler İçin Tahmin Yap (branch_id = 0, Toplam Satış)
        branch_ids_to_predict = [0] + branch_ids_in_db # [0, 1, 2, 3, 4, 5]
        
        print("\n================================================")
        print("🤖 BAŞLIYOR: Şube Bazlı Satış Tahmin Motoru")
        print("================================================")
        
        for branch_id in branch_ids_to_predict:
            
            # Veriyi çek
            df = get_data_for_prediction(engine, branch_id=branch_id)
            
            # Modeli eğit ve tahmin yap
            prediction_df = train_and_predict(df, branch_id=branch_id, periods=7)
            
            if prediction_df is not None:
                all_predictions.append(prediction_df)
                
            print(f"-> Şube {branch_id} için işlem tamamlandı.")

        
        # 2. Tahmin Sonuçlarını Birleştirme ve Veritabanına Kaydetme
        if all_predictions:
            final_predictions_df = pd.concat(all_predictions)
            
            print(f"\n-> TOPLAM {len(final_predictions_df)} adet yeni tahmin kaydı yüklenecek.")
            
            # Veriyi kaydetme
            final_predictions_df.to_sql('prediction_results', engine, schema='public', if_exists='append', index=False)
            
            print("✅ Tahmin sonuçları başarıyla 'prediction_results' tablosuna yüklendi.")
            
        else:
            print("!!! HATA: Yüklenecek tahmin bulunamadı.")
            
    print("\n[TAMAMLANDI] Tahmin Motoru çalışması sona erdi.")