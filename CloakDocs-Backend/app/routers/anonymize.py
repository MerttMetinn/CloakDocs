from flask import request, send_file
from flask_restx import Namespace, Resource, fields
from app.models.paper import Paper
from app.utils.db import query
import os
import sys
import datetime
import tempfile
import shutil
from pypdf import PdfReader, PdfWriter
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
import re
import spacy
import importlib.util
from pathlib import Path
import logging
import json
from app.utils.review_processor import process_reviewed_paper, get_reviewed_paper_path
from app.routers.status import PaperStatus as PaperStatusEnum
import traceback
from app.utils.logger import log_paper_event, PaperEventType

# Yeni eklenen import - Test modülü
from app.utils.text_extractor_test import test_pdf_extraction

# Check if scispacy is installed, if not, try to install it
try:
    import scispacy
    HAVE_SCISPACY = True
    logging.info("SciSpaCy is already installed.")
except ImportError:
    HAVE_SCISPACY = False
    logging.warning("SciSpaCy is not installed. Will attempt to install it.")
    try:
        import subprocess
        logging.info("Installing SciSpaCy...")
        subprocess.run([sys.executable, "-m", "pip", "install", "scispacy"], check=True)
        
        # Try to install scientific model
        logging.info("Installing scientific NLP model...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_md-0.5.3.tar.gz"
        ], check=True)
        
        # Re-import after installation
        import scispacy
        HAVE_SCISPACY = True
        logging.info("SciSpaCy installed successfully.")
    except Exception as e:
        logging.error(f"Failed to install SciSpaCy: {str(e)}")
        HAVE_SCISPACY = False

# PyMuPDF (fitz) kütüphanesini import et (eğer yüklü değilse: pip install pymupdf)
try:
    import fitz  # PyMuPDF
    HAVE_PYMUPDF = True
except ImportError:
    HAVE_PYMUPDF = False
    logging.warning("PyMuPDF (fitz) kütüphanesi yüklü değil. Basit PDF anonimleştirme kullanılacak.")

# Gerekli NLTK paketlerini indirme
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Load the Scientific NLP model if available, otherwise fall back to standard model
try:
    if HAVE_SCISPACY:
        try:
            # Try loading the scientific model first
            nlp = spacy.load("en_core_sci_md")
            logging.info("Loaded scientific NLP model (en_core_sci_md)")
        except OSError:
            # If the specific model isn't found, try downloading it
            logging.warning("Scientific model not found, will attempt to download it...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_md-0.5.3.tar.gz"
            ], check=True)
            nlp = spacy.load("en_core_sci_md")
            logging.info("Downloaded and loaded scientific NLP model (en_core_sci_md)")
    else:
        # Fall back to standard model if SciSpaCy isn't available
        nlp = spacy.load("en_core_web_lg")  # Use large model for better entity recognition
        logging.info("Loaded standard NLP model (en_core_web_lg)")
except OSError:
    # If all else fails, use the small model which is usually available
    logging.warning("Preferred models not found. Downloading standard model...")
    import subprocess
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")
    logging.info("Loaded small standard NLP model (en_core_web_sm)")

# Özel modülleri import et
from app.utils.text_extractor import extract_text_from_pdf
from app.utils.entity_detector import detect_entities
from app.utils.anonymize_processor import anonymize_pdf, save_anonymized_file, resolve_file_path

# Namespace tanımlama
api = Namespace('anonymize', description='Anonymization operations')

# Modelleri tanımlama
anonymize_model = api.model('AnonymizeOptions', {
    'options': fields.List(fields.String, required=True, description='Anonymization options')
})

anonymize_response = api.model('AnonymizeResponse', {
    'success': fields.Boolean(description='Operation successful?'),
    'message': fields.String(description='Operation message'),
    'anonymized_file_id': fields.Integer(description='Anonymized file ID')
})

anonymized_files_response = api.model('AnonymizedFilesResponse', {
    'success': fields.Boolean(description='Operation successful?'),
    'files': fields.List(fields.Raw(description='Anonymized file information'))
})

