"use client"

import { useState, useEffect } from 'react';
import { Document, Page, Text, View, StyleSheet, PDFViewer } from '@react-pdf/renderer';
import { REVIEW_ENDPOINTS, ANONYMIZE_ENDPOINTS } from "@/app/lib/apiConfig";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/app/components/ui/button";
import { X, Download, Loader2 } from "lucide-react";

// PDF önizleme stilleri
const styles = StyleSheet.create({
  page: {
    flexDirection: 'column',
    backgroundColor: '#fff',
    padding: 30,
  },
  section: {
    margin: 10,
    padding: 10,
  },
  title: {
    fontSize: 24,
    marginBottom: 20,
    textAlign: 'center',
  },
  text: {
    fontSize: 12,
    marginBottom: 10,
    lineHeight: 1.5,
  },
  header: {
    fontSize: 16,
    marginBottom: 10,
    marginTop: 20,
    fontWeight: 'bold',
  },
});

// PdfDocument bileşeni
interface PdfDocumentData {
  title?: string;
  abstract?: string;
  authors?: string;
}

const PdfDocument = ({ pdfData }: { pdfData: PdfDocumentData }) => (
  <Document>
    <Page size="A4" style={styles.page}>
      <Text style={styles.title}>{pdfData?.title || "Makale Başlığı"}</Text>
      <View style={styles.section}>
        <Text style={styles.header}>Makale Özeti</Text>
        <Text style={styles.text}>{pdfData?.abstract || "Makale içeriği yüklenemedi."}</Text>
      </View>
      <View style={styles.section}>
        <Text style={styles.header}>Yazarlar</Text>
        <Text style={styles.text}>{pdfData?.authors || "Yazar bilgileri mevcut değil."}</Text>
      </View>
      {/* Gerçek makale daha fazla içerik olacaktır */}
      <Text style={{ fontSize: 10, textAlign: 'center', marginTop: 20, color: '#666' }}>
        Bu yalnızca bir önizlemedir. Tam makaleyi indirmek için Dosyayı İndir butonunu kullanın.
      </Text>
    </Page>
  </Document>
);

interface PdfPreviewProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  trackingNumber: string;
  fileName: string;
  isReviewed?: boolean;
}

