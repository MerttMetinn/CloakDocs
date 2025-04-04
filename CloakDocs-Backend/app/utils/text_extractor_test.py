import os
import sys
import json
import argparse
from datetime import datetime

# Proje kök dizinini path'e ekle
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Kendi modüllerimizi import et
from app.utils.text_extractor import extract_text_from_pdf

def test_pdf_extraction(pdf_path, output_dir=None):
    """
    PDF'den metin çıkarma işlemini test eder ve sonuçları dosyalara kaydeder
    
    Args:
        pdf_path (str): İşlenecek PDF dosyasının yolu
        output_dir (str, optional): Çıktı dosyalarının kaydedileceği dizin. 
                                     Belirtilmezse PDF ile aynı dizin kullanılır.
    """
    print(f"PDF dosyası işleniyor: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"HATA: {pdf_path} dosyası bulunamadı!")
        return False
    
    # Çıktı dizinini belirle
    if not output_dir:
        output_dir = os.path.dirname(pdf_path)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Çıktı dizini oluşturuldu: {output_dir}")
    
    # PDF dosya adını al
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Zaman damgası oluştur
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # PDF'den metin çıkar
        result = extract_text_from_pdf(pdf_path)
        
        # Tam metni kaydet
        full_text_path = os.path.join(output_dir, f"{pdf_name}_full_text_{timestamp}.txt")
        with open(full_text_path, "w", encoding="utf-8") as f:
            f.write(result["full_text"])
        print(f"Tam metin kaydedildi: {full_text_path}")
        
        # Ana içeriği kaydet
        main_content_path = os.path.join(output_dir, f"{pdf_name}_main_content_{timestamp}.txt")
        with open(main_content_path, "w", encoding="utf-8") as f:
            f.write(result["sections"]["main_content"])
        print(f"Ana içerik kaydedildi: {main_content_path}")
        
        # Hariç tutulan bölümleri kaydet
        excluded_path = os.path.join(output_dir, f"{pdf_name}_excluded_{timestamp}.txt")
        with open(excluded_path, "w", encoding="utf-8") as f:
            f.write(result["sections"]["excluded_sections"])
        print(f"Hariç tutulan bölümler kaydedildi: {excluded_path}")
        
        # İlk sayfayı kaydet
        first_page_path = os.path.join(output_dir, f"{pdf_name}_first_page_{timestamp}.txt")
        with open(first_page_path, "w", encoding="utf-8") as f:
            f.write(result["sections"]["first_page"])
        print(f"İlk sayfa kaydedildi: {first_page_path}")
        
        # Başlık bölümlerini kaydet
        header_path = os.path.join(output_dir, f"{pdf_name}_header_{timestamp}.txt")
        with open(header_path, "w", encoding="utf-8") as f:
            f.write(result["sections"]["header_sections"])
        print(f"Başlık bölümleri kaydedildi: {header_path}")
        
        # Özet bilgileri JSON formatında kaydet
        summary = {
            "pdf_name": pdf_name,
            "timestamp": timestamp,
            "character_counts": {
                "full_text": len(result["full_text"]),
                "main_content": len(result["sections"]["main_content"]),
                "excluded_sections": len(result["sections"]["excluded_sections"]),
                "first_page": len(result["sections"]["first_page"]),
                "header_sections": len(result["sections"]["header_sections"])
            },
            "output_files": {
                "full_text": full_text_path,
                "main_content": main_content_path,
                "excluded_sections": excluded_path,
                "first_page": first_page_path,
                "header_sections": header_path
            }
        }
        
        summary_path = os.path.join(output_dir, f"{pdf_name}_summary_{timestamp}.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"Özet bilgiler kaydedildi: {summary_path}")
        
        print("İşlem başarıyla tamamlandı!")
        return True
        
    except Exception as e:
        print(f"HATA: PDF işlenirken bir sorun oluştu: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF metin çıkarma test aracı")
    parser.add_argument("pdf_path", help="İşlenecek PDF dosyasının yolu")
    parser.add_argument("--output-dir", help="Çıktı dosyalarının kaydedileceği dizin (opsiyonel)")
    
    args = parser.parse_args()
    
    test_pdf_extraction(args.pdf_path, args.output_dir) 