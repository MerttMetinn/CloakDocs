import os
import logging
import json
import datetime
import tempfile
import shutil
from pypdf import PdfReader, PdfWriter
import re
from pathlib import Path
import logging
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

# PyMuPDF (fitz) kütüphanesini import et
try:
    import fitz  # PyMuPDF
    HAVE_PYMUPDF = True
except ImportError:
    HAVE_PYMUPDF = False
    logging.warning("PyMuPDF (fitz) kütüphanesi yüklü değil. Basit PDF anonimleştirme kullanılacak.")

# Dikdörtgen alanı hash'e çeviren yardımcı fonksiyon
def rect_hash(rect):
    # Koordinatları yuvarlayarak aynı alanları yakala
    return tuple(round(v, 1) for v in [rect.x0, rect.y0, rect.x1, rect.y1])

# RSA anahtar çifti oluşturma
def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    public_key = private_key.public_key()
    
    return private_key, public_key

# RSA ile şifreleme
def encrypt_with_rsa(text, public_key):
    if not text:
        return ""
    
    # Özel karakterleri (örn: \n) işle
    # Satır sonu karakterlerini normalize et
    normalized_text = text.replace("\n", " ")
    
    # Metni byte dizisine dönüştür
    text_bytes = normalized_text.encode('utf-8')
    
    # RSA şifrelemesi (büyük metinler için parçalı şifreleme)
    chunk_size = 190  # RSA-2048 için maksimum şifrelenebilir boyut
    encrypted_chunks = []
    
    for i in range(0, len(text_bytes), chunk_size):
        chunk = text_bytes[i:i + chunk_size]
        encrypted_chunk = public_key.encrypt(
            chunk,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encrypted_chunks.append(encrypted_chunk)
    
    # Şifrelenmiş veriyi birleştir ve base64 kodla
    concatenated = b''.join(encrypted_chunks)
    encoded = base64.b64encode(concatenated).decode('utf-8')
    
    return encoded

# RSA anahtarlarını diske kaydetme (opsiyonel)
def save_rsa_keys(private_key, public_key, private_key_path="private_key.pem", public_key_path="public_key.pem"):
    # Özel anahtarı PEM formatında kaydet
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Genel anahtarı PEM formatında kaydet
    with open(public_key_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

# RSA anahtarlarını diskten yükleme (opsiyonel)
def load_rsa_keys(private_key_path="private_key.pem", public_key_path="public_key.pem"):
    # Özel anahtarı yükle
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None
        )
    
    # Genel anahtarı yükle
    with open(public_key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(
            f.read()
        )
    
    return private_key, public_key

def anonymize_pdf(input_path, output_path, entities, excluded_text=""):
    """
    Anonymize PDF file
    Mask detected entities in the PDF
    excluded_text: Text in excluded sections
    """
    try:
        # Başlığı tespit et (ilk sayfadaki en büyük fontlu yazı)
        title_text = ""
        title_font_size = 0
        
        if HAVE_PYMUPDF:
            try:
                doc_check = fitz.open(input_path)
                # Sadece ilk sayfada başlık kontrolü yap
                if len(doc_check) > 0:
                    first_page = doc_check[0]
                    # Sayfa metnini yapılandırılmış şekilde al
                    blocks = first_page.get_text("dict")["blocks"]
                    
                    # Her metin bloğunu kontrol et
                    for block in blocks:
                        if "lines" in block:
                            for line in block["lines"]:
                                if "spans" in line:
                                    for span in line["spans"]:
                                        # Font boyutu kontrolü
                                        curr_size = span.get("size", 0)
                                        curr_text = span.get("text", "").strip()
                                        
                                        # Boş metin ya da tek karakter değilse ve font boyutu büyükse
                                        if len(curr_text) > 5 and curr_size > title_font_size:
                                            title_font_size = curr_size
                                            title_text = curr_text
                                            
                                        # İlk sayfadaki en büyük 3 font boyutunu takip et
                                        # ve benzer font boyutundaki metinleri birleştir
                                        elif curr_size > title_font_size * 0.95 and curr_size <= title_font_size * 1.05 and len(curr_text) > 1:
                                            title_text += " " + curr_text
                
                # Eğer başlık varsa, log kaydı oluştur
                if title_text:
                    title_text = title_text.strip()
                    logging.info(f"Tespit edilen makale başlığı (font: {title_font_size}): {title_text}")
                
                doc_check.close()
            except Exception as e:
                logging.warning(f"Başlık tespiti sırasında hata: {str(e)}")
        
        # Prepare detected entities for masking
        replacements = {}
        
        # Öncelik sırasıyla kategorileri tanımla - bu sıra önemli!
        # Bir metin birden fazla kategoriye uyuyorsa, öncelik sırasına göre sadece ilk kategori için maskeleme yapılacak
        priority_order = ['author_name', 'contact_info', 'institution_info']
        
        # Metin ön işleme: Satır sonlarını temizle ve normalleştir
        normalized_entities = {
            'author_name': [],
            'contact_info': [],
            'institution_info': []
        }
        
        # Tüm metinleri normalleştir
        for category in priority_order:
            for entity in entities[category]:
                # Satır sonu karakterlerini boşluğa dönüştür
                normalized_entity = entity.replace("\n", " ").strip()
                
                # Başlık içinde geçen metinleri maskeleme
                if title_text and (normalized_entity in title_text or title_text in normalized_entity):
                    logging.info(f"'{normalized_entity}' başlık içinde tespit edildi, maskelenmeyecek")
                    continue
                    
                if normalized_entity:  # Boş string kontrolü
                    normalized_entities[category].append(normalized_entity)
        
        # Çakışan metinleri tespit et ve benzer metinleri filtrele
        filtered_entities = {
            'author_name': [],
            'contact_info': [],
            'institution_info': []
        }
        
        # Alt metinleri kontrol eden fonksiyon
        def is_substring_of_any(text, text_list):
            """Bir metnin diğer metinlerin alt metni (substring) olup olmadığını kontrol eder"""
            for other_text in text_list:
                # Eğer bu metin, diğer metnin içinde yer alıyorsa
                if text != other_text and text in other_text:
                    return True
            return False
        
        # Her kategori için benzer ve alt metinleri filtrele
        for category in priority_order:
            # Önce tüm metinleri uzunluğuna göre büyükten küçüğe sırala
            sorted_entities = sorted(normalized_entities[category], key=len, reverse=True)
            
            category_entities = []  # Bu kategorideki filtrelenmiş metinler
            
            for entity in sorted_entities:
                # Minimum karakter uzunluğu kontrolü (çok kısa metinleri atla)
                if len(entity) < 4:
                    continue
                
                # Eğer bu metin, zaten seçilmiş daha uzun bir metnin alt metni değilse ekle
                if not is_substring_of_any(entity, category_entities):
                    category_entities.append(entity)
            
            filtered_entities[category] = category_entities
        
        # Çakışan metinleri tespit et
        all_entities = set()
        entity_category = {}  # Her bir metni hangi kategoride işleyeceğimizi takip eder
        
        # Her bir kategoriyi öncelik sırasına göre işle
        for category in priority_order:
            for entity in filtered_entities[category]:
                # Eğer bu metin daha önce işlenmediyse, bu kategori ile işaretle
                if entity not in all_entities:
                    all_entities.add(entity)
                    entity_category[entity] = category
        
        # Maskeleme işlemini her metin için sadece bir kez yap
        entity_count = {
            'author_name': 0,
            'contact_info': 0,
            'institution_info': 0
        }
        
        # Her metni uygun maskeleme ile işle
        for entity, category in entity_category.items():
            count = entity_count[category]
            if category == 'author_name':
                replacements[entity] = f"[YAZAR-{count+1}]"
            elif category == 'contact_info':
                replacements[entity] = f"[ILETISIM-{count+1}]"
            elif category == 'institution_info':
                replacements[entity] = f"[KURUM-{count+1}]"
            entity_count[category] += 1
        
        # Loglama için orijinal tespit sayılarını kaydet
        original_counts = {
            'author_name': len(entities['author_name']),
            'contact_info': len(entities['contact_info']),
            'institution_info': len(entities['institution_info'])
        }
        
        # Nihai olarak işlenen tespit sayılarını kaydet
        final_counts = {
            'author_name': entity_count['author_name'],
            'contact_info': entity_count['contact_info'],
            'institution_info': entity_count['institution_info']
        }
        
        # Çakışmaları logla
        if sum(original_counts.values()) != sum(final_counts.values()):
            logging.info(f"Tespit edilen metin çakışması: {sum(original_counts.values()) - sum(final_counts.values())} metin birden fazla kategoride tespit edilmiş")
            logging.info(f"Orijinal tespitler: {original_counts}")
            logging.info(f"Çakışmalar çözüldükten sonraki tespitler: {final_counts}")

        # Advanced PDF processing using PyMuPDF
        if HAVE_PYMUPDF:
            logging.info("PyMuPDF kullanılarak gelişmiş PDF anonimleştirmesi yapılıyor...")
            
            # Open the PDF file
            doc = fitz.open(input_path)
            
            # Total replacement count
            total_replacements = {
                'author_name': 0,
                'contact_info': 0,
                'institution_info': 0
            }
            
            # For identifying excluded sections
            current_section_is_excluded = False
            excluded_section_patterns = [
                r"(?i)INTRODUCTION",
                r"(?i)RELATED\s+WORKS?",
                r"(?i)REFERENCES",
                r"(?i)BIBLIOGRAPHY",
                r"(?i)ACKNOWLEDGEMENTS?",
                r"(?i)CITED\s+REFERENCES"
            ]
            
            # Özellikle referanslar bölümünü tespit edecek daha kapsamlı desenler
            reference_section_patterns = [
                r"(?i)^\s*REFERENCES\s*$",
                r"(?i)^\s*BIBLIOGRAPHY\s*$",
                r"(?i)^\s*CITED\s+REFERENCES\s*$",
                r"(?i)^\s*REFERANSLAR\s*$",
                r"(?i)^\s*KAYNAKLAR\s*$",
                r"(?i)^\s*KAYNAKÇA\s*$",
                r"(?i)^\s*REFERENCES\s+AND\s+CITATIONS\s*$"
            ]
            
            # IEEE formatı yazar biyografilerini tespit etmek için göstergeler
            ieee_biography_indicators = [
                r"received the .+ degree",
                r"was born in",
                r"is currently pursuing",
                r"is currently a Research Scholar",
                r"is currently a Professor",
                r"is currently an Assistant Professor",
                r"is currently an Associate Professor",
                r"received the Ph\.D",
                r"research interests include",
                r"^[A-Z]{2,}(?:\s+[A-Z]{2,}){1,}\s*\(",
                r"^[A-Z]{2,}(?:\s+[A-Z]{2,}){1,}\s*received",
                # Yeni önerilen anahtar ifadeler
                r"[Hh]is research interests are",
                r"[Hh]er interests include",
                r"[Hh]e is currently working on",
                r"[Ss]he has authored over",
                r"[Hh]e has published more than",
                r"[Hh]e was with",
                r"[Ss]he was with",
                r"[Hh]e is affiliated with",
                r"[Ss]he is affiliated with",
                r"[Hh]e received his",
                r"[Ss]he received her",
                r"[Hh]e joined the",
                r"[Ss]he joined the",
                r"\b[A-Z][a-z]+ [A-Z][a-z]+\b.*received the .* degree",
                r"has been a member of",
                r"has been an? (IEEE|Associate|Senior) member",
                r"has published (more than|over|about|approximately) \d+",
                r"has co-authored (more than|over|about|approximately) \d+",
                r"has served as an? (editor|reviewer|chair|co-chair)"
            ]
            
            # Biyografi paragrafı analizinde gerekli minimum sayıda gösterge
            min_biography_indicators = 1
            
            # REFERENCES bölümü bulundu mu?
            references_section_found = False
            
            # Sansürlenen yazar biyografi sayacı
            biography_counter = 0
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Redactions to apply later
                redactions = []
                
                # Maskelenen pozisyonları takip etmek için küme - SAYFA BAŞINDA TANIMLA
                masked_positions = set()
                
                # Get all text on the page
                text = page.get_text()
                
                # Sadece PDF'nin son sayfasında biyografi tespiti ve sansürleme işlemi yap
                is_biography_page = False
                
                # Şu anki sayfanın, son sayfa olup olmadığını kontrol et
                is_last_page = (page_num == len(doc) - 1)
                
                if is_last_page:
                    # IEEE formatı biyografi tespiti - büyük harfli isimle başlayan paragrafları kontrol et
                    biography_indicators_found = 0
                    for indicator in ieee_biography_indicators:
                        if re.search(indicator, text, re.MULTILINE | re.IGNORECASE):
                            biography_indicators_found += 1
                        
                    # IEEE biyografi sayfası tespiti
                    is_biography_page = False
                    
                    # Metinde büyük harfle yazılmış yazar adlarını ara (IEEE biyografi stili)
                    caps_names_matches = re.findall(r"^([A-Z]{2,}(?:\s+[A-Z]{2,})+)", text, re.MULTILINE)
                    
                    # Alternatif Ad-Soyad tespiti (büyük harfle başlayan, boşlukla ayrılmış iki veya daha fazla kelime)
                    name_format_matches = re.findall(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,})", text, re.MULTILINE)
                    
                    # Eğer sayfada en az 2 büyük harfli isim bulunursa ve en az 1 biyografi göstergesi varsa
                    if (len(caps_names_matches) >= 2 or len(name_format_matches) >= 2) and biography_indicators_found >= min_biography_indicators:
                        is_biography_page = True
                        logging.info(f"Son sayfa (sayfa {page_num+1})'de IEEE formatı yazar biyografi sayfası tespit edildi ({len(caps_names_matches)} büyük isim, {len(name_format_matches)} normal isim, {biography_indicators_found} gösterge)")
                    
                    # "VOLUME X, YYYY NNNNN" formatını içeren sayfalar genellikle IEEE makalelerinin son sayfasıdır
                    if re.search(r"VOLUME\s+\d+,\s+\d{4}\s+\d+", text):
                        if biography_indicators_found >= min_biography_indicators:
                            is_biography_page = True
                            logging.info(f"Son sayfa (sayfa {page_num+1})'de IEEE formatı dergi bilgili son sayfa tespit edildi, biyografi içeriyor")
                    
                    # Metin yapısı analizi yaparak alternatif paragraf tespiti
                    # Paragrafları ayır (iki newline veya satır aralığına göre)
                    if not is_biography_page:  # Eğer daha önce tespit edilmediyse paragraf analizi yap
                        paragraphs = re.split(r'\n\s*\n', text)
                        for para_idx, paragraph in enumerate(paragraphs):
                            # 100+ karakter içeriyor mu?
                            if len(paragraph.strip()) < 100:
                                continue
                                
                            # Anahtar kelimelerden en az 2'sini içeriyor mu?
                            indicator_count = 0
                            for indicator in ieee_biography_indicators:
                                if re.search(indicator, paragraph, re.IGNORECASE):
                                    indicator_count += 1
                                    if indicator_count >= 2:
                                        break
                            
                            # Büyük harfli isim içeriyor mu?
                            has_name = (
                                re.search(r"^[A-Z]{2,}(?:\s+[A-Z]{2,})+", paragraph, re.MULTILINE) or 
                                re.search(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,}", paragraph, re.MULTILINE)
                            )
                            
                            # Eğer anahtar kelime ve isim kriterleri karşılanıyorsa, bu bir biyografi olabilir
                            if has_name and indicator_count >= 2 and not is_biography_page:
                                is_biography_page = True
                                logging.info(f"Son sayfa (sayfa {page_num+1})'de metin yapısı analizi ile biyografi sayfası tespit edildi")
                                break
                    
                    # Tam biyografi paragraflarını tespit et ve direkt sansürle
                    if is_biography_page:
                        # IEEE formatında yazar biyografilerini paragraf şeklinde tespit et
                        biography_paragraphs = []
                        
                        # Tüm isim formatlarını birleştir
                        all_names = caps_names_matches + name_format_matches
                        
                        # Büyük harfli isimle başlayan paragrafları bul
                        for name in all_names:
                            # İsmin pozisyonlarını bul
                            name_positions = [m.start() for m in re.finditer(re.escape(name), text)]
                            
                            for start_pos in name_positions:
                                # İsimden sonraki metni kontrol et (paragrafın geri kalanı)
                                paragraph_text = text[start_pos:]
                                
                                # Paragraf sonu - sonraki büyük harfli isim, boş satır veya sayfa sonu
                                end_match = re.search(r"\n\s*\n|\n[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+|\Z", paragraph_text)
                                
                                if end_match:
                                    end_pos = end_match.start()
                                    # Tam paragraf
                                    full_paragraph = paragraph_text[:end_pos].strip()
                                    
                                    # Biyografi göstergelerini kontrol et
                                    is_biography = False
                                    indicator_count = 0
                                    for indicator in ieee_biography_indicators:
                                        if re.search(indicator, full_paragraph, re.IGNORECASE):
                                            indicator_count += 1
                                            is_biography = True
                                            if indicator_count >= 2:
                                                break
                                    
                                    # Eğer gösterge varsa ve yeterince uzunsa biyografi olarak kabul et
                                    if is_biography and len(full_paragraph) > 75:  # Min uzunluk kontrolü
                                        biography_paragraphs.append((start_pos, start_pos + end_pos, full_paragraph))
                        
                        # Tespit edilen biyografi paragraflarını sansürle
                        for start_pos, end_pos, paragraph in biography_paragraphs:
                            logging.info(f"Son sayfada yazar biyografi paragrafı tespit edildi: {paragraph[:50]}...")
                            
                            # Paragraf sansürleme stratejisi:
                            # 1. Önce sayfanın blok yapısını alarak daha doğru konum tespiti yapalım
                            blocks = page.get_text("dict")["blocks"]
                            paragraph_blocks = []
                            
                            # Paragrafa ait blokları bul
                            for block in blocks:
                                if "lines" in block:
                                    block_text = ""
                                    for line in block["lines"]:
                                        if "spans" in line:
                                            for span in line["spans"]:
                                                block_text += span.get("text", "")
                                    
                                    # Eğer blok metni paragrafın bir parçasını içeriyorsa
                                    # veya paragraf bloğun bir parçasını içeriyorsa, bu bloğu işaretle
                                    if (block_text in paragraph) or any(
                                        phrase in block_text 
                                        for phrase in re.findall(r".{20,}", paragraph) 
                                        if len(phrase) > 20
                                    ):
                                        paragraph_blocks.append(block)
                            
                            # Eğer blok yapısından bulduysak, bu bloklara dayalı bir dikdörtgen oluştur
                            if paragraph_blocks:
                                # Dikdörtgenleri birleştir
                                paragraph_rect = fitz.Rect(paragraph_blocks[0]["bbox"])
                                for block in paragraph_blocks[1:]:
                                    paragraph_rect = paragraph_rect.include_rect(fitz.Rect(block["bbox"]))
                                
                                # Sınırları biraz genişlet
                                paragraph_rect.x0 = max(0, paragraph_rect.x0 - 5)
                                paragraph_rect.y0 = max(0, paragraph_rect.y0 - 5)
                                paragraph_rect.x1 = min(page.rect.width, paragraph_rect.x1 + 5)
                                paragraph_rect.y1 = min(page.rect.height, paragraph_rect.y1 + 5)
                                
                                # Sayacı artır
                                biography_counter += 1
                                
                                # Sansürleme işlemini bu genişletilmiş dikdörtgen üzerinde uygulayalım
                                redact_annot = page.add_redact_annot(
                                    paragraph_rect,
                                    text=f"***** [YAZAR BİYOGRAFİSİ {biography_counter} SANSÜRLENDI] *****",
                                    fontsize=9,
                                    fontname="helv",
                                    text_color=(0, 0, 0),  # Siyah metin
                                    fill=(1, 1, 1)  # Beyaz dolgu
                                )
                                
                                # Bu bölgeyi işaretleyelim ki tekrar işlemeyelim
                                masked_positions.add(rect_hash(paragraph_rect))
                                
                                # Redaksiyon listesine ekle
                                redactions.append(redact_annot)
                                
                                # Yazar biyografi sansürlemesini sayıya ekle
                                total_replacements['author_name'] += 1
                                
                                logging.info(f"Son sayfada yazar biyografisi {biography_counter} blok yapısı kullanılarak sansürlendi.")
                                continue  # Bu paragraf için diğer yöntemleri denemeye gerek yok
                            
                            # 2. Eğer blok yapısı başarısız olursa, metin parçalarını ara
                            paragraph_rects = []
                            # Uzun paragrafları parçalara ayırarak işle (aramada sınırlar var)
                            for i in range(0, len(paragraph), 50):
                                chunk = paragraph[i:i+50]
                                if len(chunk) > 10:  # Çok kısa parçaları atla
                                    chunk_instances = page.search_for(chunk)
                                    paragraph_rects.extend(chunk_instances)
                            
                            if paragraph_rects:
                                # Tüm dikdörtgenleri birleştir
                                combined_rect = paragraph_rects[0]
                                for rect in paragraph_rects[1:]:
                                    combined_rect = combined_rect.include_rect(rect)
                                
                                # Sınırları biraz genişlet
                                combined_rect.x0 = max(0, combined_rect.x0 - 5)
                                combined_rect.y0 = max(0, combined_rect.y0 - 5)
                                combined_rect.x1 = min(page.rect.width, combined_rect.x1 + 5)
                                combined_rect.y1 = min(page.rect.height, combined_rect.y1 + 5)
                                
                                # Sayacı artır
                                biography_counter += 1
                                
                                # Tüm paragrafı sansürle
                                redact_annot = page.add_redact_annot(
                                    combined_rect,
                                    text=f"***** [YAZAR BİYOGRAFİSİ {biography_counter} SANSÜRLENDI] *****",
                                    fontsize=9,
                                    fontname="helv",
                                    text_color=(0, 0, 0),  # Siyah metin
                                    fill=(1, 1, 1)  # Beyaz dolgu
                                )
                                
                                # Pozisyonu işaretleyerek diğer maskeleme işlemlerinin bu alanı tekrar işlememesini sağla
                                for rect in paragraph_rects:
                                    masked_positions.add(rect_hash(rect))
                                
                                # Redaksiyon listesine ekle
                                redactions.append(redact_annot)
                                
                                # Yazar biyografi sansürlemesini sayıya ekle
                                total_replacements['author_name'] += 1
                                
                                logging.info(f"Son sayfada yazar biyografisi {biography_counter} tam paragraf olarak sansürlendi.")
                            else:
                                # 3. Eğer doğrudan arama başarısız olursa daha hassas bir yaklaşım deneyin
                                # Paragrafı belli anahtar bölümlere ayırıp konum tespiti yapalım
                                key_phrases = []
                                
                                # Paragrafı 20-30 karakterlik anahtar ifadelere bölelim
                                phrase_length = 25
                                for j in range(0, len(paragraph), phrase_length):
                                    if j + phrase_length < len(paragraph):
                                        key_phrases.append(paragraph[j:j+phrase_length])
                                
                                # İlk ve son bölümleri kesinlikle alalım
                                if len(paragraph) > phrase_length:
                                    if paragraph[:phrase_length] not in key_phrases:
                                        key_phrases.append(paragraph[:phrase_length])
                                    if paragraph[-phrase_length:] not in key_phrases:
                                        key_phrases.append(paragraph[-phrase_length:])
                                
                                # İsim içeren bölümü mutlaka ekleyelim (daha hassas tespit için)
                                name_index = paragraph.find(name)
                                if name_index >= 0:
                                    name_phrase = paragraph[name_index:min(name_index + len(name) + 20, len(paragraph))]
                                    if name_phrase not in key_phrases:
                                        key_phrases.append(name_phrase)
                                
                                # Anahtar ifadelerin konumlarını bulalım
                                phrase_rects = []
                                for phrase in key_phrases:
                                    if len(phrase) > 10:  # Çok kısa ifadeleri atla
                                        found_rects = page.search_for(phrase)
                                        phrase_rects.extend(found_rects)
                                
                                if phrase_rects:
                                    # Dikdörtgenleri birleştir
                                    phrase_combined_rect = phrase_rects[0]
                                    for rect in phrase_rects[1:]:
                                        phrase_combined_rect = phrase_combined_rect.include_rect(rect)
                                    
                                    # Bulduğumuz tüm içeriği kapsayan bir dikdörtgen oluşturalım
                                    # Biraz daha genişletilmiş bir dikdörtgen oluşturalım (kenarlardan biraz pay bırakarak)
                                    extended_rect = fitz.Rect(
                                        max(0, phrase_combined_rect.x0 - 5),
                                        max(0, phrase_combined_rect.y0 - 5),
                                        min(page.rect.width, phrase_combined_rect.x1 + 5),
                                        min(page.rect.height, phrase_combined_rect.y1 + 5)
                                    )
                                    
                                    # Sayacı artır
                                    biography_counter += 1
                                    
                                    # Sansürleme işlemini bu genişletilmiş dikdörtgen üzerinde uygulayalım
                                    redact_annot = page.add_redact_annot(
                                        extended_rect,
                                        text=f"***** [YAZAR BIYOGRAFI {biography_counter} SANSURLENDI] *****",
                                        fontsize=9, 
                                        fontname="helv",
                                        text_color=(0, 0, 0),
                                        fill=(1, 1, 1)
                                    )
                                    
                                    # Bu bölgeyi işaretleyelim ki tekrar işlemeyelim
                                    for rect in phrase_rects:
                                        masked_positions.add(rect_hash(rect))
                                    
                                    # Redaksiyon listesine ekle
                                    redactions.append(redact_annot)
                                    
                                    # Sayacı artır
                                    total_replacements['author_name'] += 1
                                    
                                    logging.info(f"Son sayfada yazar biyografisi {biography_counter} hassas yöntemle sansürlendi.")
                
                # Referans bölümünü doğrudan kontrol et
                for pattern in reference_section_patterns:
                    if re.search(pattern, text, re.MULTILINE):
                        current_section_is_excluded = True
                        references_section_found = True
                        logging.info(f"Sayfa {page_num+1}'de referans bölümü tespit edildi, anonimleştirme yapılmayacak")
                        break
                
                # Eğer bu sayfada referans bölümünde olduğumuzu tespit ettiysek, bu sayfayı işlemeye gerek yok
                if references_section_found and not is_biography_page:
                    continue
                
                # Check if this page is in an excluded section
                # Find section headers
                section_headers = re.findall(r"(?i)^\s*(?:\d+\.)*\s*([A-Za-z\s]+)$", text, re.MULTILINE)
                
                for header in section_headers:
                    header = header.strip().upper()
                    # Is this a reference section header?
                    is_reference_section = False
                    for pattern in reference_section_patterns:
                        if re.search(pattern, header, re.IGNORECASE):
                            current_section_is_excluded = True
                            references_section_found = True
                            is_reference_section = True
                            break
                    
                    if is_reference_section:
                        logging.info(f"Sayfa {page_num+1}'de '{header}' başlığında referans bölümü tespit edildi")
                        break
                    
                    # Is this header an excluded section?
                    for pattern in excluded_section_patterns:
                        if re.search(pattern, header):
                            current_section_is_excluded = True
                            break
                    else:
                        # If not an excluded section header, it might be a normal section header
                        # If this is a "normal" section header, we're no longer in an excluded section
                        if len(header) > 3 and header not in ["TABLE", "FIGURE"]:
                            current_section_is_excluded = False
                
                # If this page is in an excluded section, skip processing
                if current_section_is_excluded and not is_biography_page:
                    logging.info(f"Sayfa {page_num+1} hariç tutulan bir bölümde, anonimleştirme atlanıyor")
                    continue
                
                # Redaksiyon listesini sayfa başında boş olarak tanımladığımız için burada tekrar tanımlama
                # redactions = []
                
                # masked_positions değişkenini sayfa başında tanımladığımız için burada tekrar tanımlama
                # masked_positions = set()
                
                # Bütün maskeleme işlemlerini bir seferde yap
                for original, replacement in replacements.items():
                    # Skip very short texts as they could match common words
                    if len(original) < 4:
                        continue
                        
                    # Eğer bu metin başlık ise ya da başlık içinde geçiyorsa atla
                    if title_text and (original in title_text or title_text in original):
                        continue
                        
                    # Search in the page
                    try:
                        # Tüm metni bul
                        text_instances = page.search_for(original)
                        
                        # Mask each found text instance
                        for inst in text_instances:
                            # Metni alarak başlık kontrolü yap
                            text_at_pos = page.get_text("text", clip=inst).strip()
                            if title_text and text_at_pos and (text_at_pos in title_text or title_text in text_at_pos):
                                logging.debug(f"Bu metin başlık içinde olduğu için maskelenmedi: {text_at_pos}")
                                continue
                                
                            # Aynı pozisyonda maskeleme yapılmışsa atla
                            inst_hash = rect_hash(inst)
                            if inst_hash in masked_positions:
                                logging.debug(f"Bu pozisyonda zaten maskeleme yapılmış, atlıyorum: {original}")
                                continue
                                
                            # Pozisyonu işlenmiş olarak işaretle
                            masked_positions.add(inst_hash)
                            
                            # Check if this text segment is in an excluded section (extra safety)
                            context_rect = fitz.Rect(inst)
                            context_rect.y0 = max(0, context_rect.y0 - 100)  # Get some text above
                            context_rect.y1 = min(context_rect.y1 + 100, page.rect.height)  # Get some text below
                            context_text = page.get_text("text", clip=context_rect)
                            
                            # Is there an excluded section heading around this text segment?
                            skip_this_instance = False
                            for pattern in excluded_section_patterns:
                                if re.search(pattern, context_text, re.IGNORECASE):
                                    skip_this_instance = True
                                    break
                            
                            if skip_this_instance:
                                continue
                            
                            # Orijinal metin alanından font bilgisi al
                            # Dikdörtgen alanı genişlet (metnin tamamını kapsaması için)
                            text_span = page.get_text("dict", clip=inst)
                            
                            # Varsayılan font boyutu (eğer okunamazsa)
                            font_size = 9
                            font_color = (0, 0, 0)  # Siyah
                            
                            # Metin dikdörtgeninden font bilgisini çıkar
                            if "blocks" in text_span and len(text_span["blocks"]) > 0:
                                for block in text_span["blocks"]:
                                    if "lines" in block and len(block["lines"]) > 0:
                                        for line in block["lines"]:
                                            if "spans" in line and len(line["spans"]) > 0:
                                                for span in line["spans"]:
                                                    if "size" in span:
                                                        # Mevcut font boyutunu al
                                                        font_size = span["size"]
                                                    if "color" in span:
                                                        # Mevcut rengi al
                                                        font_color = span["color"]
                                                    # İlk bulunan font bilgisini kullan
                                                    break
                            
                            # YENİ ÇÖZÜM: Redaksiyon işlemini KAYDET (henüz uygulamadan)
                            # Text replacement kısmını bir sözlük olarak saklayıp DAHA SONRA uygulayacağız
                            redact_annot = page.add_redact_annot(
                                inst,
                                text=replacement,  # Değiştirme metni (YAZAR-1, vb.)
                                fontsize=max(6, min(font_size, 9) * 0.85),  # Daha küçük font boyutu
                                fontname="helv",
                                text_color=font_color,
                                fill=(1, 1, 1)  # Beyaz dolgu
                            )
                            
                            # Redaksiyon listesine ekle
                            redactions.append(redact_annot)
                            
                            # Hangi kategoride olduğunu belirle ve sayacı artır
                            for category in priority_order:
                                if original in entities[category]:
                                    total_replacements[category] += 1
                                    break
                    except Exception as e:
                        logging.warning(f"'{original}' öğesini işlerken hata oluştu: {str(e)}")
                
                # TÜM sayfa redaksiyonlarını bir seferde uygula
                page.apply_redactions()
            
            # Save changes
            doc.save(output_path)
            doc.close()
            
            logging.info(f"PDF anonimleştirildi: {sum(total_replacements.values())} toplam değişiklik yapıldı")
            for entity_type, count in total_replacements.items():
                logging.info(f"  - {entity_type}: {count} değişiklik")
            
        else:
            # If PyMuPDF is not available, use basic PyPDF
            logging.info("Temel PDF işleme kullanılıyor (PyMuPDF mevcut değil)...")
            
            # PDF reading process
            reader = PdfReader(input_path)
            writer = PdfWriter()
            
            # Process and copy each page
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                writer.add_page(page)
            
            # Write the result file
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            logging.warning("PyMuPDF yüklü olmadığı için gerçek anonimleştirme yapılamadı. " +
                          "Sadece dosyanın bir kopyası oluşturuldu.")
        
        # Create success message
        success_message = (
            f"PDF başarıyla anonimleştirildi.\n"
            f"Orijinal tespitler - Yazar İsimleri: {original_counts['author_name']}, İletişim Bilgileri: {original_counts['contact_info']}, Kurum Bilgileri: {original_counts['institution_info']}\n"
            f"Çakışmalar çözüldükten sonra - Yazar İsimleri: {final_counts['author_name']}, İletişim Bilgileri: {final_counts['contact_info']}, Kurum Bilgileri: {final_counts['institution_info']}\n"
            f"Maskelen metinler - Yazar İsimleri: {total_replacements['author_name']}, İletişim Bilgileri: {total_replacements['contact_info']}, Kurum Bilgileri: {total_replacements['institution_info']}\n\n"
            f"NOT: Referanslar, Kaynaklar, Giriş ve Teşekkür bölümlerindeki isimler anonimleştirilmemiştir. Yazar biyografileri de anonimleştirilmiştir."
        )
        
        return True, success_message
        
    except Exception as e:
        logging.error(f"PDF anonimleştirme hatası: {str(e)}")
        return False, f"PDF anonimleştirme hatası: {str(e)}"


def save_anonymized_file(paper_id, file_path, filename, entities=None, options=None):
    """
    Save anonymized file to database
    """
    from app.utils.db import query
    
    # RSA anahtar çifti oluştur
    private_key, public_key = generate_rsa_key_pair()
    
    # Normalleştirilmiş metinler için
    normalized_entities = {}
    if entities:
        for entity_type in entities:
            normalized_entities[entity_type] = []
            for example in entities[entity_type]:
                # Satır sonu karakterlerini boşluğa dönüştür
                normalized_example = example.replace("\n", " ").strip()
                if normalized_example:  # Boş string değilse ekle
                    normalized_entities[entity_type].append(normalized_example)
    
    # Alt metinleri kontrol eden fonksiyon
    def is_substring_of_any(text, text_list):
        """Bir metnin diğer metinlerin alt metni (substring) olup olmadığını kontrol eder"""
        for other_text in text_list:
            # Eğer bu metin, diğer metnin içinde yer alıyorsa
            if text != other_text and text in other_text:
                return True
        return False
    
    # Çakışan metinleri tespit et ve benzer metinleri filtrele
    filtered_entities = {}
    total_removed = 0
    
    # Her kategori için benzer ve alt metinleri filtrele
    priority_order = ['author_name', 'contact_info', 'institution_info']
    for entity_type in priority_order:
        if entity_type not in normalized_entities:
            filtered_entities[entity_type] = []
            continue
        
        # Önce tüm metinleri uzunluğuna göre büyükten küçüğe sırala
        sorted_entities = sorted(normalized_entities[entity_type], key=len, reverse=True)
        
        category_entities = []  # Bu kategorideki filtrelenmiş metinler
        removed_count = 0  # Filtrelenen metin sayısı
        
        for entity in sorted_entities:
            # Minimum karakter uzunluğu kontrolü (çok kısa metinleri atla)
            if len(entity) < 4:
                removed_count += 1
                continue
            
            # Eğer bu metin, zaten seçilmiş daha uzun bir metnin alt metni değilse ekle
            if not is_substring_of_any(entity, category_entities):
                category_entities.append(entity)
            else:
                removed_count += 1
        
        filtered_entities[entity_type] = category_entities
        total_removed += removed_count
        
        # Filtreleme hakkında log
        if removed_count > 0:
            logging.info(f"{entity_type} kategorisinde {removed_count} metin alt metin olarak filtrelendi. Kalan: {len(category_entities)}")
    
    if total_removed > 0:
        logging.info(f"Toplam {total_removed} metin benzerlik/alt metin kontrolü ile filtrelendi")
    
    # Entities örneklerini şifrele (tüm kelimeleri)
    encrypted_entities = {}
    
    if filtered_entities:
        for entity_type in filtered_entities:
            encrypted_examples = []
            # Tekrarları önlemek için işlenmiş metinleri takip et
            processed_texts = set()
            
            for example in filtered_entities[entity_type]:
                # Bu metin zaten işlenmişse atla
                if example in processed_texts:
                    continue
                
                # Metni şifrele
                encrypted_example = encrypt_with_rsa(example, public_key)
                encrypted_examples.append({
                    "original": example,
                    "encrypted": encrypted_example
                })
                
                # İşlenmiş metinler kümesine ekle
                processed_texts.add(example)
            
            encrypted_entities[entity_type] = encrypted_examples
    
    # Şifrelenmiş örnekleri JSON formatında birleştir
    encrypted_examples_text = json.dumps(encrypted_entities, ensure_ascii=False, indent=2)
    
    # Database saving process
    # Save anonymization information as JSON
    anonymization_info = {
        "options": options or [],
        "entities_found": {
            "author_name_count": len(entities.get('author_name', [])) if entities else 0,
            "contact_info_count": len(entities.get('contact_info', [])) if entities else 0,
            "institution_info_count": len(entities.get('institution_info', [])) if entities else 0
        },
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    sql = """
        INSERT INTO anonymized_files (
            paper_id, file_path, filename, created_at, 
            anonymization_info, encrypted_examples
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    result = query(sql, (
        paper_id, 
        file_path, 
        filename, 
        datetime.datetime.now(),
        json.dumps(anonymization_info),
        encrypted_examples_text
    ), one=True)
    
    # RSA anahtarlarını dosyaya kaydet (opsiyonel - güvenlik için daha sonra silinebilir)
    keys_dir = os.path.join(os.path.dirname(file_path), "keys")
    os.makedirs(keys_dir, exist_ok=True)
    
    private_key_path = os.path.join(keys_dir, f"private_key_{result['id']}.pem")
    public_key_path = os.path.join(keys_dir, f"public_key_{result['id']}.pem")
    
    save_rsa_keys(private_key, public_key, private_key_path, public_key_path)
    
    return result['id'] if result else None


# Dosya yolu çözümleme yardımcı fonksiyonu
def resolve_file_path(db_file_path):
    """
    Takes the file path from database and resolves the actual physical file path.
    Tries multiple possible paths and returns the first one found.
    """
    # Normalize absolute path
    db_file_path = os.path.normpath(db_file_path)
    print(f"Çözümlenecek yol: {db_file_path}")
    
    # Find the root directory of the project
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"Geçerli dizin: {current_dir}")
    
    # Possible root directories - will be tried in this order
    base_dirs = [
        # Windows paths
        os.path.join("C:", "Projects"),
        os.path.join("C:", "Projects", "CloakDocs-Backend"),
        current_dir,  # Current working directory
        os.path.join(current_dir, ".."),  # Parent directory
        
        # Possible Linux/Unix paths
        "/var/www/cloakdocs",
        "/opt/cloakdocs",
        
        # Empty path - db_file_path is used directly
        ""
    ]
    
    # Possible file paths
    possible_paths = []
    
    # Create possible full paths for each base directory
    for base_dir in base_dirs:
        # Full path
        full_path = os.path.join(base_dir, db_file_path)
        possible_paths.append(full_path)
        
        # If "uploads" is in the path, try without it
        if "uploads" in db_file_path:
            alt_path = os.path.join(base_dir, db_file_path.replace("uploads/", ""))
            possible_paths.append(alt_path)
        else:
            # If "uploads" is not in the path, try with uploads
            alt_path = os.path.join(base_dir, "uploads", db_file_path)
            possible_paths.append(alt_path)
    
    # Try each possible path
    for path in possible_paths:
        normalized_path = os.path.normpath(path)
        print(f"Deneniyor: {normalized_path}")
        if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
            print(f"Dosya bulundu: {normalized_path}")
            return normalized_path
    
    # Return None if no path is found
    print(f"Dosya bulunamadı. Denenen yollar: {', '.join(possible_paths)}")
    return None 