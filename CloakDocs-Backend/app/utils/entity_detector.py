import re
import logging
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
import spacy
import importlib.util
import sys
import subprocess

# Gerekli NLTK paketlerini indirme
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Check if scispacy is installed, if not, try to install it
try:
    import scispacy
    HAVE_SCISPACY = True
    logging.info("SciSpaCy is already installed.")
except ImportError:
    HAVE_SCISPACY = False
    logging.warning("SciSpaCy is not installed. Will attempt to install it.")
    try:
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
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")
    logging.info("Loaded small standard NLP model (en_core_web_sm)")

# Yazar isimlerinde kullanılabilen ünvan ve nitelikleri tanımla
ACADEMIC_TITLES = [
    r"Dr\.?", 
    r"Prof\.?", 
    r"Professor", 
    r"Assoc\.? Prof\.?", 
    r"Assistant Prof\.?", 
    r"Asst\.? Prof\.?", 
    r"PhD", 
    r"Ph\.D\.?", 
    r"M\.?Sc\.?", 
    r"B\.?Sc\.?", 
    r"MD", 
    r"M\.?D\.?", 
    r"M\.?Tech\.?",
    r"B\.?Tech\.?",
    r"Er\.?",  # Mühendis (Engineer) ünvanı için Er. kısaltması
    r"Engr\.?"  # Engineer ünvanı için alternatif kısaltma
]

# Ünvan regex'i - isimlerden önce gelebilecek tüm ünvanlar
TITLE_REGEX = r"(?:{})\s+".format("|".join(ACADEMIC_TITLES))

def detect_entities(text, options=None, excluded_text="", first_page_text="", header_sections=""):
    """
    Detect personal information in text using a heuristic approach
    options: ['author_name', 'contact_info', 'institution_info']
    excluded_text: Text in excluded sections
    first_page_text: Text from the first page for prioritized author detection
    header_sections: Text from header areas likely containing author information
    
    Her bir varlık tipi (yazar adı, iletişim bilgisi, kurum bilgisi) birbirinden bağımsız olarak tespit edilir.
    """
    if options is None:
        options = ['author_name', 'contact_info', 'institution_info']
    
    entities = {
        'author_name': [],
        'contact_info': [],
        'institution_info': []
    }
    
    # Seçili olmayan seçenekleri hesaplama zamanından tasarruf etmek için işlemden çıkar
    active_options = [opt for opt in options if opt in entities.keys()]
    
    if not active_options:
        return entities
    
    # Keywords ve INDEX TERMS bölümlerini belirleme - bunlar sansürlemeye dahil edilmeyecek
    keywords_sections = []
    index_terms_sections = []
    
    # INDEX TERMS bölümlerini özel olarak bul
    index_patterns = [
        r'INDEX\s+TERMS[\s\:\-]+.*?(?=\n\n|\Z)',  # INDEX TERMS: ile başlayan bölüm
        r'INDEX\s+TERMS.*?\n(.*?)(?=\n\n|\Z)',  # INDEX TERMS sonrası içerik
        r'(?:^|\n)INDEX\s+TERMS[^\n]*\n((?:[^\n]+[\n]?){1,5})',  # INDEX TERMS kısmı ve sonraki 5 satır
    ]
    
    for pattern in index_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            if match.group(0):
                index_terms_sections.append(match.group(0))
                logging.info(f"INDEX TERMS bölümü tespit edildi: {match.group(0)[:50]}...")
    
    # KEYWORDS bölümlerini özel olarak bul
    keywords_patterns = [
        r'KEYWORDS[\s\:\-]+.*?(?=\n\n|\Z)',  # KEYWORDS: ile başlayan bölüm
        r'KEYWORDS.*?\n(.*?)(?=\n\n|\Z)',  # KEYWORDS sonrası içerik
        r'(?:^|\n)KEYWORDS[^\n]*\n((?:[^\n]+[\n]?){1,5})',  # KEYWORDS kısmı ve sonraki 5 satır
    ]
    
    for pattern in keywords_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            if match.group(0):
                keywords_sections.append(match.group(0))
                logging.info(f"KEYWORDS bölümü tespit edildi: {match.group(0)[:50]}...")
    
    # Tüm bu bölümleri excluded_text'e ekle
    if index_terms_sections or keywords_sections:
        all_excluded_sections = index_terms_sections + keywords_sections
        excluded_text = (excluded_text + "\n" + "\n".join(all_excluded_sections)) if excluded_text else "\n".join(all_excluded_sections)
        logging.info(f"Toplam {len(all_excluded_sections)} anahtar kelime/terim bölümü sansürleme dışında bırakıldı")
    
    # Her varlık tipi için ayrı ayrı işlem yaparak birbirlerini etkilemelerini önle
    for entity_type in active_options:
        # Her varlık tipi için ayrı candidates sözlüğü oluştur
        candidates = {entity_type: {}}  # {entity: score} formatında
        
        # Boş veya çok büyük metni kontrol et
        if not text or len(text) < 10:
            continue
        
        # Header bölümlerinden varlık tespiti (yüksek öncelikli)
        if header_sections:
            process_text_for_single_entity_type(header_sections, candidates, entity_type, 
                                               context="header", first_page=True)
        
        # İlk sayfadan varlık tespiti (orta öncelik)
        if first_page_text:
            process_text_for_single_entity_type(first_page_text, candidates, entity_type, 
                                               context="first_page", first_page=True)
        
        # Ana içerikten varlık tespiti (normal öncelik)
        process_text_for_single_entity_type(text, candidates, entity_type, 
                                          context="main_content", first_page=False)
        
        # Varlık tipine özgü minimum puanları belirle
        min_score = 1  # Varsayılan minimum puan
        
        # Varlık tipine göre özelleştirilmiş filtreler uygula
        if entity_type == 'author_name':
            filtered_candidates = {k: v for k, v in candidates[entity_type].items() 
                                if (v >= min_score + 1 or 
                                    ('header' in k[1] or 'first_page' in k[1]))}
        else:
            filtered_candidates = {k: v for k, v in candidates[entity_type].items() 
                                if v >= min_score}
        
        # Güven puanına göre sırala (azalan)
        sorted_candidates = sorted(filtered_candidates.items(), key=lambda x: x[1], reverse=True)
        
        # Varlık metinlerini tuple'lardan çıkar ve nihai listeye ekle
        entities[entity_type] = [candidate[0][0] for candidate in sorted_candidates]
    
    # Son filtreleme ve normalizasyon
    entities = normalize_and_filter_entities(entities, text, excluded_text)
    
    # Sonuçları logla
    log_entity_stats(entities)
    
    return entities


