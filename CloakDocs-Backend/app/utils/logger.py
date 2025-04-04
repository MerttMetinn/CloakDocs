import logging
import datetime
import json
from app.utils.db import query

def log_paper_event(paper_id, event_type, event_description, user_email=None, additional_data=None):
    """
    Makale işlem loglarını veritabanına kaydeder
    
    Args:
        paper_id (int): Makale ID
        event_type (str): İşlem türü (UPLOADED, ASSIGNED, REVIEWED vb.)
        event_description (str): İşlem açıklaması
        user_email (str, optional): İşlemi yapan kullanıcı e-postası
        additional_data (dict, optional): İşlemle ilgili ek bilgiler (JSON olarak kaydedilecek)
    
    Returns:
        bool: İşlem başarılı ise True, değilse False
    """
    try:
        # Standart loglama
        log_message = f"PAPER_LOG [ID:{paper_id}] [{event_type}]: {event_description}"
        if user_email:
            log_message += f" (User: {user_email})"
        logging.info(log_message)
        
        # Veritabanına kaydet
        sql = """
            INSERT INTO paper_logs (paper_id, event_type, event_description, user_email, created_at, additional_data)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        # JSONB formatına çevir
        additional_data_json = json.dumps(additional_data) if additional_data else None
        
        # Şu anki tarih/saat
        now = datetime.datetime.now()
        
        # Sorguyu çalıştır
        result = query(sql, (paper_id, event_type, event_description, user_email, now, additional_data_json), one=True, commit=True)
        
        if result and 'id' in result:
            logging.debug(f"Log kaydı oluşturuldu. ID: {result['id']}")
            return True
        else:
            logging.error("Log kaydı oluşturulamadı: Sorgu sonucu boş veya 'id' alanı eksik")
            return False
            
    except Exception as e:
        logging.error(f"Log kaydı oluşturma hatası: {str(e)}")
        return False

def get_paper_logs(paper_id, limit=None, event_type=None):
    """
    Belirli bir makaleye ait log kayıtlarını getirir
    
    Args:
        paper_id (int): Makale ID
        limit (int, optional): Getirilecek kayıt sayısı limiti
        event_type (str, optional): Belirli bir işlem türüne göre filtreleme
    
    Returns:
        list: Log kayıtları listesi
    """
    try:
        if event_type:
            sql = """
                SELECT * FROM paper_logs
                WHERE paper_id = %s AND event_type = %s
                ORDER BY created_at DESC
            """
            params = (paper_id, event_type)
        else:
            sql = """
                SELECT * FROM paper_logs
                WHERE paper_id = %s
                ORDER BY created_at DESC
            """
            params = (paper_id,)
        
        # Limit ekle
        if limit:
            sql += " LIMIT %s"
            params = params + (limit,)
        
        # Sorguyu çalıştır
        results = query(sql, params)
        
        # JSON verisini python objesine dönüştür
        for log in results:
            if 'additional_data' in log and log['additional_data']:
                try:
                    log['additional_data'] = json.loads(log['additional_data'])
                except:
                    log['additional_data'] = {}
                    
            # Datetime nesnelerini string'e dönüştür
            if 'created_at' in log and log['created_at']:
                log['created_at'] = log['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                
        return results
        
    except Exception as e:
        logging.error(f"Log kayıtları getirme hatası: {str(e)}")
        return []

# Olay türleri için sabit tanımlar
class PaperEventType:
    UPLOADED = "UPLOADED"                # Makale yüklendi
    ASSIGNED = "ASSIGNED"                # Hakem atandı
    ANONYMIZED = "ANONYMIZED"            # Anonimleştirildi
    REVIEW_STARTED = "REVIEW_STARTED"    # Değerlendirme başladı
    REVIEWED = "REVIEWED"                # Değerlendirme tamamlandı
    REVISION_REQUESTED = "REVISION_REQUESTED"  # Revizyon istendi
    REVISED = "REVISED"                  # Revize edildi
    ACCEPTED = "ACCEPTED"                # Kabul edildi
    REJECTED = "REJECTED"                # Reddedildi
    PUBLISHED = "PUBLISHED"              # Yayınlandı
    STATUS_CHANGED = "STATUS_CHANGED"    # Durum değiştirildi
    DOWNLOADED = "DOWNLOADED"            # İndirildi
    MESSAGE_SENT = "MESSAGE_SENT"        # Mesaj gönderildi
    SYSTEM_LOG = "SYSTEM_LOG"            # Sistem tarafından oluşturulan log 