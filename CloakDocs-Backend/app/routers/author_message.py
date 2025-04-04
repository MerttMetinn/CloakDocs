import traceback
from flask import request, current_app, jsonify
from flask_restx import Namespace, Resource, fields
from app.models.paper import Paper
import os
import datetime
import json
from app.utils.db import query, execute

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
api = Namespace('internal-message', description='Yazar mesaj işlemleri')

# Model tanımlama
message_model = api.model('AuthorMessage', {
    'trackingNumber': fields.String(required=True, description='Makale takip numarası'),
    'subject': fields.String(required=True, description='Mesaj konusu'),
    'message': fields.String(required=True, description='Mesaj içeriği')
})

message_response = api.model('MessageResponse', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'messageId': fields.Integer(description='Oluşturulan mesaj ID')
})

thread_model = api.model('MessageThread', {
    'success': fields.Boolean(description='İşlem başarılı mı?'),
    'messages': fields.List(fields.Raw, description='Mesaj listesi')
})

@api.route('')
class AuthorMessage(Resource):
    @api.expect(message_model)
    @api.response(200, 'Başarılı', message_response)
    @api.response(400, 'Geçersiz istek')
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def post(self):
        """
        Yazarın editöre site içi mesaj göndermesi
        """
        try:
            print("\n---------- YAZAR MESAJ GÖNDERİMİ BAŞLADI ----------")
            data = request.json
            tracking_number = data.get('trackingNumber')
            subject = data.get('subject')
            message_content = data.get('message')

            print(f"Mesaj bilgileri: Takip No: {tracking_number}, Konu: {subject}, Mesaj (ilk 50 karakter): {message_content[:50]}...")

            if not tracking_number or not subject or not message_content:
                return {'error': 'Takip numarası, konu ve mesaj içeriği gereklidir'}, 400

            # Makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number)

            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404

            # E-posta adresi papers.email alanından alınıyor
            author_email = paper.get('email')
            
            if not author_email:
                return {'error': 'Yazara ait e-posta adresi bulunamadı'}, 500

            print(f"Yazar e-postası: {author_email}")

            # Mesajı veritabanına kaydet
            now = datetime.datetime.now()

            sql = """
                INSERT INTO messages 
                (paper_id, sender_email, is_from_author, subject, message, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING id
            """

            result = query(sql, (paper['id'], author_email, True, subject, message_content, now), one=True, commit=True)

            if not result or 'id' not in result:
                return {'error': 'Mesaj kaydedilirken bir hata oluştu'}, 500

            message_id = result['id']
            print(f"Mesaj başarıyla kaydedildi. ID: {message_id}")

            return {
                'success': True,
                'messageId': message_id
            }

        except Exception as e:
            print(f"HATA: Mesaj gönderme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Mesaj gönderilirken bir hata oluştu: {str(e)}'}, 500

@api.route('/messages/<string:tracking_number>')
class MessageThread(Resource):
    @api.response(200, 'Başarılı', thread_model)
    @api.response(404, 'Makale bulunamadı')
    @api.response(500, 'Sunucu hatası')
    def get(self, tracking_number):
        """
        Bir makalenin mesaj geçmişini getir
        """
        try:
            print(f"\n---------- MESAJ LİSTESİ GETİRME BAŞLADI ----------")
            print(f"Takip Numarası: {tracking_number}")
            
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
                
            # Mesajları getir
            sql = """
                SELECT m.id, m.subject, m.message, m.sender_email, m.is_from_author, 
                       m.created_at, m.is_read
                FROM messages m
                WHERE m.paper_id = %s
                ORDER BY m.created_at ASC
            """
            
            messages = query(sql, (paper['id'],))
            
            # Tarih alanlarını ISO formatına dönüştür
            messages = convert_datetime_fields(messages)
            
            print(f"Toplam mesaj sayısı: {len(messages)}")
            
            return {
                'success': True,
                'messages': messages
            }
            
        except Exception as e:
            print(f"HATA: Mesaj listesi getirme hatası: {e}")
            traceback.print_exc()
            return {'error': f'Mesaj listesi alınırken bir hata oluştu: {str(e)}'}, 500
