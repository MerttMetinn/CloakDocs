from flask import request, send_file
from flask_restx import Namespace, Resource, fields
from app.models.paper import Paper
from app.utils.db import query
import datetime
import json
import traceback
from app.utils.logger import get_paper_logs
import os
from app.utils.review_processor import resolve_file_path

# Makale durumları için sabit tanımlar
class PaperStatus:
    # Ana makale durumları
    DRAFT = "draft"
    PENDING = "pending"
    IN_REVIEW = "in_review"
    REVIEWED = "reviewed"
    REVISION_REQUIRED = "revision_required"
    REVISED = "revised"
    FORWARDED = "forwarded"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PUBLISHED = "published"
    
    # Alt durumlar veya özel durumlar 
    ASSIGNED = "assigned" # Hakem atanmış, inceleme sürecinde
    ANONYMIZED = "anonymized" # Makale anonimleştirildi, hakeme atanmaya hazır
    UNDER_EDITOR_REVIEW = "under_editor_review" # Editör kontrolünde
    WAITING_AUTHOR_RESPONSE = "waiting_author_response" # Yazar yanıtı bekliyor
    WITHDRAWN = "withdrawn" # Yazar tarafından geri çekilmiş
    
    # Belirsiz durumlar
    UNDEFINED = "undefined"
    
    # Tüm durumlar
    ALL_STATUSES = [
        DRAFT, PENDING, IN_REVIEW, REVIEWED, REVISION_REQUIRED, 
        REVISED, FORWARDED, ACCEPTED, REJECTED, PUBLISHED,
        ASSIGNED, ANONYMIZED, UNDER_EDITOR_REVIEW, WAITING_AUTHOR_RESPONSE, WITHDRAWN
    ]
    
    # Durumların kullanıcı dostu Türkçe karşılıkları
    STATUS_NAMES = {
        DRAFT: "Taslak",
        PENDING: "Beklemede",
        IN_REVIEW: "İncelemede",
        REVIEWED: "Değerlendirildi",
        REVISION_REQUIRED: "Revizyon Gerekli",
        REVISED: "Revize Edildi",
        FORWARDED: "İletildi",
        ACCEPTED: "Kabul Edildi",
        REJECTED: "Reddedildi",
        PUBLISHED: "Yayınlandı",
        ASSIGNED: "Hakem Atandı",
        ANONYMIZED: "Anonimleştirildi",
        UNDER_EDITOR_REVIEW: "Editör İncelemesinde",
        WAITING_AUTHOR_RESPONSE: "Yazar Yanıtı Bekleniyor",
        WITHDRAWN: "Geri Çekildi",
        UNDEFINED: "Belirsiz"
    }

# JSON serileştirme için yardımcı fonksiyon
def convert_datetime(item):
    if isinstance(item, dict):
        # Önce datetime alanlarını belirleyip bunları saklayalım
        datetime_fields = {}
        for key, value in item.items():
            if isinstance(value, datetime.datetime):
                # Tarih formatını ISO standardına çevir, ancak 'T' karakteri yerine boşluk kullanılarak
                item[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                
                # Ayrıca özel formatlı versiyonları saklayalım
                if key == 'upload_date':
                    datetime_fields['upload_date_formatted'] = value.strftime("%d.%m.%Y %H:%M")
                
                if key == 'last_updated':
                    datetime_fields['last_updated_formatted'] = value.strftime("%d.%m.%Y %H:%M")
        
        # Sonra yeni alanları ekleyelim
        for key, value in datetime_fields.items():
            # Sadece yoksa ekle
            if key not in item:
                item[key] = value
                
    return item

# Namespace tanımlama
api = Namespace('status', description='Durum işlemleri')

# Modelleri tanımlama
paper_model = api.model('Paper', {
    'id': fields.Integer(description='Makale ID'),
    'tracking_number': fields.String(required=True, description='Makale takip numarası'),
    'email': fields.String(required=True, description='Yazar e-posta adresi'),
    'original_filename': fields.String(required=True, description='Orijinal dosya adı'),
    'upload_date': fields.DateTime(description='Yükleme tarihi'),
    'status': fields.String(description='Makalenin durumu'),
    'download_count': fields.Integer(description='İndirme sayısı')
})

papers_response = api.model('PapersResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'count': fields.Integer(description='Makale sayısı'),
    'papers': fields.List(fields.Nested(paper_model), description='Makaleler listesi')
})

