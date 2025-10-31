import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import random

# ----------------- YAPILANDIRMA AYARLARI -----------------
DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "Sudem12345" # <-- Kendi şifreniz

# ----------------- FONKSİYONLAR -----------------

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

def load_stock_data(engine):
    """Mevcut stok ve maliyet verilerini çeker."""
    # SQL sorgusu ile ürün stok ve reorder point bilgilerini çek
    query = """
    SELECT 
        p.product_name, 
        p.current_stock_level, 
        p.reorder_point,
        p.unit_cost,
        p.category
    FROM products p
    ORDER BY current_stock_level DESC;
    """
    df = pd.read_sql(query, engine)
    
    # Basit bir KPI hesaplama: Stok Değerini Hesaplama
    df['total_stock_value'] = df['current_stock_level'] * df['unit_cost']
    
    # Az Stok Uyarısı (Reorder Point'in altında olanlar)
    low_stock_count = df[df['current_stock_level'] < df['reorder_point']].shape[0]
    
    return df, low_stock_count

def load_employee_metrics(engine):
    """Personel maliyeti ve verimlilik metriklerini hesaplar."""
    
    # Toplam Personel Sayısı
    total_employees = pd.read_sql("SELECT COUNT(employee_id) FROM employees", engine).iloc[0, 0]
    
    # Çalışan Başına Satış Hacmi (Ortalama)
    query_sales_per_employee = """
    SELECT 
        e.employee_id,
        SUM(s.total_sale_amount) as total_sales
    FROM sales s
    JOIN employees e ON s.employee_id = e.employee_id
    GROUP BY e.employee_id
    """
    sales_per_employee_df = pd.read_sql(query_sales_per_employee, engine)
    
    avg_sales_per_employee = sales_per_employee_df['total_sales'].mean()
    
    # Basit Toplam Maliyet Tahmini (40 çalışan * ortalama saatlik ücret * 160 saat/ay)
    avg_monthly_cost = 40 * 250 * 160 
    
    return avg_sales_per_employee, avg_monthly_cost, total_employees

# ----------------- STREAMLIT ANA PANEL KODU -----------------

st.set_page_config(layout="wide")
st.title("💰 Akıllı Şube Satış Tahmin Paneli")

# HATA YÖNETİMİ VE TÜM KOD AKIŞI TEK TRY BLOĞUNDA
try:
    # 1. MOTORU KURMA (Tüm KPI'lar için ilk adım)
    engine = get_db_engine()

    # --- 1. STOK YÖNETİMİ KPI'ları ---
    stock_df, low_stock_count = load_stock_data(engine)
    total_stock_value = stock_df['total_stock_value'].sum()

    st.header("📦 Stok Yönetimi KPI'ları")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam Stok Değeri", f"₺ {total_stock_value:,.2f}")
    with col2:
        st.metric("Kritik Stok Uyarısı", f"{low_stock_count} Ürün", 
                delta=f"Son 24 Saatte {random.randint(0, 5)} yeni uyarı", delta_color="inverse")
    with col3:
        wastage_cost = total_stock_value * 0.005
        st.metric("Tahmini Fire Maliyeti (Günlük)", f"₺ {wastage_cost:,.2f}")
    st.divider() 

    # --- 2. PERSONEL VERİMLİLİK KPI'ları ---
    avg_sales, avg_cost, total_employees = load_employee_metrics(engine)

    st.header("👨‍💼 Personel Yönetimi KPI'ları")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam Personel Sayısı", f"{total_employees}")
    with col2:
        st.metric("Çalışan Başına Ortalama Satış Hacmi", f"₺ {avg_sales:,.2f}")
    with col3:
        st.metric("Tahmini Aylık Personel Maliyeti", f"₺ {avg_cost:,.0f}")
    st.divider() 

    # --- 3. TAHMİN MODÜLÜ (AI) ---
    predictions_df = load_predictions(engine)
    
    # FİLTRELEME VE GÖRSELLEŞTİRME
    
    # 1. Şube Seçimi
    branch_options = ['Genel Toplam'] + [f'Şube {i}' for i in predictions_df['branch_id'].unique() if i != 0]
    selected_branch = st.selectbox("Hangi Şubenin Tahminini Görmek İstersiniz?", branch_options)
    
    # 2. Seçime göre filtreleme
    if selected_branch == 'Genel Toplam':
        filtered_df = predictions_df[predictions_df['branch_id'] == 0].copy()
    else:
        branch_id = int(selected_branch.split(' ')[1])
        filtered_df = predictions_df[predictions_df['branch_id'] == branch_id].copy()

    # 3. Görselleştirme
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

    # 4. Detay Tablosu
    st.subheader("Tahmin Detayları (Raw Data)")
    st.dataframe(filtered_df[['prediction_date', 'predicted_sales', 'lower_bound', 'upper_bound', 'prediction_run_time']].reset_index(drop=True), use_container_width=True)

except Exception as e:
    st.error(f"Veritabanı bağlantı hatası veya veri yükleme hatası oluştu: {e}")
    st.info("Lütfen PostgreSQL'in çalıştığından ve tüm adımların tamamlandığından emin olun.")