import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import random
from datetime import datetime, timedelta


st.set_page_config(
    layout="wide", 
    # BU KISMI KONTROL EDİN VE GÜNCELLEYİN:
    menu_items={
        'Get help': 'mailto:yardim@ornek.com', # İsteğe bağlı
        'Report a bug': None, # R harfi büyük, a küçük, b küçük
        'About': "Akıllı Şube Yönetim Sistemi | Proje Sürümü 1.0"
    }
)
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

# !!! KRİTİK GÜNCELLEME: ŞUBE BAZLI STOK ÇEKME FONKSİYONU
def load_stock_data(engine, branch_id=None):
    """Branch Inventory ve Products tablolarını kullanarak şube bazlı stok verilerini çeker."""
    
    if branch_id and branch_id != 0:
        # Tek bir şube seçildiğinde
        query = f"""
        SELECT 
            bi.current_stock_level, 
            bi.reorder_point, 
            p.unit_cost, 
            p.product_name
        FROM branch_inventory bi
        JOIN products p ON bi.product_id = p.product_id
        WHERE bi.branch_id = {branch_id};
        """
        df = pd.read_sql(query, engine)
    else:
        # Genel Toplam seçildiğinde (Tüm şubeleri topla)
        query = """
        SELECT 
            SUM(bi.current_stock_level) as current_stock_level, 
            bi.reorder_point, 
            p.unit_cost, 
            p.product_name
        FROM branch_inventory bi
        JOIN products p ON bi.product_id = p.product_id
        GROUP BY p.product_name, p.unit_cost, bi.reorder_point
        """
        df = pd.read_sql(query, engine)
        
    df['total_stock_value'] = df['current_stock_level'] * df['unit_cost']
    
    # Kritk stok uyarısı: Reorder point'in altındaki ürünlerin sayısı
    low_stock_count = df[df['current_stock_level'] < df['reorder_point']].shape[0]
    
    return df, low_stock_count

# !!! KRİTİK GÜNCELLEME: ŞUBE BAZLI PERSONEL METRİKLERİ (Simülasyon)
def load_employee_metrics(engine, branch_id=None):
    """Personel maliyeti ve verimlilik metriklerini hesaplar (Şube bazlı görsel simülasyon)."""
    
    base_sales_per_hour = 450
    base_employees = 240
    
    if branch_id and branch_id != 0:
        # Şube Bazlı Görünür Farklılık Yaratma Simülasyonu
        # Şube ID arttıkça verimlilik de artıyor gibi göstereceğiz.
        avg_sales_per_hour = base_sales_per_hour + (branch_id * 35) 
        
        # Şubedeki personel sayısı
        total_employees = 8 + (branch_id % 3) 
    else:
        # Genel Toplam değerler
        avg_sales_per_hour = base_sales_per_hour
        total_employees = base_employees
    
    avg_monthly_cost = total_employees * 250 * 160 
    
    return avg_sales_per_hour, avg_monthly_cost, total_employees


def generate_optimization_recommendation(predicted_df):
    """AI tahminini kullanarak personel ihtiyacı optimizasyonu önerir (Şube Bazlı)."""
    
    MIN_SALES_PER_HOUR = 3000 # Simülasyon hedefi
    forecast_data = predicted_df 
    
    # filtered_df zaten seçili şubeye ait tahmin verisini içeriyor.
    max_sales_day = forecast_data['predicted_sales'].max()
    avg_predicted_sales = forecast_data['predicted_sales'].mean()
    
    # Şube bazlı baz personel sayısı (load_employee_metrics'den çekebiliriz, ama basitleştirelim)
    total_employees_base = 10 # Varsayılan şube personeli
    
    # Satış tahmini %10'dan fazla artıyorsa personel artışı öner
    if max_sales_day > avg_predicted_sales * 1.10:
        staff_increase_needed = int(total_employees_base * 0.2) 
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
st.title("AI-Driven Smart Branch Management Dashboard")


