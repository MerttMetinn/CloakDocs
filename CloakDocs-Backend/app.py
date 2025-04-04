from app import create_app
from dotenv import load_dotenv
import os

# .env dosyasını yükle
load_dotenv()

# Flask uygulamasını oluştur
app = create_app()

if __name__ == '__main__':
    # Host ve port ayarları
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    # Uygulamayı başlat
    app.run(host=host, port=port, debug=debug) 