def process_text_for_single_entity_type(text, candidates, entity_type, context="main_content", first_page=False):
    """
    Belirli bir varlık tipi için metni işle
    """
    # Büyük metni parçalar halinde işle
    if len(text) > 500000:  # metin ~500KB'dan büyükse
        logging.info(f"Büyük metin tespit edildi ({len(text)} karakter), parçalar halinde işleniyor")
        chunks = [text[i:i+250000] for i in range(0, len(text), 250000)]
        for chunk in chunks:
            process_chunk_for_single_entity_type(chunk, candidates, entity_type, context, first_page)
    else:
        process_chunk_for_single_entity_type(text, candidates, entity_type, context, first_page)
    
    # Özellikle konferans makaleleri için akademik başlık ve yazar taraması yap
    if first_page and entity_type == 'author_name':
        extract_academic_header_entities(text, candidates, [entity_type], context)


def process_chunk_for_single_entity_type(text, candidates, entity_type, context, first_page):
    """Tek bir varlık tipi için metin parçasını işle"""
    # spaCy NER kullan
    doc = nlp(text)
    
    # NER ile varlıkları çıkar
    extract_ner_entities_for_type(doc, candidates, entity_type, context, first_page)
    
    # Regex ile varlıkları çıkar
    extract_regex_entities_for_type(text, candidates, entity_type, context, first_page)
    
    # Yazar bağlamında geçen varlıkların puanlarını artır
    if entity_type == 'author_name':
        boost_entities_in_author_contexts(text, candidates, [entity_type], context, first_page)


def extract_ner_entities_for_type(doc, candidates, entity_type, context, first_page):
    """Belirli bir varlık tipi için NER kullanarak varlıkları çıkar"""
    # Kişi isimleri
    if entity_type == 'author_name':
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG:PERSON"]:
                name = ent.text.strip()
                
                # Çok kısa isimleri veya muhtemel yanlış pozitifleri atla
                if is_valid_person_name(name):
                    # Temel puan: NER tespiti için 1
                    score = 1
                    
                    # İlk sayfa veya başlık bağlamı için daha yüksek puan
                    if first_page:
                        score += 1
                    if context == "header":
                        score += 2
                    
                    # Daha sonra filtreleme için bağlam bilgisiyle sakla
                    key = (name, context)
                    candidates[entity_type][key] = max(candidates[entity_type].get(key, 0), score)
    
    # Kurum Bilgileri
    elif entity_type == 'institution_info':
        for ent in doc.ents:
            if ent.label_ in ["ORG", "FAC", "GPE", "LOC", "FACILITY", "ORGANIZATION"]:
                institution = ent.text.strip()
                
                # Çok kısa veya geçersiz kurum adlarını atla
                if len(institution) > 3 and not is_common_word(institution):
                    # Temel puan: NER tespiti için 1
                    score = 1
                    
                    # Belirli bağlamlar için daha yüksek puan
                    if first_page:
                        score += 1
                    if context == "header":
                        score += 1
                    
                    # Üniversite, bölüm vb. için ekstra puan
                    if any(term in institution.lower() for term in ['university', 'institute', 'department', 
                                                                  'college', 'school', 'laboratory']):
                        score += 1
                    
                    key = (institution, context)
                    candidates[entity_type][key] = max(candidates[entity_type].get(key, 0), score)
    
    # İletişim Bilgileri - email için NER özel olarak çalışmayabilir, regex daha etkili
    elif entity_type == 'contact_info':
        # Email ve diğer iletişim bilgileri için özel kontrol gerekir
        # Bu tip tespitler genellikle regex_entities bölümünde yapılır
        pass  # Email için özel bir NER işlemi olmadığı için boş geçiyoruz


