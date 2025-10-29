# smart-branch-ai
# 🧠 Akıllı Şube AI Yönetim Sistemi
# 🚀 Akıllı Şube Satış Tahmin ve Yönetim Sistemi (AI-Driven Smart Branch)

## 🌟 Proje Özeti

Bu proje, bir perakende zincirinin operasyonel verimliliğini artırmak amacıyla, Makine Öğrenimi (ML) tekniklerini kullanarak şube ve genel düzeyde **gelecekteki satış hacmini** tahmin eden kapsamlı bir İş Zekası (BI) çözümüdür.

Tüm terminal ve veri hazırlama zorluklarının üstesinden gelerek 5 milyonluk devasa bir veri seti ile çalışan, gerçekçi bir AI motoru oluşturulmuştur.

---

## 🛠️ Teknik Mimarisi ve Ana Modüller

| Bileşen | Teknoloji / Kütüphane | Amaç ve Fonksiyon |
| :--- | :--- | :--- |
| **Veritabanı** | PostgreSQL / SQLAlchemy | Tüm operasyonel ve 5M Satış kaydının depolanması. |
| **Veri Simülasyonu** | Python / Pandas / Faker | **Branches, Employees, Products** tablolarına gerçekçi statik veri ve **5 Milyon** dinamik satış hareketi yükleme. |
| **AI/Tahmin Motoru** | Python / Prophet (Facebook) | Zaman serisi analizi ile **önümüzdeki 7 günlük** satış tahminlerini şube bazında (`branch_id`) ve genel toplam (`branch_id=0`) olarak üretme. |
| **Görselleştirme** | Streamlit / Plotly | AI tahminlerini ve güven aralıklarını (Confidence Interval) interaktif web panelinde görselleştirme. |

---

## 📊 Veri Modeli ve Kapsam

Proje, şu temel modüllere ve AI çıktı tablolarına sahiptir:

| Tablo Adı | Açıklama | Kayıt Sayısı (Simülasyon) | İlişkili Modül |
| :--- | :--- | :--- | :--- |
| `sales` | Detaylı satış hareketleri ve zaman damgası. | ~4.9 Milyon | **Tahmin Motoru Girdisi** |
| `products` | Ürün bilgileri, maliyet ve stok seviyeleri. | 100 | Stok Kontrol |
| `employees` | Personel bilgileri. | 40 | Personel Analizi |
| `branches` | Şube konum ve açılış tarihleri. | 5 | Şube Bazlı Analiz |
| `prediction_results` | **AI Tahmin Çıktısı.** 7 günlük şube bazlı ve genel toplam tahmin sonuçları. | ~217 | Yönetici Paneli |

---

## 🚀 Kurulum ve Çalıştırma Rehberi

Bu projeyi yerel ortamınızda çalıştırmak için aşağıdaki adımları sırasıyla takip edin.

### 1. Ön Gereksinimler

* [**PostgreSQL**](https://www.postgresql.org/download/) kurulu olmalıdır.
* Python 3.x ve **Git Bash** kurulu olmalıdır.
* Bağlantı Ayarları: `DB_USER` ve `DB_PASS` (Şifreniz: **Sudem12345**) dosyalar içinde kontrol edilmelidir.

### 2. Ortamı Hazırlama

Projenin ana klasöründe Git Bash'i açın ve gerekli tüm kütüphaneleri kurun:

```bash
/c/Users/sudem/AppData/Local/Programs/Python/Python313/python.exe -m pip install sqlalchemy prophet pandas psycopg2-binary streamlit plotly