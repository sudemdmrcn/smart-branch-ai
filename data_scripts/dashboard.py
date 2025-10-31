import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import random
from datetime import datetime # datetime modülünün tamamını import ediyoruz

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
    latest_run_time = pd.read_sql("SELECT MAX(prediction_run_time) FROM prediction_results", engine).iloc[0, 0]
    query = f"""
    SELECT * FROM prediction_results 
    WHERE prediction_run_time = '{latest_run_time}'
    ORDER BY branch_id, prediction_date;
    """
    df = pd.read_sql(query, engine)
    df['branch_name'] = df['branch_id'].apply(lambda x: 'Genel Toplam' if x == 0 else f'Şube {x}')
    return df

def load_stock_data(engine):
    """Mevcut stok ve maliyet verilerini çeker."""
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
    df['total_stock_value'] = df['current_stock_level'] * df['unit_cost']
    low_stock_count = df[df['current_stock_level'] < df['reorder_point']].shape[0]
    return df, low_stock_count

def load_employee_metrics(engine):
    """Personel maliyeti ve verimlilik metriklerini hesaplar (Saatlik Verimlilik)."""
    query_efficiency = """
    WITH EmployeeSales AS (
        SELECT 
            s.employee_id,
            SUM(s.total_sale_amount) AS total_sales_generated
        FROM sales s
        GROUP BY s.employee_id
    ),
    EmployeeHours AS (
        SELECT
            e.employee_id,
            SUM(e.duration_hours) AS total_hours_worked
        FROM staff_schedules e
        GROUP BY e.employee_id
    )
    SELECT
        (es.total_sales_generated / eh.total_hours_worked) AS sales_per_hour
    FROM EmployeeSales es
    JOIN EmployeeHours eh ON es.employee_id = eh.employee_id
    """
    efficiency_df = pd.read_sql(query_efficiency, engine)
    
    avg_sales_per_hour = efficiency_df['sales_per_hour'].mean()
    total_employees = pd.read_sql("SELECT COUNT(employee_id) FROM employees", engine).iloc[0, 0]
    avg_monthly_cost = 40 * 250 * 160 
    
    return avg_sales_per_hour, avg_monthly_cost, total_employees

def generate_optimization_recommendation(predicted_df):
    """AI tahminini kullanarak personel ihtiyacı optimizasyonu önerir (Şube Bazlı)."""
    
    MIN_SALES_PER_HOUR = 3000
    forecast_data = predicted_df 
    
    max_sales_day = forecast_data['predicted_sales'].max()
    avg_predicted_sales = forecast_data['predicted_sales'].mean()
    
    total_employees_base = 40 
    
    # Basit bir artış mantığı: Tahmin %5'ten fazla artış gösteriyorsa, artış öner
    if max_sales_day > avg_predicted_sales * 1.05:
        staff_increase_needed = int(total_employees_base * 0.15) 
    else:
        staff_increase_needed = 0

    recommendation = {
        "title": "Personel İhtiyacı Optimizasyonu",
        "needed": total_employees_base + staff_increase_needed,
        "increase": staff_increase_needed,
        "efficiency_target": MIN_SALES_PER_HOUR,
    }
    return recommendation


# ----------------- STREAMLIT ANA PANEL KODU -----------------

st.set_page_config(layout="wide")
st.title("💰 Akıllı Şube Satış Tahmin Paneli")

# HATA YÖNETİMİ VE TÜM KOD AKIŞI TEK TRY BLOĞUNDA
try:
    # 1. MOTORU KURMA (Tüm KPI'lar için ilk adım)
    engine = get_db_engine()
    # ----------------------------------------------------
    # ===> KRİTİK ADIM: TAHMİN VERİSİNİ ŞİMDİ ÇEKİYORUZ! <===
    predictions_df = load_predictions(engine)
    # ----------------------------------------------------
    
    # --- 1. STOK YÖNETİMİ KPI'ları ve AI SİPARİŞ ÖNERİSİ ---
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

        # dashboard.py dosyasında, Personel KPI'larının hemen altındaki st.divider() satırından ÖNCE ekleyin

# --- 2.5. AI Destekli Sipariş Önerisi ---
    st.header("🛒 AI Destekli Sipariş Önerisi")
    st.subheader("Gelecek 7 Günlük Tahmine Göre İhtiyaç Analizi")

