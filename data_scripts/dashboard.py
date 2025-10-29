# dashboard.py

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

# ----------------- YAPILANDIRMA AYARLARI -----------------
DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Sudem12345" # <-- Kendi şifreniz

def get_db_engine():
    """SQLAlchemy motorunu oluşturur."""
    engine_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    return create_engine(engine_url)

def load_predictions(engine):
    """Veritabanından en son tahmin sonuçlarını çeker."""
    
    # En son ne zaman tahmin yapıldığını bul (prediction_run_time)
    latest_run_time = pd.read_sql("SELECT MAX(prediction_run_time) FROM prediction_results", engine).iloc[0, 0]
    
    # Sadece o en son çalışma zamanındaki verileri çek
    query = f"""
    SELECT * FROM prediction_results 
    WHERE prediction_run_time = '{latest_run_time}'
    ORDER BY branch_id, prediction_date;
    """
    df = pd.read_sql(query, engine)
    
    # branch_id 0 olanı "Genel Toplam" olarak adlandır
    df['branch_name'] = df['branch_id'].apply(lambda x: 'Genel Toplam' if x == 0 else f'Şube {x}')
    return df

# ----------------- STREAMLIT ANA PANELİ -----------------
st.set_page_config(layout="wide")
st.title("💰 Akıllı Şube Satış Tahmin Paneli")

# 1. Veri Yükleme ve Hata Yönetimi
try:
    engine = get_db_engine()
    predictions_df = load_predictions(engine)
    
    # Tüm şube ID'lerini ve Genel Toplamı seçenek olarak hazırla
    branch_options = ['Genel Toplam'] + [f'Şube {i}' for i in predictions_df['branch_id'].unique() if i != 0]
    selected_branch = st.selectbox("Hangi Şubenin Tahminini Görmek İstersiniz?", branch_options)
    
    # Seçime göre filtreleme
    if selected_branch == 'Genel Toplam':
        filtered_df = predictions_df[predictions_df['branch_id'] == 0]
    else:
        # Şube X -> X ID'sini al
        branch_id = int(selected_branch.split(' ')[1])
        filtered_df = predictions_df[predictions_df['branch_id'] == branch_id]

    # 2. Görselleştirme
    st.header(f"📈 {selected_branch} İçin 7 Günlük Tahmin")
    
    # Plotly ile grafik oluşturma
    fig = px.line(
        filtered_df,
        x='prediction_date',
        y='predicted_sales',
        title=f'{selected_branch} Satış Tahmini (₺)',
        labels={'predicted_sales': 'Tahmin Edilen Satış (₺)', 'prediction_date': 'Tarih'}
    )
    
    # Güven aralığını ekleme
    fig.add_scatter(x=filtered_df['prediction_date'], y=filtered_df['upper_bound'], fill=None, mode='lines', line_color='lightgrey', name='Üst Sınır')
    fig.add_scatter(x=filtered_df['prediction_date'], y=filtered_df['lower_bound'], fill='tonexty', mode='lines', line_color='lightgrey', name='Alt Sınır')
    fig.update_layout(showlegend=True)

    st.plotly_chart(fig, use_container_width=True)

    # 3. Detay Tablosu
    st.subheader("Tahmin Detayları (Raw Data)")
    st.dataframe(filtered_df[['prediction_date', 'predicted_sales', 'lower_bound', 'upper_bound', 'prediction_run_time']].reset_index(drop=True), use_container_width=True)

except Exception as e:
    st.error(f"Veritabanı bağlantı hatası veya veri yükleme hatası oluştu: {e}")
    st.info("Lütfen tüm 'seed_data.py' ve 'prediction_engine.py' adımlarının tamamlandığından emin olun.")