# CloakDocs - Backend

Bu proje, Akademik Makale Değerlendirme Sistemi'nin backend API'sını içerir. Flask ile geliştirilmiş RESTful API yapısına sahiptir.

## Kurulum

1. Proje klasörüne gidin:
```
cd CloakDocs-Backend
```

2. Python sanal ortamını etkinleştirin:
```
# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Gerekli paketleri yükleyin:
```
pip install -r requirements.txt
```

4. Veritabanını kurun:
```
# PostgreSQL'i başlatın
# Veritabanını oluşturun
psql -U postgres -c "CREATE DATABASE akademik_makale_db;"

# Şemayı yükleyin
psql -U postgres -d akademik_makale_db -f schema.sql
```

5. `.env` dosyasını düzenleyin:
```
# PostgreSQL bağlantı bilgilerini ve
# SMTP ayarlarını kendi ortamınıza göre düzenleyin
```

## Çalıştırma

```
python app.py
```

Uygulama varsayılan olarak `http://localhost:5000` adresinde çalışacaktır.

## API Belgelendirmesi

### Makale Yükleme
- **URL:** `/api/paper/upload`
- **Metod:** `POST`
- **Parametreler:** `file` (PDF dosyası), `email` (yazar e-postası)

### Makale Durumu Sorgulama
- **URL:** `/api/paper/status`
- **Metod:** `GET`
- **Parametreler:** `trackingNumber`, `email`

### Editör İşlemleri
- **URL:** `/api/editor/papers`
- **Metod:** `GET`
- **Parametreler:** `status` (opsiyonel)

### Hakem İşlemleri
- **URL:** `/api/review/papers`
- **Metod:** `GET`
- **Parametreler:** `key` (hakem kimliği)

## Dosya Yapısı

```
CloakDocs-Backend/
├── app/                    # Ana uygulama paketi
│   ├── __init__.py         # Flask app oluşturma
│   ├── models/             # Veritabanı modelleri
│   │   └── paper.py
│   ├── routers/            # API rotaları
│   │   ├── paper.py
│   │   ├── editor.py
│   │   ├── review.py
│   │   └── status.py
│   ├── utils/              # Yardımcı modüller
│   │   ├── db.py
│   │   └── email.py
│   └── uploads/            # Yüklenen dosyalar
├── app.py                  # Uygulama giriş noktası
├── schema.sql              # Veritabanı şeması
├── requirements.txt        # Gerekli Python paketleri
└── .env                    # Ortam değişkenleri
```

## Geliştirme

API'yi genişletmek veya değiştirmek için:

1. `app/routers/` dizini altında uygun dosyayı düzenleyin veya yeni bir dosya oluşturun
2. Yeni bileşenleri oluşturmak için `app/models/` altında bir model oluşturun
3. Ana uygulamada yeni router'ı kaydedin (`app/__init__.py`) 