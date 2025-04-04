#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import request, send_file, current_app, Response, redirect, url_for
from flask_restx import Namespace, Resource, fields
from app.models.paper import Paper
import os
import datetime
from app.utils.email import send_email
import traceback
from app.utils.db import query, execute
from app.routers.author_message import convert_datetime_fields
from app.utils.db import get_db
from psycopg2.extras import RealDictCursor
import json
import tempfile
import pandas as pd
from io import BytesIO
from app.utils.logger import get_paper_logs

# Namespace tanımlama
api = Namespace('editor', description='Editör işlemleri')

# Modeller
paper_model = api.model('EditorPaper', {
    'id': fields.Integer(description='Makale ID'),
    'tracking_number': fields.String(required=True, description='Makale takip numarası'),
    'email': fields.String(required=True, description='Yazar e-posta adresi'),
    'original_filename': fields.String(required=True, description='Orijinal dosya adı'),
    'upload_date': fields.DateTime(description='Yükleme tarihi'),
    'status': fields.String(description='Makalenin durumu'),
    'download_count': fields.Integer(description='İndirme sayısı')
})

papers_response = api.model('EditorPapersResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'count': fields.Integer(description='Makale sayısı'),
    'papers': fields.List(fields.Nested(paper_model), description='Makaleler listesi')
})

paper_detail_response = api.model('PaperDetailResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'paper': fields.Nested(paper_model, description='Makale detayları')
})

message_model = api.model('AuthorMessage', {
    'message': fields.String(required=True, description='Mesaj içeriği')
})

message_response = api.model('MessageResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'emailSent': fields.Boolean(description='E-posta gönderildi mi?')
})