update_model = api.model('StatusUpdate', {
    'trackingNumber': fields.String(required=True, description='Makale takip numarası'),
    'status': fields.String(required=True, description='Yeni durum')
})

update_response = api.model('UpdateResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'paper': fields.Nested(paper_model, description='Güncellenmiş makale')
})

status_counts_response = api.model('StatusCountsResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'counts': fields.Raw(description='Durum bazında makale sayıları')
})

status_response = api.model('StatusResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'paper': fields.Nested(paper_model, description='Makale bilgileri')
})

@api.route('/papers')
class PapersList(Resource):
    status_parser = api.parser()
    status_parser.add_argument('status', location='args', type=str, required=False, help='Durum filtresi')
    
    @api.expect(status_parser)
    @api.response(200, 'Başarılı', papers_response)
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Tüm makaleleri veya belirli bir duruma göre makaleleri getirme
        (Sadece editörler için kullanılmalı)
        """
        try:
            # Durum filtresi
            status = request.args.get('status')
            
            # Eğer status parametresi verildiyse ve geçerli bir durum değilse uyarı ver
            if status and status not in PaperStatus.ALL_STATUSES:
                print(f"Uyarı: Geçersiz durum filtresi: {status}. Tüm durumlar: {PaperStatus.ALL_STATUSES}")
            
            # Makaleleri getir
            papers = Paper.get_all_papers(status)
            
            # Datetime objelerini stringe çevir
            for paper in papers:
                convert_datetime(paper)
            
            return {
                'success': True,
                'count': len(papers),
                'papers': papers
            }
            
        except Exception as e:
            print(f"Makale listesi getirme hatası: {e}")
            return {'error': f'Makale listesi alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/update')
class StatusUpdate(Resource):
    @api.expect(update_model)
    @api.response(200, 'Başarılı', update_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self):
        """
        Makale durumunu güncelleme
        (Sadece editörler için kullanılmalı)
        """
        try:
            data = request.json
            tracking_number = data.get('trackingNumber')
            new_status = data.get('status')
            
            if not tracking_number or not new_status:
                return {'error': 'Takip numarası ve yeni durum gereklidir'}, 400
            
            # Durum geçerliliğini kontrol et
            if new_status not in PaperStatus.ALL_STATUSES:
                return {'error': f'Geçersiz durum değeri. Geçerli durumlar: {", ".join(PaperStatus.ALL_STATUSES)}'}, 400
            
            # Makalenin mevcut olup olmadığını kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Durumu güncelle
            updated_paper = Paper.update_status(tracking_number, new_status)
            
            if not updated_paper:
                return {'error': 'Makale durumu güncellenirken bir hata oluştu'}, 500
            
            return {
                'success': True,
                'paper': updated_paper
            }
            
        except Exception as e:
            print(f"Durum güncelleme hatası: {e}")
            return {'error': f'Makale durumu güncellenirken bir hata oluştu: {str(e)}'}, 500

@api.route('/counts')
class StatusCounts(Resource):
    @api.response(200, 'Başarılı', status_counts_response)
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Durum bazında makale sayılarını getirme
        (Editör paneli için kullanılabilir)
        """
        try:
            # Veritabanından durum sayılarını al
            sql = """
                SELECT status, COUNT(*) as count
                FROM papers
                GROUP BY status
            """
            
            result = query(sql)
            
            # Sonuçları formatla
            status_counts = {}
            for row in result:
                status = row['status'] or PaperStatus.PENDING
                status_counts[status] = row['count']
            
            # Tüm durumlar için sayı olmayanları sıfır olarak ekle
            for status in PaperStatus.ALL_STATUSES:
                if status not in status_counts:
                    status_counts[status] = 0
            
            return {
                'success': True,
                'counts': status_counts
            }
            
        except Exception as e:
            print(f"Durum sayıları getirme hatası: {e}")
            return {'error': f'Durum sayıları alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/status')