try:
    # 1. MOTORU KURMA (Tüm KPI'lar için ilk adım)
    engine = get_db_engine()
    predictions_df = load_predictions(engine)
    
    
    # KRİTİK ADIM: ŞUBE SEÇİMİ VE FİLTRELEME (EN ÜSTE TAŞINDI!)
    branch_options = ['Genel Toplam'] + [f'Şube {i}' for i in predictions_df['branch_id'].unique() if i != 0]
    selected_branch = st.selectbox("Hangi Şubeyi Görmek İstersiniz?", branch_options)
    
    if selected_branch == 'Genel Toplam':
        selected_branch_id = 0
    else:
        selected_branch_id = int(selected_branch.split(' ')[1])
    
    # Seçime göre tahmin verisini filtreleme
    if selected_branch_id == 0:
        filtered_df = predictions_df[predictions_df['branch_id'] == 0].copy()
    else:
        filtered_df = predictions_df[predictions_df['branch_id'] == selected_branch_id].copy()


    st.divider() 

    # --- 1. STOK YÖNETİMİ KPI'ları ---
    # Şube ID'sini stock fonksiyonuna GÖNDERİYORUZ
    stock_df, low_stock_count = load_stock_data(engine, branch_id=selected_branch_id)

    st.header(f" {selected_branch} Stok Yönetimi KPI'ları")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Toplam Stok Değeri", f"₺ {stock_df['total_stock_value'].sum():,.2f}")
    with col2:
        st.metric("Kritik Stok Uyarısı", f"{low_stock_count} Ürün", 
                delta=f"Son 24 Saatte {random.randint(0, 5)} yeni uyarı", delta_color="inverse")
    with col3:
        # Fire maliyetini toplam stok değerine göre hesapla
        wastage_cost = stock_df['total_stock_value'].sum() * 0.005
        st.metric("Tahmini Fire Maliyeti (Günlük)", f"₺ {wastage_cost:,.2f}")
    st.divider() 

    # --- 2. AI Destekli Sipariş Önerisi ---
    st.header("AI-Powered Inventory Requisition")
    st.subheader(f"{selected_branch} İçin Gelecek 7 Günlük Tahmine Göre İhtiyaç Analizi")

    predicted_sales_sum = filtered_df['predicted_sales'].sum() 
    
    if low_stock_count > 0:
        # Sadece kritik stok altındaki ürünleri listeler
        critical_products = stock_df[stock_df['current_stock_level'] < stock_df['reorder_point']].sort_values('current_stock_level').head(3)
        st.markdown("** KRİTİK SİPARİŞ LİSTESİ (Reorder Point Altındakiler):**")
        
        for index, row in critical_products.iterrows():
            p_name = row['product_name']
            p_stock = row['current_stock_level']
            p_reorder = row['reorder_point']
            
            # AI Tahminine dayalı talep hesaplama (Simülasyon)
            weekly_demand_forecast = int(predicted_sales_sum * 0.00000005 * 7 * random.uniform(0.9, 1.1)) 
            order_amount = max(0, (p_reorder - p_stock) + weekly_demand_forecast) # Negatif sipariş olmaz
            
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
    # Şube ID'sini employee fonksiyonuna GÖNDERİYORUZ
    avg_sales, avg_cost, total_employees = load_employee_metrics(engine, branch_id=selected_branch_id)

    st.header(" Workforce Performance Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Toplam Personel Sayısı", f"{total_employees}")
    with col2:
        # Burası Şube ID'sine göre bariz bir şekilde değişmeli (load_employee_metrics fonksiyonundaki simülasyon sayesinde)
        st.metric("Çalışan Başına Saatlik Verimlilik", f"₺ {avg_sales:,.2f}", delta="Şube Performansı", delta_color="off")
    with col3:
        st.metric("Tahmini Aylık Personel Maliyeti", f"₺ {avg_cost:,.0f}")
    st.divider() 

    # --- 4. TAHMİN VE OPTİMİZASYON ---
    optimization_result = generate_optimization_recommendation(filtered_df) 

    st.header(" AI-Driven Resource Optimization")
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
    st.header(f" {selected_branch} İçin 7 Günlük Tahmin")
    
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

    st.plotly_chart(fig, width='stretch')

    # dashboard.py dosyasında, TAHMİN GRAFİĞİ VE DETAYLAR (5. kısım) bloğunu bulun

# 4. TAHMİN GRAFİĞİ VE DETAYLAR (filtered_df'i kullanır)
# ... (Grafik kodları) ...

# 5. Detay Tablosu (Bu kısmı güncelleyeceğiz)
    st.subheader("Tahmin Detayları (Raw Data)")

# --- YENİ KOD: Sütun Adlarını Türkçeleştirme ---
    turkish_df = filtered_df[[
    'prediction_date', 
    'predicted_sales', 
    'lower_bound', 
    'upper_bound', 
    'prediction_run_time'
    ]].copy()

    turkish_df.columns = [
    'Tahmin Tarihi', 
    'Tahmin Edilen Satış', 
    'Alt Güven Sınırı', 
    'Üst Güven Sınırı', 
    'Çalışma Zamanı'
    ]
# ---------------------------------------------

    st.dataframe(turkish_df, width='stretch') # Artık türkçe dataframe'i kullanıyoruz.
except Exception as e:
    st.error(f"Veritabanı bağlantı hatası veya veri yükleme hatası oluştu: {e}")
    st.info("Lütfen PostgreSQL'in çalıştığından ve tüm adımların tamamlandığından emin olun.")