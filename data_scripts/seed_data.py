import psycopg2
from psycopg2 import sql
import pandas as pd
from faker import Faker
import random


# ----------------- 1. YAPILANDIRMA AYARLARI -----------------
DB_HOST = "localhost"
DB_NAME = "postgres" # Küçük harf, doğru isim
DB_USER = "postgres"  
DB_PASS = "Sudem12345" # <-- Kendi şifreniz, Türkçe karakter olmamalı

# ----------------- 2. VERITABANI BAĞLANTI FONKSIYONU -----------------
def connect_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            # UTF-8 hata sorununu çözmek için bu satırı ekliyoruz
            client_encoding='latin1' 
        )
        print("\n[BAŞARILI] Veritabanına bağlantı kuruldu.")
        return conn
    except psycopg2.Error as e:
    # ... (Hata kodu) ...
        return None

# ----------------- 4. ANA ÇALIŞTIRMA BLOĞU -----------------
if __name__ == "__main__":
    
    # 1. Bağlantıyı Dene
    conn = connect_db()
    
    if conn is None:
        print("\n[DURDURULDU] Bağlantı hatası nedeniyle veri üretimi başlatılamadı.")
    else:
        # Hata olmaması için bu kısım çalışmalı
        print("\n-> BAĞLANTI BAŞARILI. SORGULANIYOR.")

        # SQL ile basit bir kontrol yapalım
        cur = conn.cursor()
        cur.execute("SELECT now();") # Veritabanından güncel saati istiyoruz
        result = cur.fetchone()
        print(f"-> Veritabanı Kontrolü Başarılı: PostgreSQL Güncel Saati: {result[0]}")
        
        # ... (Diğer kodlar)
        conn.close()
        print("\n[TAMAMLANDI] Bağlantı kapatıldı.")