@api.route('/process/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Paper tracking number'})
class AnonymizePaper(Resource):
    @api.expect(anonymize_model)
    @api.response(200, 'Success', anonymize_response)
    @api.response(400, 'Invalid request')
    @api.response(404, 'Paper not found')
    @api.response(500, 'Server error')
    def post(self, tracking_number):
        """
        Anonymize the paper and save the anonymized version
        """
        # Ana try-except bloğu
        try:
            # Check the paper
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'No paper found with the specified tracking number'}, 404
            
            data = request.json
            options = data.get('options', [])
            
            if not options:
                return {'error': 'At least one anonymization option must be selected'}, 400
            
            # Check valid options
            valid_options = ['author_name', 'contact_info', 'institution_info']
            if not all(opt in valid_options for opt in options):
                return {'error': 'Invalid anonymization option'}, 400
            
            # Get and resolve file path
            db_file_path = paper.get('file_path')
            file_path = resolve_file_path(db_file_path)
            
            if not file_path:
                print(f"File not found. Database path: {db_file_path}")
                return {'error': 'Paper file not found'}, 404
            
            # Log the anonymization request
            paper_id = paper.get('id')
            user_email = request.environ.get('HTTP_X_USER_EMAIL', None)  # Kullanıcı email bilgisini headerdan al
            
            log_paper_event(
                paper_id=paper_id, 
                event_type=PaperEventType.ANONYMIZED,
                event_description=f"Anonimleştirme işlemi başlatıldı - Seçenekler: {', '.join(options)}",
                user_email=user_email,
                additional_data={"options": options}
            )
            
            # Prepare folder path for anonymized file
            base_dir = os.path.dirname(file_path)
            anonymized_dir = os.path.join(base_dir, 'anonymized')
            os.makedirs(anonymized_dir, exist_ok=True)
            
            # Create anonymized filename
            original_filename = paper.get('original_filename')
            file_extension = os.path.splitext(original_filename)[1]
            anonymized_filename = f"anonymized_{tracking_number}{file_extension}"
            anonymized_path = os.path.join(anonymized_dir, anonymized_filename)
            
            try:
                # Extract text from PDF with improved section separation
                extracted_text = extract_text_from_pdf(file_path)
                main_content = extracted_text["sections"]["main_content"]
                excluded_sections = extracted_text["sections"]["excluded_sections"]
                first_page = extracted_text["sections"]["first_page"]
                header_sections = extracted_text["sections"]["header_sections"]
                full_text = extracted_text["full_text"]
                
                logging.info(f"PDF extracted. Main content: {len(main_content)} chars, First page: {len(first_page)} chars")
                logging.info(f"Excluded sections: {len(excluded_sections)} chars, Header sections: {len(header_sections)} chars")
            except Exception as extract_error:
                logging.error(f"PDF text extraction error: {str(extract_error)}")
                return {'error': f'Error extracting text from PDF: {str(extract_error)}'}, 500
                
            try:
                # Detect entities with improved context-aware approach
                entities = detect_entities(
                    main_content, 
                    options, 
                    excluded_sections,
                    first_page,
                    header_sections
                )
            except Exception as entity_error:
                logging.error(f"Entity detection error: {str(entity_error)}")
                return {'error': f'Error detecting entities in text: {str(entity_error)}'}, 500
            
            try:
                # Anonymize the PDF
                success, message = anonymize_pdf(file_path, anonymized_path, entities, excluded_sections)
                
                if not success:
                    return {'error': message}, 500
            except Exception as anon_error:
                logging.error(f"PDF anonymization error: {str(anon_error)}")
                return {'error': f'Error anonymizing PDF: {str(anon_error)}'}, 500
            
            try:
                # Save anonymized file to database
                anonymized_file_id = save_anonymized_file(paper.get('id'), anonymized_path, anonymized_filename, entities, options)
                
                if not anonymized_file_id:
                    logging.error("Failed to save anonymized file to database")
                    return {'error': 'Failed to save anonymized file to database'}, 500
                
                # Log entity counts
                entity_counts = {
                    "author_name_count": len(entities.get('author_name', [])),
                    "contact_info_count": len(entities.get('contact_info', [])),
                    "institution_info_count": len(entities.get('institution_info', []))
                }
                
                log_paper_event(
                    paper_id=paper_id,
                    event_type=PaperEventType.ANONYMIZED,
                    event_description=f"Anonimleştirme tamamlandı - Bulunan varlıklar: Yazar: {entity_counts['author_name_count']}, İletişim: {entity_counts['contact_info_count']}, Kurum: {entity_counts['institution_info_count']}",
                    user_email=user_email,
                    additional_data={
                        "entity_counts": entity_counts,
                        "anonymized_file_id": anonymized_file_id
                    }
                )
                
            except Exception as save_error:
                logging.error(f"Error saving anonymized file: {str(save_error)}")
                return {'error': f'Error saving anonymized file: {str(save_error)}'}, 500
            
            try:
                # Makale durumunu ANONYMIZED olarak güncelle
                status_anonymized = PaperStatusEnum.ANONYMIZED
                # Update paper status
                updated_paper = Paper.update_status(tracking_number, status_anonymized)
                
                if not updated_paper:
                    logging.warning(f"Failed to update paper status to ANONYMIZED for paper {tracking_number}")
                    # Durumu güncellemede başarısız olsak bile işlemi bitiriyoruz
            except Exception as status_error:
                logging.error(f"Error updating paper status: {str(status_error)}")
                # Durumu güncelleyemedik, ancak anonimleştirme başarılıydı, bu yüzden işlem başarılı
                # Durumu daha sonra elle güncellenebilir
            
            return {
                'success': True,
                'message': 'Paper successfully anonymized',
                'anonymized_file_id': anonymized_file_id
            }
            
        except Exception as e:
            logging.error(f"Anonymization error: {str(e)}")
            traceback.print_exc()  # Daha detaylı hata izleri
            return {'error': f'An error occurred while anonymizing the paper: {str(e)}'}, 500

