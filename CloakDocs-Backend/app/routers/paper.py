from flask import request, jsonify, current_app, send_file
from flask_restx import Namespace, Resource, fields
import os
import uuid
from werkzeug.utils import secure_filename
from app.models.paper import Paper
from app.utils.email import send_tracking_number_email
import datetime
from werkzeug.datastructures import FileStorage
import traceback
from app.utils.pdf_processor import PdfProcessor

# Namespace tanımlama
api = Namespace('paper', description='Makale işlemleri')

# Modelleri tanımlama (Swagger dokümantasyonu için)
paper_model = api.model('Paper', {
    'tracking_number': fields.String(required=True, description='Makale takip numarası'),
    'email': fields.String(required=True, description='Yazar e-posta adresi'),
    'original_filename': fields.String(required=True, description='Orijinal dosya adı'),
    'upload_date': fields.DateTime(description='Yükleme tarihi'),
    'status': fields.String(description='Makalenin durumu'),
    'download_count': fields.Integer(description='İndirme sayısı')
})

upload_response = api.model('UploadResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'trackingNumber': fields.String(description='Takip numarası'),
    'fileName': fields.String(description='Dosya adı'),
    'emailSent': fields.Boolean(description='E-posta gönderildi mi?')
})

status_response = api.model('StatusResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'paper': fields.Nested(paper_model, description='Makale bilgileri')
})

# API Yanıtları için model tanımlamaları
keyword_model = api.model('Keywords', {
    'manual': fields.List(fields.String, description='Makale içinde belirtilen anahtar kelimeler'),
    'keybert': fields.List(fields.String, description='KeyBERT ile çıkarılan anahtar kelimeler'),
    'yake': fields.List(fields.String, description='YAKE ile çıkarılan anahtar kelimeler')
})

keyword_response = api.model('KeywordResponse', {
    'success': fields.Boolean(description='İşlem başarısı'),
    'tracking_number': fields.String(description='Makale takip numarası'),
    'keywords': fields.Nested(keyword_model, description='Anahtar kelimeler')
})