export default function PdfPreview({ isOpen, onOpenChange, trackingNumber, fileName, isReviewed = false }: PdfPreviewProps) {
  const [loading, setLoading] = useState(true);
  const [pdfData, setPdfData] = useState<PdfDocumentData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [anonymizedFileName, setAnonymizedFileName] = useState<string | null>(null);

  // Anonimleştirilmiş dosya bilgisini getir
  const fetchAnonymizedFileName = async (trackingNumber: string) => {
    try {
      const response = await fetch(ANONYMIZE_ENDPOINTS.INFO(trackingNumber));
      if (!response.ok) {
        throw new Error('Anonimleştirilmiş dosya bilgisi alınamadı');
      }
      const data = await response.json();
      if (data.success && data.anonymized_file) {
        setAnonymizedFileName(data.anonymized_file.filename);
        return data.anonymized_file.filename;
      }
      return null;
    } catch (error) {
      console.error('Anonimleştirilmiş dosya bilgisi getirme hatası:', error);
      return null;
    }
  };

  // PDF'i indirme fonksiyonu
  const handleDownload = async (trackingNumber: string) => {
    // Önce dosya adını almaya çalış
    let fileNameToUse = anonymizedFileName;
    
    if (!fileNameToUse) {
      // Henüz dosya adı alınmadıysa, almaya çalış
      fileNameToUse = await fetchAnonymizedFileName(trackingNumber);
    }
    
    // Eğer blob varsa, doğrudan blob'dan indir
    if (pdfBlob) {
      const url = URL.createObjectURL(pdfBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileNameToUse || `${isReviewed ? 'reviewed_' : 'anonymized_'}${trackingNumber}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      return;
    }
    
    // Blob yoksa, API'den indir
    const downloadUrl = isReviewed 
      ? ANONYMIZE_ENDPOINTS.DOWNLOAD_REVIEWED(trackingNumber)
      : ANONYMIZE_ENDPOINTS.DOWNLOAD(trackingNumber);
    
    try {
      const response = await fetch(downloadUrl);
      if (!response.ok) throw new Error('PDF indirilemedi');
      
      const blob = await response.blob();
      
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileNameToUse || `${isReviewed ? 'reviewed_' : 'anonymized_'}${trackingNumber}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('PDF indirme hatası:', error);
      setError('PDF indirilemedi: ' + (error as Error).message);
    }
  }

  // PDF'i güvenli bir şekilde yükle ve görüntüle
  const fetchPdf = async () => {
    setLoading(true);
    setError(null);
    setPdfUrl(null);
    setPdfBlob(null);
    
    try {
      // Önizleme verilerini getir
      const previewUrl = REVIEW_ENDPOINTS.PAPER_PREVIEW(trackingNumber);
      const previewResponse = await fetch(previewUrl);
      
      if (!previewResponse.ok) {
        throw new Error('Makale içeriği alınamadı');
      }
      
      const previewData = await previewResponse.json();
      setPdfData(previewData);
      
      // PDF dosyasını getir, otomatik indirmeyi engellemek için blob olarak işle
      const pdfUrl = isReviewed
        ? ANONYMIZE_ENDPOINTS.DOWNLOAD_REVIEWED(trackingNumber)
        : ANONYMIZE_ENDPOINTS.DOWNLOAD(trackingNumber);
      
      const pdfResponse = await fetch(pdfUrl);
      
      if (!pdfResponse.ok) {
        throw new Error('PDF dosyası yüklenemedi');
      }
      
      const blob = await pdfResponse.blob();
      setPdfBlob(blob);
      
      // Blob'dan URL oluştur ve güvenli bir şekilde ayarla
      const blobUrl = URL.createObjectURL(blob);
      setPdfUrl(blobUrl);
      
      setLoading(false);
    } catch (error) {
      console.error('PDF yükleme hatası:', error);
      setError((error as Error).message);
      setLoading(false);
    }
  };

  // Sheet açıldığında PDF'i yükle
  useEffect(() => {
    if (isOpen && trackingNumber) {
      // Anonimleştirilmiş dosya adını al
      fetchAnonymizedFileName(trackingNumber);
      
      // PDF'i güvenli bir şekilde yükle
      fetchPdf();
    }
    
    // Component unmount olduğunda URL ve blob'u temizle
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
        setPdfUrl(null);
        setPdfBlob(null);
      }
    };
  }, [isOpen, trackingNumber, isReviewed]);

  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-[80vw] md:max-w-[70vw] lg:max-w-[65vw] overflow-auto p-0 w-full" side="right">
        <div className="bg-gradient-to-r from-[#d4af37]/90 to-[#d4af37] p-6 flex items-center justify-between sticky top-0 z-10">
          <SheetTitle className="text-xl font-semibold text-white">
            {isReviewed ? 'Değerlendirilmiş Makale Önizleme' : 'Anonimleştirilmiş Makale Önizleme'}
          </SheetTitle>
          <Button 
            variant="ghost" 
            size="icon" 
            className="text-white hover:bg-white/20 rounded-full" 
            onClick={() => onOpenChange(false)}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>
        
        <div className="flex flex-col md:flex-row h-[calc(100vh-80px)]">
          {/* Bilgi paneli */}
          <div className="p-6 md:w-[280px] flex-shrink-0 md:border-r border-gray-200">
            <div className="bg-background/50 rounded-lg p-4 border border-border/30 mb-4">
              <h3 className="text-xs font-semibold text-[#d4af37] uppercase tracking-wider mb-3">Makale Bilgileri</h3>
              <p className="text-sm font-medium"><span className="text-muted-foreground">Takip No:</span> {trackingNumber}</p>
              <p className="text-sm font-medium mt-1"><span className="text-muted-foreground">Dosya Adı:</span> {anonymizedFileName || fileName}</p>
              {isReviewed && (
                <p className="text-sm font-medium mt-1">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 border border-green-200 mt-2">
                    Değerlendirilmiş
                  </span>
                </p>
              )}
            </div>
            
            <div className="mb-4">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => handleDownload(trackingNumber)}
                className="w-full gap-1 border-[#d4af37]/30 text-[#d4af37] hover:bg-[#d4af37]/5"
              >
                <Download className="h-4 w-4" />
                İndir
              </Button>
            </div>
          </div>
          
          {/* PDF görüntüleme alanı */}
          <div className="flex-1 p-6 md:p-4 flex flex-col overflow-hidden">
            <div className="border rounded-lg overflow-hidden bg-white flex-1 flex items-center justify-center">
              {loading ? (
                <div className="flex flex-col items-center justify-center p-10">
                  <Loader2 className="h-10 w-10 text-[#d4af37] animate-spin mb-4" />
                  <p className="text-muted-foreground">
                    {isReviewed ? 'Değerlendirilmiş' : 'Anonimleştirilmiş'} PDF dosyası yükleniyor...
                  </p>
                </div>
              ) : error ? (
                <div className="text-center p-10">
                  <p className="text-red-500 mb-2">{error}</p>
                  {pdfData ? (
                    // Önizleme verisi varsa onu göster
                    <div className="w-full h-full">
                      <PDFViewer width="100%" height="100%" className="border-0">
                        <PdfDocument pdfData={pdfData} />
                      </PDFViewer>
                    </div>
                  ) : (
                    <Button onClick={fetchPdf} variant="outline" size="sm" className="mt-2">
                      Tekrar Dene
                    </Button>
                  )}
                </div>
              ) : pdfBlob && pdfUrl ? (
                // Güvenli bir şekilde PDF'i göster
                <div className="w-full h-full flex flex-col">
                  <div className="bg-gray-100 p-2 border-b text-center">
                    <p className="text-sm text-muted-foreground">
                      PDF gösterilemiyor mu? <Button variant="link" size="sm" className="p-0 h-auto" onClick={() => handleDownload(trackingNumber)}>İndirmek için tıklayın</Button>
                    </p>
                  </div>
                  <div className="flex-1 relative">
                    <object
                      data={pdfUrl}
                      type="application/pdf"
                      width="100%"
                      height="100%"
                      className="absolute inset-0"
                    >
                      <p>PDF görüntülenemiyor. <a href="#" onClick={(e) => { e.preventDefault(); handleDownload(trackingNumber); }}>İndirmek için tıklayın</a></p>
                    </object>
                  </div>
                </div>
              ) : pdfData ? (
                // Fallback olarak önizleme verisi göster
                <div className="w-full h-full">
                  <PDFViewer width="100%" height="100%" className="border-0">
                    <PdfDocument pdfData={pdfData} />
                  </PDFViewer>
                </div>
              ) : (
                <p className="text-muted-foreground">PDF yüklenemiyor</p>
              )}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
} 