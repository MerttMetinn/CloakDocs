from flask import request, send_file, current_app
from flask_restx import Namespace, Resource, fields
from app.models.paper import Paper
import os
import datetime
import json
from werkzeug.datastructures import FileStorage
import psycopg2
from psycopg2.extras import RealDictCursor
from app.utils.db import get_db
from app.utils.db import query, execute, get_db_connection
import traceback

# JSON serileyebilmek için datetime dönüştürücü
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)

# Tarih dönüştürücü yardımcı fonksiyon
def convert_datetime_fields(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, datetime.datetime):
                        item[key] = value.isoformat()
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime.datetime):
                data[key] = value.isoformat()
    return data

# Namespace tanımlama
api = Namespace('review', description='Hakem işlemleri')

# Modeller
paper_model = api.model('ReviewPaper', {
    'id': fields.Integer(description='Makale ID'),
    'tracking_number': fields.String(required=True, description='Makale takip numarası'),
    'original_filename': fields.String(required=True, description='Orijinal dosya adı'),
    'upload_date': fields.DateTime(description='Yükleme tarihi'),
    'status': fields.String(description='Makalenin durumu'),
    'download_count': fields.Integer(description='İndirme sayısı')
})

papers_response = api.model('ReviewPapersResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'count': fields.Integer(description='Makale sayısı'),
    'papers': fields.List(fields.Nested(paper_model), description='Makaleler listesi')
})

review_response = api.model('ReviewSubmitResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'message': fields.String(description='Sonuç mesajı')
})

# -----------------------------------------------
# Dosya yolu çözümleme yardımcı fonksiyonu - bu fonksiyon çeşitli olası dosya yollarını dener
def resolve_file_path(db_file_path):
    """
    Veritabanından gelen dosya yolunu alır ve gerçek fiziksel dosya yolunu çözümler.
    Birden fazla olası yolu dener ve ilk bulunan dosya yolunu döndürür.
    """
    # Mutlak yolu normalize et
    db_file_path = os.path.normpath(db_file_path)
    print(f"Çözümlenecek dosya yolu: {db_file_path}")
    
    # Projenin kök dizinini bulma
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"Mevcut dizin: {current_dir}")
    
    # Olası kök dizinler - bu sırayla denenecek
    base_dirs = [
        # Windows yolları
        os.path.join("C:", "Projects"),
        os.path.join("C:", "Projects", "CloakDocs-Backend"),
        current_dir,  # Mevcut çalışma dizini
        os.path.join(current_dir, ".."),  # Üst dizin
        
        # Olası Linux/Unix yolları
        "/var/www/cloakdocs",
        "/opt/cloakdocs",
        
        # Boş yol - doğrudan db_file_path kullanılır
        ""
    ]
    
    # Olası dosya yolları
    possible_paths = []
    
    # Her bir temel dizin için olası tam yolları oluştur
    for base_dir in base_dirs:
        # Tam yol
        full_path = os.path.join(base_dir, db_file_path)
        possible_paths.append(full_path)
        
        # Yol içinde "uploads" varsa bir de o olmadan dene
        if "uploads" in db_file_path:
            alt_path = os.path.join(base_dir, "uploads", db_file_path)
            possible_paths.append(alt_path)
        else:
            # "uploads" yoksa bir de uploads ile dene
            alt_path = os.path.join(base_dir, "uploads", db_file_path)
            possible_paths.append(alt_path)
    
    # Her bir olası yolu dene
    for path in possible_paths:
        normalized_path = os.path.normpath(path)
        print(f"Deneniyor: {normalized_path}")
        if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
            print(f"Dosya bulundu: {normalized_path}")
            return normalized_path
    
    # Hiçbir yol bulunamazsa None döndür
    print(f"Dosya bulunamadı. Denenen yollar: {', '.join(possible_paths)}")
    return None