@api.route('/papers')
class EditorPapers(Resource):
    papers_parser = api.parser()
    papers_parser.add_argument('status', location='args', type=str, required=False, help='Durum filtresi')
    
    @api.expect(papers_parser)
    @api.response(200, 'Başarılı', papers_response)
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Editör için tüm makaleleri getirme
        """
        try:
            # Durum filtresi (opsiyonel)
            status = request.args.get('status')
            
            # Makaleleri getir
            papers = Paper.get_all_papers(status)
            
            # Editör için ekstra bilgiler ekle
            for paper in papers:
                # Hassas verileri temizle
                if 'file_path' in paper:
                    del paper['file_path']
            
            return {
                'success': True,
                'count': len(papers),
                'papers': papers
            }
            
        except Exception as e:
            print(f"Editör makaleleri getirme hatası: {e}")
            return {'error': f'Makaleler alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/paper/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class EditorPaperDetail(Resource):
    @api.response(200, 'Başarılı', paper_detail_response)
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Editör için makale detaylarını getirme
        """
        try:
            # Makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Makale durum geçmişini de ekle (eğer varsa)
            # Bu kısım, durum değişikliklerini izleyen bir tablo varsa eklenebilir
            
            return {
                'success': True,
                'paper': paper
            }
            
        except Exception as e:
            print(f"Makale detayı getirme hatası: {e}")
            return {'error': f'Makale detayları alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/download/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class DownloadPaper(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale veya dosya bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Editör için makale indirme
        """
        try:
            print("\n---------- MAKALE İNDİRME BAŞLATILIYOR (EDITÖR) ----------")
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

@api.route('/message/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class SendMessage(Resource):
    @api.expect(message_model)
    @api.response(200, 'Başarılı', message_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, tracking_number):
        """
        Editörün yazara mesaj göndermesi
        """
        try:
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            data = request.json
            message = data.get('message')
            
            if not message:
                return {'error': 'Mesaj içeriği boş olamaz'}, 400
            
            # Yazara e-posta gönder
            subject = f"Makale Değerlendirme Sistemi - Makale: {tracking_number}"
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
              <h2 style="color: #003366; border-bottom: 1px solid #e0e0e0; padding-bottom: 10px;">Makale Hakkında Bildirim</h2>
              
              <p style="color: #333333; font-size: 16px; line-height: 1.5;">
                Sayın Yazar,
              </p>
              
              <p style="color: #333333; font-size: 16px; line-height: 1.5;">
                {tracking_number} takip numaralı makaleniz hakkında editörden bir mesaj aldınız.
              </p>
              
              <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="color: #333333; font-size: 16px; line-height: 1.5;">{message}</p>
              </div>
              
              <p style="color: #333333; font-size: 16px; line-height: 1.5;">
                Makalenizin durumunu sorgulamak için <a href="${{BASE_URL}}/author/check-status" style="color: #008080; text-decoration: none; font-weight: bold;">Makale Durumu Sorgulama</a> sayfasını ziyaret edebilirsiniz.
              </p>
              
              <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666666; font-size: 14px;">
                <p>Bu e-posta otomatik olarak gönderilmiştir, lütfen yanıtlamayınız.</p>
                <p>© {{'CURRENT_YEAR'}} Akademik Makale Değerlendirme Sistemi</p>
              </div>
            </div>
            """
            
            # BASE_URL ve CURRENT_YEAR değişkenlerini değiştir
            base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
            current_year = str(datetime.datetime.now().year)
            
            html_content = html_content.replace("${{BASE_URL}}", base_url)
            html_content = html_content.replace("{{'CURRENT_YEAR'}}", current_year)
            
            # E-posta gönder
            email_sent = send_email(paper['email'], subject, html_content)
            
            # Mesajı veritabanına kaydet (opsiyonel)
            # Bu kısım, mesajları depolayan bir tablo varsa eklenebilir
            
            return {
                'success': True,
                'emailSent': email_sent
            }
            
        except Exception as e:
            print(f"Mesaj gönderme hatası: {e}")
            return {'error': f'Mesaj gönderilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/messages')
class EditorMessages(Resource):
    @api.response(200, 'Başarılı')
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Editör için tüm mesajları getir
        """
        try:
            print("\n---------- EDİTÖR MESAJLARI GETİRME BAŞLADI ----------")
            
            # Yazarlardan gelen mesajları getir
            sql = """
                SELECT m.id, m.paper_id, p.tracking_number, m.subject, m.message, 
                       m.sender_email as email, m.created_at, m.is_read,
                       p.original_filename
                FROM messages m
                JOIN papers p ON m.paper_id = p.id
                WHERE m.is_from_author = TRUE
                ORDER BY m.created_at DESC
            """
            
            author_messages = query(sql)
            
            # Her bir mesaj için son yanıtı bul
            for message in author_messages:
                # Yanıt için SQL sorgusu - o mesaj sonrası editörden gelen ilk mesajı al
                response_sql = """
                    SELECT m.id, m.message as response_message, m.created_at as responded_at
                    FROM messages m
                    WHERE m.paper_id = %s 
                      AND m.is_from_author = FALSE
                      AND m.created_at > %s
                    ORDER BY m.created_at ASC
                    LIMIT 1
                """
                response = query(response_sql, (message['paper_id'], message['created_at']), one=True)
                
                if response:
                    message['response_message'] = response['response_message']
                    message['responded_at'] = response['responded_at']
                else:
                    message['response_message'] = None
                    message['responded_at'] = None
            
            # Tarih alanlarını dönüştür
            author_messages = convert_datetime_fields(author_messages)
            
            print(f"Toplam {len(author_messages)} mesaj bulundu")
            print("---------- EDİTÖR MESAJLARI GETİRME TAMAMLANDI ----------\n")
            
            return {
                'success': True,
                'messages': author_messages
            }
            
        except Exception as e:
            print(f"HATA: Mesajları getirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Mesajlar alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/messages/<int:message_id>/read')
@api.doc(params={'message_id': 'Mesaj ID'})
class MarkMessageRead(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Mesaj bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, message_id):
        """
        Mesajı okundu olarak işaretle
        """
        try:
            print(f"\n---------- MESAJ OKUNDU İŞARETLEME BAŞLADI (ID: {message_id}) ----------")
            
            # Mesajı kontrol et
            sql = "SELECT * FROM messages WHERE id = %s LIMIT 1"
            message = query(sql, (message_id,), one=True)
            
            if not message:
                print(f"Mesaj bulunamadı: {message_id}")
                return {'error': 'Mesaj bulunamadı'}, 404
            
            # Okundu olarak işaretle
            update_sql = "UPDATE messages SET is_read = TRUE WHERE id = %s"
            execute(update_sql, (message_id,))
            
            print(f"Mesaj okundu olarak işaretlendi: {message_id}")
            print("---------- MESAJ OKUNDU İŞARETLEME TAMAMLANDI ----------\n")
            
            return {
                'success': True
            }
            
        except Exception as e:
            print(f"HATA: Mesajı okundu işaretleme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Mesaj okundu işaretlenirken bir hata oluştu: {str(e)}'}, 500

@api.route('/messages/<int:message_id>/respond')
@api.doc(params={'message_id': 'Mesaj ID'})
class RespondToMessage(Resource):
    @api.expect(message_model)
    @api.response(200, 'Başarılı')
    @api.response(404, 'Mesaj bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, message_id):
        """
        Mesaja yanıt ver
        """
        try:
            print(f"\n---------- MESAJ YANITLAMA BAŞLADI (ID: {message_id}) ----------")
            
            # Mesajı ve makaleyi al
            sql = """
                SELECT m.*, p.tracking_number, p.email as author_email
                FROM messages m
                JOIN papers p ON m.paper_id = p.id
                WHERE m.id = %s LIMIT 1
            """
            message = query(sql, (message_id,), one=True)
            
            if not message:
                print(f"Mesaj bulunamadı: {message_id}")
                return {'error': 'Mesaj bulunamadı'}, 404
            
            data = request.json
            response_content = data.get('response')
            
            if not response_content:
                return {'error': 'Yanıt içeriği boş olamaz'}, 400
                
            # Mesajın konusunu al (RE: ekleyerek)
            subject = message.get('subject', '')
            if not subject.startswith('RE:'):
                subject = f"RE: {subject}"
                
            # Yanıtı veritabanına kaydet
            now = datetime.datetime.now()
            
            sql = """
                INSERT INTO messages 
                (paper_id, sender_email, is_from_author, subject, message, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING id
            """
            
            # Sistemde tek editör olduğundan sabit bir e-posta kullanabilirsiniz
            editor_email = "editor@sistem.com"
            
            result = query(sql, (
                message['paper_id'], 
                editor_email, 
                False, # Editörden geldiği için is_from_author = FALSE
                subject, 
                response_content, 
                now
            ), one=True, commit=True)
            
            if not result or 'id' not in result:
                return {'error': 'Yanıt kaydedilirken bir hata oluştu'}, 500
                
            response_id = result['id']
            print(f"Yanıt kaydedildi. Yanıt ID: {response_id}")
            
            # Mesajı okundu olarak işaretle
            update_sql = "UPDATE messages SET is_read = TRUE WHERE id = %s"
            execute(update_sql, (message_id,))
            
            # Yazara e-posta bildirimi gönderme (isteğe bağlı)
            # ...
            
            print("---------- MESAJ YANITLAMA TAMAMLANDI ----------\n")
            
            return {
                'success': True,
                'messageId': response_id
            }
            
        except Exception as e:
            print(f"HATA: Mesaj yanıtlama hatası: {e}")
            traceback.print_exc()
            return {'error': f'Mesaj yanıtlanırken bir hata oluştu: {str(e)}'}, 500

@api.route('/check-review-status/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class CheckReviewStatus(Resource):
    
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Bir makalenin hakem durumunu kontrol eder
        """
        try:
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Veritabanı bağlantısı al
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Makalenin reviews tablosunda kaydı var mı kontrol et
            check_query = """
                SELECT id, reviewer_id, subcategory_id, score, recommendation, created_at 
                FROM reviews
                WHERE paper_id = %s
            """
            cursor.execute(check_query, (paper['id'],))
            review = cursor.fetchone()
            
            if review:
                # JSON serialization için datetime alanlarını string'e dönüştür
                review = convert_datetime_fields(review)
                
                return {
                    'success': True,
                    'has_reviewer': True,
                    'review': review
                }
            else:
                return {
                    'success': True,
                    'has_reviewer': False
                }
            
        except Exception as e:
            print(f"Hakem durumu kontrol hatası: {e}")
            return {'error': f'Hakem durumu kontrol edilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/anonymize/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class AnonymizePaper(Resource):
    anonymize_model = api.model('AnonymizeOptions', {
        'options': fields.List(fields.String, required=True, description='Anonimleştirilecek seçenekler')
    })
    
    @api.expect(anonymize_model)
    @api.response(200, 'Başarılı')
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, tracking_number):
        """
        Bir editör, yazara makaleyi anonimleştirdiğini ve hakemlere gönderildiğini bildirir.
        """
        try:
            # PaperStatus'ü sadece bu metod içinde import et
            from app.routers.status import PaperStatus as PaperStatusEnum
            
            # Kontrol - ASSIGNED sabiti var mı?
            if not hasattr(PaperStatusEnum, 'ANONYMIZED'):
                print(f"HATA: PaperStatusEnum sınıfında ANONYMIZED sabiti bulunamadı!")
                return {'error': 'Durum sabitleri tanımlanmamış: ANONYMIZED'}, 500
            
            # ANONYMIZED değeri string olarak kullanılacak
            anonymized_status = PaperStatusEnum.ANONYMIZED
            
            # Veritabanı bağlantısı oluştur
            conn = get_db()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Önce makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Anonimleştirilmiş bir dosya var mı kontrol et
            anon_query = """
                SELECT * FROM anonymized_files
                WHERE paper_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            cursor.execute(anon_query, (paper['id'],))
            anon_file = cursor.fetchone()
            
            if not anon_file:
                return {'error': 'Bu makale henüz anonimleştirilmemiş'}, 400
            
            try:
                # Makaleyi 'anonymized' durumuna getir - anonimleştirildi anlamında
                updated_paper = Paper.update_status(tracking_number, anonymized_status)
                
                if not updated_paper:
                    print(f"UYARI: Makale durumu güncellenemedi: {tracking_number}")
                    return {'error': 'Makale durumu güncellenemedi'}, 500
            except Exception as status_error:
                print(f"Durum güncelleme hatası: {status_error}")
                traceback.print_exc()
                return {'error': f'Makale durumu güncellenirken bir hata oluştu: {str(status_error)}'}, 500
            
            # Başarılı yanıt
            return {
                'success': True,
                'message': 'Makale başarıyla anonimleştirildi ve durumu güncellendi',
                'paper': {
                    'id': paper['id'],
                    'tracking_number': tracking_number,
                    'status': anonymized_status
                }
            }
            
        except Exception as e:
            print(f"Anonimleştirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Makale anonimleştirilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/forward-review/<int:review_id>')
@api.doc(params={'review_id': 'Değerlendirme ID'})
class ForwardReview(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Değerlendirme bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, review_id):
        """
        Hakem tarafından değerlendirilmiş makaleyi yazara ilet
        """
        try:
            # PaperStatus'ü sadece bu metod içinde import et
            from app.routers.status import PaperStatus as PaperStatusEnum
            
            print(f"\n---------- DEĞERLENDİRME YAZARA İLETME BAŞLADI (ID: {review_id}) ----------")
            
            # Değerlendirmeyi kontrol et
            review_query = """
                SELECT r.*, p.tracking_number, p.email as author_email, p.original_filename
                FROM reviews r
                JOIN papers p ON r.paper_id = p.id
                WHERE r.id = %s LIMIT 1
            """
            review = query(review_query, (review_id,), one=True)
            
            if not review:
                print(f"Değerlendirme bulunamadı: {review_id}")
                return {'error': 'Değerlendirme bulunamadı'}, 404
            
            # Değerlendirme zaten yazara iletilmiş mi kontrol et
            if review.get('forwarded_to_author'):
                return {
                    'success': True,
                    'message': 'Bu değerlendirme zaten yazara iletilmiş'
                }
            
            # İletildi olarak işaretle
            update_sql = "UPDATE reviews SET forwarded_to_author = TRUE WHERE id = %s"
            execute(update_sql, (review_id,))
            
            # Makalenin durumunu güncelle - değerlendirme sonucuna göre
            recommendation = review.get('recommendation', '')
            new_status = PaperStatusEnum.REVIEWED  # Varsayılan durum
            
            if recommendation == 'accept':
                new_status = PaperStatusEnum.ACCEPTED
            elif recommendation == 'reject':
                new_status = PaperStatusEnum.REJECTED
            elif recommendation in ['minor_revision', 'major_revision']:
                new_status = PaperStatusEnum.REVISION_REQUIRED
            
            # Makale durumunu güncelle
            Paper.update_status(review['tracking_number'], new_status)
            
            # Yazara e-posta gönder
            author_email = review.get('author_email')
            if author_email:
                subject = f"Makale Değerlendirme Sonucu - {review['tracking_number']}"
                
                # Öneri metnini hazırla
                recommendation_text = "Değerlendirildi"
                if recommendation == 'accept':
                    recommendation_text = "Kabul"
                elif recommendation == 'reject':
                    recommendation_text = "Red"
                elif recommendation == 'minor_revision':
                    recommendation_text = "Küçük Revizyon"
                elif recommendation == 'major_revision':
                    recommendation_text = "Büyük Revizyon"
                
                html_content = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
                  <h2 style="color: #003366; border-bottom: 1px solid #e0e0e0; padding-bottom: 10px;">Makale Değerlendirme Sonucu</h2>
                  
                  <p style="color: #333333; font-size: 16px; line-height: 1.5;">
                    Sayın Yazar,
                  </p>
                  
                  <p style="color: #333333; font-size: 16px; line-height: 1.5;">
                    "{review['original_filename']}" başlıklı, {review['tracking_number']} takip numaralı makaleniz değerlendirilmiştir.
                  </p>
                  
                  <div style="background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #333333; margin-top: 0;">Değerlendirme Sonucu:</h3>
                    <p style="color: #333333; font-size: 16px; line-height: 1.5;"><strong>Puan:</strong> {review.get('score', 'Belirtilmemiş')}/10</p>
                    <p style="color: #333333; font-size: 16px; line-height: 1.5;"><strong>Öneri:</strong> {recommendation_text}</p>
                  </div>
                  
                  <p style="color: #333333; font-size: 16px; line-height: 1.5;">
                    Makalenizin durumunu sorgulamak ve değerlendirme raporunu indirmek için <a href="${{BASE_URL}}/author/check-status" style="color: #008080; text-decoration: none; font-weight: bold;">Makale Durumu Sorgulama</a> sayfasını ziyaret edebilirsiniz.
                  </p>
                  
                  <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666666; font-size: 14px;">
                    <p>Bu e-posta otomatik olarak gönderilmiştir, lütfen yanıtlamayınız.</p>
                    <p>© {{'CURRENT_YEAR'}} Akademik Makale Değerlendirme Sistemi</p>
                  </div>
                </div>
                """
                
                # BASE_URL ve CURRENT_YEAR değişkenlerini değiştir
                base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
                current_year = str(datetime.datetime.now().year)
                
                html_content = html_content.replace("${{BASE_URL}}", base_url)
                html_content = html_content.replace("{{'CURRENT_YEAR'}}", current_year)
                
                # E-posta gönder
                email_sent = send_email(author_email, subject, html_content)
                print(f"E-posta gönderildi: {email_sent}")
            else:
                email_sent = False
                print("Yazar e-postası bulunamadı, e-posta gönderilemedi")
            
            print(f"Değerlendirme yazara iletildi. ID: {review_id}")
            print("---------- DEĞERLENDİRME YAZARA İLETME TAMAMLANDI ----------\n")
            
            return {
                'success': True,
                'message': 'Değerlendirme başarıyla yazara iletildi',
                'emailSent': email_sent
            }
            
        except Exception as e:
            print(f"HATA: Değerlendirme iletme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirme yazara iletilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/reviews')
class EditorReviews(Resource):
    reviews_parser = api.parser()
    reviews_parser.add_argument('status', location='args', type=str, required=False, help='Değerlendirme durumu (reviewed/all)')
    
    @api.expect(reviews_parser)
    @api.response(200, 'Başarılı')
    @api.response(500, 'Sunucu hatası')
    def get(self):
        """
        Editör için tüm hakem değerlendirmelerini getir
        """
        try:
            # PaperStatus'ü sadece bu metod içinde import et
            from app.routers.status import PaperStatus as PaperStatusEnum
            
            print("\n---------- EDİTÖR DEĞERLENDİRMELERİ GETİRME BAŞLADI ----------")
            
            # Durum filtresi
            status = request.args.get('status', 'all')
            
            # SQL sorgusu
            sql = f"""
                SELECT r.id, r.paper_id, r.score, r.recommendation, r.comments,
                       r.reviewer_id, r.subcategory_id, r.created_at,
                       p.tracking_number, p.original_filename, p.status as paper_status
                FROM reviews r
                JOIN papers p ON r.paper_id = p.id
                """
            
            # Tamamlanmış değerlendirmeleri filtrele
            if status == "completed":
                sql += f" WHERE p.status = '{PaperStatusEnum.REVIEWED}'"
            
            sql += " ORDER BY r.created_at DESC"
            
            # Değerlendirmeleri getir
            reviews = query(sql)
            
            # Tarih alanlarını dönüştür
            reviews = convert_datetime_fields(reviews)
            
            print(f"Toplam {len(reviews)} değerlendirme bulundu")
            print("---------- EDİTÖR DEĞERLENDİRMELERİ GETİRME TAMAMLANDI ----------\n")
            
            return {
                'success': True,
                'reviews': reviews
            }
            
        except Exception as e:
            print(f"HATA: Değerlendirmeleri getirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirmeler alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/review/<int:review_id>')
@api.doc(params={'review_id': 'Değerlendirme ID'})
class ReviewDetail(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Değerlendirme bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, review_id):
        """
        Belirli bir değerlendirmenin detaylarını getir
        """
        try:
            print(f"\n---------- DEĞERLENDİRME DETAYI GETİRME BAŞLADI (ID: {review_id}) ----------")
            
            # Değerlendirmeyi getir
            review_query = """
                SELECT r.*, p.tracking_number, p.original_filename
                FROM reviews r
                JOIN papers p ON r.paper_id = p.id
                WHERE r.id = %s LIMIT 1
            """
            review = query(review_query, (review_id,), one=True)
            
            if not review:
                print(f"Değerlendirme bulunamadı: {review_id}")
                return {'error': 'Değerlendirme bulunamadı'}, 404
                
            # Tarih alanlarını dönüştür
            review = convert_datetime_fields(review)
            
            print(f"Değerlendirme detayı başarıyla getirildi: {review_id}")
            print("---------- DEĞERLENDİRME DETAYI GETİRME TAMAMLANDI ----------\n")
            
            return {
                'success': True,
                'review': review
            }
            
        except Exception as e:
            print(f"HATA: Değerlendirme detayı getirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirme detayı alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/download-review/<int:review_id>')
@api.doc(params={'review_id': 'Değerlendirme ID'})
class DownloadReview(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Değerlendirme veya dosya bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, review_id):
        """
        Değerlendirme dosyasını indir
        """
        try:
            print(f"\n---------- DEĞERLENDİRME DOSYASI İNDİRME BAŞLADI (ID: {review_id}) ----------")
            
            # Değerlendirmeyi kontrol et
            review_query = """
                SELECT r.*, p.tracking_number
                FROM reviews r
                JOIN papers p ON r.paper_id = p.id
                WHERE r.id = %s LIMIT 1
            """
            review = query(review_query, (review_id,), one=True)
            
            if not review:
                print(f"Değerlendirme bulunamadı: {review_id}")
                return {'error': 'Değerlendirme bulunamadı'}, 404
                
            # Dosya yolunu kontrol et
            if not review.get('review_file_path'):
                print(f"Değerlendirme dosyası yolu bulunamadı: {review_id}")
                return {'error': 'Değerlendirme dosyası bulunamadı'}, 404
                
            # Mutlak dosya yolunu al
            from app.utils.review_processor import resolve_file_path
            file_path = resolve_file_path(os.path.join("uploads", review['review_file_path']))
            
            if not file_path or not os.path.exists(file_path):
                print(f"Değerlendirme dosyası bulunamadı: {file_path}")
                return {'error': 'Değerlendirme dosyası bulunamadı'}, 404
                
            # Dosya adını oluştur
            filename = f"review_{review['tracking_number']}.pdf"
            
            print(f"Değerlendirme dosyası indiriliyor: {file_path}")
            print("---------- DEĞERLENDİRME DOSYASI İNDİRME TAMAMLANDI ----------\n")
            
            # Dosyayı gönder
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
            
        except Exception as e:
            print(f"HATA: Değerlendirme dosyası indirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirme dosyası indirilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/download-logs-report/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class DownloadLogsReport(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Paper not found')
    @api.response(500, 'Server error')
    def get(self, tracking_number):
        """
        Makale log raporunu Excel formatında indirme
        """
        try:
            # Makale kontrolü
            paper = Paper.get_by_tracking_number(tracking_number)
            if not paper:
                return {'error': f'Takip numarası {tracking_number} olan makale bulunamadı'}, 404
            
            # Log kayıtlarını getir
            logs = get_paper_logs(paper.get('id'))
            
            if not logs:
                return {'error': 'Bu makale için log kaydı bulunamadı'}, 404
            
            # DataFrame oluştur
            df = pd.DataFrame(logs)
            
            # Kolonları düzenle
            if 'additional_data' in df.columns:
                # JSON alanını metne dönüştür
                df['additional_data'] = df['additional_data'].apply(
                    lambda x: json.dumps(x, ensure_ascii=False) if x else ''
                )
            
            # Kolon isimlerini Türkçe yap
            column_names = {
                'id': 'ID',
                'paper_id': 'Makale ID',
                'event_type': 'İşlem Türü',
                'event_description': 'Açıklama',
                'user_email': 'Kullanıcı',
                'created_at': 'Tarih',
                'additional_data': 'Ek Bilgiler'
            }
            df = df.rename(columns=column_names)
            
            # Excel dosyasını oluştur
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Log Kayıtları', index=False)
                
                # Çalışma sayfasını al
                workbook = writer.book
                worksheet = writer.sheets['Log Kayıtları']
                
                # Format ayarları
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # Kolon başlıklarını formatla
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    
                # Kolon genişliklerini ayarla
                worksheet.set_column('A:A', 5)  # ID
                worksheet.set_column('B:B', 10)  # Makale ID
                worksheet.set_column('C:C', 15)  # İşlem Türü
                worksheet.set_column('D:D', 50)  # Açıklama
                worksheet.set_column('E:E', 20)  # Kullanıcı
                worksheet.set_column('F:F', 20)  # Tarih
                worksheet.set_column('G:G', 50)  # Ek Bilgiler
            
            # BytesIO'yu başa sar
            output.seek(0)
            
            # Excel dosyasını gönder
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'makale_log_{tracking_number}_{datetime.datetime.now().strftime("%Y%m%d")}.xlsx'
            )
            
        except Exception as e:
            print(f"Log raporu indirme hatası: {str(e)}")
            return {'error': f'Log raporu oluşturulurken bir hata oluştu: {str(e)}'}, 500

@api.route('/deanonymize-review/<int:review_id>')
@api.doc(params={'review_id': 'Değerlendirme ID'})
class DeanonymizeReview(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Değerlendirme veya dosya bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self, review_id):
        """
        Değerlendirmenin anonimliğini kaldırır ve orijinal PDF ile hakem raporunu birleştirir
        """
        try:
            print(f"\n---------- DEĞERLENDİRME ANONİMLİĞİNİ KALDIRMA BAŞLADI (ID: {review_id}) ----------")
            
            # Değerlendirmeyi getir
            review_query = """
                SELECT r.*, p.tracking_number, p.original_filename, p.id as paper_id
                FROM reviews r
                JOIN papers p ON r.paper_id = p.id
                WHERE r.id = %s LIMIT 1
            """
            review = query(review_query, (review_id,), one=True)
            
            if not review:
                print(f"Değerlendirme bulunamadı: {review_id}")
                return {'error': 'Değerlendirme bulunamadı'}, 404
            
            # İşlemi başlat
            print(f"Değerlendirme bilgileri: {review}")
            
            # 1. Orijinal makale PDF'ini bul
            paper_id = review['paper_id']
            
            # Orijinal dosya yolunu getir
            paper_query = "SELECT file_path FROM papers WHERE id = %s"
            paper_result = query(paper_query, (paper_id,), one=True)
            
            if not paper_result or not paper_result.get('file_path'):
                print(f"Orijinal makale dosyası bulunamadı: Paper ID {paper_id}")
                return {'error': 'Orijinal makale dosyası bulunamadı'}, 404
            
            # 2. Hakem değerlendirme dosyasını getir
            review_file_path = review.get('review_file_path')
            if not review_file_path:
                print(f"Değerlendirme dosyası bulunamadı: Review ID {review_id}")
                return {'error': 'Değerlendirme dosyası bulunamadı'}, 404
            
            # 3. Dosya yollarını çözümle
            from app.utils.review_processor import resolve_file_path
            
            original_pdf_path = resolve_file_path(os.path.join("uploads", paper_result['file_path']))
            review_pdf_path = resolve_file_path(os.path.join("uploads", review_file_path))
            
            if not original_pdf_path or not os.path.exists(original_pdf_path):
                print(f"Orijinal PDF dosyası bulunamadı: {original_pdf_path}")
                return {'error': 'Orijinal PDF dosyası bulunamadı'}, 404
            
            if not review_pdf_path or not os.path.exists(review_pdf_path):
                print(f"Değerlendirme PDF dosyası bulunamadı: {review_pdf_path}")
                return {'error': 'Değerlendirme PDF dosyası bulunamadı'}, 404
            
            # 4. PDF dosyalarını birleştir
            from PyPDF2 import PdfWriter, PdfReader
            
            # Çıktı klasörü oluştur
            output_dir = os.path.join(os.path.dirname(os.path.dirname(review_pdf_path)), "final_pdfs")
            os.makedirs(output_dir, exist_ok=True)
            
            # Dosya adını oluştur
            output_filename = f"final_{paper_id}_{review_id}.pdf"
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                # PDF'leri birleştir
                writer = PdfWriter()
                
                # Orijinal PDF'i ekle
                original_reader = PdfReader(original_pdf_path)
                for page in original_reader.pages:
                    writer.add_page(page)
                
                # Değerlendirme PDF'inin sadece son sayfasını ekle
                review_reader = PdfReader(review_pdf_path)
                if len(review_reader.pages) > 0:
                    # Son sayfayı ekle
                    last_page = review_reader.pages[-1]
                    writer.add_page(last_page)
                else:
                    print("UYARI: Değerlendirme PDF'i boş, son sayfa eklenemedi")
                
                # Final PDF'i kaydet
                with open(output_path, "wb") as output_file:
                    writer.write(output_file)
                
                print(f"Final PDF oluşturuldu: {output_path}")
                
                # Relatif dosya yolunu hesapla - uploads klasörüne göre
                relative_path = os.path.relpath(output_path, os.path.join(os.getcwd(), "uploads"))
                print(f"Relatif dosya yolu: {relative_path}")
                
                # 5. Veritabanını güncelle
                update_query = """
                    UPDATE reviews 
                    SET deanonymized = TRUE, 
                        final_pdf_path = %s
                    WHERE id = %s
                    RETURNING id, final_pdf_path, deanonymized
                """
                result = query(update_query, (relative_path, review_id), one=True)
                print(f"Veritabanı güncelleme sonucu: {result}")
                
                if not result:
                    print("HATA: Veritabanı güncellemesi başarısız oldu")
                    return {'error': 'Veritabanı güncellemesi başarısız oldu'}, 500
                
                print(f"Değerlendirme başarıyla güncellendi ve anonimlik kaldırıldı: {review_id}")
                print("---------- DEĞERLENDİRME ANONİMLİĞİNİ KALDIRMA TAMAMLANDI ----------\n")
                
                return {
                    'success': True,
                    'message': 'Değerlendirmenin anonimliği başarıyla kaldırıldı ve final PDF oluşturuldu',
                    'final_pdf_path': relative_path,
                    'review': result
                }
                
            except Exception as pdf_error:
                print(f"PDF birleştirme hatası: {pdf_error}")
                traceback.print_exc()
                return {'error': f'PDF birleştirme işlemi sırasında bir hata oluştu: {str(pdf_error)}'}, 500
            
        except Exception as e:
            print(f"HATA: Değerlendirme anonimliğini kaldırma hatası: {e}")
            traceback.print_exc()
            return {'error': f'Değerlendirme anonimliğini kaldırma sırasında bir hata oluştu: {str(e)}'}, 500

@api.route('/download-final-pdf/<int:review_id>')
@api.doc(params={'review_id': 'Değerlendirme ID'})
class DownloadFinalPdf(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Değerlendirme veya dosya bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, review_id):
        """
        Oluşturulan final PDF'i indir
        """
        try:
            print(f"\n---------- FİNAL PDF İNDİRME BAŞLADI (ID: {review_id}) ----------")
            
            # Değerlendirmeyi kontrol et
            review_query = """
                SELECT r.*, p.tracking_number, p.original_filename, p.id as paper_id
                FROM reviews r
                JOIN papers p ON r.paper_id = p.id
                WHERE r.id = %s LIMIT 1
            """
            review = query(review_query, (review_id,), one=True)
            
            if not review:
                print(f"Değerlendirme bulunamadı: {review_id}")
                return {'error': 'Değerlendirme bulunamadı'}, 404
            
            # Önce deanonymized değerini kontrol et
            if not review.get('deanonymized'):
                print(f"Bu değerlendirmenin anonimliği henüz kaldırılmamış: {review_id}")
                return {'error': 'Final PDF bulunamadı, lütfen önce anonimliği kaldırın'}, 404
            
            # Final PDF yolunu kontrol et
            if not review.get('final_pdf_path'):
                print(f"Final PDF bulunamadı: {review_id}")
                # Anonimlik kaldırılmış ama final_pdf_path yoksa, onu oluşturmayı deneyelim
                if review.get('deanonymized'):
                    # DeanonymizeReview sınıfını kullanarak final PDF oluştur
                    try:
                        from app.utils.review_processor import resolve_file_path
                        
                        # Orijinal makaleyi getir
                        paper_query = "SELECT file_path FROM papers WHERE id = %s"
                        paper_result = query(paper_query, (review['paper_id'],), one=True)
                        
                        if not paper_result or not paper_result.get('file_path'):
                            return {'error': 'Orijinal makale dosyası bulunamadı'}, 404
                        
                        # Değerlendirme dosyasını kontrol et
                        review_file_path = review.get('review_file_path')
                        if not review_file_path:
                            return {'error': 'Değerlendirme dosyası bulunamadı'}, 404
                        
                        # Dosya yollarını çözümle
                        original_pdf_path = resolve_file_path(os.path.join("uploads", paper_result['file_path']))
                        review_pdf_path = resolve_file_path(os.path.join("uploads", review_file_path))
                        
                        # PDF'leri birleştir
                        from PyPDF2 import PdfWriter, PdfReader
                        
                        # Çıktı klasörü oluştur
                        output_dir = os.path.join(os.path.dirname(os.path.dirname(review_pdf_path)), "final_pdfs")
                        os.makedirs(output_dir, exist_ok=True)
                        
                        output_filename = f"final_{review['paper_id']}_{review_id}.pdf"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        try:
                            # PDF'leri birleştir
                            writer = PdfWriter()
                            
                            # Orijinal PDF'i ekle
                            original_reader = PdfReader(original_pdf_path)
                            for page in original_reader.pages:
                                writer.add_page(page)
                            
                            # Değerlendirme PDF'inin sadece son sayfasını ekle
                            review_reader = PdfReader(review_pdf_path)
                            if len(review_reader.pages) > 0:
                                # Son sayfayı ekle
                                last_page = review_reader.pages[-1]
                                writer.add_page(last_page)
                            else:
                                print("UYARI: Değerlendirme PDF'i boş, son sayfa eklenemedi")
                            
                            # Final PDF'i kaydet
                            with open(output_path, "wb") as output_file:
                                writer.write(output_file)
                            
                            # Relatif dosya yolunu hesapla
                            relative_path = os.path.relpath(output_path, os.path.join(os.getcwd(), "uploads"))
                            
                            # Veritabanını güncelle
                            update_query = """
                                UPDATE reviews 
                                SET final_pdf_path = %s
                                WHERE id = %s
                            """
                            execute(update_query, (relative_path, review_id))
                            
                            print(f"Eksik final PDF oluşturuldu: {output_path}")
                            review['final_pdf_path'] = relative_path
                        except Exception as pdf_error:
                            print(f"PDF birleştirme hatası: {pdf_error}")
                            traceback.print_exc()
                            return {'error': f'PDF birleştirme işlemi sırasında bir hata oluştu: {str(pdf_error)}'}, 500
                    except Exception as reprocess_error:
                        print(f"Final PDF yeniden oluşturma hatası: {reprocess_error}")
                        return {'error': 'Final PDF bulunamadı ve yeniden oluşturulamadı'}, 404
                else:
                    return {'error': 'Final PDF bulunamadı, lütfen önce anonimliği kaldırın'}, 404
            
            # Mutlak dosya yolunu çözümle
            from app.utils.review_processor import resolve_file_path
            
            # Dosya yolunu log'a yaz
            print(f"Aranan final PDF dosya yolu: uploads/{review['final_pdf_path']}")
            
            # Birden fazla dosya yolu denemesi
            possible_paths_to_try = [
                os.path.join("uploads", review['final_pdf_path']),
                review['final_pdf_path'],
                os.path.join("uploads", review['final_pdf_path'].replace("uploads/", "")),
                os.path.join("uploads/papers", review['final_pdf_path'].replace("uploads/papers/", ""))
            ]
            
            file_path = None
            for path_to_try in possible_paths_to_try:
                print(f"Denenen yol: {path_to_try}")
                resolved_path = resolve_file_path(path_to_try)
                if resolved_path and os.path.exists(resolved_path):
                    file_path = resolved_path
                    print(f"Geçerli dosya yolu bulundu: {file_path}")
                    break
            
            if not file_path or not os.path.exists(file_path):
                print(f"Final PDF dosyası bulunamadı: {review.get('final_pdf_path')}")
                return {'error': 'Final PDF dosyası bulunamadı'}, 404
            
            # Dosya adını oluştur
            filename = f"final_{review['tracking_number']}.pdf"
            
            print(f"Final PDF indiriliyor: {file_path}")
            print("---------- FİNAL PDF İNDİRME TAMAMLANDI ----------\n")
            
            # Dosyayı gönder
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
            
        except Exception as e:
            print(f"HATA: Final PDF indirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Final PDF indirilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/author/download-final-pdf/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Makale takip numarası'})
class AuthorDownloadFinalPdf(Resource):
    @api.response(200, 'Başarılı')
    @api.response(404, 'Makale veya dosya bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Yazar için oluşturulan final PDF'i indir - Yönlendirme
        
        Bu endpointin işlevselliği artık status.py içinde yer almaktadır.
        Bu sadece eski isteklerle uyumluluk için korunmuştur.
        """
        # status altındaki AuthorDownloadFinalPdf endpointine yönlendir
        redirect_url = url_for('status_author_download_final_pdf', tracking_number=tracking_number, _external=True)
        print(f"Yönlendirme: {redirect_url}")
        return redirect(redirect_url) 