@api.route('/download/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Paper tracking number'})
class DownloadAnonymizedPaper(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Paper or anonymized file not found')
    @api.response(500, 'Server error')
    def get(self, tracking_number):
        """
        Download anonymized paper
        """
        try:
            # Check the paper
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'No paper found with the specified tracking number'}, 404
            
            # Get anonymized file from database
            sql = """
                SELECT * FROM anonymized_files
                WHERE paper_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            result = query(sql, (paper.get('id'),), one=True)
            
            if not result:
                return {'error': 'No anonymized file found for this paper'}, 404
            
            db_file_path = result.get('file_path')
            filename = result.get('filename')
            
            # Resolve file path
            file_path = resolve_file_path(db_file_path)
            
            if not file_path:
                print(f"Anonymized file not found. Database path: {db_file_path}")
                return {'error': 'Anonymized file has been deleted from your system'}, 404
            
            # Update download count (optional)
            sql = """
                UPDATE anonymized_files
                SET download_count = download_count + 1
                WHERE id = %s
            """
            query(sql, (result.get('id'),))
            
            # Send the file
            return send_file(file_path, 
                             download_name=filename,
                             as_attachment=True,
                             mimetype='application/pdf')
            
        except Exception as e:
            logging.error(f"Anonymized file download error: {str(e)}")
            return {'error': f'An error occurred while downloading the file: {str(e)}'}, 500

@api.route('/files/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Paper tracking number'})
class AnonymizedFilesList(Resource):
    @api.response(200, 'Success', anonymized_files_response)
    @api.response(404, 'Paper not found')
    @api.response(500, 'Server error')
    def get(self, tracking_number):
        """
        List all anonymized files for a paper
        """
        try:
            # Check the paper
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'No paper found with the specified tracking number'}, 404
            
            # Get anonymized files from database
            sql = """
                SELECT * FROM anonymized_files
                WHERE paper_id = %s
                ORDER BY created_at DESC
            """
            
            results = query(sql, (paper.get('id'),))
            
            return {
                'success': True,
                'files': results
            }
            
        except Exception as e:
            logging.error(f"Anonymized file list error: {str(e)}")
            return {'error': f'An error occurred while listing anonymized files: {str(e)}'}, 500

@api.route('/stats/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Paper tracking number'})
class AnonymizationStats(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Paper or anonymized file not found')
    @api.response(500, 'Server error')
    def get(self, tracking_number):
        """
        Show paper anonymization statistics and results
        """
        try:
            # Check the paper
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'No paper found with the specified tracking number'}, 404
            
            # Get anonymized file from database
            sql = """
                SELECT id, filename, created_at, download_count, anonymization_info
                FROM anonymized_files
                WHERE paper_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            result = query(sql, (paper.get('id'),), one=True)
            
            if not result:
                return {'error': 'No anonymized file found for this paper'}, 404
            
            # Process anonymization information
            anonymization_info = {}
            
            try:
                if result.get('anonymization_info'):
                    anonymization_info = json.loads(result.get('anonymization_info'))
            except json.JSONDecodeError:
                anonymization_info = {"error": "Anonymization information is not in JSON format"}
            
            # Combine original and anonymized file information
            response = {
                'success': True,
                'paper': {
                    'id': paper.get('id'),
                    'tracking_number': tracking_number,
                    'original_filename': paper.get('original_filename'),
                    'status': paper.get('status'),
                    'upload_date': paper.get('upload_date').isoformat() if paper.get('upload_date') else None
                },
                'anonymized_file': {
                    'id': result.get('id'),
                    'filename': result.get('filename'),
                    'created_at': result.get('created_at').isoformat() if result.get('created_at') else None,
                    'download_count': result.get('download_count')
                },
                'anonymization_stats': anonymization_info
            }
            
            return response
            
        except Exception as e:
            logging.error(f"Anonymization statistics error: {str(e)}")
            return {'error': f'An error occurred while retrieving anonymization statistics: {str(e)}'}, 500