# Dosya uzantısı kontrolü
ALLOWED_EXTENSIONS = {'pdf'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# API rotaları
@api.route('/upload')
class PaperUpload(Resource):
    # Swagger için belgelendirme
    upload_parser = api.parser()
    upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='PDF dosyası')
    upload_parser.add_argument('email', location='form', type=str, required=True, help='Yazar e-posta adresi')
    upload_parser.add_argument('tracking_number', location='form', type=str, required=False, help='Revizyon için orijinal makale takip numarası')
    upload_parser.add_argument('is_revision', location='form', type=str, required=False, help='Revize makale gönderimi mi?')
    
    @api.expect(upload_parser)
    @api.response(200, 'Başarılı', upload_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(500, 'Sunucu hatası')
    def post(self):
        """
        Makale dosyası yükleme API'si
        Yeni makale yükleme veya varolan bir makalenin revize edilmiş versiyonunu yükleme için kullanılır
        """
        try:
            # Form verilerini kontrol etme
            if 'file' not in request.files:
                return {'error': 'Dosya bulunamadı'}, 400
            
            file = request.files['file']
            email = request.form.get('email')
            
            # Revizyon parametrelerini kontrol et
            is_revision = request.form.get('is_revision') == 'true'
            original_tracking_number = request.form.get('tracking_number')
            
            if is_revision and not original_tracking_number:
                return {'error': 'Revizyon için orijinal makale takip numarası gereklidir'}, 400
            
            print(f"Makale yüklemesi başlatıldı. E-posta: {email}, Dosya Adı: {file.filename}, Revizyon: {is_revision}")
            
            if not email:
                return {'error': 'E-posta adresi gereklidir'}, 400
            
            if file.filename == '':
                return {'error': 'Dosya seçilmedi'}, 400
            
            if not allowed_file(file.filename):
                return {'error': 'Yalnızca PDF dosyaları kabul edilmektedir'}, 400
            
            # Revizyon durumunda orijinal makaleyi kontrol et
            if is_revision:
                original_paper = Paper.get_by_tracking_number(original_tracking_number, email)
                if not original_paper:
                    return {'error': 'Belirtilen takip numarası ve e-posta ile eşleşen makale bulunamadı'}, 404
                
                # Revizyon için yeni takip numarası oluştur (orijinalle ilişkili)
                # Orijinal takip numarasının bir kısmını koru, revizyon numarası ekle
                base_tracking = original_tracking_number.split("-")
                if len(base_tracking) >= 3:
                    # TR-YYMMDDHHNN-XXXX formatını koru, sadece son kısmı değiştir
                    timestamp = base_tracking[1]
                    unique_id = str(uuid.uuid4())[:8].upper()
                    tracking_number = f"TR-{timestamp}-R{unique_id}"
                else:
                    # Eğer orijinal takip numarası beklenen formatta değilse, yeni oluştur
                    timestamp = datetime.datetime.now().strftime("%y%m%d%H%M")
                    unique_id = str(uuid.uuid4())[:8].upper()
                    tracking_number = f"TR-{timestamp}-R{unique_id}"
                
                print(f"Revize makale için takip numarası oluşturuldu: {tracking_number}")
            else:
                # Normal makale için takip numarası oluşturma
                timestamp = datetime.datetime.now().strftime("%y%m%d%H%M")
                unique_id = str(uuid.uuid4())[:8].upper()
                tracking_number = f"TR-{timestamp}-{unique_id}"
                
                print(f"Takip numarası oluşturuldu: {tracking_number}")
            
            # Dosya yolu oluşturma
            year_month = datetime.datetime.now().strftime("%Y-%m")
            sanitized_email = email.replace('@', '_at_').replace('.', '_dot_')
            
            # Eğer revizyon ise, orijinal makale ile aynı klasöre kaydet
            # ancak revision alt klasörü oluştur
            if is_revision:
                relative_path = os.path.dirname(original_paper.get('file_path', ''))
                # Eğer orijinal yol bulunamazsa, yeni bir yol oluştur
                if not relative_path:
                    relative_path = os.path.join('papers', year_month, sanitized_email)
                
                # Revizyon alt klasörü ekle
                relative_path = os.path.join(relative_path, 'revisions')
            else:
                relative_path = os.path.join('papers', year_month, sanitized_email)
            
            # Uploads klasörü yolu
            upload_folder = current_app.config['UPLOAD_FOLDER']
            full_dir = os.path.join(upload_folder, relative_path)
            
            print(f"Yapılandırma UPLOAD_FOLDER: {upload_folder}")
            print(f"Oluşturulan dizin yolu: {full_dir}")
            print(f"Bu dizin mevcut mu: {os.path.exists(upload_folder)}")
            
            # Klasör yoksa oluştur
            os.makedirs(full_dir, exist_ok=True)
            
            print(f"Dizin oluşturulduktan sonra mevcut mu: {os.path.exists(full_dir)}")
            
            # Güvenli dosya adı
            secure_name = secure_filename(file.filename)
            file_name = f"{tracking_number}_{secure_name}"
            file_path = os.path.join(full_dir, file_name)
            
            print(f"Dosya kaydedilecek: {file_path}")
            
            # Dosyayı kaydet
            try:
                file.save(file_path)
                print(f"Dosya başarıyla kaydedildi")
                
                if os.path.exists(file_path):
                    print(f"Dosya disk üzerinde doğrulandı. Boyut: {os.path.getsize(file_path)} byte")
                else:
                    print(f"HATA: Dosya kaydedildi ancak disk üzerinde bulunamıyor!")
            except Exception as save_error:
                print(f"Dosya kaydetme hatası: {save_error}")
                traceback.print_exc()
                return {'error': f'Dosya kaydedilemedi: {str(save_error)}'}, 500
            
            # Dosya boyutunu al
            file_size = os.path.getsize(file_path)
            
            # Veritabanı parametrelerini oluştur
            paper_params = {
                'tracking_number': tracking_number,
                'email': email,
                'file_path': os.path.join(relative_path, file_name),
                'original_filename': file.filename,
                'file_size': file_size
            }
            
            # Eğer revizyon ise, orijinal makale bağlantısını ekle
            if is_revision:
                paper_params['original_paper_id'] = original_paper.get('id')
                paper_params['is_revision'] = True
            
            # Veritabanına kaydet
            try:
                paper_id = Paper.save_paper(**paper_params)
                
                print(f"Makale veritabanına kaydedildi. ID: {paper_id}")
                
                if not paper_id:
                    # Veritabanına kaydetme başarısız olursa, dosyayı sil
                    os.remove(file_path)
                    return {'error': 'Makale veritabanına kaydedilemedi'}, 500
            except Exception as db_error:
                print(f"Veritabanı kaydetme hatası: {db_error}")
                traceback.print_exc()
                # Dosyayı sil
                if os.path.exists(file_path):
                    os.remove(file_path)
                return {'error': f'Veritabanı hatası: {str(db_error)}'}, 500
            
            # E-posta gönder
            try:
                if is_revision:
                    # Revizyon e-postası gönder
                    from app.utils.email import send_revision_confirmation_email
                    email_sent = send_revision_confirmation_email(email, tracking_number, original_tracking_number, file.filename)
                else:
                    # Normal makale e-postası gönder
                    email_sent = send_tracking_number_email(email, tracking_number, file.filename)
                print(f"E-posta gönderme sonucu: {'Başarılı' if email_sent else 'Başarısız'}")
            except Exception as email_error:
                print(f"E-posta gönderme hatası: {email_error}")
                traceback.print_exc()
                email_sent = False
            
            # E-posta gönderilmese bile işlem başarılı
            # Başarılı yanıt
            response_data = {
                'success': True,
                'trackingNumber': tracking_number,
                'fileName': file.filename,
                'emailSent': email_sent
            }
            
            # Eğer revizyon ise, ek bilgileri ekle
            if is_revision:
                response_data['isRevision'] = True
                response_data['originalTrackingNumber'] = original_tracking_number
            
            return response_data
            
        except Exception as e:
            print(f"Makale yükleme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Makale yükleme hatası: {str(e)}'}, 500

@api.route('/status')
class PaperStatus(Resource):
    # Swagger için belgelendirme
    status_parser = api.parser()
    status_parser.add_argument('trackingNumber', location='args', type=str, required=True, help='Makale takip numarası')
    status_parser.add_argument('email', location='args', type=str, required=True, help='Yazar e-posta adresi')
    
    @api.expect(status_parser)
    @api.response(200, 'Başarılı', status_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Makale durumu sorgulama API'si
        """
        try:
            print("\n---------- MAKALE DURUMU SORGULAMA BAŞLADI ----------")
            tracking_number = request.args.get('trackingNumber')
            email = request.args.get('email')
            
            print(f"İstek parametreleri:")
            print(f"- Takip Numarası: '{tracking_number}'")
            print(f"- E-posta: '{email}'")
            
            if not tracking_number or not email:
                print("HATA: Takip numarası veya e-posta eksik")
                print("---------- MAKALE DURUMU SORGULAMA TAMAMLANDI (HATA) ----------\n")
                return {'error': 'Takip numarası ve e-posta gereklidir'}, 400
            
            # Makaleyi getir
            print(f"Paper.get_by_tracking_number fonksiyonu çağrılıyor...")
            paper = Paper.get_by_tracking_number(tracking_number, email)
            
            if not paper:
                print("HATA: Makale bulunamadı")
                print("---------- MAKALE DURUMU SORGULAMA TAMAMLANDI (BULUNAMADI) ----------\n")
                return {'error': 'Belirtilen takip numarası ve e-posta ile eşleşen makale bulunamadı'}, 404
            
            # Datetime alanlarını string formatına dönüştür (JSON serileştirme için)
            if 'upload_date' in paper and paper['upload_date']:
                paper['upload_date'] = paper['upload_date'].strftime("%Y-%m-%d %H:%M:%S")
            
            if 'last_downloaded' in paper and paper['last_downloaded']:
                paper['last_downloaded'] = paper['last_downloaded'].strftime("%Y-%m-%d %H:%M:%S")
                
            if 'last_updated' in paper and paper['last_updated']:
                paper['last_updated'] = paper['last_updated'].strftime("%Y-%m-%d %H:%M:%S")
            
            # Başarılı yanıt
            print(f"Makale bulundu: ID={paper.get('id')}, Status={paper.get('status')}")
            print("---------- MAKALE DURUMU SORGULAMA TAMAMLANDI (BAŞARILI) ----------\n")
            return {
                'success': True,
                'paper': paper
            }
            
        except Exception as e:
            print(f"HATA: Makale durumu sorgulama hatası: {e}")
            traceback.print_exc()
            print("---------- MAKALE DURUMU SORGULAMA TAMAMLANDI (HATA) ----------\n")
            return {'error': f'Makale durumu sorgulanırken bir hata oluştu: {str(e)}'}, 500

@api.route('/download/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class DownloadPaperById(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale veya dosya bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Makale indirme API'si (sadece takip numarası ile)
        """
        try:
            print("\n---------- MAKALE İNDİRME BAŞLATILIYOR (ID İLE) ----------")
            print(f"Takip Numarası: {tracking_number}")
            
            # Makaleyi getir
            print(f"Paper.get_by_tracking_number fonksiyonu çağrılıyor...")
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                print("HATA: Makale bulunamadı")
                print("---------- MAKALE İNDİRME TAMAMLANDI (BULUNAMADI) ----------\n")
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Dosya yolu
            print(f"Makale bilgileri: {paper}")
            print(f"Dosya yolu veritabanında: {paper['file_path']}")
            
            # Proje kök dizinini alalım
            project_root = os.getcwd()
            print(f"Proje kök dizini: {project_root}")
            print(f"Upload folder: {current_app.config['UPLOAD_FOLDER']}")
            
            # Çoklu dosya yolu denemesi
            file_paths_to_try = [
                # 1. Doğrudan uploads klasöründen dosya yolunu oluştur
                os.path.join(project_root, current_app.config['UPLOAD_FOLDER'], paper['file_path']),
                
                # 2. app/ önekini kaldırarak dene
                os.path.join(project_root, current_app.config['UPLOAD_FOLDER'], paper['file_path'].replace("app/", "")),
                
                # 3. papers/ önekini atlayarak dene
                os.path.join(project_root, current_app.config['UPLOAD_FOLDER'].replace("app/", ""), 
                          paper['file_path'].replace("papers/", "")),
                
                # 4. Mutlak yol oluştur
                os.path.join(project_root, "uploads", paper['file_path'].replace("papers/", "")),
                
                # 5. Sadece file_path kullanarak
                os.path.join(project_root, paper['file_path']),
                
                # 6. Upload klasörü ve file_path kombinasyonu 
                os.path.join(project_root, "uploads", paper['file_path'])
            ]
            
            # Tüm olası yolları dene
            file_path = None
            for i, path in enumerate(file_paths_to_try):
                print(f"Deneniyor yol #{i+1}: {path}")
                if os.path.exists(path):
                    print(f"Dosya bulundu: {path}")
                    file_path = path
                    break
                else:
                    print(f"Dosya bulunamadı: {path}")
            
            if not file_path:
                print(f"HATA: Hiçbir dosya yolunda dosya bulunamadı")
                print("---------- MAKALE İNDİRME TAMAMLANDI (DOSYA BULUNAMADI) ----------\n")
                return {'error': 'Dosya bulunamadı'}, 404
            
            # İndirme sayısını artır
            Paper.increment_download_count(tracking_number)
            
            # Dosyayı gönder
            print(f"Dosya bulundu, gönderiliyor: {file_path}")
            print("---------- MAKALE İNDİRME TAMAMLANDI (BAŞARILI) ----------\n")
            return send_file(
                file_path,
                as_attachment=True,
                download_name=paper['original_filename']
            )
            
        except Exception as e:
            print(f"HATA: Dosya indirme hatası: {e}")
            traceback.print_exc()
            print("---------- MAKALE İNDİRME TAMAMLANDI (HATA) ----------\n")
            return {'error': f'Dosya indirilirken bir hata oluştu: {str(e)}'}, 500 

@api.route('/keywords/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class ExtractKeywords(Resource):
    @api.response(200, 'Başarılı', keyword_response)
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Makalenin anahtar kelimelerini getir
        
        Daha önce işlenmiş anahtar kelimeleri döndürür.
        Eğer anahtar kelimeler daha önce çıkarılmamışsa, boş sonuç döndürür.
        """
        try:
            print(f"\n---------- ANAHTAR KELİMELER GETİRİLİYOR ----------")
            print(f"Takip Numarası: {tracking_number}")
            
            # Makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                print("HATA: Makale bulunamadı")
                print("---------- ANAHTAR KELİMELER İŞLEMİ TAMAMLANDI (HATA) ----------\n")
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Anahtar kelimeleri getir
            keywords = Paper.get_keywords(tracking_number)
            
            print(f"Anahtar kelimeler döndürülüyor: {keywords}")
            print("---------- ANAHTAR KELİMELER İŞLEMİ TAMAMLANDI (BAŞARILI) ----------\n")
            
            return {
                'success': True,
                'tracking_number': tracking_number,
                'keywords': keywords
            }
            
        except Exception as e:
            print(f"HATA: Anahtar kelimeler getirilirken hata: {e}")
            traceback.print_exc()
            print("---------- ANAHTAR KELİMELER İŞLEMİ TAMAMLANDI (HATA) ----------\n")
            return {'error': f'Anahtar kelimeler getirilirken bir hata oluştu: {str(e)}'}, 500
    
    @api.response(200, 'Başarılı', keyword_response)
    @api.response(404, 'Makale veya dosya bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, tracking_number):
        """
        PDF dosyasından anahtar kelimeleri çıkar ve kaydet
        
        Makaleyi işleyerek anahtar kelimeleri çıkarır ve veritabanına kaydeder.
        """
        try:
            print(f"\n---------- ANAHTAR KELİMELER ÇIKARILIYOR ----------")
            print(f"Takip Numarası: {tracking_number}")
            
            # Makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                print("HATA: Makale bulunamadı")
                print("---------- ANAHTAR KELİMELER İŞLEMİ TAMAMLANDI (HATA) ----------\n")
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # PDF dosyasının yolunu oluştur
            project_root = os.getcwd()
            
            # Olası dosya yollarını oluştur
            file_paths_to_try = [
                os.path.join(project_root, current_app.config['UPLOAD_FOLDER'], paper['file_path']),
                os.path.join(project_root, current_app.config['UPLOAD_FOLDER'], paper['file_path'].replace("app/", "")),
                os.path.join(project_root, current_app.config['UPLOAD_FOLDER'].replace("app/", ""), 
                          paper['file_path'].replace("papers/", "")),
                os.path.join(project_root, "uploads", paper['file_path'].replace("papers/", "")),
                os.path.join(project_root, paper['file_path']),
                os.path.join(project_root, "uploads", paper['file_path'])
            ]
            
            # Dosya yolunu bul
            pdf_path = None
            for i, path in enumerate(file_paths_to_try):
                print(f"Deneniyor yol #{i+1}: {path}")
                if os.path.exists(path):
                    print(f"PDF dosyası bulundu: {path}")
                    pdf_path = path
                    break
                else:
                    print(f"PDF dosyası bulunamadı: {path}")
            
            if not pdf_path:
                print(f"HATA: Hiçbir dosya yolunda PDF bulunamadı")
                print("---------- ANAHTAR KELİMELER İŞLEMİ TAMAMLANDI (HATA) ----------\n")
                return {'error': 'PDF dosyası bulunamadı'}, 404
            
            # PDF'i işle
            processor = PdfProcessor()
            keywords = processor.process_pdf(pdf_path)
            
            # Sonuçları veritabanına kaydet
            success = Paper.update_keywords(tracking_number, keywords)
            
            if not success:
                print("HATA: Anahtar kelimeler veritabanına kaydedilemedi")
                print("---------- ANAHTAR KELİMELER İŞLEMİ TAMAMLANDI (HATA) ----------\n")
                return {'error': 'Anahtar kelimeler veritabanına kaydedilemedi'}, 500
            
            print(f"Anahtar kelimeler çıkarıldı ve kaydedildi: {keywords}")
            print("---------- ANAHTAR KELİMELER İŞLEMİ TAMAMLANDI (BAŞARILI) ----------\n")
            
            return {
                'success': True,
                'tracking_number': tracking_number,
                'keywords': keywords
            }
            
        except Exception as e:
            print(f"HATA: Anahtar kelimeler çıkarılırken hata: {e}")
            traceback.print_exc()
            print("---------- ANAHTAR KELİMELER İŞLEMİ TAMAMLANDI (HATA) ----------\n")
            return {'error': f'Anahtar kelimeler çıkarılırken bir hata oluştu: {str(e)}'}, 500 