@api.route('/papers')
class ReviewPapers(Resource):
    papers_parser = api.parser()
    papers_parser.add_argument('reviewer_id', location='args', type=str, required=True, help='Hakem ID')
    papers_parser.add_argument('subcategory_id', location='args', type=int, required=True, help='Hakem alt kategori ID')
    
    @api.expect(papers_parser)
    @api.response(200, 'Başarılı', papers_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Hakem için kendisine atanmış makaleleri getirme
        """
        try:
            # PaperStatus'ü sadece bu metod içinde import et
            from app.routers.status import PaperStatus as PaperStatusEnum
            
            # Hakem kimliği ve alt kategori ID'si
            reviewer_id = request.args.get('reviewer_id')
            subcategory_id = request.args.get('subcategory_id')
            
            if not reviewer_id or not subcategory_id:
                return {'error': 'Hakem ID ve alt kategori ID gereklidir'}, 400
            
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Hakeme atanmış makaleleri getir (reviews tablosunu kullanarak)
            query = """
                SELECT p.id, p.tracking_number, p.original_filename, p.upload_date, 
                       p.status, p.download_count
                FROM papers p
                INNER JOIN reviews r ON p.id = r.paper_id
                WHERE r.reviewer_id = %s
                ORDER BY p.upload_date DESC
            """
            
            cursor.execute(query, (reviewer_id,))
            assigned_papers = cursor.fetchall()
            
            # "in_review" durumundaki ve belirli alt kategoriye sahip olup henüz bu hakeme atanmamış makaleleri de getir
            # Bu kısım, hakem sistemdeki kendisi ile ilgili makaleleri görebilmesi için
            query_pending = """
                SELECT p.id, p.tracking_number, p.original_filename, p.upload_date, 
                       p.status, p.download_count
                FROM papers p
                LEFT JOIN reviews r ON p.id = r.paper_id AND r.reviewer_id = %s
                WHERE p.status = %s
                  AND r.id IS NULL
                  AND p.id IN (
                     -- Hakeme atanabilecek makaleler için alt sorgu, subcategory_id ile ilişkili
                     SELECT p2.id 
                     FROM papers p2
                     WHERE p2.id NOT IN (
                        SELECT paper_id FROM reviews WHERE reviewer_id != %s
                     )
                  )
                ORDER BY p.upload_date DESC
            """
            
            cursor.execute(query_pending, (reviewer_id, PaperStatusEnum.IN_REVIEW, reviewer_id))
            pending_review_papers = cursor.fetchall()
            
            # Sonuçları birleştir
            all_papers = []
            
            # Hakeme atanmış makalelere 'status' kısmına hakem durumunu ekleyelim
            for paper in assigned_papers:
                # Hakeme atanmış makalenin inceleme durumunu getir
                review_query = """
                    SELECT score, recommendation, created_at 
                    FROM reviews 
                    WHERE paper_id = %s AND reviewer_id = %s
                """
                cursor.execute(review_query, (paper['id'], reviewer_id))
                review = cursor.fetchone()
                
                paper_dict = dict(paper)
                if review:
                    if review['score'] is not None and review['score'] > 0:
                        paper_dict['review_status'] = 'completed'
                    else:
                        paper_dict['review_status'] = 'in_progress'
                else:
                    paper_dict['review_status'] = 'assigned'
                
                # Eğer makale durumu 'in_review' ancak henüz hakem değerlendirme yapmamışsa
                if paper_dict['status'] == PaperStatusEnum.IN_REVIEW and paper_dict['review_status'] in ['assigned', 'in_progress']:
                    all_papers.append(paper_dict)
                # Eğer makale durumu 'reviewed' ve hakem değerlendirmesi tamamlandıysa
                elif paper_dict['status'] == PaperStatusEnum.REVIEWED and paper_dict['review_status'] == 'completed':
                    all_papers.append(paper_dict)
                # Eğer makale durumu 'revision_required' veya 'revised' ise
                elif paper_dict['status'] in [PaperStatusEnum.REVISION_REQUIRED, PaperStatusEnum.REVISED]:
                    all_papers.append(paper_dict)
                # Bu hakem için önceden değerlendirdiği tüm makaleler (tarihsel kayıt)
                elif paper_dict['review_status'] == 'completed':
                    all_papers.append(paper_dict)
            
            # İnceleme bekleyen makaleleri ekle
            for paper in pending_review_papers:
                paper_dict = dict(paper)
                # Makale durumuna göre review_status değerini belirle
                if paper['status'] in ['reviewed', 'accepted', 'rejected', 'revision_required']:
                    paper_dict['review_status'] = 'completed'
                elif paper['status'] == 'in_review':
                    paper_dict['review_status'] = 'assigned'
                else:
                    paper_dict['review_status'] = 'pending'
                all_papers.append(paper_dict)
            
            # Hassas verileri temizle
            for paper in all_papers:
                if 'file_path' in paper:
                    del paper['file_path']
                if 'email' in paper:
                    del paper['email']  # Yazarın kimliği hakeme gösterilmemeli
            
            cursor.close()
            conn.close()
            
            # JSON serialization için datetime alanlarını string'e dönüştür
            all_papers = convert_datetime_fields(all_papers)
            
            return {
                'success': True,
                'count': len(all_papers),
                'papers': all_papers
            }
            
        except Exception as e:
            print(f"Hakem makaleleri getirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Makaleler alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/download/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class DownloadReviewPaper(Resource):
    download_parser = api.parser()
    download_parser.add_argument('reviewer_id', location='args', type=str, required=True, help='Hakem ID')
    
    @api.expect(download_parser)
    @api.response(200, 'Başarılı')
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale veya dosya bulunamadı')
    @api.response(403, 'Erişim engellendi')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Hakem için makale indirme (tüm makalelere erişim sağlanır)
        """
        try:
            # Hakem kimliği
            reviewer_id = request.args.get('reviewer_id')
            
            if not reviewer_id:
                return {'error': 'Hakem ID gereklidir'}, 400
            
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Önce makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            cursor.close()
            conn.close()
            
            # DOSYA YOLU YÖNETİMİ
            # -----------------------------------------------
            # Veritabanındaki dosya yolunu al
            db_file_path = paper['file_path']
            print(f"Veritabanından gelen dosya yolu: {db_file_path}")
            
            # Dosya yolunu çöz
            found_path = resolve_file_path(db_file_path)
            
            # Dosya bulunamadıysa hata döndür
            if not found_path:
                error_message = f"Dosya bulunamadı. Veritabanındaki yol: {db_file_path}"
                print(error_message)
                return {'error': error_message}, 404
            
            # İndirme sayısını artır - ayrı bir veritabanı bağlantısı kullan
            try:
                Paper.increment_download_count(tracking_number)
            except Exception as e:
                print(f"İndirme sayısı artırma hatası (göz ardı edildi): {e}")
                # Hatayı göz ardı et, indirmeye devam et
            
            # Dosyayı gönder
            print(f"send_file için kullanılan yol: {found_path}")
            return send_file(
                found_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"REVIEW_{paper['original_filename']}"
            )
            
        except Exception as e:
            print(f"Hakem dosya indirme hatası: {e}")
            traceback.print_exc()  # Detaylı hata izini yazdır
            return {'error': f'Dosya indirilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/submit/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class SubmitReview(Resource):
    submit_parser = api.parser()
    submit_parser.add_argument('reviewer_id', location='form', type=str, required=True, help='Hakem ID')
    submit_parser.add_argument('score', location='form', type=int, required=True, help='Değerlendirme puanı (1-10)')
    submit_parser.add_argument('comments', location='form', type=str, required=True, help='Değerlendirme yorumları')
    submit_parser.add_argument('recommendation', location='form', type=str, required=True, help='Öneri (kabul/revizyon/red)')
    submit_parser.add_argument('subcategory_id', location='form', type=int, required=True, help='Alt kategori ID')
    submit_parser.add_argument('reviewFile', location='files', type=FileStorage, required=False, help='Değerlendirme dosyası (opsiyonel)')
    
    @api.expect(submit_parser)
    @api.response(200, 'Başarılı', review_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(403, 'Erişim engellendi')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, tracking_number):
        """
        Makale değerlendirmesi gönder
        """
        try:
            # PaperStatus'ü sadece bu metod içinde import et
            from app.routers.status import PaperStatus as PaperStatusEnum
            
            print(f"\n---------- MAKALE DEĞERLENDİRME GÖNDERME BAŞLADI ----------")
            print(f"Takip Numarası: {tracking_number}")
            
            # Form verilerini al
            form_data = request.form
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                print(f"Makale bulunamadı: {tracking_number}")
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
                
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Makalenin bu hakeme atanmış olup olmadığını kontrol et
            query = """
                SELECT 1 FROM reviews 
                WHERE paper_id = %s AND reviewer_id = %s
                UNION
                SELECT 1 FROM papers 
                WHERE id = %s AND status = %s 
                  AND id NOT IN (
                    SELECT paper_id FROM reviews WHERE reviewer_id != %s
                  )
                LIMIT 1
            """
            
            cursor.execute(query, (paper['id'], form_data['reviewer_id'], paper['id'], PaperStatusEnum.IN_REVIEW, form_data['reviewer_id']))
            can_access = cursor.fetchone()
            
            if not can_access:
                cursor.close()
                conn.close()
                return {'error': 'Bu makaleyi değerlendirme yetkiniz bulunmamaktadır'}, 403
            
            # Değerlendirme verilerini al
            score = form_data['score']
            comments = form_data['comments']
            recommendation = form_data['recommendation']
            subcategory_id = form_data['subcategory_id']
            
            if not score or not comments or not recommendation or not subcategory_id:
                cursor.close()
                conn.close()
                return {'error': 'Puan, yorumlar, öneri ve alt kategori ID gereklidir'}, 400
            
            # Ek değerlendirme dosyası (opsiyonel)
            review_file_path = None
            if 'reviewFile' in request.files:
                review_file = request.files['reviewFile']
                
                if review_file.filename:
                    # Değerlendirme dosyasını kaydet
                    review_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reviews')
                    os.makedirs(review_dir, exist_ok=True)
                    
                    from werkzeug.utils import secure_filename
                    file_name = f"REVIEW_{tracking_number}_{secure_filename(review_file.filename)}"
                    review_file_path = os.path.join('reviews', file_name)
                    full_path = os.path.join(review_dir, file_name)
                    
                    review_file.save(full_path)
            
            # Tüm hakem yorumlarını birleştirerek review_document alanına kaydet
            review_document = f"""
            Puan: {score}/10
            Öneri: {recommendation}
            Yorumlar:
            {comments}
            """
            
            # Değerlendirmeyi veritabanına kaydet
            # Önce mevcut bir değerlendirme var mı kontrol et
            check_query = """
                SELECT id FROM reviews
                WHERE paper_id = %s AND reviewer_id = %s
            """
            cursor.execute(check_query, (paper['id'], form_data['reviewer_id']))
            existing_review = cursor.fetchone()
            
            if existing_review:
                # Mevcut değerlendirmeyi güncelle
                update_query = """
                    UPDATE reviews
                    SET score = %s, comments = %s, recommendation = %s, 
                        review_file_path = COALESCE(%s, review_file_path),
                        subcategory_id = %s, review_document = %s
                    WHERE id = %s
                """
                cursor.execute(update_query, (score, comments, recommendation, 
                                            review_file_path, subcategory_id, 
                                            review_document, existing_review['id']))
            else:
                # Yeni değerlendirme ekle
                insert_query = """
                    INSERT INTO reviews
                    (paper_id, reviewer_id, score, comments, recommendation, 
                     review_file_path, subcategory_id, review_document)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (paper['id'], form_data['reviewer_id'], score, 
                                            comments, recommendation, review_file_path, 
                                            subcategory_id, review_document))
            
            # Makale durumunu güncelle
            Paper.update_status(tracking_number, PaperStatusEnum.REVIEWED)
            
            # Değişiklikleri kaydet
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': 'Değerlendirme başarıyla kaydedildi'
            }
            
        except Exception as e:
            print(f"HATA: Değerlendirme gönderme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirme gönderilirken bir hata oluştu: {str(e)}'}, 500

# Hakem durumunu kontrol etmek için yeni endpoint
@api.route('/status/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class ReviewStatus(Resource):
    status_parser = api.parser()
    status_parser.add_argument('reviewer_id', location='args', type=str, required=True, help='Hakem ID')
    
    @api.expect(status_parser)
    @api.response(200, 'Başarılı')
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Hakem tarafından makale inceleme durumunu kontrol etme
        """
        try:
            reviewer_id = request.args.get('reviewer_id')
            
            if not reviewer_id:
                return {'error': 'Hakem ID gereklidir'}, 400
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # İnceleme durumunu getir
            query = """
                SELECT id, score, comments, recommendation, created_at
                FROM reviews
                WHERE paper_id = %s AND reviewer_id = %s
            """
            cursor.execute(query, (paper['id'], reviewer_id))
            review = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not review:
                return {
                    'success': True,
                    'has_review': False,
                    'message': 'Bu makale için henüz değerlendirme yapılmamış'
                }
            
            # JSON serialization için datetime alanlarını string'e dönüştür
            review = convert_datetime_fields(review)
            
            return {
                'success': True,
                'has_review': True,
                'review': {
                    'id': review['id'],
                    'score': review['score'],
                    'recommendation': review['recommendation'],
                    'review_document': review['review_document'],
                    'created_at': review['created_at']
                },
                'message': 'Değerlendirme bilgileri başarıyla getirildi'
            }
            
        except Exception as e:
            print(f"Değerlendirme durumu kontrol hatası: {e}")
            return {'error': f'Değerlendirme durumu kontrol edilirken bir hata oluştu: {str(e)}'}, 500

# Bir hakem tarafından yapılan tüm değerlendirmeleri getirme
@api.route('/reviewer-reviews')
class ReviewerReviews(Resource):
    reviews_parser = api.parser()
    reviews_parser.add_argument('reviewer_id', location='args', type=str, required=True, help='Hakem ID')
    
    @api.expect(reviews_parser)
    @api.response(200, 'Başarılı')
    @api.response(400, 'Geçersiz istek')
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Hakem tarafından yapılan tüm değerlendirmeleri getirme
        """
        try:
            reviewer_id = request.args.get('reviewer_id')
            
            if not reviewer_id:
                return {'error': 'Hakem ID gereklidir'}, 400
            
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Hakem tarafından yapılan tüm değerlendirmeleri getir
            query = """
                SELECT r.id, r.score, r.recommendation, r.created_at,
                       p.tracking_number, p.original_filename, p.status
                FROM reviews r
                JOIN papers p ON r.paper_id = p.id
                WHERE r.reviewer_id = %s
                ORDER BY r.created_at DESC
            """
            cursor.execute(query, (reviewer_id,))
            reviews = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # JSON serialization için datetime alanlarını string'e dönüştür
            reviews = convert_datetime_fields(reviews)
            
            return {
                'success': True,
                'count': len(reviews),
                'reviews': reviews
            }
            
        except Exception as e:
            print(f"Hakem değerlendirmeleri getirme hatası: {e}")
            return {'error': f'Değerlendirmeler alınırken bir hata oluştu: {str(e)}'}, 500

# Değerlendirme bilgilerini getirme endpoint'i
@api.route('/get-review')
class GetReview(Resource):
    review_parser = api.parser()
    review_parser.add_argument('tracking_number', location='args', type=str, required=True, help='Makale takip numarası')
    review_parser.add_argument('reviewer_id', location='args', type=str, required=False, help='Hakem ID (opsiyonel)')
    
    @api.expect(review_parser)
    @api.response(200, 'Başarılı')
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Makale değerlendirme bilgilerini getirme
        """
        try:
            tracking_number = request.args.get('tracking_number')
            reviewer_id = request.args.get('reviewer_id')
            
            if not tracking_number:
                return {'error': 'Makale takip numarası gereklidir'}, 400
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # İnceleme durumunu getir
            if reviewer_id:
                # Belirli bir hakemin değerlendirmesini getir
                query = """
                    SELECT id, score, comments, recommendation, created_at
                    FROM reviews
                    WHERE paper_id = %s AND reviewer_id = %s
                """
                cursor.execute(query, (paper['id'], reviewer_id))
            else:
                # Makale için herhangi bir değerlendirme
                query = """
                    SELECT id, score, comments, recommendation, created_at
                    FROM reviews
                    WHERE paper_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                cursor.execute(query, (paper['id'],))
                
            review = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not review:
                return {
                    'success': True,
                    'has_review': False,
                    'message': 'Bu makale için henüz değerlendirme yapılmamış'
                }
            
            # JSON serialization için datetime alanlarını string'e dönüştür
            review = convert_datetime_fields(review)
            
            return {
                'success': True,
                'has_review': True,
                'review': {
                    'id': review['id'],
                    'score': review['score'],
                    'comments': review['comments'],
                    'recommendation': review['recommendation'],
                    'created_at': review['created_at']
                },
                'message': 'Değerlendirme bilgileri başarıyla getirildi'
            }
            
        except Exception as e:
            print(f"Değerlendirme bilgileri getirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirme bilgileri alınırken bir hata oluştu: {str(e)}'}, 500

# Hakeme makale atama endpoint'i
@api.route('/assign/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class AssignReviewer(Resource):
    assign_parser = api.parser()
    assign_parser.add_argument('reviewer_id', location='form', type=str, required=True, help='Hakem ID')
    assign_parser.add_argument('subcategory_id', location='form', type=int, required=True, help='Alt kategori ID')
    
    @api.expect(assign_parser)
    @api.response(200, 'Başarılı', review_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, tracking_number):
        """
        Makaleyi hakeme atama
        """
        try:
            # Hakem ve alt kategori ID'si
            reviewer_id = request.form.get('reviewer_id')
            subcategory_id = request.form.get('subcategory_id')
            
            if not reviewer_id or not subcategory_id:
                return {'error': 'Hakem ID ve alt kategori ID gereklidir'}, 400
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Makale zaten bu hakeme atanmış mı kontrol et
            check_query = """
                SELECT id FROM reviews
                WHERE paper_id = %s AND reviewer_id = %s
            """
            cursor.execute(check_query, (paper['id'], reviewer_id))
            existing_review = cursor.fetchone()
            
            if existing_review:
                # Zaten atanmışsa dön
                cursor.close()
                conn.close()
                return {
                    'success': True,
                    'already_assigned': True,
                    'message': 'Makale zaten bu hakeme atanmış'
                }
            
            # Yeni bir değerlendirme kaydı oluştur (NOT NULL kısıtlamaları için varsayılan değerler eklendi)
            insert_query = """
                INSERT INTO reviews
                (paper_id, reviewer_id, subcategory_id, score, comments, recommendation)
                VALUES (%s, %s, %s, 0, '', 'pending')
                RETURNING id
            """
            cursor.execute(insert_query, (paper['id'], reviewer_id, subcategory_id))
            new_review = cursor.fetchone()
            
            # Makale durumunu 'in_review' olarak güncelle
            Paper.update_status(tracking_number, 'in_review')
            
            # Değişiklikleri kaydet
            conn.commit()
            cursor.close()
            conn.close()
            
            # JSON serialization için datetime alanlarını string'e dönüştür
            if new_review:
                new_review = convert_datetime_fields(new_review)
            
            return {
                'success': True,
                'message': 'Makale başarıyla hakeme atandı',
                'review_id': new_review['id'] if new_review else None
            }
            
        except Exception as e:
            print(f"Makale atama hatası: {e}")
            return {'error': f'Makale hakeme atanırken bir hata oluştu: {str(e)}'}, 500

# Makalenin hakemini değiştirme endpoint'i
@api.route('/update-reviewer/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class UpdateReviewer(Resource):
    update_parser = api.parser()
    update_parser.add_argument('new_reviewer_id', location='form', type=str, required=True, help='Yeni Hakem ID')
    update_parser.add_argument('subcategory_id', location='form', type=int, required=True, help='Alt kategori ID')
    
    @api.expect(update_parser)
    @api.response(200, 'Başarılı', review_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, tracking_number):
        """
        Makalenin hakemini değiştirme
        """
        try:
            # Yeni hakem ve alt kategori ID'si
            new_reviewer_id = request.form.get('new_reviewer_id')
            subcategory_id = request.form.get('subcategory_id')
            
            if not new_reviewer_id or not subcategory_id:
                return {'error': 'Yeni Hakem ID ve alt kategori ID gereklidir'}, 400
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Makalenin mevcut bir değerlendirmesi var mı kontrol et
            check_query = """
                SELECT id FROM reviews
                WHERE paper_id = %s
            """
            cursor.execute(check_query, (paper['id'],))
            existing_review = cursor.fetchone()
            
            if existing_review:
                # Mevcut değerlendirmeyi güncelle
                update_query = """
                    UPDATE reviews
                    SET reviewer_id = %s, subcategory_id = %s
                    WHERE id = %s
                    RETURNING id
                """
                cursor.execute(update_query, (new_reviewer_id, subcategory_id, existing_review['id']))
                updated_review = cursor.fetchone()
                
                # Değişiklikleri kaydet
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    'success': True,
                    'message': 'Makalenin hakemi başarıyla değiştirildi',
                    'review_id': updated_review['id'] if updated_review else None
                }
            else:
                # Mevcut değerlendirme yoksa, yeni bir değerlendirme kaydı oluştur
                insert_query = """
                    INSERT INTO reviews
                    (paper_id, reviewer_id, subcategory_id, score, comments, recommendation)
                    VALUES (%s, %s, %s, 0, '', 'pending')
                    RETURNING id
                """
                cursor.execute(insert_query, (paper['id'], new_reviewer_id, subcategory_id))
                new_review = cursor.fetchone()
                
                # Makale durumunu 'in_review' olarak güncelle
                Paper.update_status(tracking_number, 'in_review')
                
                # Değişiklikleri kaydet
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    'success': True,
                    'message': 'Makaleye yeni hakem başarıyla atandı',
                    'review_id': new_review['id'] if new_review else None
                }
            
        except Exception as e:
            print(f"Hakem değiştirme hatası: {e}")
            return {'error': f'Makalenin hakemi değiştirilirken bir hata oluştu: {str(e)}'}, 500

# Makale önizleme endpoint'i
@api.route('/preview/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class PreviewPaper(Resource):
    preview_parser = api.parser()
    preview_parser.add_argument('reviewer_id', location='args', type=str, required=False, help='Hakem ID')
    
    @api.expect(preview_parser)
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale bulunamadı')
    @api.response(403, 'Erişim engellendi')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Makale önizleme verisi getirme (tüm makalelere erişim sağlanır)
        """
        try:
            # İsteğe bağlı hakem kimliği
            reviewer_id = request.args.get('reviewer_id')
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Makale meta verileri
            paper_data = {
                'title': f"Makale: {paper['tracking_number']}",
                'abstract': "Bu bir makale önizlemesidir. Hakem değerlendirmesi için tam makale indirilmelidir.",
                'authors': "Makale yazarları",
                'keywords': ["akademik", "araştırma", "hakemli dergi"],
                'publication_date': paper['upload_date'].strftime("%d.%m.%Y") if 'upload_date' in paper and paper['upload_date'] else "Belirtilmemiş",
                'pages': 10,
                'content': """
                Bu içerik, makale önizlemesi için oluşturulmuş bir taslaktır.
                Gerçek içerik, PDF dosyasında yer almaktadır ve Dosyayı İndir butonunu 
                kullanarak tam metne erişebilirsiniz.
                
                Bu önizleme, makalenin genel yapısını göstermek amacıyla sunulmaktadır.
                
                Değerlendirme yapmak için lütfen tam metni indirin ve detaylı inceleme yapın.
                """
            }
            
            # PDF sayfa verisi
            return paper_data
            
        except Exception as e:
            print(f"Makale önizleme hatası: {e}")
            return {'error': f'Makale önizleme verisi alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/submit-to-editor/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class SubmitToEditor(Resource):
    submit_editor_parser = api.parser()
    submit_editor_parser.add_argument('reviewer_id', type=str, location='form', required=True, help='Hakem ID')
    
    @api.expect(submit_editor_parser)
    @api.response(200, 'Başarılı', review_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale veya değerlendirme bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, tracking_number):
        """
        Hakemin değerlendirdiği makaleyi editöre gönderme
        """
        try:
            # PaperStatus'ü sadece bu metod içinde import et
            from app.routers.status import PaperStatus as PaperStatusEnum
            
            print(f"\n---------- DEĞERLENDİRİLMİŞ MAKALEYİ EDİTÖRE GÖNDERME BAŞLADI ----------")
            print(f"Takip Numarası: {tracking_number}")
            
            # Form verilerini al
            reviewer_id = request.form.get('reviewer_id')
            
            if not reviewer_id:
                return {'error': 'Hakem ID gereklidir'}, 400
                
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
                
            # Veritabanı bağlantısı
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Değerlendirmeyi kontrol et
            check_query = """
                SELECT id, reviewer_id, paper_id, score, recommendation
                FROM reviews
                WHERE paper_id = %s AND reviewer_id = %s
            """
            cursor.execute(check_query, (paper['id'], reviewer_id))
            review = cursor.fetchone()
            
            if not review:
                return {'error': 'Bu makale için değerlendirme bulunamadı'}, 404
                
            if review['score'] is None or review['score'] <= 0:
                return {'error': 'Bu makale henüz değerlendirilmemiş'}, 400
            
            # Makalenin durumunu 'reviewed' olarak güncelle
            Paper.update_status(tracking_number, PaperStatusEnum.REVIEWED)
            
            # Editöre bildirim gönder (isteğe bağlı)
            # ...
            
            print(f"Değerlendirme başarıyla editöre gönderildi. Makale ID: {paper['id']}")
            print("---------- DEĞERLENDİRİLMİŞ MAKALEYİ EDİTÖRE GÖNDERME TAMAMLANDI ----------\n")
            
            return {
                'success': True,
                'message': 'Değerlendirme başarıyla editöre iletildi'
            }
            
        except Exception as e:
            print(f"HATA: Değerlendirme editöre gönderme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirme editöre gönderilirken bir hata oluştu: {str(e)}'}, 500 