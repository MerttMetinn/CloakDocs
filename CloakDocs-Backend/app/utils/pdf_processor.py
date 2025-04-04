import os
import re
import PyPDF2
import spacy
from pdfminer.high_level import extract_text
import yake
import logging
from typing import List, Dict, Union, Tuple, Optional
import traceback

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PdfProcessor:
    """
    Class for processing PDF files and extracting keywords
    """
    
    def __init__(self):
        # Load SpaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("SpaCy model loaded: en_core_web_sm")
        except Exception as e:
            logger.error(f"Error loading SpaCy model: {e}")
            self.nlp = None
            
        # Configure YAKE keyword extractor
        try:
            self.yake_extractor = yake.KeywordExtractor(
                lan="en", 
                n=3,  # n-gram size
                dedupLim=0.9,  # threshold for filtering similar keywords
                dedupFunc='seqm',  # similarity measurement method
                windowsSize=1,
                top=20
            )
            logger.info("YAKE keyword extractor ready")
        except Exception as e:
            logger.error(f"Error creating YAKE keyword extractor: {e}")
            self.yake_extractor = None
        
        # Abbreviations that should remain uppercase
        self.abbreviations = [
            "EEG", "CNN", "DEAP", "DENS", "LSTM", "SEED", "FFT", "CWT", 
            "DFT", "DTFT", "DCT", "SVM", "KNN", "PCA", "LDA", "ICA", 
            "ANN", "RNN", "GRU", "fMRI", "MEG", "ECG", "EMG", "EOG"
        ]
        
        # Known multi-word terms to preserve as single keywords
        self.multi_word_terms = {
            "abnormal behavior detection": ["abnormal", "behavior", "detection"],
            "action sequence analysis": ["action", "sequence", "analysis"],
            "behavioral intention": ["behavioral", "intention"],
            "video surveillance": ["video", "surveillance"],
            "public safety": ["public", "safety"],
            "emotion recognition": ["emotion", "recognition"],
            "eeg data": ["eeg", "data"],
            "deap dataset": ["deap", "dataset"],
            "band power": ["band", "power"],
            "lstm network": ["lstm", "network"],
            "eeg signals": ["eeg", "signals"],
            "frequency analysis": ["frequency", "analysis"],
            "signal classification": ["signal", "classification"],
            "mental arithmetic task": ["mental", "arithmetic", "task"],
            "affective computing": ["affective", "computing"],
            "feature extraction": ["feature", "extraction"],
            "time domain": ["time", "domain"],
            "frequency domain": ["frequency", "domain"],
            "signal processing": ["signal", "processing"],
            "machine learning": ["machine", "learning"],
            "deep learning": ["deep", "learning"]
        }
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file
        
        Args:
            pdf_path: Full path to the PDF file
            
        Returns:
            str: Extracted text from the PDF
        """
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            
            # First try with PyPDF2
            try:
                text = ""
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text += page.extract_text() + "\n"
                
                if text.strip():
                    logger.info(f"Text successfully extracted with PyPDF2 ({len(text)} characters)")
                    return text
            except Exception as e:
                logger.warning(f"Error extracting text with PyPDF2: {e}")
            
            # If PyPDF2 fails, try with pdfminer.six
            try:
                text = extract_text(pdf_path)
                if text.strip():
                    logger.info(f"Text successfully extracted with pdfminer.six ({len(text)} characters)")
                    return text
            except Exception as e:
                logger.error(f"Error extracting text with pdfminer.six: {e}")
            
            return ""
            
        except Exception as e:
            logger.error(f"General error extracting text from PDF: {e}")
            return ""
    
    def extract_keywords_section(self, text: str) -> str:
        """
        Extract the "Keywords" or similar section from text
        
        Args:
            text: Extracted text from the PDF
            
        Returns:
            str: Text from the Keywords section
        """
        try:
            logger.info("Searching for Keywords section...")
            
            # Daha geniş bir başlık için daha esnek bir pattern kullanımı
            patterns = [
                # Kesmeyle veya tirelerle ayrılmış keywords
                r'(?i)Keywords\s*[-—:]\s*([\s\S]*?)(?=\n\s*\n|\n\s*[A-Z0-9][A-Z0-9\s\.]*\n|\s{4,}|ABSTRACT|INTRODUCTION|I\.\s+INTRODUCTION)',
                # Standart format
                r'(?i)Keywords\s*:\s*([\s\S]*?)(?=\n\s*\n|\n\s*[A-Z0-9][A-Z0-9\s\.]*\n|\s{4,}|ABSTRACT|INTRODUCTION|I\.\s+INTRODUCTION)',
                # Alternatif yazım
                r'(?i)Key\s+[wW]ords\s*[:;-—]\s*([\s\S]*?)(?=\n\s*\n|\n\s*[A-Z0-9][A-Z0-9\s\.]*\n|\s{4,}|ABSTRACT|INTRODUCTION|I\.\s+INTRODUCTION)',
                # Türkçe
                r'(?i)Anahtar\s+[kK]elime(?:ler)?\s*[:;-—]\s*([\s\S]*?)(?=\n\s*\n|\n\s*[A-Z0-9][A-Z0-9\s\.]*\n|\s{4,}|ABSTRACT|INTRODUCTION|I\.\s+INTRODUCTION)',
                # Index Terms
                r'(?i)INDEX\s+TERMS\s*[:;-—]?\s*([\s\S]*?)(?=\n\s*\n|\n\s*[A-Z0-9][A-Z0-9\s\.]*\n|\s{4,}|ABSTRACT|INTRODUCTION|I\.\s+INTRODUCTION)',
            ]
            
            # Orijinal metinde ara
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    keywords_text = match.group(1).strip()
                    logger.info(f"Keywords section found: '{keywords_text[:150]}...'")
                    return keywords_text
            
            # Başka türlü ara
            normalized_text = re.sub(r'\n', ' ', text)
            normalized_text = re.sub(r'\s+', ' ', normalized_text)
            
            simple_patterns = [
                r'(?i)Keywords\s*[-—:]\s*(.*?)(?=\s{4,}|ABSTRACT|INTRODUCTION|\.|$)',
                r'(?i)Key\s+[wW]ords\s*[:;-—]\s*(.*?)(?=\s{4,}|ABSTRACT|INTRODUCTION|\.|$)',
                r'(?i)INDEX\s+TERMS\s*[:;-—]?\s*(.*?)(?=\s{4,}|ABSTRACT|INTRODUCTION|\.|$)',
            ]
            
            for pattern in simple_patterns:
                match = re.search(pattern, normalized_text, re.DOTALL)
                if match:
                    keywords_text = match.group(1).strip()
                    logger.info(f"Keywords section found with simple pattern: '{keywords_text[:150]}...'")
                    return keywords_text
            
            logger.warning("Keywords section not found")
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting Keywords section: {e}")
            traceback.print_exc()
            return ""
    
    def normalize_case(self, keyword: str) -> str:
        """
        Normalize case for keywords, keeping abbreviations uppercase
        
        Args:
            keyword: Keyword to normalize
        
        Returns:
            str: Normalized keyword
        """
        # Keep known abbreviations uppercase
        if keyword.upper() in self.abbreviations:
            return keyword.upper()
        
        # Check if the keyword contains any known abbreviations
        words = keyword.split()
        normalized_words = []
        
        for word in words:
            if word.upper() in self.abbreviations:
                normalized_words.append(word.upper())
            elif word.lower() in ["of", "the", "and", "in", "to", "for", "with", "by", "on", "at", "from", "as"]:
                normalized_words.append(word.lower())
            else:
                # Capitalize first letter
                normalized_words.append(word.capitalize())
        
        return " ".join(normalized_words)

    def parse_keywords_from_section(self, keywords_text: str) -> List[str]:
        """
        Parse keywords from the extracted Keywords section text
        
        Args:
            keywords_text: Text from the Keywords section
            
        Returns:
            List[str]: List of parsed keywords
        """
        try:
            # Boş metin kontrolü
            if not keywords_text:
                return []
            
            # Orijinal metni kaydet
            original_text = keywords_text
            logger.debug(f"Raw keyword text: '{keywords_text}'")
            
            # "ABSTRACT" ve sonrasını kaldır
            if "ABSTRACT" in keywords_text:
                keywords_text = keywords_text.split("ABSTRACT")[0]
                logger.debug(f"ABSTRACT removed: '{keywords_text}'")
            
            # Parantez içi içeriği kaldır
            keywords_text = re.sub(r'\([^)]*\)', '', keywords_text)
            
            # Ayrıştırıcıyı algıla
            delimiter = None
            
            # Virgülle ayrılmış format
            if "," in keywords_text:
                delimiter = ","
                logger.debug("Comma delimiter detected")
            # Noktalı virgülle ayrılmış format
            elif ";" in keywords_text:
                delimiter = ";"
                logger.debug("Semicolon delimiter detected")
            # Tire veya uzun tire ile ayrılmış format
            elif re.search(r'[-—]', keywords_text):
                delimiter = "-"
                logger.debug("Dash delimiter detected")
            # Çok satırlı format
            elif "\n" in keywords_text and len(keywords_text.strip().split("\n")) > 1:
                # Satırları ayrıştır
                lines = [line.strip() for line in keywords_text.split("\n") if line.strip()]
                
                # Başlık ve boş satırları filtrele
                filtered_lines = []
                for line in lines:
                    # Başlık satırlarını atla
                    if re.match(r'^(Keywords|ARTICLE INFO|INDEX TERMS):?\s*$', line, re.IGNORECASE):
                        continue
                    # "ABSTRACT" içeren satırları atla
                    if "ABSTRACT" in line:
                        continue
                    # Parantezleri temizle
                    clean_line = re.sub(r'\([^)]*\)', '', line).strip()
                    if clean_line:
                        filtered_lines.append(clean_line)
                
                if filtered_lines:
                    logger.debug(f"Line-based keywords: {filtered_lines}")
                    # Orijinal metindeki yazımı koru
                    return filtered_lines
            
            # Ayırıcı kullanılarak anahtar kelimeleri çıkar
            if delimiter:
                keywords = [kw.strip() for kw in re.split(f'[{delimiter}]', keywords_text) if kw.strip()]
                
                # Son temizlik
                filtered_keywords = []
                for kw in keywords:
                    # Başlık terimlerini atla
                    if kw.lower() in ["keywords", "article", "info", "abstract", "component", "components"]:
                        continue
                    # Genel önekleri/sonekleri temizle
                    kw = re.sub(r'^(component[s]?|and)\s*[:;]*\s*', '', kw)
                    kw = re.sub(r'\s+(component[s]?|and)\s*$', '', kw)
                    
                    if kw and len(kw) > 1:  # En az 2 karakter
                        # Orijinal metindeki yazımı koru - normalize etme
                        filtered_keywords.append(kw)
                
                return filtered_keywords
            
            # Ayırıcı bulunamadıysa, satır sonlarını kontrol et ve boşluklarla ayrılmış olabilir
            if "\n" in original_text:
                # Satır sonlarını boşluklara dönüştür
                clean_text = re.sub(r'\n', ' ', original_text)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                # Başlık bilgilerini kaldır
                clean_text = re.sub(r'^Keywords\s*[-—:]\s*', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'^INDEX\s+TERMS\s*[-—:]\s*', '', clean_text, flags=re.IGNORECASE)
                
                # Boşluklarla ayrılmış kelimeleri al
                words = clean_text.split()
                
                if words:
                    return [clean_text]  # Tüm metni tek bir anahtar kelime olarak döndür
            
            # Hiçbir şey bulunamadıysa, orijinal metni olduğu gibi döndür
            logger.warning("Could not parse keywords, returning original text")
            return [original_text.strip()]
            
        except Exception as e:
            logger.error(f"Error parsing keywords: {e}")
            traceback.print_exc()
            return []
    
    def extract_keywords_with_yake(self, text: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Extract keywords using YAKE algorithm
        
        Args:
            text: Extracted text from the PDF
            top_n: Maximum number of keywords to return
            
        Returns:
            List[Tuple[str, float]]: List of keyword and score pairs
        """
        try:
            if not self.yake_extractor or not text.strip():
                return []
            
            logger.info(f"Extracting keywords with YAKE (top {top_n})...")
            keywords = self.yake_extractor.extract_keywords(text)
            
            # Sort by score (lower is better in YAKE)
            keywords = sorted(keywords, key=lambda x: x[1])[:top_n]
            
            logger.info(f"Extracted {len(keywords)} keywords with YAKE")
            return keywords
            
        except Exception as e:
            logger.error(f"Error extracting keywords with YAKE: {e}")
            return []

    def extract_keywords_with_spacy(self, text: str, top_n: int = 20) -> List[str]:
        """
        Extract potential keywords using SpaCy's NLP capabilities
        
        Args:
            text: The text to analyze
            top_n: Maximum number of keywords to return
            
        Returns:
            List[str]: List of potential keywords
        """
        try:
            if not self.nlp or not text.strip():
                return []
                
            logger.info("Extracting keywords with SpaCy...")
            
            # Process the text with SpaCy
            doc = self.nlp(text)
            
            # Extract noun phrases and named entities
            noun_phrases = []
            for chunk in doc.noun_chunks:
                # Clean and normalize the noun phrase
                clean_phrase = ' '.join([token.text for token in chunk 
                                        if not token.is_stop and not token.is_punct])
                if clean_phrase and len(clean_phrase) > 2:
                    noun_phrases.append(clean_phrase)
            
            entities = [ent.text for ent in doc.ents 
                       if ent.label_ in ['ORG', 'PRODUCT', 'GPE', 'EVENT', 'WORK_OF_ART']]
            
            # Combine and filter candidates
            candidates = noun_phrases + entities
            
            # Count frequency
            candidate_freq = {}
            for candidate in candidates:
                candidate_lower = candidate.lower()
                candidate_freq[candidate_lower] = candidate_freq.get(candidate_lower, 0) + 1
            
            # Sort by frequency
            sorted_candidates = sorted(candidate_freq.items(), key=lambda x: x[1], reverse=True)
            top_candidates = [candidate for candidate, freq in sorted_candidates[:top_n]]
            
            # Normalize case of final keywords
            normalized_keywords = [self.normalize_case(kw) for kw in top_candidates]
            
            logger.info(f"Extracted {len(normalized_keywords)} keywords with SpaCy")
            return normalized_keywords
            
        except Exception as e:
            logger.error(f"Error extracting keywords with SpaCy: {e}")
            return []
    
    def process_pdf(self, pdf_path: str) -> Dict[str, Union[List[str], List[Tuple[str, float]]]]:
        """
        Process a PDF file to extract keywords
        
        Args:
            pdf_path: Full path to the PDF file
            
        Returns:
            Dict: Dictionary containing keywords extracted with different methods
        """
        result = {
            "manual_keywords": [],  # Keywords from the Keywords section
            "yake_keywords": [],    # Keywords extracted with YAKE
            "spacy_keywords": []    # Keywords extracted with SpaCy
        }
        
        try:
            logger.info(f"Processing PDF: {pdf_path}")
            
            # Check if file exists
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return result
            
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            if not text.strip():
                logger.warning(f"Could not extract text from PDF: {pdf_path}")
                return result
            
            # Find and parse Keywords section
            keywords_section = self.extract_keywords_section(text)
            
            # Orijinal metni koru, normalize etme!
            result["manual_keywords"] = self.parse_keywords_from_section(keywords_section)
            
            # If manual keywords not found, try automatic methods
            if not result["manual_keywords"]:
                logger.info("Manual keywords not found, using automatic extraction methods")
                
                # YAKE keywords
                result["yake_keywords"] = self.extract_keywords_with_yake(text)
                
                # SpaCy keywords (orijinal yazımı koru)
                spacy_keywords = self.extract_keywords_with_spacy(text)
                result["spacy_keywords"] = spacy_keywords  # normalize_case kullanmıyoruz
                
                # If automatic methods found keywords, log them
                if result["yake_keywords"] or result["spacy_keywords"]:
                    logger.info("Extracted keywords using automatic methods")
                else:
                    logger.warning("No keywords found with any method")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return result

    def detect_format(self, text: str) -> str:
        """
        Detect the format of keywords in the text
        
        Args:
            text: The keywords section text
            
        Returns:
            str: Detected format description
        """
        # Check for comma-separated format
        if "," in text:
            return "comma-separated"
        
        # Check for semicolon-separated format
        if ";" in text:
            return "semicolon-separated"
        
        # Check for line-separated format
        if "\n" in text and len(text.split("\n")) > 1:
            return "line-separated"
        
        # Check for dash-separated format
        if "-" in text or "—" in text:
            return "dash-separated"
        
        # Default to space-separated
        return "space-separated"


# Test the class
if __name__ == "__main__":
    processor = PdfProcessor()
    
    # Test PDF
    test_pdf = "path/to/test.pdf"
    
    if os.path.exists(test_pdf):
        results = processor.process_pdf(test_pdf)
        print("Manual keywords:", results["manual_keywords"])
        print("YAKE keywords:", results["yake_keywords"])
        print("SpaCy keywords:", results["spacy_keywords"])
    else:
        print(f"Test PDF not found: {test_pdf}")