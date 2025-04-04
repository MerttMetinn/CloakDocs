import os
from pypdf import PdfReader
import re
import logging


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF and separate into sections"""
    full_text = ""
    sections = {
        "main_content": "",
        "excluded_sections": "",  # References, acknowledgements, introduction, etc.
        "first_page": "",         # First page content for author identification
        "header_sections": ""     # Title, author info, abstract sections
    }
    
    # Define sections to exclude from anonymization (English only)
    excluded_section_patterns = [
        r"(?i)INTRODUCTION",
        r"(?i)RELATED\s+WORKS?",
        r"(?i)REFERENCES",
        r"(?i)BIBLIOGRAPHY",
        r"(?i)ACKNOWLEDGEMENTS?",
        r"(?i)CITED\s+REFERENCES"
    ]
    
    # Daha kapsamlı referans bölümü tanımlama desenleri
    reference_section_patterns = [
        r"(?i)^\s*REFERENCES\s*$",
        r"(?i)^\s*BIBLIOGRAPHY\s*$",
        r"(?i)^\s*CITED\s+REFERENCES\s*$",
        r"(?i)^\s*REFERANSLAR\s*$",
        r"(?i)^\s*KAYNAKLAR\s*$",
        r"(?i)^\s*KAYNAKÇA\s*$",
        r"(?i)^\s*REFERENCES\s+AND\s+CITATIONS\s*$"
    ]
    
    # Regex pattern to identify section headers
    section_header_pattern = r"(?i)^\s*(?:\d+\.)*\s*([A-Za-z\s]+)$"
    
    # Author context phrases - these indicate high probability of author names nearby
    author_context_phrases = [
        r"(?i)corresponding author",
        r"(?i)author(s)?[:]?",
        r"(?i)prepared by",
        r"(?i)written by",
        r"(?i)submitted by",
        r"(?i)affiliation",
        r"(?i)department of",
        r"(?i)faculty of",
        r"(?i)school of",
        r"(?i)university of",
        r"(?i)institute of",
        r"(?i)contact[:]?"
    ]
    
    # Title indicators
    title_patterns = [
        r"(?i)^ABSTRACT",
        r"(?i)^TITLE[:]?",
        r"(?i)^KEYWORDS[:]?"
    ]
    
    with open(pdf_path, "rb") as file:
        reader = PdfReader(file)
        current_section = "main_content"  # Default to main content
        in_reference_section = False  # Referanslar bölümünde olup olmadığımızı takip et
        
        # Process each page
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text() + "\n"
            full_text += page_text
            
            # First page is treated specially for author detection
            if page_num == 0:
                sections["first_page"] = page_text
                
                # Look for author context phrases on first page
                for phrase in author_context_phrases:
                    if re.search(phrase, page_text):
                        # Extract lines around author indicators for header_sections
                        lines = page_text.split('\n')
                        for i, line in enumerate(lines):
                            if re.search(phrase, line):
                                # Add 3 lines before and 3 lines after to header_sections
                                start_idx = max(0, i-3)
                                end_idx = min(len(lines), i+4)
                                sections["header_sections"] += "\n".join(lines[start_idx:end_idx]) + "\n"
                
                # Look for title indicators on first page
                for pattern in title_patterns:
                    if re.search(pattern, page_text):
                        # Title area is likely followed by authors
                        match_pos = [m.start() for m in re.finditer(pattern, page_text)]
                        for pos in match_pos:
                            # Extract ~10 lines after title marker
                            excerpt = page_text[pos:pos+1000]  # Roughly 10 lines
                            lines = excerpt.split('\n')[:10]
                            sections["header_sections"] += "\n".join(lines) + "\n"
            
            # Referans bölümünü tespit et
            for pattern in reference_section_patterns:
                if re.search(pattern, page_text, re.MULTILINE):
                    in_reference_section = True
                    current_section = "excluded_sections"
                    logging.info(f"Referans bölümü tespit edildi, sayfa {page_num+1}")
                    break
            
            # Eğer referans bölümündeyse tüm metni excluded_sections'a ekle
            if in_reference_section:
                sections["excluded_sections"] += page_text
                continue
            
            # Check each line in the page for section headers
            lines = page_text.split('\n')
            for line in lines:
                # Is this a new section heading?
                match = re.match(section_header_pattern, line.strip())
                if match:
                    section_title = match.group(1).strip().upper()
                    
                    # Referans bölümü kontrolü
                    is_reference_section = False
                    for pattern in reference_section_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            current_section = "excluded_sections"
                            in_reference_section = True
                            is_reference_section = True
                            break
                    
                    if is_reference_section:
                        continue
                    
                    # Is this an excluded section?
                    excluded = False
                    for pattern in excluded_section_patterns:
                        if re.search(pattern, section_title):
                            current_section = "excluded_sections"
                            excluded = True
                            break
                    
                    # If not an excluded section, return to main content
                    if not excluded:
                        current_section = "main_content"
                
                # Add to relevant section
                sections[current_section] += line + "\n"
    
    # Referanslar bölümü içeriğini günlüğe kaydet
    if sections["excluded_sections"]:
        ref_text_sample = sections["excluded_sections"][:200] + "..." if len(sections["excluded_sections"]) > 200 else sections["excluded_sections"]
        logging.info(f"Anonimleştirmeden hariç tutulan bölümler tespit edildi: {len(sections['excluded_sections'])} karakter")
        logging.info(f"Örnek içerik: {ref_text_sample}")
    
    return {"full_text": full_text, "sections": sections} 