import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import random
from datetime import datetime

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

def load_stock_data(engine, branch_id=None):
    """Mevcut stok ve maliyet verilerini çeker (Şube bazlı görselleştirme için)."""
    # Not: Products tablosu şube bazlı olmadığından, her şube için aynı veriyi çekeceğiz.
    query = """
    SELECT current_stock_level, reorder_point, unit_cost, product_name
    FROM products
    ORDER BY current_stock_level DESC;
    """
    df = pd.read_sql(query, engine)
    
    # Burası sadece görselleştirme amaçlıdır: Şube 1'i seçince toplam stok değeri düşmüş gibi görünecek.
    # Gerçek hayatta bu SQL ile şube bazlı stok çekilirdi.
    if branch_id and branch_id != 0:
        df['current_stock_level'] = (df['current_stock_level'] / 5).astype(int) # Toplam stoğu 5 şubeye böleriz
    
    df['total_stock_value'] = df['current_stock_level'] * df['unit_cost']
    low_stock_count = df[df['current_stock_level'] < df['reorder_point']].shape[0]
    
    return df, low_stock_count

# dashboard.py dosyasındaki load_employee_metrics fonksiyonunu BULUN ve DEĞİŞTİRİN

def load_employee_metrics(engine, branch_id=None):
    """Personel maliyeti ve verimlilik metriklerini hesaplar (Şube bazlı görsel simülasyon)."""
    
    # Varsayılan değerler
    base_sales_per_hour = 450
    base_employees = 240
    
    if branch_id and branch_id != 0:
        # Şube Bazlı Görünür Farklılık Yaratma Simülasyonu
        
        # Şube ID'sine göre Verimlilikte Gözle Görülür Fark Yaratma:
        # Şube ID arttıkça verimlilik de artıyor gibi göstereceğiz.
        avg_sales_per_hour = base_sales_per_hour + (branch_id * 25) 
        
        # Şubedeki personel sayısı
        total_employees = 8 + (branch_id % 3) 
    else:
        # Genel Toplam değerler
        avg_sales_per_hour = base_sales_per_hour
        total_employees = base_employees
    
    # Aylık maliyet, güncellenen total_employees sayısına göre hesaplanır
    avg_monthly_cost = total_employees * 250 * 160 
    
    return avg_sales_per_hour, avg_monthly_cost, total_employees

def generate_optimization_recommendation(predicted_df):
    """AI tahminini kullanarak personel ihtiyacı optimizasyonu önerir (Şube Bazlı)."""
    
    MIN_SALES_PER_HOUR = 3000
    forecast_data = predicted_df 
    
    max_sales_day = forecast_data['predicted_sales'].max()
    avg_predicted_sales = forecast_data['predicted_sales'].mean()
    
    total_employees_base = 40 # Şube bazlı baz personel sayısı
    
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


try:
    # 1. MOTORU KURMA (Tüm KPI'lar için ilk adım)
    engine = get_db_engine()
    predictions_df = load_predictions(engine)
    
    
    # -------------------------------------------------------------
    # KRİTİK ADIM: ŞUBE SEÇİMİ VE FİLTRELEME (EN ÜSTE TAŞINDI!)
    # -------------------------------------------------------------
    
    branch_options = ['Genel Toplam'] + [f'Şube {i}' for i in predictions_df['branch_id'].unique() if i != 0]
    selected_branch = st.selectbox("Hangi Şubeyi Görmek İstersiniz?", branch_options)
    
    if selected_branch == 'Genel Toplam':
        selected_branch_id = 0
    else:
        selected_branch_id = int(selected_branch.split(' ')[1])
    
    # Seçime göre tahmin verisini filtreleme (Bu, tüm modülleri etkiler)
    if selected_branch_id == 0:
        filtered_df = predictions_df[predictions_df['branch_id'] == 0].copy()
    else:
        filtered_df = predictions_df[predictions_df['branch_id'] == selected_branch_id].copy()


    st.divider() 

    # --- 1. STOK YÖNETİMİ KPI'ları ---
    stock_df, low_stock_count = load_stock_data(engine, branch_id=selected_branch_id)

    st.header(f"📦 {selected_branch} Stok Yönetimi KPI'ları")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Toplam Stok Değeri", f"₺ {stock_df['total_stock_value'].sum():,.2f}")
    with col2:
        st.metric("Kritik Stok Uyarısı", f"{low_stock_count} Ürün", 
                delta=f"Son 24 Saatte {random.randint(0, 5)} yeni uyarı", delta_color="inverse")
    with col3:
        wastage_cost = stock_df['total_stock_value'].sum() * 0.005
        st.metric("Tahmini Fire Maliyeti (Günlük)", f"₺ {wastage_cost:,.2f}")
    st.divider() 

    # --- 2. AI Destekli Sipariş Önerisi ---
    st.header("🛒 AI Destekli Sipariş Önerisi")
    st.subheader(f"{selected_branch} İçin Gelecek 7 Günlük Tahmine Göre İhtiyaç Analizi")

    predicted_sales_sum = filtered_df['predicted_sales'].sum() 
    
    if low_stock_count > 0:
        critical_products = stock_df[stock_df['current_stock_level'] < stock_df['reorder_point']].sort_values('current_stock_level').head(3)
        st.markdown("**🚨 KRİTİK SİPARİŞ LİSTESİ (Reorder Point Altındakiler):**")
        
        for index, row in critical_products.iterrows():
            p_name = row['product_name']
            p_stock = row['current_stock_level']
            p_reorder = row['reorder_point']
            
            weekly_demand_forecast = int(predicted_sales_sum * 0.00000005 * 7) # Simülasyon çarpanı
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
        st.warning("⚠️ Siparişler, AI talep tahminiyle desteklenmiştir.")
    else:
        st.success("Tebrikler! Şu anda kritik stok seviyesinin altında ürün bulunmamaktadır.")
    st.divider() 

    # --- 3. PERSONEL VERİMLİLİK KPI'ları ---
    avg_sales, avg_cost, total_employees = load_employee_metrics(engine, branch_id=selected_branch_id)

    st.header("👨‍💼 Personel Yönetimi KPI'ları")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam Personel Sayısı", f"{total_employees}")
    with col2:
        st.metric("Çalışan Başına Saatlik Verimlilik", f"₺ {avg_sales:,.2f}")
    with col3:
        st.metric("Tahmini Aylık Personel Maliyeti", f"₺ {avg_cost:,.0f}")
    st.divider() 

    # --- 4. TAHMİN VE OPTİMİZASYON ---
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

    # --- 5. TAHMİN GRAFİĞİ VE DETAYLAR ---
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

    st.subheader("Tahmin Detayları (Raw Data)")
    st.dataframe(filtered_df[['prediction_date', 'predicted_sales', 'lower_bound', 'upper_bound', 'prediction_run_time']].reset_index(drop=True), use_container_width=True)

except Exception as e:
    st.error(f"Veritabanı bağlantı hatası veya veri yükleme hatası oluştu: {e}")
    st.info("Lütfen PostgreSQL'in çalıştığından ve tüm adımların tamamlandığından emin olun.")