class PaperStatusResource(Resource):
    # Query string parametreleri için parser
    status_parser = api.parser()
    status_parser.add_argument('trackingNumber', location='args', type=str, required=True, help='Makale takip numarası')
    status_parser.add_argument('email', location='args', type=str, required=True, help='Yazar e-posta adresi')
    
    @api.expect(status_parser)
    @api.response(200, 'Başarılı', status_response)
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Tek bir makalenin durumunu sorgulama
        (Yazarlar tarafından sorgulanabilir)
        """
        try:
            tracking_number = request.args.get('trackingNumber')
            email = request.args.get('email')
            
            if not tracking_number or not email:
                return {'error': 'Takip numarası ve e-posta adresi gereklidir'}, 400
            
            # Makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number, email)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Datetime objelerini stringe çevir
            convert_datetime(paper)
            
            return {
                'success': True,
                'paper': paper
            }
            
        except Exception as e:
            print(f"Makale durumu sorgulama hatası: {e}")
            return {'error': f'Makale durumu sorgulanırken bir hata oluştu: {str(e)}'}, 500

@api.route('/paper/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class PaperStatusDetails(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Belirli bir makalenin durum detaylarını döndürür
        """
        try:
            print(f"Makale durum detayları alınıyor: {tracking_number}")
            
            # Makaleyi al
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': f'Takip numarası {tracking_number} olan makale bulunamadı'}, 404
                
            # Durum adını ekle
            status = paper['status'] or PaperStatus.PENDING
            paper['status_name'] = PaperStatus.STATUS_NAMES.get(status, 'Bilinmeyen Durum')
            
            # İşlemi yapan editör bilgilerini ekle (varsa)
            if paper.get('editor_id'):
                editor_query = """
                    SELECT id, name, email FROM users 
                    WHERE id = %s AND role = 'editor'
                """
                editor = query(editor_query, (paper['editor_id'],), one=True)
                if editor:
                    paper['editor'] = {
                        'id': editor['id'],
                        'name': editor['name'],
                        'email': editor['email']
                    }
                    
            return {
                'success': True,
                'paper': paper
            }
            
        except Exception as e:
            print(f"Makale durum detayları alma hatası: {e}")
            traceback.print_exc()
            return {'error': f'Makale durum detayları alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/revisions/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class PaperRevisions(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Bir makalenin tüm revizyonlarını döndürür.
        Hem orijinal makaleyi hem de revize edilmiş sürümlerini içerir.
        """
        try:
            print(f"Makale revizyonları getiriliyor: {tracking_number}")
            
            # Revizyon listesini al
            revisions = Paper.get_revisions(tracking_number)
            
            if not revisions:
                return {'error': f'Takip numarası {tracking_number} olan makale bulunamadı veya revizyonu yok'}, 404
                
            # Her revizyona durum adını ekle ve tarih formatlarını düzenle
            for revision in revisions:
                # Durum adını ekle
                status = revision['status'] or PaperStatus.PENDING
                revision['status_name'] = PaperStatus.STATUS_NAMES.get(status, 'Bilinmeyen Durum')
                
                # Datetime objelerini stringe çevir
                convert_datetime(revision)
            
            print(f"Döndürülen revizyon sayısı: {len(revisions)}")
            
            return {
                'success': True,
                'revisions': revisions,
                'count': len(revisions)
            }
            
        except Exception as e:
            print(f"Makale revizyonları getirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Makale revizyonları getirilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/logs/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class PaperLogs(Resource):
    logs_parser = api.parser()
    logs_parser.add_argument('limit', type=int, required=False, help='Maksimum kayıt sayısı')
    logs_parser.add_argument('event_type', type=str, required=False, help='İşlem türü filtresi')
    
    @api.expect(logs_parser)
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Belirli bir makaleye ait log kayıtlarını döndürür.
        Bu endpoint yalnızca editör rolündeki kullanıcılar için erişilebilir olmalıdır.
        """
        try:
            # Makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': f'Takip numarası {tracking_number} olan makale bulunamadı'}, 404
            
            # İsteğe bağlı parametreleri al
            limit = request.args.get('limit', type=int)
            event_type = request.args.get('event_type')
            
            # Log kayıtlarını getir
            logs = get_paper_logs(paper.get('id'), limit, event_type)
            
            # Başarılı yanıt
            return {
                'success': True,
                'paper': {
                    'id': paper.get('id'),
                    'tracking_number': tracking_number,
                    'status': paper.get('status'),
                    'email': paper.get('email')
                },
                'logs': logs,
                'count': len(logs)
            }
            
        except Exception as e:
            print(f"Makale log kayıtları alma hatası: {e}")
            traceback.print_exc()
            return {'error': f'Makale log kayıtları alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/author/download-review/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class AuthorDownloadReview(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale veya değerlendirme dosyası bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Yazarın kendi makalesinin değerlendirme raporunu indirmesini sağlar.
        Bu endpoint yalnızca makale sahibi yazarlar için erişilebilir olmalıdır.
        """
        try:
            print(f"\n---------- YAZAR DEĞERLENDİRME RAPORU İNDİRME BAŞLADI ({tracking_number}) ----------")
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                print(f"Makale bulunamadı: {tracking_number}")
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Değerlendirmeyi bul
            review_query = """
                SELECT * FROM reviews
                WHERE paper_id = %s
                AND review_file_path IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
            """
            review = query(review_query, (paper['id'],), one=True)
            
            if not review:
                print(f"Değerlendirme dosyası bulunamadı: {tracking_number}")
                return {'error': 'Bu makale için değerlendirme dosyası bulunamadı'}, 404
            
            # Dosya yolunu kontrol et
            if not review.get('review_file_path'):
                print(f"Değerlendirme dosyası yolu bulunamadı: {tracking_number}")
                return {'error': 'Değerlendirme dosyası bulunamadı'}, 404
            
            # Mutlak dosya yolunu çözümle
            file_path = resolve_file_path(os.path.join("uploads", review['review_file_path']))
            
            if not file_path or not os.path.exists(file_path):
                print(f"Değerlendirme dosyası bulunamadı: {file_path}")
                return {'error': 'Değerlendirme dosyası bulunamadı'}, 404
            
            # Dosya adını oluştur
            filename = f"review_{tracking_number}.pdf"
            
            print(f"Yazar değerlendirme raporu indiriliyor: {file_path}")
            print("---------- YAZAR DEĞERLENDİRME RAPORU İNDİRME TAMAMLANDI ----------\n")
            
            # Dosyayı gönder
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
            
        except Exception as e:
            print(f"HATA: Yazar değerlendirme raporu indirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirme raporu indirilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/author/download-final-pdf/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class AuthorDownloadFinalPdf(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale veya dosya bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Yazar için oluşturulan final PDF'i indir
        """
        try:
            print(f"\n---------- YAZAR FİNAL PDF İNDİRME BAŞLADI ({tracking_number}) ----------")
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                print(f"Makale bulunamadı: {tracking_number}")
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Değerlendirmeyi bul
            review_query = """
                SELECT * FROM reviews
                WHERE paper_id = %s
                AND final_pdf_path IS NOT NULL
                AND deanonymized = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """
            review = query(review_query, (paper['id'],), one=True)
            
            if not review:
                print(f"Final PDF bulunamadı: {tracking_number}")
                return {'error': 'Bu makale için final PDF bulunamadı'}, 404
            
            # Final PDF yolunu kontrol et
            if not review.get('final_pdf_path'):
                print(f"Final PDF yolu bulunamadı: {tracking_number}")
                return {'error': 'Final PDF yolu bulunamadı'}, 404
            
            # Mutlak dosya yolunu çözümle
            file_path = resolve_file_path(os.path.join("uploads", review['final_pdf_path']))
            
            if not file_path or not os.path.exists(file_path):
                print(f"Final PDF dosyası bulunamadı: {file_path}")
                return {'error': 'Final PDF dosyası bulunamadı'}, 404
            
            # Dosya adını oluştur
            filename = f"final_{tracking_number}.pdf"
            
            print(f"Yazar final PDF indiriliyor: {file_path}")
            print("---------- YAZAR FİNAL PDF İNDİRME TAMAMLANDI ----------\n")
            
            # Dosyayı gönder
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
            
        except Exception as e:
            print(f"HATA: Yazar final PDF indirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Final PDF indirilirken bir hata oluştu: {str(e)}'}, 500 