from app.utils.db import get_db, query, execute, get_db_connection
import uuid
import os
import datetime
from flask import current_app
import traceback
import json
from psycopg2.extras import RealDictCursor
from app.utils.logger import log_paper_event, PaperEventType

class Paper:
    @staticmethod
    def save_paper(tracking_number, email, file_path, original_filename, file_size=0, original_paper_id=None, is_revision=False):
        """
        Makale bilgilerini veritabanına kaydetme
        """
        try:
            # PaperStatus.py içe aktarmak yerine doğrudan string sabitleri kullanalım
            # from app.routers.status import PaperStatus
            
            print(f"Makale kayıt işlemi başlatılıyor: {tracking_number}")
            
            # Revizyon parametrelerini kontrol et
            if is_revision and original_paper_id:
                sql = """
                    INSERT INTO papers (tracking_number, email, file_path, original_filename, file_size, upload_date, status, original_paper_id, is_revision)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                
                # Şu anki tarih ve saat
                now = datetime.datetime.now()
                
                # Revize edilmiş durumu string sabit kullanarak
                status = "revised"
                
                params = (tracking_number, email, file_path, original_filename, file_size, now, status, original_paper_id, is_revision)
            else:
                sql = """
                    INSERT INTO papers (tracking_number, email, file_path, original_filename, file_size, upload_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                
                # Şu anki tarih ve saat
                now = datetime.datetime.now()
                
                # Beklemede durumu string sabit kullanarak
                status = "pending"
                
                params = (tracking_number, email, file_path, original_filename, file_size, now, status)
            
            print(f"SQL Sorgusu: {sql}")
            print(f"Parametreler: {params}")
            
            result = query(sql, params, one=True, commit=True)
            
            if result and 'id' in result:
                paper_id = result['id']
                print(f"Makale başarıyla kaydedildi. ID: {paper_id}")
                
                # Makale yükleme işlemini logla
                if is_revision:
                    log_paper_event(
                        paper_id=paper_id,
                        event_type=PaperEventType.REVISED,
                        event_description=f"Makale revize edildi: {tracking_number}",
                        user_email=email,
                        additional_data={"original_paper_id": original_paper_id}
                    )
                else:
                    log_paper_event(
                        paper_id=paper_id,
                        event_type=PaperEventType.UPLOADED,
                        event_description=f"Yeni makale yüklendi: {tracking_number}",
                        user_email=email
                    )
                
                return paper_id
            else:
                print("Makale kaydı başarısız oldu: Sorgu sonucu boş veya 'id' alanı eksik")
                return None
        except Exception as e:
            print(f"Makale kaydı hatası: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_by_tracking_number(tracking_number, email=None):
        """
        Takip numarasına göre makaleyi getirir.
        E-posta doğrulaması gerekiyorsa, makalenin sahibine ait olup olmadığını da kontrol eder.
        """
        try:
            print(f"\n---------- MAKALE SORGULAMA BAŞLIYOR ----------")
            print(f"Aranan takip numarası: '{tracking_number}', E-posta: '{email if email else 'Belirtilmedi'}'")

            # Eğer email doğrulaması isteniyorsa, sorguya ekleyelim
            if email:
                sql = """
                    SELECT * FROM papers 
                    WHERE tracking_number = %s AND email = %s
                    LIMIT 1
                """
                params = (tracking_number, email)
            else:
                sql = """
                    SELECT * FROM papers 
                    WHERE tracking_number = %s
                    LIMIT 1
                """
                params = (tracking_number,)

            print(f"SQL Sorgusu: {sql}")
            print(f"Parametreler: {params}")

            # Sorguyu çalıştır
            result = query(sql, params, one=True)

            if result:
                print(f"Makale bulundu: {result}")
            else:
                print(f"Makale bulunamadı! Aranan kriterler: Takip No: '{tracking_number}', Email: '{email}'")

            print(f"---------- MAKALE SORGULAMA TAMAMLANDI ----------\n")    
            return result
        except Exception as e:
            print(f"Makale sorgulama hatası: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def get_all_papers(status=None):
        """
        Tüm makaleleri veya belirli bir duruma göre makaleleri getirme
        """
        try:
            if status:
                sql = """
                    SELECT * FROM papers
                    WHERE status = %s
                    ORDER BY upload_date DESC
                """
                params = (status,)
            else:
                sql = """
                    SELECT * FROM papers
                    ORDER BY upload_date DESC
                """
                params = None
            
            print(f"Tüm makaleler sorgulanıyor. Durum filtresi: {status if status else 'Yok'}")
            results = query(sql, params)
            
            print(f"Sorgu sonucu: {len(results)} makale bulundu")
            return results
        except Exception as e:
            print(f"Makale listesi getirme hatası: {e}")
            traceback.print_exc()
            return []
    
    @staticmethod
    def increment_download_count(tracking_number):
        """
        Makalenin indirme sayısını artırır
        """
        try:
            from app.utils.db import get_db, query
            
            # Önce makaleyi getir
            paper = Paper.get_by_tracking_number(tracking_number)
            if not paper:
                print(f"İndirme sayısı güncellenemedi. Makale bulunamadı: {tracking_number}")
                return None
            
            paper_id = paper.get('id')
            email = paper.get('email')
            
            # Doğrudan veritabanı bağlantısı kullanarak sayıyı artır
            sql = """
                UPDATE papers
                SET download_count = download_count + 1,
                    last_downloaded = NOW()
                WHERE tracking_number = %s
                RETURNING download_count
            """
            
            result = query(sql, (tracking_number,), one=True)
            
            if result:
                new_count = result['download_count']
                print(f"Makale indirme sayısı artırıldı: {tracking_number}, Yeni sayı: {new_count}")
                
                # İndirme işlemini logla
                log_paper_event(
                    paper_id=paper_id,
                    event_type=PaperEventType.DOWNLOADED,
                    event_description=f"Makale indirildi (indirme sayısı: {new_count})",
                    user_email=None,  # İndiren kişinin kimliği bilinmiyor olabilir
                    additional_data={"download_count": new_count}
                )
                
                return new_count
            else:
                print(f"İndirme sayısı güncellenemedi. Makale bulunamadı: {tracking_number}")
                return None
        except Exception as e:
            print(f"İndirme sayısı artırma hatası: {e}")
            traceback.print_exc()
            # Hatayı yut ama loglama yap - indirme işlemini etkilememesi için
            return None
    
    @staticmethod
    def update_status(tracking_number, new_status):
        """
        Makale durumunu güncelleme
        """
        try:
            # İlk olarak mevcut durumu getir
            paper = Paper.get_by_tracking_number(tracking_number)
            if not paper:
                print(f"Makale durumu güncellenemedi. Makale bulunamadı: {tracking_number}")
                return None
            
            old_status = paper.get('status')
            paper_id = paper.get('id')
            email = paper.get('email')
            
            # Statü değişmiyorsa loglama yapma
            if old_status == new_status:
                print(f"Makale durumu zaten {new_status} olarak ayarlanmış: {tracking_number}")
                return paper
            
            # Durumu güncelle
            sql = """
                UPDATE papers
                SET status = %s,
                    last_updated = NOW()
                WHERE tracking_number = %s
                RETURNING *
            """
            
            print(f"Makale durumu güncelleniyor: {tracking_number}, Yeni durum: {new_status}")
            result = query(sql, (new_status, tracking_number), one=True, commit=True)
            
            if result:
                print(f"Makale durumu güncellendi: {tracking_number}, Yeni durum: {new_status}")
                
                # Durum değişikliğini logla
                event_type = PaperEventType.STATUS_CHANGED
                
                # Özel durum türleri için event_type'ı belirle
                if new_status == "assigned":
                    event_type = PaperEventType.ASSIGNED
                elif new_status == "anonymized":
                    event_type = PaperEventType.ANONYMIZED
                elif new_status == "reviewed":
                    event_type = PaperEventType.REVIEWED
                elif new_status == "revision_required":
                    event_type = PaperEventType.REVISION_REQUESTED
                elif new_status == "revised":
                    event_type = PaperEventType.REVISED
                elif new_status == "accepted":
                    event_type = PaperEventType.ACCEPTED
                elif new_status == "rejected":
                    event_type = PaperEventType.REJECTED
                elif new_status == "published":
                    event_type = PaperEventType.PUBLISHED
                
                # Log kaydı oluştur
                log_paper_event(
                    paper_id=paper_id,
                    event_type=event_type,
                    event_description=f"Makale durumu değiştirildi: {old_status} -> {new_status}",
                    user_email=email,
                    additional_data={
                        "old_status": old_status,
                        "new_status": new_status
                    }
                )
            else:
                print(f"Makale durumu güncellenemedi. Makale bulunamadı: {tracking_number}")
                
            return result
        except Exception as e:
            print(f"Makale durumu güncelleme hatası: {e}")
            traceback.print_exc()
            return None
    
    @staticmethod
    def update_keywords(tracking_number, keywords):
        """
        Makalenin anahtar kelimelerini güncelleme
        """
        try:
            # JSON'a dönüştür
            keywords_json = json.dumps(keywords, ensure_ascii=False)
            
            # SQL sorgusu
            sql = """
                UPDATE papers 
                SET keywords = %s
                WHERE tracking_number = %s
                RETURNING id
            """
            
            # Sorguyu çalıştır
            result = query(sql, (keywords_json, tracking_number), one=True, commit=True)
            
            if result:
                print(f"Anahtar kelimeler güncellendi - Takip No: {tracking_number}")
                return True
            else:
                print(f"Anahtar kelimeler güncellenemedi - Takip No: {tracking_number}")
                return False
            
        except Exception as e:
            print(f"Anahtar kelimeler güncellenirken hata: {str(e)}")
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_keywords(tracking_number):
        """
        Makalenin anahtar kelimelerini getirme
        """
        try:
            # SQL sorgusu
            sql = """
                SELECT keywords FROM papers
                WHERE tracking_number = %s
            """
            
            # Sorguyu çalıştır
            result = query(sql, (tracking_number,), one=True)
            
            if result and result['keywords']:
                try:
                    # JSON'dan Python nesnesine dönüştür
                    return json.loads(result['keywords'])
                except json.JSONDecodeError:
                    print(f"Anahtar kelimeler JSON formatına dönüştürülemedi: {result['keywords']}")
                    return {
                        "manual": [],
                        "keybert": [],
                        "yake": []
                    }
            else:
                return {
                    "manual": [],
                    "keybert": [],
                    "yake": []
                }
            
        except Exception as e:
            print(f"Anahtar kelimeler getirilirken hata: {str(e)}")
            traceback.print_exc()
            return {
                "manual": [],
                "keybert": [],
                "yake": []
            }
    
    @staticmethod
    def get_revisions(tracking_number):
        """
        Bir makalenin tüm revizyonlarını getirir, orijinal makale dahil
        """
        try:
            print(f"Makale revizyonları getiriliyor: {tracking_number}")
            
            # Önce gelen takip numarasına sahip makaleyi bul
            current_paper_sql = """
                SELECT id, tracking_number, email, is_revision, original_paper_id 
                FROM papers
                WHERE tracking_number = %s
                LIMIT 1
            """
            
            current_paper = query(current_paper_sql, (tracking_number,), one=True)
            
            if not current_paper:
                print(f"Belirtilen takip numarasıyla makale bulunamadı: {tracking_number}")
                return []
            
            # Bu makale bir revizyon mu, yoksa orijinal mi?
            is_revision = current_paper.get('is_revision', False)
            original_paper_id = current_paper.get('original_paper_id')
            
            # Eğer bu bir revizyonsa, orijinal makaleyi bul
            if is_revision and original_paper_id:
                print(f"Bu bir revizyon: {tracking_number}, Orijinal ID: {original_paper_id}")
                # Orijinal makale ve tüm revizyonlarını getir
                revisions_sql = """
                    SELECT 
                        id, tracking_number, email, original_filename, 
                        file_path, upload_date, status, download_count,
                        last_updated, keywords, is_revision, original_paper_id
                    FROM papers
                    WHERE id = %s OR original_paper_id = %s
                    ORDER BY 
                        CASE 
                            WHEN is_revision = FALSE THEN 0 
                            ELSE 1 
                        END,
                        upload_date
                """
                
                revisions = query(revisions_sql, (original_paper_id, original_paper_id))
            else:
                # Bu orijinal bir makale, kendi revizyonlarını getir
                print(f"Bu bir orijinal makale: {tracking_number}, ID: {current_paper['id']}")
                revisions_sql = """
                    SELECT 
                        id, tracking_number, email, original_filename, 
                        file_path, upload_date, status, download_count,
                        last_updated, keywords, is_revision, original_paper_id
                    FROM papers
                    WHERE id = %s OR original_paper_id = %s
                    ORDER BY 
                        CASE 
                            WHEN is_revision = FALSE THEN 0 
                            ELSE 1 
                        END,
                        upload_date
                """
                
                revisions = query(revisions_sql, (current_paper['id'], current_paper['id']))
            
            if not revisions:
                print(f"Revizyonlar bulunamadı: {tracking_number}")
                # En azından mevcut makaleyi döndür
                this_paper_sql = """
                    SELECT 
                        id, tracking_number, email, original_filename, 
                        file_path, upload_date, status, download_count,
                        last_updated, keywords, is_revision, original_paper_id
                    FROM papers
                    WHERE tracking_number = %s
                    LIMIT 1
                """
                
                this_paper = query(this_paper_sql, (tracking_number,), one=True)
                return [this_paper] if this_paper else []
            
            print(f"Revizyonlar bulundu: {len(revisions)} adet")
            
            # Tarih alanlarını düzgün formata çevir
            for revision in revisions:
                if revision.get('upload_date'):
                    try:
                        upload_date = revision['upload_date']
                        revision['upload_date_formatted'] = upload_date.strftime('%d.%m.%Y %H:%M')
                    except Exception as e:
                        print(f"upload_date formatı hatası: {e}")
                        # Eğer dönüşümde hata olursa, en azından mevcut veriyi koruyalım
                        revision['upload_date_formatted'] = str(upload_date)
                
                if revision.get('last_updated'):
                    try:
                        last_updated = revision['last_updated']
                        revision['last_updated_formatted'] = last_updated.strftime('%d.%m.%Y %H:%M')
                    except Exception as e:
                        print(f"last_updated formatı hatası: {e}")
                        # Eğer dönüşümde hata olursa, en azından mevcut veriyi koruyalım
                        revision['last_updated_formatted'] = str(last_updated)
            
            return revisions
            
        except Exception as e:
            print(f"Makale revizyonları getirme hatası: {e}")
            traceback.print_exc()
            return [] 