# Tahmin ve Stok verileri çekildi. Şimdi sipariş önerisini hesaplayalım.
    general_forecast_df = predictions_df[predictions_df['branch_id'] == 0].copy()
    predicted_sales_sum = general_forecast_df['predicted_sales'].sum() 
    stock_df_temp, low_stock_count_temp = load_stock_data(engine) # Stok verisini tekrar çekiyoruz

    critical_products = stock_df_temp[stock_df_temp['current_stock_level'] < stock_df_temp['reorder_point']].sort_values('current_stock_level')

    if not critical_products.empty:
        top_critical_products = critical_products.head(3)
        st.markdown("**🚨 KRİTİK SİPARİŞ LİSTESİ (Reorder Point Altındakiler):**")
    
        for index, row in top_critical_products.iterrows():
            p_name = row['product_name']
            p_stock = row['current_stock_level']
            p_reorder = row['reorder_point']
        
        # Sipariş Miktarı Hesaplama (Mevcut mantık)
            weekly_demand_forecast = int(predicted_sales_sum * 0.000001 * 7)
            order_amount = (p_reorder - p_stock) + weekly_demand_forecast

            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
            with col1:
                st.write(f"**{p_name}**")
            with col2:
                st.metric("Mevcut Stok", f"{p_stock} adet")
            with col3:
                st.metric("Talep Tahmini (7 Gün)", f"{weekly_demand_forecast} adet")
            with col4:
                st.metric("SİPARİŞ ÖNERİSİ", f"{order_amount} adet", delta="ACİL", delta_color="inverse")

        st.warning("⚠️ Bu siparişler, Reorder Point'in altına düştüğü ve AI talep tahminiyle desteklendiği için önceliklidir.")
    else:
        st.success("Tebrikler! Şu anda kritik stok seviyesinin altında ürün bulunmamaktadır.")

    st.divider() # Yeni blok bitti, şimdi personel KPI'ları devam etmeli
    
    # --- 1.5. AI Destekli Otomatik Sipariş Önerisi ---
    
    # Not: Buradaki kod, artık AI Optimizasyonunu gerektirmediği için silinmiştir.
    # Sipariş önerisini en alta, grafiklerin yanına koymak daha temizdir.
    # Geçici olarak boş bırakıyoruz.


    # --- 2. PERSONEL VERİMLİLİK KPI'ları ---
    avg_sales, avg_cost, total_employees = load_employee_metrics(engine)
    

    st.header("👨‍💼 Personel Yönetimi KPI'ları")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam Personel Sayısı", f"{total_employees}")
    with col2:
        st.metric("Çalışan Başına Saatlik Verimlilik", f"₺ {avg_sales:,.2f}")
    with col3:
        st.metric("Tahmini Aylık Personel Maliyeti", f"₺ {avg_cost:,.0f}")
    st.divider() 

    # --- 3. TAHMİN MODÜLÜ (AI) ve OPTİMİZASYON ---
    predictions_df = load_predictions(engine) # Tüm tahminler çekildi
    
    # 1. Şube Seçimi
    branch_options = ['Genel Toplam'] + [f'Şube {i}' for i in predictions_df['branch_id'].unique() if i != 0]
    selected_branch = st.selectbox("Hangi Şubenin Tahminini Görmek İstersiniz?", branch_options)
    
    # 2. Seçime göre filtreleme (filtered_df'in TANIMLANDIĞI YER)
    if selected_branch == 'Genel Toplam':
        filtered_df = predictions_df[predictions_df['branch_id'] == 0].copy()
    else:
        branch_id = int(selected_branch.split(' ')[1])
        filtered_df = predictions_df[predictions_df['branch_id'] == branch_id].copy()

    # 3. AI OPTİMİZASYON ÖNERİSİ
    optimization_result = generate_optimization_recommendation(filtered_df) 

    st.header("🤖 AI Destekli Kaynak Optimizasyonu")
    st.subheader("Gelecek 7 Gün İçin Öneriler")

    col_opt1, col_opt2 = st.columns([1, 2])

    with col_opt1:
        st.metric(optimization_result["title"], 
                  f"{optimization_result['needed']} Personel", 
                  delta=f"Bugüne göre +{optimization_result['increase']} Kişi", 
                  delta_color="normal")

    with col_opt2:
        max_date = filtered_df['prediction_date'].max()
        st.info(
            f"**AI Analizi:** En yoğun talep gününde ({max_date.strftime('%d %b %Y')}), {optimization_result['needed']} personele çıkılması önerilmektedir. "
            f"Amaç: Çalışan verimliliğini saatte ₺{optimization_result['efficiency_target']} satış seviyesinin üzerinde tutmaktır."
        )
    st.divider()

    # 4. TAHMİN GRAFİĞİ VE DETAYLAR
    st.header(f"📈 {selected_branch} İçin 7 Günlük Tahmin")
    
    fig = px.line(
        filtered_df,
        x='prediction_date',
        y='predicted_sales',
        title=f'{selected_branch} Satış Tahmini (₺)',
        labels={'predicted_sales': 'Tahmin Edilen Satış (₺)', 'prediction_date': 'Tarih'}
    )
    
    fig.add_scatter(x=filtered_df['prediction_date'], y=filtered_df['upper_bound'], fill=None, mode='lines', line_color='lightgrey', name='Üst Sınır')
    fig.add_scatter(x=filtered_df['prediction_date'], y=filtered_df['lower_bound'], fill='tonexty', mode='lines', line_color='lightgrey', name='Alt Sınır')
    fig.update_layout(showlegend=True)

    st.plotly_chart(fig, use_container_width=True)

    # 5. Detay Tablosu
    st.subheader("Tahmin Detayları (Raw Data)")
    st.dataframe(filtered_df[['prediction_date', 'predicted_sales', 'lower_bound', 'upper_bound', 'prediction_run_time']].reset_index(drop=True), use_container_width=True)

except Exception as e:
    st.error(f"Veritabanı bağlantı hatası veya veri yükleme hatası oluştu: {e}")
    st.info("Lütfen PostgreSQL'in çalıştığından ve tüm adımların tamamlandığından emin olun.")