@api.route('/info/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Paper tracking number'})
class AnonymizedFileInfo(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Paper or anonymized file not found')
    @api.response(500, 'Server error')
    def get(self, tracking_number):
        """
        Get anonymized file information for a paper
        """
        try:
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Veritabanından anonimleştirilmiş dosya bilgilerini al
            sql = """
                SELECT * FROM anonymized_files
                WHERE paper_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            result = query(sql, (paper.get('id'),), one=True)
            
            if not result:
                return {'error': 'Bu makale için anonimleştirilmiş dosya bulunamadı'}, 404
            
            # Döndürülecek veriyi hazırla
            anonymized_file = {
                'id': result.get('id'),
                'filename': result.get('filename'),
                'file_path': result.get('file_path'),
                'created_at': result.get('created_at').isoformat() if result.get('created_at') else None,
                'download_count': result.get('download_count')
            }
            
            return {
                'success': True,
                'anonymized_file': anonymized_file,
                'message': 'Anonimleştirilmiş dosya bilgileri başarıyla getirildi'
            }
            
        except Exception as e:
            print(f"Anonimleştirilmiş dosya bilgisi getirme hatası: {e}")
            return {'error': f'Anonimleştirilmiş dosya bilgileri alınırken bir hata oluştu: {str(e)}'}, 500

@api.route('/merge-review/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Paper tracking number'})
class MergeReviewWithPaper(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Paper not found')
    @api.response(500, 'Server error')
    def post(self, tracking_number):
        """
        Değerlendirilmiş makalenin anonimleştirilmiş PDF'i ile review PDF'ini birleştirir.
        """
        try:
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Anonimleştirilmiş dosyayı bul
            sql = """
                SELECT * FROM anonymized_files
                WHERE paper_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            anonymized_result = query(sql, (paper.get('id'),), one=True)
            
            if not anonymized_result:
                return {'error': 'Bu makale için anonimleştirilmiş dosya bulunamadı'}, 404
            
            # Review PDF'i al
            review_pdf = request.files.get('review_pdf')
            if not review_pdf:
                return {'error': 'Review PDF dosyası bulunamadı'}, 400
            
            # Geçici dosya oluştur
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                review_pdf.save(temp_file.name)
                review_pdf_path = temp_file.name
            
            # Anonimleştirilmiş dosya yolunu çözümle
            anonymized_pdf_path = resolve_file_path(anonymized_result.get('file_path'))
            if not anonymized_pdf_path:
                return {'error': 'Anonimleştirilmiş dosya bulunamadı'}, 404
            
            # PDF'leri birleştir
            merged_pdf_path = process_reviewed_paper(
                paper.get('id'),
                anonymized_pdf_path,
                review_pdf_path
            )
            
            # Geçici dosyayı sil
            os.unlink(review_pdf_path)
            
            if merged_pdf_path:
                return {
                    'success': True,
                    'message': 'PDF\'ler başarıyla birleştirildi ve kaydedildi',
                    'file_path': merged_pdf_path
                }
            else:
                return {'error': 'PDF birleştirme işlemi başarısız oldu'}, 500
            
        except Exception as e:
            logging.error(f"PDF birleştirme hatası: {str(e)}")
            return {'error': f'PDF birleştirme işlemi sırasında bir hata oluştu: {str(e)}'}, 500

@api.route('/reviewed-paper/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Paper tracking number'})
class GetReviewedPaper(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Paper not found')
    @api.response(500, 'Server error')
    def get(self, tracking_number):
        """
        Değerlendirilmiş makalenin birleştirilmiş PDF'ini indirir.
        """
        try:
            # Makaleyi kontrol et
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'Belirtilen takip numarası ile eşleşen makale bulunamadı'}, 404
            
            # Birleştirilmiş PDF yolunu al
            reviewed_pdf_path = get_reviewed_paper_path(paper.get('id'))
            
            if not reviewed_pdf_path:
                return {'error': 'Değerlendirilmiş makale PDF\'i bulunamadı'}, 404
            
            # Dosya adını oluştur
            filename = f"reviewed_{tracking_number}.pdf"
            
            # Dosyayı gönder
            return send_file(
                reviewed_pdf_path,
                download_name=filename,
                as_attachment=True,
                mimetype='application/pdf'
            )
            
        except Exception as e:
            logging.error(f"Değerlendirilmiş makale indirme hatası: {str(e)}")
            return {'error': f'Dosya indirme işlemi sırasında bir hata oluştu: {str(e)}'}, 500