def extract_regex_entities_for_type(text, candidates, entity_type, context, first_page):
    """Belirli bir varlık tipi için regex kullanarak varlıkları çıkar"""
    
    # Kişi isimleri için regex kalıpları
    if entity_type == 'author_name':
        # Akademik makalelerde yaygın olan satır bazlı yazar formatı - isim + departman + üniversite
        # Örnek: "Divyashikha Sethia\nDepartment of Computer\nScience and Engineering\nDelhi Technological University\nDelhi, India"
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            # Tek kelimelik ve tek satırlık isimler
            if i < len(lines) - 1 and re.match(r'^[A-Z][a-zA-Z\-]+$', line):
                name = line
                # Sonraki satırda "Department" veya benzeri kelimeler varsa
                if i+1 < len(lines) and re.search(r'Department|Faculty|Institute|School', lines[i+1]):
                    if is_valid_person_name(name):
                        name_key = (name, context)
                        candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 3.0)
                        logging.info(f"Tek kelimelik satır bazlı yazar tespit edildi: {name}")
            
            # İki veya daha fazla kelimeden oluşan isimler
            if re.match(r'^[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+$', line):
                name = line
                # Sonraki satırda "Department" veya benzeri kelimeler varsa
                if i+1 < len(lines) and re.search(r'Department|Faculty|Institute|School', lines[i+1]):
                    if is_valid_person_name(name):
                        name_key = (name, context)
                        candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 3.0)
                        logging.info(f"Satır bazlı yazar tespit edildi: {name}")
                        
            # İsmi başında inisyal olan yazarları tespit et (örn: "S. Indu")
            if re.match(r'^[A-Z]\.\s+[A-Z][a-zA-Z\-]+$', line):
                name = line
                # Sonraki satırda "Department" veya benzeri kelimeler varsa
                if i+1 < len(lines) and re.search(r'Department|Faculty|Institute|School', lines[i+1]):
                    if is_valid_person_name(name):
                        name_key = (name, context)
                        candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 3.0)
                        logging.info(f"İnisyalli satır bazlı yazar tespit edildi: {name}")
        
        # Özellikle Hindistan'da yaygın olan "Er." önekli mühendis isimlerini tespit et
        er_names = re.findall(r'Er\.\s+([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)', text)
        for name in er_names:
            full_name = f"Er. {name.strip()}"
            if is_valid_person_name(full_name):
                # "Er." önekine sahip isimlere yüksek güven skoru ver (özellikle IEEE makalelerinde yaygın)
                name_key = (full_name, context)
                # 3.0 puan vererek kesin tespit olarak işaretle
                candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 3.0)
                logging.info(f"Er. önekli isim tespit edildi: {full_name}")
        
        # Yazar - email deseni
        author_email_matches = re.findall(r'([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)[\s,]*[\(\{]?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[\)\}]?', text)
        for match in author_email_matches:
            name, email = match
            name = name.strip()
            if is_valid_person_name(name):
                name_key = (name, context)
                # Email ile ilişkili isim olduğu için daha yüksek puan
                candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 2.0)
        
        # İnisyalli isimleri (S. Indu vb.) e-posta ile eşleştir
        initial_names_with_email = re.findall(r'([A-Z]\.\s+[A-Z][a-zA-Z\-]+)[\s\n]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
        for match in initial_names_with_email:
            name, email = match
            name = name.strip()
            if is_valid_person_name(name):
                name_key = (name, context)
                candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 3.0)
                logging.info(f"İnisyalli isim ve e-posta tespit edildi: {name}")
        
        # İsim eşleştirme: Aynı satırda isim ardından e-posta adresi (2 satırda)
        # Örnek:
        # Divyashikha Sethia
        # divyashikha@dtu.ac.in
        lines = text.split('\n')
        for i in range(len(lines) - 1):
            # İlk satır isim olabilir
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            
            # İsim formatı kontrolü
            if (re.match(r'^[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+$', current_line) or 
                re.match(r'^[A-Z]\.\s+[A-Z][a-zA-Z\-]+$', current_line)):
                # Sonraki satır email olabilir
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', next_line):
                    name = current_line
                    email = next_line
                    
                    if is_valid_person_name(name):
                        name_key = (name, context)
                        # Çok yüksek güven skoru (isim + e-posta)
                        candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 4.0)
                        logging.info(f"Satır bazlı isim + e-posta tespit edildi: {name}")
        
        # İletişim bilgileri bağlamında geçen isimler
        contact_name_matches = re.findall(r'(?:Contact|Corresponding Author|For correspondence):?\s*([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)', text, re.IGNORECASE)
        for name in contact_name_matches:
            name = name.strip()
            if is_valid_person_name(name):
                name_key = (name, context)
                candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 2.0)
                
        # IEEE formatındaki isimler (John Smith, Member, IEEE)
        ieee_author_matches = re.findall(r'([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)(?:,\s+(?:Member|Senior Member|Fellow|Student Member|Associate Member),\s+IEEE)', text)
        for name in ieee_author_matches:
            name = name.strip()
            if is_valid_person_name(name):
                name_key = (name, context)
                candidates[entity_type][name_key] = max(candidates[entity_type].get(name_key, 0), 2.5)
    
    # İletişim bilgileri için regex kalıpları
    elif entity_type == 'contact_info':
        # Telefon numaraları için regex kalıpları
        phone_patterns = [
            # Temizlenmiş uluslararası telefon formatı
            r'\b\+\d{1,3}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4}\b',
            
            # US/Kanada formatı
            r'\b\(\d{3}\)[\s\-\.]?\d{3}[\s\-\.]?\d{4}\b',
            r'\b\d{3}[\s\-\.]?\d{3}[\s\-\.]?\d{4}\b',
            
            # Avrupa türü formatlar
            r'\b\d{2,4}[\s\-\.]\d{2,4}[\s\-\.]\d{2,4}[\s\-\.]\d{2,4}\b',
            
            # Türkiye formatı
            r'\b0[\s\-\.]?\d{3}[\s\-\.]\d{3}[\s\-\.]\d{2}[\s\-\.]\d{2}\b',
            r'\b\+90[\s\-\.]?\d{3}[\s\-\.]\d{3}[\s\-\.]\d{2}[\s\-\.]\d{2}\b',
            
            # Akademik makalelerdeki özel formatlar
            r'(?:phone|tel)(?:ephone)?(?:\.|\:|\s)+[\(\s]*(?:\+?\d[\d\s\(\)\-\.]{7,20})',
            
            # Parantezli ve tireyle ayrılmış formatlar (özellikle akademik makalelerde yaygın)
            r'\(?\d{2,3}\)?[\s\-\.]+\d{2,4}[\s\-\.]+\d{2,4}[\s\-\.]+\d{2,4}'
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            for phone in matches:
                phone_key = (phone, context)
                # Temel güven skoru başlat
                score = 1.0
                
                # Context-aware scoring (bağlam kontrolü) - anahtar kelimeler içeriyor mu?
                phone_context = get_context_window(text, phone, window_size=50)
                
                # Telefon içeren bir metnin önünde/arkasında telefon göstergeleri var mı?
                phone_indicators = ['phone', 'tel', 'telefon', 'iletişim', 'contact', 'call', 'telephone', 'number', 'numara']
                for indicator in phone_indicators:
                    if indicator.lower() in phone_context.lower():
                        score += 0.5
                        break
                
                # "phone:" veya "tel:" ile başlayan formatlar genellikle kesin telefon numaralarıdır
                if re.search(r'(?:phone|tel)(?:ephone)?(?:\.|\:|\s)+', phone_context, re.IGNORECASE):
                    score += 1.0
                    
                # Parantez içeren formatlar için ek güven
                if '(' in phone or ')' in phone:
                    score += 0.5
                
                candidates[entity_type][phone_key] = max(candidates[entity_type].get(phone_key, 0), score)
        
        # E-posta adresleri
        email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
        for email in email_matches:
            email_key = (email, context)
            candidates[entity_type][email_key] = max(candidates[entity_type].get(email_key, 0), 2.0)  # E-postalar oldukça belirgin
            
        # ORCID format - iD
        orcid_matches = re.findall(r'ORCID(?:\:|\s)+(?:https?\:\/\/orcid\.org\/)?(\d{4}\-\d{4}\-\d{4}\-\d{4})', text, re.IGNORECASE)
        for orcid in orcid_matches:
            orcid_formatted = f"ORCID: {orcid}"
            orcid_key = (orcid_formatted, context)
            candidates[entity_type][orcid_key] = max(candidates[entity_type].get(orcid_key, 0), 2.0)
    
    # Kurum bilgileri için regex kalıpları
    elif entity_type == 'institution_info':
        # Üniversiteler ve kurumlar için yaygın kalıplar
        institution_patterns = [
            # Department, School, Faculty, Institute
            r'(?:Department|Dept|School|Faculty|Institute)\s+of\s+[A-Z][^,;\n\d]{5,50}',
            
            # University, College
            r'[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+){1,8}\s+(?:University|College|Institute|School)',
            r'(?:University|College|Institute|School)\s+of\s+[A-Z][^,;\n\d]{5,50}',
            
            # Labs, Centers, etc.
            r'[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+){1,8}\s+(?:Lab(?:orator(?:y|ies))?|Center|Centre|Foundation)',
            
            # Address blocks (especially for academic papers)
            r'[A-Z][a-zA-Z\-]+(?:,|\s+)\s*[A-Z][a-zA-Z\s]{10,100}(?:,|\s+)(?:[A-Z]{2,3}|\d{5})'
        ]
        
        for pattern in institution_patterns:
            matches = re.findall(pattern, text)
            for institution in matches:
                # 100 karakterden uzun kurumları atla - muhtemelen yanlış tespitlerdir
                if len(institution) > 100:
                    continue
                
                institution_key = (institution, context)
                
                # Temel güven skoru
                score = 1.0
                
                # Bağlam kontrolü - anahtar kelimeler içeriyor mu?
                inst_context = get_context_window(text, institution, window_size=100)
                inst_indicators = ['university', 'college', 'department', 'faculty', 'school', 'institute', 
                                  'laboratory', 'center', 'centre', 'üniversite', 'fakülte', 'bölüm', 'enstitü']
                
                for indicator in inst_indicators:
                    if indicator.lower() in institution.lower():
                        score += 0.5
                        break
                
                # Affiliation, address gibi anahtar kelimelere yakınsa
                if re.search(r'(?:affiliation|address|department|kurum|adres)', inst_context, re.IGNORECASE):
                    score += 0.5
                
                candidates[entity_type][institution_key] = max(candidates[entity_type].get(institution_key, 0), score)


def boost_entities_in_author_contexts(text, candidates, options, context, first_page):
    """Boost confidence scores for entities appearing near author context phrases"""
    # Define context phrases that indicate author information
    author_context_phrases = [
        r"(?i)corresponding author",
        r"(?i)author(s)?[:]?",
        r"(?i)prepared by",
        r"(?i)written by",
        r"(?i)submitted by",
        r"(?i)affiliation",
        r"(?i)department of",
        r"(?i)faculty of",
        r"(?i)university of",
        r"(?i)institute of",
        r"(?i)contact[:]?",
        r"(?i)e-?mail[:]?"
    ]
    
    # Find locations of context phrases
    context_locations = []
    for phrase in author_context_phrases:
        for match in re.finditer(phrase, text):
            start, end = match.span()
            context_locations.append((start, end, match.group()))
    
    # If no context phrases found, return
    if not context_locations:
        return
    
    # For each context location, find nearby entities and boost their scores
    for start, end, phrase in context_locations:
        # Consider text within a window of the context phrase
        window_size = 200  # Characters before/after the phrase
        window_start = max(0, start - window_size)
        window_end = min(len(text), end + window_size)
        context_window = text[window_start:window_end]
        
        # Boost scores for entities in this window
        for entity_type in candidates:
            if entity_type in options:
                boosted_keys = []
                
                for (entity, ent_context), score in candidates[entity_type].items():
                    # If entity is in this context window, boost its score
                    if entity in context_window:
                        boost = 1.0
                        
                        # Higher boost for closer phrases
                        if phrase.lower() in ["corresponding author", "author:", "authors:"]:
                            boost = 2.0
                        
                        boosted_keys.append((entity, ent_context))
                        candidates[entity_type][(entity, ent_context)] = score + boost
                
                # Log boosted entities
                if boosted_keys and len(boosted_keys) < 5:  # Avoid excessive logging
                    logging.info(f"Boosted {entity_type} scores for entities near '{phrase}': {[k[0] for k in boosted_keys]}")


def is_valid_person_name(name):
    """
    Bir metnin geçerli bir kişi ismi olup olmadığını kontrol eder.
    """
    if not name or len(name) < 3:
        return False
    
    # İsimlerde yaygın olmayan karakterleri kontrol et
    if re.search(r'[0-9@#$%^&*()_+=\[\]{}|\\<>/]', name):
        return False
    
    # Çok fazla noktalama işareti varsa
    if len(re.findall(r'[.,;:!?]', name)) > 2:
        return False
    
    # Yaygın stop words'ler isim değildir
    stop_words = ["the", "and", "or", "in", "at", "on", "by", "to", "for", "with", "about"]
    name_lower = name.lower()
    for word in stop_words:
        if name_lower == word:
            return False
    
    # IEEE rolleri/terimleri isim değildir (ismin kendisi değilse)
    ieee_roles = ["member", "senior member", "fellow", "student member", "associate member", "ieee"]
    for role in ieee_roles:
        if name_lower == role:
            return False
    
    # İnisyal ile başlayan isimleri kabul et (örneğin "S. Indu")
    if re.match(r'^[A-Z]\.\s+[A-Z][a-zA-Z\-]+$', name):
        return True
    
    # Çok kısa olmadıkça ve büyük harfle başlayan kelimelerden oluşuyorsa isim olabilir
    if len(name) > 5 and re.match(r'^([A-Z][a-zÀ-ÿ\-]+(\s+[A-Z][a-zÀ-ÿ\-]+)+)$', name):
        return True
    
    # "Er." önekini özel olarak işle
    if name.startswith("Er.") and len(name) > 5:
        # "Er." sonrası büyük harfle başlayan isim olmalı
        remaining_name = name[3:].strip()
        return re.match(r'^([A-Z][a-zÀ-ÿ\-]+(\s+[A-Z][a-zÀ-ÿ\-]+)*)$', remaining_name) is not None
    
    # Diğer ünvanlar için de benzer kontrol
    for title in ACADEMIC_TITLES:
        title_pattern = rf"^{title}\s+"
        if re.match(title_pattern, name):
            # Ünvan sonrası büyük harfle başlayan isim olmalı
            match = re.search(title_pattern, name)
            remaining_name = name[match.end():].strip()
            return re.match(r'^([A-Z][a-zÀ-ÿ\-]+(\s+[A-Z][a-zÀ-ÿ\-]+)*)$', remaining_name) is not None
            
    # Bilimsel terim değilse
    scientific_terms = ["figure", "table", "section", "equation", "theorem", "corollary", "proof", "algorithm"]
    for term in scientific_terms:
        if name_lower == term:
            return False
    
    # Bu adımlardan sonra geçerli kabul edilen isim
    return True


def is_common_word(text):
    """Check if text is a common word that should not be considered an entity"""
    common_words = [
        'table', 'figure', 'abstract', 'introduction', 'methodology',
        'results', 'discussion', 'conclusion', 'references', 'appendix',
        'example', 'analysis', 'method', 'section', 'equation', 'value'
    ]
    
    return text.lower() in common_words


def get_context_window(text, target, window_size=50):
    """
    Bir metin içindeki hedef metinle ilgili bağlamsal pencereyi döndürür.
    Bu, varlıkların puanlanmasında bağlam ipuçlarını toplamak için kullanılır.
    
    Args:
        text (str): Tüm metin
        target (str): Bağlamı alınacak hedef metin
        window_size (int): Hedefin önünde ve arkasında alınacak karakter sayısı
        
    Returns:
        str: Hedefin çevresindeki bağlam metni
    """
    try:
        target_pos = text.find(target)
        if target_pos == -1:
            return ""
            
        start_pos = max(0, target_pos - window_size)
        end_pos = min(len(text), target_pos + len(target) + window_size)
        
        return text[start_pos:end_pos]
    except:
        return ""


def get_confidence_score(entity_text, context_text, window_size=100):
    """
    Bir varlığın (kişi, kurum, iletişim bilgisi vs.) güven skorunu hesaplar.
    Daha yüksek skorlar daha güvenilir tespitleri gösterir.
    
    Args:
        entity_text (str): Tespit edilen varlık metni
        context_text (str): Varlığın geçtiği metin bağlamı
        window_size (int): Varlık etrafındaki bağlam penceresi boyutu
        
    Returns:
        float: 0 ile 5 arasında bir güven skoru (5 en yüksek güven)
    """
    if not entity_text or not context_text:
        return 0.0
    
    # Temel güven skoru
    score = 1.0
    
    # 1. İsim uzunluğuna göre puanlama - çok kısa isimler daha düşük güven skorları alır
    length = len(entity_text)
    if length < 5:
        score -= 0.5
    elif length > 20:
        score += 0.3  # Daha uzun isimler genellikle daha ayırt edicidir
    
    # 2. İsmin geçtiği bağlam penceresini al
    context_window = get_context_window(context_text, entity_text, window_size)
    
    # 3. Bağlam ipuçlarını kontrol et
    context_indicators = {
        # Kişi adlarıyla ilişkili ipuçları
        'author': 0.8,
        'yazar': 0.8,
        'dr': 0.7,
        'prof': 0.7,
        'professor': 0.7,
        'member': 0.6,
        'ieee': 0.6,
        'ph.d': 0.7,
        'contact': 0.7,
        'corresponding': 0.8,
        'student': 0.5,
        
        # Kurum adlarıyla ilişkili ipuçları
        'university': 0.7,
        'college': 0.7,
        'institute': 0.7,
        'laboratory': 0.7,
        'department': 0.7,
        'faculty': 0.7,
        'school': 0.6,
        'üniversit': 0.7,  # Türkçe için
        'fakülte': 0.7,    # Türkçe için
        'enstitü': 0.7,    # Türkçe için
        
        # İletişim bilgileriyle ilişkili ipuçları
        'email': 0.8,
        'phone': 0.8,
        'telefon': 0.8,
        'address': 0.7,
        'tel': 0.8,
        'contact': 0.7,
        'iletişim': 0.7,   # Türkçe için
        'numara': 0.6      # Türkçe için
    }
    
    # Bağlam ipuçlarının yakınlık puanı hesabı
    for indicator, boost in context_indicators.items():
        if indicator in context_window.lower():
            score += boost
            # Her ipucu için en fazla bir kez puanlama yapalım
            break
    
    # 4. İsim formatının geçerliliği (büyük harfle başlama vs.)
    if re.match(r'^[A-Z][a-zÀ-ÿ]+(\s+[A-Z][a-zÀ-ÿ]+)+$', entity_text):
        score += 0.5  # İsim formatı doğru olan isimler ek puan alır
    
    # 5. Özel durumlar
    # IEEE üyelik bilgisi içeren isimler
    if re.search(r'(?:Member|Senior Member|Fellow),\s*IEEE', context_window):
        score += 1.0
    
    # Email adresi içeren isimler
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', context_window):
        score += 0.8
    
    # "Er." önekine sahip isimler özellikle IEEE makalelerinde yaygın
    if entity_text.startswith("Er.") or "Er. " in entity_text:
        score += 0.7
    
    # Sonucu 0-5 aralığına sınırla
    return min(5.0, max(0.0, score))


def normalize_and_filter_entities(entities, main_text, excluded_text):
    """Final filtering and normalization of detected entities"""
    # Tam eşleşme garantilemek için büyük/küçük harf duyarlı sözlük
    normalized_entities = {
        "author_name": set(),
        "contact_info": set(),
        "institution_info": set()
    }
    
    # INDEX TERMS veya KEYWORDS içeren satırları belirle
    index_terms_lines = []
    keywords_lines = []
    
    # Metni satırlara böl
    lines = main_text.split('\n')
    
    # INDEX TERMS veya KEYWORDS içeren satırları bul
    for i, line in enumerate(lines):
        if re.search(r'INDEX\s+TERMS', line, re.IGNORECASE):
            # Bu satırı ve sonraki iki satırı kaydet
            index_terms_lines.extend([i, i+1, i+2, i+3])
        elif re.search(r'KEYWORDS', line, re.IGNORECASE):
            # Bu satırı ve sonraki iki satırı kaydet
            keywords_lines.extend([i, i+1, i+2, i+3])
    
    # Her kategori için normalleştirme ve tam eşleşme sağla
    for key, values in entities.items():
        for value in values:
            # Değer kontrolü
            if not value or len(value) < 2:
                continue
                
            # Hariç tutulan metinlerde geçiyorsa atla
            if excluded_text and value in excluded_text:
                logging.info(f"Hariç tutulan metinde olduğu için atlandı: {value}")
                continue
            
            # INDEX TERMS veya KEYWORDS bölümlerinde geçiyor mu kontrol et
            # 1. Tam satır eşleşmesi: Değerin geçtiği satırları bul
            in_index_terms_or_keywords = False
            
            for line_index in list(set(index_terms_lines + keywords_lines)):
                if line_index < len(lines) and value in lines[line_index]:
                    in_index_terms_or_keywords = True
                    logging.info(f"INDEX TERMS/KEYWORDS satırında olduğu için atlandı: {value}")
                    break
            
            if in_index_terms_or_keywords:
                continue
                
            # 2. Bağlam penceresi kontrolü
            text_pos = main_text.find(value)
            if text_pos > -1:
                # Öncesindeki ve sonrasındaki metni kontrol et (geniş pencere)
                surrounding_text = main_text[max(0, text_pos - 200):min(len(main_text), text_pos + len(value) + 200)]
                
                # Kelimenin INDEX TERMS veya KEYWORDS bölümünde geçip geçmediğini kontrol et
                if re.search(r'INDEX\s+TERMS[\s\:\-]*.*' + re.escape(value), surrounding_text, re.IGNORECASE | re.DOTALL) or \
                   re.search(r'KEYWORDS[\s\:\-]*.*' + re.escape(value), surrounding_text, re.IGNORECASE | re.DOTALL):
                    logging.info(f"INDEX TERMS/KEYWORDS bölüm bağlamında olduğu için atlandı: {value}")
                    continue
            
            # Bilimsel terimler listesinde var mı kontrol et (kısaltmalar için)
            if key == "author_name" and value.upper() in ['CNN', 'RNN', 'LSTM', 'GRU', 'DNN', 'SVM', 'PCA', 'LDA', 
                                                         'DEAP', 'DENS', 'EEG', 'ECG', 'EMG', 'MRI', 'SEED',
                                                         'GPU', 'CPU', 'API', 'IoT', 'NLP', 'OCR', 'RSS']:
                logging.info(f"Bilimsel kısaltma olduğu için yazar olarak atlandı: {value}")
                continue
                
            # Tam metin eşleşmesi algıla (parça yerine bütün)
            full_match = value
            
            # Metin içinde tamamen eşleşiyor mu?
            if full_match in main_text:
                normalized_entities[key].add(full_match)
    
    # Set'ten listeye dönüştür ve sırala
    result = {}
    for key, values in normalized_entities.items():
        result[key] = sorted(list(values), key=len, reverse=True)
        
    return result


def log_entity_stats(entities):
    """Log statistics of detected entities"""
    for category, items in entities.items():
        logging.info(f"Detected {category}: {len(items)} items")
        if len(items) > 0:
            # Log a few examples (to avoid excessive logging)
            sample = items[:min(3, len(items))]
            logging.info(f"Examples: {', '.join(sample)}")


def extract_academic_header_entities(text, candidates, options, context):
    """
    Akademik makale başlıklarında yaygın olan yazar, iletişim ve kurum bilgilerini inceleyen
    özel bir fonksiyon. Tipik olarak konferans makalelerinin ilk sayfasındaki yapılandırılmış bilgileri hedefler.
    """
    # Konferans makaleleri tipik olarak şu formatta olur:
    # - Konferans adı ve tarihi
    # - Makale başlığı
    # - Yazarlar, departmanlar ve e-posta adresleri
    
    # Satır içi ve satır arası formatlama sorunlarını azaltmak için metni temizle
    cleaned_text = text
    # Fazla boşlukları tek boşluğa indir
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    # Parantezleri içerikleriyle birlikte geçici olarak kaldır (daha sonra eklenecek)
    parenthesis_matches = re.finditer(r'\([^)]+\)', cleaned_text)
    parenthesis_contents = []
    for match in parenthesis_matches:
        parenthesis_contents.append(match.group(0))
    cleaned_text = re.sub(r'\([^)]+\)', ' PARENMARK ', cleaned_text)
    
    # IEEE formatı için özel tespit
    if 'author_name' in options:
        # IEEE formatındaki yazar isimleri, örn: "Jane Doe, Member, IEEE"
        ieee_author_patterns = [
            # "Name, Title, IEEE" formatı
            r"([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})\s*,\s*(?:Member|Senior Member|Fellow|Student Member|Graduate Student Member)\s*,\s*IEEE",
            
            # Birden fazla yazarı virgülle ayıran satırlar (IEEE üyelik bilgisi içeren)
            r"([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3}),\s*([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3}),\s*(?:Member|Senior Member|Fellow|Student Member|Graduate Student Member),\s*IEEE",
            
            # IEEE üyelik bilgisi sonraki satırda olan yazarlar
            r"([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})(?:\n|\r\n?)\s*(?:Member|Senior Member|Fellow|Student Member|Graduate Student Member),\s*IEEE",
            
            # Virgülle ayrılmış yazar listesi
            r"([A-Z][a-zÀ-ÿ]+(?:[ -][A-Z][a-zÀ-ÿ]+){1,3}),\s*([A-Z][a-zÀ-ÿ]+(?:[ -][A-Z][a-zÀ-ÿ]+){1,3})",
            
            # Birden fazla yazarı virgülle ayıran satırlar (genel)
            r"([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3}),\s*([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3}),\s*([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})",
            
            # "AND" veya "ve" ile bağlanan yazarlar
            r"([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})\s+(?:AND|Ve|and)\s+([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})"
        ]
        
        # Önce temizlenmiş metinde, sonra orijinal metinde ara
        for search_text in [cleaned_text, text]:
            for pattern in ieee_author_patterns:
                ieee_matches = re.finditer(pattern, search_text)
                for match in ieee_matches:
                    # Tüm eşleşen grupları al - birden fazla yazar olabilir
                    name_groups = [g for g in match.groups() if g]
                    
                    for name in name_groups:
                        name = name.strip()
                        if is_valid_person_name(name):
                            # IEEE formatı için ekstra yüksek güvenilirlik puanı
                            score = 4.0  # Çok yüksek güvenilirlik
                            key = (name, context)
                            candidates['author_name'][key] = max(candidates['author_name'].get(key, 0), score)
                            
                            # Tam eşleşmeyi de kaydet (tüm satır)
                            if match.group(0).strip():
                                full_match = match.group(0).strip()
                                # Eğer satır içinde "IEEE" veya virgüller varsa güven puanını artır
                                if "IEEE" in full_match or full_match.count(",") > 1:
                                    score = 4.5  # En yüksek güvenilirlik
                                full_key = (full_match, context)
                                candidates['author_name'][full_key] = max(candidates['author_name'].get(full_key, 0), score)
                            
                            logging.info(f"IEEE formatında yazar tespit edildi: {name}")
        
        # Özellikle büyük harfli yazar tespitini güçlendir
        big_caps_author_patterns = [
            # Tamamen büyük harfli tek isim
            r"\b([A-Z]{3,})\b",
            
            # Tamamen büyük harfli iki veya daha fazla kelimelik isim
            r"\b([A-Z]{2,}(?:\s+[A-Z]{2,}){1,})\b",
            
            # TEJAS VINODBHAI gibi isimler 
            r"\b([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})?)\b",
            
            # "AND" veya virgülle bağlanan büyük harfli isimler
            r"([A-Z]{2,}(?:\s+[A-Z]{2,})?),\s*(?:AND|AND|Ve)?\s*([A-Z]{2,}(?:\s+[A-Z]{2,})?)",
            
            # MAJITHIA TEJAS VINODBHAI formatı - üç veya daha fazla büyük harfli kelime
            r"\b([A-Z]{2,}(?:\s+[A-Z]{2,}){2,3})\b",
        ]
        
        # Özellikle büyük harfli isimleri tespit et
        for pattern in big_caps_author_patterns:
            for match in re.finditer(pattern, text):
                name = match.group(0).strip()
                
                # Özel büyük harfli isim doğrulama
                if name.isupper() and len(name) > 5 and not any(x in name for x in ["TABLE", "FIGURE", "IEEE"]):
                    # Büyük harfli ismi doğru formata çevir
                    proper_name = ' '.join([word.title() for word in name.split()])
                    
                    # Büyük harfli isimler için ekstra yüksek puan
                    score = 4.2  # Çok yüksek güvenilirlik (özel durum)
                    
                    # Her iki versiyonu da kaydet
                    key_original = (name, context)
                    key_proper = (proper_name, context)
                    
                    candidates['author_name'][key_original] = max(candidates['author_name'].get(key_original, 0), score)
                    candidates['author_name'][key_proper] = max(candidates['author_name'].get(key_proper, 0), score)
                    
                    logging.info(f"Özel büyük harfli yazar tespit edildi: {name} -> {proper_name}")
        
        # Satır sonlarına dikkat et (büyük harfli yazarlar genellikle ayrı satırlarda olabilir)
        # İlginç büyük harfli yazar satırları için ek desenleri kontrol et
        line_based_patterns = [
            r"^([A-Z]{2,}(?:\s+[A-Z]{2,})+)[\s,]*$",  # Satırın tamamını kaplayan büyük harfli yazar
            r"[\n\r]([A-Z]{2,}(?:\s+[A-Z]{2,})+)[\s,]*[\n\r]",  # Satırlar arasında büyük harfli yazar
            r"[\n\r]([A-Z]{2,}(?:\s+[A-Z]{2,})+),\s*(?:AND|And|and|VE|Ve|ve)?\s*([A-Z]{2,}(?:\s+[A-Z]{2,})+)"  # "AND" ile bağlı iki büyük harfli yazar
        ]
        
        for pattern in line_based_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                groups = match.groups()
                for name in groups:
                    if name and name.strip() and len(name.strip()) > 5:
                        name = name.strip()
                        proper_name = ' '.join([word.title() for word in name.split()])
                        
                        # Satır bazlı yazar tespiti - daha güvenilir
                        score = 4.5  # Çok yüksek güvenilirlik (en güvenilir durum)
                        
                        key_original = (name, context)
                        key_proper = (proper_name, context)
                        
                        candidates['author_name'][key_original] = max(candidates['author_name'].get(key_original, 0), score)
                        candidates['author_name'][key_proper] = max(candidates['author_name'].get(key_proper, 0), score)
                        
                        logging.info(f"Satır bazlı büyük harfli yazar tespit edildi: {name} -> {proper_name}")
        
        # İlk sayfada makale başlığını takip eden yazar isimleri
        # Çoğu akademik makalede, başlık sonrası yazar isimleri listelenir
        title_matches = re.finditer(r'([A-Z][A-Za-zÀ-ÿ0-9\s\:\-]{20,150}?)(?:\n|\r\n?)([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})', text)
        
        for match in title_matches:
            potential_title = match.group(1).strip()
            potential_author = match.group(2).strip()
            
            # Başlık + sonrasında isim kombinasyonu
            if len(potential_title) > 20 and is_valid_person_name(potential_author):
                score = 3.5  # Başlık sonrası yazarlar için yüksek güven puanı
                key = (potential_author, context)
                candidates['author_name'][key] = max(candidates['author_name'].get(key, 0), score)
                logging.info(f"Başlık sonrası yazar tespit edildi: {potential_author} (Başlık: {potential_title[:30]}...)")
        
        # Akademik unvanlarla birlikte yazar tespiti
        academic_title_patterns = [
            r"((?:Dr|Prof|Asst|Assoc|Professor|Ph\.D)\.?\s+[A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})",
            r"([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3}),\s*(?:Ph\.D|M\.D|B\.Sc|M\.Sc|M\.A|B\.A)"
        ]
        
        for pattern in academic_title_patterns:
            for match in re.finditer(pattern, text):
                name = match.group(1).strip()
                if is_valid_person_name(name):
                    score = 3.8  # Akademik unvan içeren isimler için yüksek güven puanı
                    key = (name, context)
                    candidates['author_name'][key] = max(candidates['author_name'].get(key, 0), score)
                    logging.info(f"Akademik unvanlı yazar tespit edildi: {name}")
                    
        # İlişkilendirme satırlarını tespit et - "Corresponding Author" gibi satırlar genellikle yazar isimleri içerir
        corresponding_patterns = [
            r"(?:Corresponding|Contact)\s+[Aa]uthor(?:s)?[:\s]+([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})",
            r"(?:Corresponding|Contact)\s+[Aa]uthor(?:s)?[:\s]+(?:[^,]+),\s*([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})",
            r"([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})(?:\s+\([^)]+\))?(?:\s*,\s*|\s+and\s+|\s*;\s*)([A-Z][a-zÀ-ÿ]+(?:\s+[A-Z][a-zÀ-ÿ]+){1,3})"
        ]
        
        for pattern in corresponding_patterns:
            for match in re.finditer(pattern, text):
                groups = match.groups()
                for potential_name in groups:
                    if potential_name and is_valid_person_name(potential_name.strip()):
                        name = potential_name.strip()
                        score = 3.9  # İlişkilendirme satırlarında geçen isimler için çok yüksek güven puanı
                        key = (name, context)
                        candidates['author_name'][key] = max(candidates['author_name'].get(key, 0), score)
                        logging.info(f"İlişkilendirme satırında yazar tespit edildi: {name}")
    
    # Kurum bilgilerinin tespit edilmesi ve güçlendirilmesi
    if 'institution_info' in options:
        # Akademik makale için tipik kurum/adres formatları
        institution_patterns = [
            # Kurum adı + şehir/adres
            r"([A-Z][a-zA-Z\s&,.'-]+(?:University|College|Institute|School|Laboratory|Department))(?:\s*,\s*|\s+at\s+)([A-Z][a-zA-Z\s,]+)",
            
            # İlk satırda kurumlar listesi, yaygın format
            r"([A-Z][a-zA-Z\s&\.'-]+(?:University|College|Institute|School|Laboratory|Department)[a-zA-Z\s&\.]+)(?:,|\n|\r\n)[^,.]*?([A-Z][a-zA-Z\s,]+\d{5,})",
            
            # Tipik adres formatı - kurum, şehir, ülke, posta kodu
            r"([A-Z][a-zA-Z\s&]+)(?:,|\s)+([A-Z][a-zA-Z\s]+),\s*([A-Z][a-zA-Z\s]+),?\s*\d{5,}",
            
            # Satır tabanlı adres ve kurum formatları
            r"^([A-Z][a-zA-Z\s&,.'()-]+(?:University|College|Institute|School|Laboratory|Department)[a-zA-Z\s&,.'-]*)$",
            
            # India gibi ülke adını takip eden posta kodu
            r"([A-Z][a-zA-Z\s&,.'()-]+),\s*([A-Z][a-zA-Z]+),\s*([A-Z][a-zA-Z]+)(?:\s+\d{5,})",
            
            # Özel olarak Hindistan adreslerine odaklan (verilen örnekteki gibi)
            r"([A-Z][a-zA-Z\s&,.'()-]+(?:University|College|Institute|School|Laboratory|Department)[a-zA-Z\s&,.'-]*),\s*([A-Z][a-zA-Z\s&,.'()-]+),\s*([A-Z][a-zA-Z]+)\s+(\d{6})",
            
            # Özel durum: Indian Institute of Information Technology Allahabad, Allahabad, Uttar Pradesh 211012, India
            r"(Indian\s+Institute\s+of\s+[A-Za-z\s]+)(?:,|\s)+([A-Za-z\s]+)(?:,|\s)+([A-Za-z\s]+)\s+(\d{6})"
        ]
        
        for pattern in institution_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groups()
                
                # Tüm satırı bir bütün olarak yüksek güvenirlikle kaydet
                full_match = match.group(0).strip()
                if len(full_match) > 10:
                    full_key = (full_match, context)
                    full_score = 4.0  # Tam adres için çok yüksek güven puanı
                    candidates['institution_info'][full_key] = max(candidates['institution_info'].get(full_key, 0), full_score)
                    logging.info(f"Tam adres/kurum satırı tespit edildi: {full_match}")
                
                # Tüm eşleşen grupları işle
                for group in groups:
                    if group and len(group.strip()) > 5:
                        institution = group.strip()
                        
                        # Özellikle "University", "Institute" vb. içeren kurumlar
                        if re.search(r'(?:University|College|Institute|School|Department|Laboratory)', institution, re.IGNORECASE):
                            score = 4.0  # Kurum adları için yüksek güven puanı
                        else:
                            # Olası şehir, eyalet veya ülke adları
                            score = 3.0
                            
                        key = (institution, context)
                        candidates['institution_info'][key] = max(candidates['institution_info'].get(key, 0), score)
                        logging.info(f"Kurum/adres bileşeni tespit edildi: {institution}")
        
        # İlave özel durum: "Indian Institute of Information Technology" gibi belirli kalıplar
        special_institutions = [
            "Indian Institute of Information Technology",
            "Indian Institute of Technology",
            "All India Institute of Medical Sciences"
        ]
        
        for special_inst in special_institutions:
            if special_inst in text:
                # İlgili satırı bul
                pattern = fr"({re.escape(special_inst)}[A-Za-z\s,]*)"
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    institution = match.group(1).strip()
                    if len(institution) > len(special_inst):  # Daha fazla bilgi içeriyorsa
                        score = 4.5  # Çok yüksek güven puanı
                        key = (institution, context)
                        candidates['institution_info'][key] = max(candidates['institution_info'].get(key, 0), score)
                        
                        # Tam satır içeriğini bulmak için çevresindeki metni incele
                        start_pos = max(0, match.start() - 20)
                        end_pos = min(len(text), match.end() + 150)
                        surrounding_text = text[start_pos:end_pos]
                        
                        # Adres ve ilgili diğer bilgileri bulmak için satır sonlarını ara
                        lines = re.split(r'[\n\r]+', surrounding_text)
                        for line in lines:
                            if institution in line and len(line.strip()) > len(institution):
                                full_line = line.strip()
                                full_key = (full_line, context)
                                full_score = 4.5
                                candidates['institution_info'][full_key] = max(candidates['institution_info'].get(full_key, 0), full_score)
                                logging.info(f"Özel kurum satırı tespit edildi: {full_line}")
        
        # Sayısal posta kodu içeren satırlar
        postal_code_pattern = r"([A-Za-z,\s]+)\s+(\d{5,6})(?:,\s*([A-Za-z]+))?"
        postal_matches = re.finditer(postal_code_pattern, text)
        
        for match in postal_matches:
            if match.group(0).strip():
                address_with_postal = match.group(0).strip()
                key = (address_with_postal, context)
                score = 3.8  # Posta kodu içeren adresler için yüksek güven puanı
                candidates['institution_info'][key] = max(candidates['institution_info'].get(key, 0), score)
                logging.info(f"Posta kodu içeren adres tespit edildi: {address_with_postal}")
    
    # 1. İletişim bilgilerini daha agresif şekilde ara
    if 'contact_info' in options:
        # E-posta adreslerine özel odaklanma
        email_pattern = r'\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b'
        email_matches = re.finditer(email_pattern, text)
        
        for match in email_matches:
            email = match.group().strip()
            
            # E-posta için yüksek güvenilirlik puanı ver
            score = 3.0  # Çok yüksek güvenilirlik
            
            # Akademik uzantılar için ek puan
            if re.search(r'\.edu$|\.ac\.[a-z]{2,}$|@university|@faculty|@dtu|@ieee|@gmail', email, re.IGNORECASE):
                score += 0.5
            
            key = (email, context)
            candidates['contact_info'][key] = max(candidates['contact_info'].get(key, 0), score)
            
            # E-posta ile ilişkili isim tespiti (genellikle e-posta adresinden önce isim gelir)
            prior_text = text[max(0, match.start() - 100):match.start()]
            name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*$', prior_text)
            
            if name_match and 'author_name' in options:
                name = name_match.group(1).strip()
                if is_valid_person_name(name):
                    name_score = 2.5
                    name_key = (name, context)
                    candidates['author_name'][name_key] = max(candidates['author_name'].get(name_key, 0), name_score)

def extract_potential_person_names(text, min_score=0.1):
    """
    Metinden potansiyel kişi isimlerini çıkarır.
    """
    
    # NLP modeli kullanarak kişi isimleri çıkarılır
    doc = nlp(text)
    
    # İsimlerin güven skorları ile birlikte bir liste oluşturulur
    persons = []
    
    # Named Entity Recognition (NER) kullanarak isimleri buluyor
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            if is_valid_person_name(ent.text):
                confidence = get_confidence_score(ent.text, text)
                # Min skordan büyükse listeye ekle
                if confidence >= min_score:
                    persons.append({"text": ent.text, "confidence": confidence})
    
    # Özel kalıpları kullanarak isim formatlarını bul (NER tarafından kaçırılmış olabilir)
    # Bunlar özellikle bilimsel makaleler için önemli
    person_patterns = [
        # ORCID ID ile ilişkili isimler
        r"([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)(?:\s+)?(?:orcid|ORCID)",
        
        # Yazar ismi ve email adresi deseni
        r"([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)(?:\s+)?[\(\[]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*[\)\]]",
        
        # Akademik ünvanlar ile isimler
        rf"{TITLE_REGEX}([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)",
        
        # IEEE formatındaki isimler: "John Smith, Member, IEEE"
        r"([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)(?:,\s+(?:Member|Senior Member|Fellow|Student Member|Associate Member),\s+IEEE)",
        
        # "Er. " önekine sahip isimler (Hindistan'da mühendisler için yaygın ünvan)
        r"(Er\.\s+[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)+)",

        # Yalın isim formatı (yalnızca büyük harfle başlayan kelimeler)
        r"\b([A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+){1,3})\b",
    ]
    
    # Tüm kalıpları kontrol et
    for pattern in person_patterns:
        for match in re.finditer(pattern, text):
            # İlk yakalama grubu isimdir
            name = match.group(1).strip()
            if is_valid_person_name(name):
                # Daha önce eklenmiş mi kontrol et
                if not any(p["text"] == name for p in persons):
                    confidence = get_confidence_score(name, text)
                    # "Er." ünvanı varsa ek güven puanı ver
                    if name.startswith("Er.") or "Er. " in name:
                        confidence += 0.2  # Güven skorunu artır
                    if confidence >= min_score:
                        persons.append({"text": name, "confidence": confidence})
    
    # Tekrar eden öğeleri kaldır
    # (Aynı isim farklı kalıplar tarafından yakalanmış olabilir)
    unique_persons = []
    seen_names = set()
    
    for person in persons:
        if person["text"] not in seen_names:
            seen_names.add(person["text"])
            unique_persons.append(person)
    
    return sorted(unique_persons, key=lambda x: x["confidence"], reverse=True)