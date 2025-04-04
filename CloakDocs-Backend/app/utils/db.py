import os
import psycopg2
import psycopg2.extras
from flask import current_app, g
import traceback

# Veritabanı bağlantısını sağlama
def get_db():
    """
    Veritabanı bağlantısını sağlama fonksiyonu
    """
    if 'db' not in g:
        try:
            print("\n---------- VERİTABANI BAĞLANTISI BAŞLIYOR ----------")
            # Flask uygulamasından veritabanı yapılandırma bilgilerini al
            dbname = current_app.config['DB_NAME']
            user = current_app.config['DB_USER']
            password = current_app.config['DB_PASS']
            host = current_app.config['DB_HOST']
            port = current_app.config['DB_PORT']
            
            print(f"Veritabanı bağlantı bilgileri:")
            print(f"- Host: {host}")
            print(f"- Port: {port}")
            print(f"- DB Name: {dbname}")
            print(f"- User: {user}")
            print(f"- Password: {'*' * len(password) if password else 'Yok'}")
            
            # Veritabanı bağlantısını oluştur
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port
            )
            
            # Sözlük benzeri sonuçlar için cursor'ı yapılandır
            g.db = conn
            print("Veritabanı bağlantısı başarılı!")
            print("---------- VERİTABANI BAĞLANTISI TAMAMLANDI ----------\n")
            return conn
        except Exception as e:
            print(f"HATA: Veritabanı bağlantı hatası: {e}")
            print(f"Bağlantı parametreleri: host={host}, port={port}, dbname={dbname}, user={user}")
            traceback.print_exc()
            print("---------- VERİTABANI BAĞLANTISI BAŞARISIZ ----------\n")
            return None
    else:
        return g.db

# Veritabanı bağlantısını kapatma
def close_db(e=None):
    """
    Uygulama bağlamı sonlandığında veritabanı bağlantısını kapat
    """
    db = g.pop('db', None)
    
    if db is not None:
        try:
            db.close()
            print("Veritabanı bağlantısı kapatıldı")
        except Exception as e:
            print(f"Veritabanı bağlantısını kapatma hatası: {e}")
            traceback.print_exc()

# Flask uygulamasını yapılandırma
def init_app(app):
    app.teardown_appcontext(close_db)

# Sorgu çalıştırma yardımcı fonksiyonu 
def query(query, args=None, one=False, commit=False):
    """
    SQL sorgusu çalıştırma yardımcı fonksiyonu
    
    Args:
        query (str): Çalıştırılacak SQL sorgusu
        args (tuple, optional): Sorgu parametreleri. Varsayılan None.
        one (bool, optional): Tek bir sonuç mu döndürülecek. Varsayılan False.
        commit (bool, optional): Değişiklik işlemi mi (INSERT, UPDATE, DELETE). Varsayılan False.
    
    Returns:
        list or dict: Sorgu sonuçları
    """
    try:
        print(f"\n---------- SQL SORGUSU BAŞLIYOR ----------")
        print(f"SQL Sorgusu: {query}")
        if args:
            print(f"Parametreler: {args}")
        print(f"one={one}, commit={commit}")
            
        conn = get_db()
        if not conn:
            print("HATA: Veritabanı bağlantısı alınamadı!")
            print("---------- SQL SORGUSU BAŞARISIZ ----------\n")
            return [] if not one else None
            
        # Sözlük benzeri sonuçlar için cursor oluştur
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        print(f"Cursor oluşturuldu, sorgu çalıştırılıyor...")
            
        # Sorguyu çalıştır
        try:
            cur.execute(query, args)
            print(f"Sorgu başarıyla çalıştırıldı.")
        except Exception as exec_err:
            print(f"HATA: Sorgu çalıştırma hatası: {exec_err}")
            print("---------- SQL SORGUSU HATA İLE SONLANDI ----------\n")
            raise exec_err
        
        # SELECT sorgusu ise sonuçları al
        if query.strip().upper().startswith('SELECT') or query.strip().upper().find(' RETURNING ') > 0:
            try:
                if one:
                    result = cur.fetchone()
                    print(f"fetchone() sonucu: {result}")
                    result = dict(result) if result else None
                else:
                    result = cur.fetchall()
                    print(f"fetchall() sonucu: {len(result)} satır")
                    if len(result) > 0:
                        print(f"İlk satır örnek: {result[0]}")
                    result = [dict(row) for row in result]
            except Exception as fetch_err:
                print(f"HATA: Sonuç alma hatası: {fetch_err}")
                print("---------- SQL SORGUSU HATA İLE SONLANDI ----------\n")
                raise fetch_err
        else:
            result = None
            print(f"SELECT sorgusu değil, etkilenen satır sayısı: {cur.rowcount}")
        
        # Değişiklik varsa kaydet
        if commit or not query.strip().upper().startswith('SELECT'):
            try:
                conn.commit()
                print(f"İşlem commit edildi, etkilenen satır sayısı: {cur.rowcount}")
            except Exception as commit_err:
                print(f"HATA: Commit hatası: {commit_err}")
                print("---------- SQL SORGUSU HATA İLE SONLANDI ----------\n")
                raise commit_err
        
        # Cursor'ı kapat
        cur.close()
        print(f"Cursor kapatıldı.")
        print(f"---------- SQL SORGUSU BAŞARIYLA TAMAMLANDI ----------\n")
        
        return result
        
    except Exception as e:
        print(f"GENEL HATA: Sorgu çalıştırma hatası: {e}")
        traceback.print_exc()
        
        try:
            # Hata durumunda geri al
            if 'conn' in locals() and conn:
                conn.rollback()
                print("İşlem geri alındı (rollback)")
        except Exception as rb_err:
            print(f"HATA: Rollback hatası: {rb_err}")
        
        print("---------- SQL SORGUSU HATA İLE SONLANDI ----------\n")
        return [] if not one else None

def execute(sql, params=None):
    """
    INSERT, UPDATE veya DELETE gibi değişiklik içeren SQL ifadeleri için yardımcı fonksiyon
    
    Args:
        sql (str): Çalıştırılacak SQL sorgusu
        params (tuple, optional): Sorgu parametreleri. Varsayılan None.
    
    Returns:
        int: Etkilenen satır sayısı
    """
    try:
        conn = get_db()
        if not conn:
            print("Veritabanı bağlantısı alınamadı")
            return 0
            
        cur = conn.cursor()
        
        print(f"Execute SQL: {sql}")
        if params:
            print(f"Parametreler: {params}")
            
        cur.execute(sql, params)
        rowcount = cur.rowcount
        
        conn.commit()
        print(f"İşlem tamamlandı, etkilenen satır sayısı: {rowcount}")
        
        cur.close()
        return rowcount
        
    except Exception as e:
        print(f"SQL çalıştırma hatası: {e}")
        traceback.print_exc()
        
        try:
            # Hata durumunda geri al
            conn.rollback()
            print("İşlem geri alındı")
        except:
            pass
            
        return 0

def get_db_connection():
    """
    Veritabanı bağlantısını sağlama fonksiyonu - get_db için alternatif isim
    
    Returns:
        psycopg2.connection: Veritabanı bağlantısı
    """
    # get_db fonksiyonunu çağırarak aynı işlevi sağlayalım
    return get_db() 