@api.route('/test-extraction/<string:tracking_number>')
@api.doc(params={'tracking_number': 'Paper tracking number'})
class TestPDFExtraction(Resource):
    @api.response(200, 'Success')
    @api.response(404, 'Paper not found')
    @api.response(500, 'Server error')
    def get(self, tracking_number):
        """
        Test PDF metin çıkarma işlemini çalıştırır ve sonuçları dosyalara kaydeder.
        Bu endpoint sadece test/geliştirme amaçlıdır.
        """
        try:
            # Check the paper
            paper = Paper.get_by_tracking_number(tracking_number)
            
            if not paper:
                return {'error': 'No paper found with the specified tracking number'}, 404
            
            # Get file path
            db_file_path = paper.get('file_path')
            file_path = resolve_file_path(db_file_path)
            
            if not file_path:
                return {'error': 'Paper file not found'}, 404
            
            # Çıktı dizinini oluştur
            output_dir = os.path.join(os.path.dirname(file_path), 'extraction_tests')
            os.makedirs(output_dir, exist_ok=True)
            
            # Metin çıkarma testini çalıştır
            success = test_pdf_extraction(file_path, output_dir)
            
            if success:
                user_email = request.environ.get('HTTP_X_USER_EMAIL', None)
                log_paper_event(
                    paper_id=paper.get('id'),
                    event_type=PaperEventType.SYSTEM_LOG,
                    event_description=f"PDF metin çıkarma testi yapıldı",
                    user_email=user_email
                )
                
                return {
                    'success': True,
                    'message': 'PDF metin çıkarma testi başarıyla tamamlandı',
                    'output_directory': output_dir
                }
            else:
                return {'error': 'PDF metin çıkarma testi başarısız oldu'}, 500
            
        except Exception as e:
            logging.error(f"PDF metin çıkarma testi hatası: {str(e)}")
            traceback.print_exc()
            return {'error': f'Test sırasında bir hata oluştu: {str(e)}'}, 500 