from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
from app.routers.paper import api as paper_api
from app.routers.editor import api as editor_api
from app.routers.review import api as review_api
from app.routers.status import api as status_api
from flask_restx import Api
from app.routers.anonymize import api as anonymize_api

# .env dosyasını yükle
load_dotenv()

def create_app(test_config=None):
    """
    Flask uygulamasını oluşturma işlevi
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # CORS yapılandırması - tüm kaynaklara izin ver
    CORS(app, resources={r"/api/*": {"origins": "*"}}, 
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Uygulama yapılandırması
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16 MB
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads')),
    )
    
    # Veritabanı yapılandırması
    app.config.update(
        DB_NAME=os.environ.get('POSTGRES_DATABASE', 'akademik_makale_db'),
        DB_USER=os.environ.get('POSTGRES_USER', 'postgres'),
        DB_PASS=os.environ.get('POSTGRES_PASSWORD', '123456'),
        DB_HOST=os.environ.get('POSTGRES_HOST', 'localhost'),
        DB_PORT=os.environ.get('POSTGRES_PORT', '5432')
    )
    
    if test_config is not None:
        # test için özel yapılandırma uygula
        app.config.from_mapping(test_config)
    
    # Uploads klasörünü oluştur
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # API nesnesi oluştur
    api = Api(
        app, 
        version='1.0', 
        title='Akademik Makale Değerlendirme API',
        description='Akademik makalelerin değerlendirilmesi için API',
        prefix='/api'
    )
    
    # Namespace'leri API'ye ekle
    api.add_namespace(paper_api)
    api.add_namespace(editor_api)
    api.add_namespace(review_api)
    api.add_namespace(status_api)
    
    # Author message endpointi için route
    from app.routers.author_message import api as author_message_api
    api.add_namespace(author_message_api)
    
    # Anonimleştirme endpointi için route
    api.add_namespace(anonymize_api, path='/anonymize')
    
    # CORS için after_request handler
    @app.after_request
    def add_cors_headers(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept, Origin')
        response.headers.add('Access-Control-Allow-Methods', 'GET, PUT, POST, DELETE, OPTIONS')
        return response
    
    # OPTIONS istekleri için özel handler
    @app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def options_handler(path):
        return '', 200
    
    # Ana sayfayı tanımla
    @app.route('/')
    def index():
        return 'Akademik Makale Değerlendirme Sistemi API'
    
    return app 