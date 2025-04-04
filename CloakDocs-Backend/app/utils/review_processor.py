import os
import json
import logging
import tempfile
from pypdf import PdfReader, PdfWriter
from pathlib import Path
from app.utils.db import query, execute

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def resolve_file_path(db_file_path):
    """
    Veritabanındaki dosya yolunu gerçek fiziksel dosya yoluna çevirir.
    """
    # Normalize absolute path
    db_file_path = os.path.normpath(db_file_path)
    
    # Find the root directory of the project
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Possible root directories
    base_dirs = [
        os.path.join("C:", "Projects"),
        os.path.join("C:", "Projects", "CloakDocs-Backend"),
        current_dir,
        os.path.join(current_dir, ".."),
        "/var/www/cloakdocs",
        "/opt/cloakdocs",
        ""
    ]
    
    # Try each possible path
    for base_dir in base_dirs:
        full_path = os.path.join(base_dir, db_file_path)
        normalized_path = os.path.normpath(full_path)
        if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
            return normalized_path
    
    return None

def merge_review_with_anonymized_pdf(anonymized_pdf_path, review_pdf_path, output_dir):
    """
    Anonimleştirilmiş PDF ile review PDF'i birleştirip, sonucu output_dir altında kaydeder.
    """
    try:
        # Anonimleştirilmiş PDF'i oku
        anonymized_reader = PdfReader(anonymized_pdf_path)
        # Review PDF'i oku
        review_reader = PdfReader(review_pdf_path)
        # Yeni PDF yazıcı oluştur
        writer = PdfWriter()

        # Anonimleştirilmiş PDF'in tüm sayfalarını ekle
        for page in anonymized_reader.pages:
            writer.add_page(page)
        # Review PDF'in tüm sayfalarını ekle
        for page in review_reader.pages:
            writer.add_page(page)

        # Çıktı dosya adını oluştur (anonymized dosya adına 'reviewed_' ekle)
        anonymized_filename = os.path.basename(anonymized_pdf_path)
        output_filename = f"reviewed_{anonymized_filename}"
        output_path = os.path.join(output_dir, output_filename)

        # Birleştirilmiş PDF'i kaydet
        with open(output_path, "wb") as output_file:
            writer.write(output_file)

        logging.info(f"Birleştirilmiş PDF kaydedildi: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"PDF birleştirme hatası: {str(e)}")
        return None

def process_reviewed_paper(paper_id, anonymized_pdf_path, review_pdf_path):
    """
    Hakem değerlendirmesini ve anonimleştirilmiş makaleyi birleştiren fonksiyon
    """
    try:
        # PaperStatus'ü sadece bu fonksiyon içinde import et
        from app.routers.status import PaperStatus as PaperStatusEnum
        
        # Anonimleştirilmiş PDF dosyasının yolundan yazar klasörünü belirleme
        anonymized_dir = os.path.dirname(anonymized_pdf_path)  # .../yazar_klasoru/anonymized
        author_dir = os.path.dirname(anonymized_dir)  # .../yazar_klasoru
        
        # Çıktı klasörü yolu - değişiklik burada
        output_dir = os.path.join(author_dir, "anonymized_reviewed")
        os.makedirs(output_dir, exist_ok=True)

        # PDF'leri birleştir
        merged_pdf_path = merge_review_with_anonymized_pdf(anonymized_pdf_path, review_pdf_path, output_dir)
        if merged_pdf_path:
            logging.info(f"Değerlendirilmiş makale PDF'i kaydedildi: {merged_pdf_path}")
            
            # Veritabanına kaydet
            relative_path = os.path.relpath(merged_pdf_path, "uploads")
            sql = """
                UPDATE reviews 
                SET review_file_path = %s 
                WHERE paper_id = %s 
                AND review_file_path IS NULL
            """
            query(sql, (relative_path, paper_id))
            
            # Makalenin durumunu REVIEWED olarak güncelle
            update_status_sql = """
                UPDATE papers 
                SET status = %s 
                WHERE id = %s
            """
            execute(update_status_sql, (PaperStatusEnum.REVIEWED, paper_id))
            
            return merged_pdf_path
        else:
            logging.error("PDF birleştirme işlemi başarısız oldu.")
            return None
    except Exception as e:
        logging.error(f"Error while processing reviewed paper: {str(e)}")
        return None

def get_reviewed_paper_path(paper_id):
    """
    Değerlendirilmiş makalenin PDF yolunu veritabanından alır.
    """
    try:
        sql = """
            SELECT review_file_path 
            FROM reviews 
            WHERE paper_id = %s 
            AND review_file_path IS NOT NULL 
            ORDER BY created_at DESC 
            LIMIT 1
        """
        result = query(sql, (paper_id,), one=True)
        
        if result and result.get('review_file_path'):
            return resolve_file_path(os.path.join("uploads", result['review_file_path']))
        return None
    except Exception as e:
        logging.error(f"Değerlendirilmiş makale yolu alma hatası: {str(e)}")
        return None

if __name__ == "__main__":
    # Test için örnek kullanım
    paper_id = 1
    anonymized_pdf_path = r"C:\Projects\CloakDocs-Backend\uploads\papers\2025-03\akademikmakaledegerlendirmesir_at_gmail_dot_com\anonymized\anonymized_TR-2503272252-69E3252C.pdf"
    review_pdf_path = "path/to/review.pdf"  # ReviewPdfGenerator.tsx ile oluşturulan PDF yolu
    result = process_reviewed_paper(paper_id, anonymized_pdf_path, review_pdf_path)
    if result:
        print(f"İşlem başarılı: {result}")
        print(f"Beklenen yeni konum: {os.path.join(os.path.dirname(os.path.dirname(anonymized_pdf_path)), 'anonymized_reviewed')}")
    else:
        print("İşlem başarısız.") 