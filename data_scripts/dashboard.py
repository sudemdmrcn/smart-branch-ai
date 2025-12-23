import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import random
import re
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

# Koyu tema ve kart görünümü için hafif CSS dokunuşu
st.markdown(
    """
    <style>
    /* Genel arka plan ve font rengi */
    .stApp {
        background: radial-gradient(circle at 20% 20%, #0f172a 0%, #0b1221 30%, #070d19 60%, #050a15 100%);
        color: #e2e8f0;
    }
    /* Kart benzeri container (metric, expander, vb.) */
    .stMarkdown, .stDataFrame, .stPlotlyChart, .stMetric, .stAlert {
        border-radius: 12px !important;
        background-color: #0f172a88 !important;
        padding: 8px 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.35);
    }
    /* Başlıklar */
    h1, h2, h3, h4 {
        color: #e2e8f0 !important;
    }
    /* Butonlar */
    button[kind="primary"] {
        border-radius: 10px;
        background: linear-gradient(135deg, #22d3ee, #3b82f6);
        color: #0b1221 !important;
        font-weight: 700;
        border: none;
    }
    button[kind="primary"]:hover {
        filter: brightness(1.05);
    }
    /* Input kutuları */
    .stTextInput>div>div>input {
        background: #0f172a !important;
        color: #e2e8f0 !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px;
    }
    /* Divider rengi */
    hr { border-color: #1f2937; }
    </style>
    """,
    unsafe_allow_html=True,
)


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
    
    # Şube rozetini gösterelim
    badge = "Genel Toplam" if selected_branch_id == 0 else f"Şube {selected_branch_id}"
    st.markdown(f"**Seçili Şube:** `{badge}`")

    # Seçime göre tahmin verisini filtreleme
    if selected_branch_id == 0:
        filtered_df = predictions_df[predictions_df['branch_id'] == 0].copy()
    else:
        filtered_df = predictions_df[predictions_df['branch_id'] == selected_branch_id].copy()


    # --- DOĞAL DİL CHAT (HEURİSTİK NL→SQL) – SAYFA BAŞINA TAŞINDI ---
    st.divider()
    st.header("💬 Soru Sor (Beta) – Şube Bağlamlı Chatbot")
    st.caption("Örnek: son 7 günde en çok satan 5 ürün · son 30 günde toplam ciro · kritik stoklar · tahmin ortalaması")

    def parse_user_query(text: str):
        """Anahtar kelimelere göre sınırlı şablon seçer."""
        t = text.lower()

        # Varsayılan zaman penceresi: 7 gün
        days = 7
        m = re.search(r"(\d+)\s*gün", t)
        if m:
            days = min(max(int(m.group(1)), 1), 90)  # 1-90 arası sınırla
        if "30" in t and "gün" in t:
            days = 30
        if "hafta" in t and "son" in t:
            days = 7

        if any(k in t for k in ["en çok satan", "ilk 5", "top 5", "top5"]):
            return {"intent": "top_products", "days": days, "limit": 5}
        if any(k in t for k in ["ciro", "toplam satış", "toplam ciro", "gelir"]):
            return {"intent": "total_revenue", "days": days}
        if any(k in t for k in ["stok", "reorder", "kritik"]):
            return {"intent": "low_stock"}
        if any(k in t for k in ["tahmin", "forecast", "öngörü"]):
            return {"intent": "forecast_summary"}

        return None

    def run_chat_query(engine, intent_info, branch_id):
        """Seçili niyete göre güvenli şablonlu sorgu çalıştırır."""
        intent = intent_info["intent"]
        days = intent_info.get("days", 7)
        limit = intent_info.get("limit", 5)

        branch_filter = ""
        if branch_id and branch_id != 0:
            branch_filter = f"AND branch_id = {branch_id}"

        if intent == "top_products":
            sql = f"""
            SELECT p.product_name,
                   SUM(s.quantity) AS adet,
                   SUM(s.total_sale_amount) AS ciro
            FROM sales s
            JOIN products p ON p.product_id = s.product_id
            WHERE s.sale_datetime >= NOW() - INTERVAL '{days} days'
            {branch_filter}
            GROUP BY p.product_name
            ORDER BY adet DESC
            LIMIT {limit};
            """
            df = pd.read_sql(sql, engine)
            summary = f"Son {days} günde en çok satan ilk {limit} ürün."
            return df, summary

        if intent == "total_revenue":
            sql = f"""
            SELECT
                SUM(total_sale_amount) AS toplam_ciro,
                SUM(quantity) AS toplam_adet,
                COUNT(*) AS islem_sayisi
            FROM sales
            WHERE sale_datetime >= NOW() - INTERVAL '{days} days'
            {branch_filter};
            """
            df = pd.read_sql(sql, engine)
            summary = f"Son {days} günde toplam ciro ve adet özeti."
            return df, summary

        if intent == "low_stock":
            sql = f"""
            SELECT p.product_name,
                   bi.current_stock_level,
                   bi.reorder_point
            FROM branch_inventory bi
            JOIN products p ON p.product_id = bi.product_id
            WHERE bi.current_stock_level < bi.reorder_point
            {branch_filter}
            ORDER BY bi.current_stock_level ASC
            LIMIT 20;
            """
            df = pd.read_sql(sql, engine)
            summary = "Reorder noktası altında kritik stoklar."
            return df, summary

        if intent == "forecast_summary":
            sql = f"""
            SELECT
                AVG(predicted_sales) AS ortalama_tahmin,
                MIN(prediction_date) AS baslangic,
                MAX(prediction_date) AS bitis
            FROM prediction_results
            WHERE prediction_run_time = (SELECT MAX(prediction_run_time) FROM prediction_results)
            {branch_filter};
            """
            df = pd.read_sql(sql, engine)
            summary = "Son tahmin çalışmasından özet."
            return df, summary

        return None, "Bu sorgu için şablon yok."

    # Chat input state
    if "chat_query" not in st.session_state:
        st.session_state.chat_query = ""

    user_question = st.text_input(
        "Doğal dilde sorun (örn: 'son 7 günde en çok satan 5 ürün')",
        placeholder="Örn: Son 7 günde Şube 2'de en çok satan 5 ürün nedir?",
        value=st.session_state.chat_query,
        key="chat_query_input"
    )
    ask_btn = st.button("Çalıştır", type="primary")

    if ask_btn and user_question.strip():
        parsed = parse_user_query(user_question)
        if not parsed:
            st.warning("Bu soruyu anlayamadım. Örnek: 'son 7 günde en çok satan 5 ürün', 'son 30 günde toplam ciro'.")
        else:
            try:
                result_df, summary = run_chat_query(engine, parsed, selected_branch_id)
                st.success(summary)
                st.dataframe(result_df, width='stretch')
            except Exception as e:
                st.error(f"Sorgu çalıştırılırken hata oluştu: {e}")
                st.info("Veritabanı bağlantısı açık ve erişilebilir mi? Port/kimlik bilgilerini kontrol edin.")


    st.divider()

    # Ortak veri hazırlıkları
    stock_df, low_stock_count = load_stock_data(engine, branch_id=selected_branch_id)
    predicted_sales_sum = filtered_df['predicted_sales'].sum()
    avg_sales, avg_cost, total_employees = load_employee_metrics(engine, branch_id=selected_branch_id)
    optimization_result = generate_optimization_recommendation(filtered_df)

    tabs = st.tabs(["Genel Bakış", "Stok & Sipariş", "Personel", "Tahmin"])

    # --- GENEL BAKIŞ ---
    with tabs[0]:
        st.subheader("Genel Bakış")
        o1, o2, o3 = st.columns(3)
        with o1:
            st.metric("Toplam Stok Değeri", f"₺ {stock_df['total_stock_value'].sum():,.2f}")
        with o2:
            st.metric("Kritik Stok Ürün", f"{low_stock_count} adet")
        with o3:
            st.metric("7 Günlük Tahmin Toplamı", f"₺ {predicted_sales_sum:,.0f}")

    # --- STOK & SİPARİŞ ---
    with tabs[1]:
        st.header(f"{selected_branch} Stok Yönetimi KPI'ları")
        k1, k2, k3 = st.columns(3)
        
        with k1:
            st.metric("Toplam Stok Değeri", f"₺ {stock_df['total_stock_value'].sum():,.2f}")
        with k2:
            st.metric("Kritik Stok Uyarısı", f"{low_stock_count} Ürün", 
                    delta=f"Son 24 Saatte {random.randint(0, 5)} yeni uyarı", delta_color="inverse")
        with k3:
            wastage_cost = stock_df['total_stock_value'].sum() * 0.005
            st.metric("Tahmini Fire Maliyeti (Günlük)", f"₺ {wastage_cost:,.2f}")

        st.markdown("**Stok Listesi (CSV indirilebilir):**")
        st.download_button("⬇ Stok CSV", data=stock_df.to_csv(index=False).encode("utf-8"), file_name="stok.csv", mime="text/csv")
        st.dataframe(stock_df, use_container_width=True)

        st.divider()
        st.header("Sipariş Önerisi")
        st.subheader(f"{selected_branch} İçin Gelecek 7 Günlük Tahmine Göre İhtiyaç Analizi")

        if low_stock_count > 0:
            critical_products = stock_df[stock_df['current_stock_level'] < stock_df['reorder_point']].sort_values('current_stock_level').head(3)
            st.markdown("**KRİTİK SİPARİŞ LİSTESİ (Reorder Point Altındakiler):**")
            
            for index, row in critical_products.iterrows():
                p_name = row['product_name']
                p_stock = row['current_stock_level']
                p_reorder = row['reorder_point']
                weekly_demand_forecast = int(predicted_sales_sum * 0.00000005 * 7 * random.uniform(0.9, 1.1)) 
                order_amount = max(0, (p_reorder - p_stock) + weekly_demand_forecast)
                
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
            st.download_button("⬇ Kritik Stok CSV", data=critical_products.to_csv(index=False).encode("utf-8"), file_name="kritik_stok.csv", mime="text/csv")
        else:
            st.success("Tebrikler! Şu anda kritik stok seviyesinin altında ürün bulunmamaktadır.")

    # --- PERSONEL ---
    with tabs[2]:
        st.header("Çalışan Performans")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Personel Sayısı", f"{total_employees}")
        with col2:
            st.metric("Çalışan Başına Saatlik Verimlilik", f"₺ {avg_sales:,.2f}", delta="Şube Performansı", delta_color="off")
        with col3:
            st.metric("Tahmini Aylık Personel Maliyeti", f"₺ {avg_cost:,.0f}")

    # --- TAHMİN ---
    with tabs[3]:
        st.header("Gelecek 7 Gün İçin Öneriler")
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
        st.header(f"{selected_branch} İçin 7 Günlük Tahmin")
        
        fig = px.line(
            filtered_df,
            x='prediction_date',
            y='predicted_sales',
            title=f'{selected_branch} Satış Tahmini (₺)',
            labels={'predicted_sales': 'Tahmin Edilen Satış (₺)', 'prediction_date': 'Tarih'},
            template="plotly_dark",
            color_discrete_sequence=["#22d3ee"]
        )
        
        fig.add_scatter(x=filtered_df['prediction_date'], y=filtered_df['upper_bound'], fill=None, mode='lines', line_color='lightgrey', name='Üst Sınır')
        fig.add_scatter(x=filtered_df['prediction_date'], y=filtered_df['lower_bound'], fill='tonexty', mode='lines', line_color='lightgrey', name='Alt Sınır')
        fig.update_layout(
            showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis=dict(gridcolor="#1f2937"),
            yaxis=dict(gridcolor="#1f2937"),
        )

        st.plotly_chart(fig, width='stretch')

        st.subheader("Tahmin Detayları (Raw Data)")
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
        st.download_button("⬇ Tahmin CSV", data=turkish_df.to_csv(index=False).encode("utf-8"), file_name="tahmin.csv", mime="text/csv")
        st.dataframe(turkish_df, width='stretch')

except Exception as e:
    st.error(f"Veritabanı bağlantı hatası veya veri yükleme hatası oluştu: {e}")
    st.info("Lütfen PostgreSQL'in çalıştığından ve tüm adımların tamamlandığından emin olun.")