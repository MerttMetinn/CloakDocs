"use client"

import { useState, useEffect } from "react"
import { Loader2, FileCheck, Save, Download } from "lucide-react"
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Slider } from "@/components/ui/slider"
import { Button } from "@/app/components/ui/button"
import { ANONYMIZE_ENDPOINTS } from "@/app/lib/apiConfig"
import { ArticleStatus, StatusBadge } from "@/app/lib/articleStatus"

// Tipleri tanımla
interface ReviewPaper {
  id: number;
  tracking_number: string;
  original_filename: string;
  upload_date: string;
  status: string;
  download_count: number;
  review_status?: string;
}

interface ReviewData {
  score: number;
  comments: string;
  recommendation: string;
}

interface ReviewSheetProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  selectedPaper: ReviewPaper | null;
  reviewData: ReviewData;
  setReviewData: (data: ReviewData) => void;
  submittingReview: boolean;
  onSubmit: () => Promise<void>;
}

export default function ReviewSheet({
  isOpen,
  onOpenChange,
  selectedPaper,
  reviewData,
  setReviewData,
  submittingReview,
  onSubmit
}: ReviewSheetProps) {
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

  // Makale değiştiğinde anonimleştirilmiş dosya bilgilerini getir
  useEffect(() => {
    if (selectedPaper && selectedPaper.tracking_number) {
      fetchAnonymizedFileName(selectedPaper.tracking_number);
    }
  }, [selectedPaper]);

  // Anonimleştirilmiş makaleyi indirme fonksiyonu
  const handleAnonymizedDownload = async (trackingNumber: string) => {
    // Önce dosya adını almaya çalış
    let fileNameToUse = anonymizedFileName;
    
    if (!fileNameToUse) {
      // Henüz dosya adı alınmadıysa, almaya çalış
      fileNameToUse = await fetchAnonymizedFileName(trackingNumber);
    }
    
    const downloadUrl = ANONYMIZE_ENDPOINTS.DOWNLOAD(trackingNumber);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = fileNameToUse || `anonymized_${trackingNumber}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
  
  // Birleştirme fonksiyonu
  const mergeReviewedPdf = async (pdf: Blob, trackingNumber: string) => {
    try {
      const formData = new FormData();
      formData.append('review_pdf', pdf, 'review.pdf');
      
      const response = await fetch(ANONYMIZE_ENDPOINTS.MERGE_REVIEW(trackingNumber), {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        console.log('PDF\'ler başarıyla birleştirildi:', data);
        return true;
      } else {
        console.error('PDF birleştirme hatası:', data.error);
        return false;
      }
    } catch (error) {
      console.error('PDF birleştirme hatası:', error);
      return false;
    }
  };

  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-md overflow-y-auto p-0">
        <div className="bg-gradient-to-r from-[#d4af37]/90 to-[#d4af37] p-6 text-white">
          <SheetTitle className="text-xl font-semibold text-white flex items-center gap-2">
            <FileCheck className="h-5 w-5" />
            Makale Değerlendirme
          </SheetTitle>
          {selectedPaper && (
            <p className="text-white/80 text-sm font-mono mt-1">{selectedPaper.tracking_number}</p>
          )}
        </div>
        
        {selectedPaper && (
          <div className="px-6 py-5 space-y-6">
            {/* Makale Bilgileri Kartı */}
            <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
              <h3 className="text-xs font-semibold text-[#d4af37] uppercase tracking-wider mb-3">Makale Bilgileri</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Takip No</span>
                  <span className="bg-[#d4af37]/10 text-[#d4af37] px-3 py-1 rounded-md font-mono font-medium text-sm">
                    {selectedPaper.tracking_number}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Dosya Adı</span>
                  <span className="text-foreground text-sm max-w-[220px] truncate">
                    {anonymizedFileName || selectedPaper.original_filename}
                  </span>
                </div>
              </div>
              
              {/* Anonimleştirilmiş Makale İndirme Butonu */}
              <div className="mt-3">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => handleAnonymizedDownload(selectedPaper.tracking_number)}
                  className="w-full gap-1 border-[#d4af37]/30 text-[#d4af37] hover:bg-[#d4af37]/5"
                >
                  <Download className="h-4 w-4" />
                  Anonimleştirilmiş Makaleyi İndir
                </Button>
              </div>
            </div>
            
            {/* Puanlama */}
            <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
              <h3 className="text-xs font-semibold text-[#d4af37] uppercase tracking-wider mb-3">Değerlendirme Puanı</h3>
              <div className="px-2">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-muted-foreground">Puan Seçiniz</span>
                  <span className="font-bold text-lg px-2 py-0.5 rounded bg-[#d4af37]/10 text-[#d4af37]">
                    {reviewData.score}/10
                  </span>
                </div>
                <Slider
                  id="score"
                  min={1}
                  max={10}
                  step={1}
                  value={[reviewData.score]}
                  onValueChange={(value) => setReviewData({ ...reviewData, score: value[0] })}
                  className="my-4"
                />
                <div className="flex justify-between text-xs mt-1.5 text-muted-foreground">
                  <span>Zayıf (1)</span>
                  <span>Orta (5)</span>
                  <span>Mükemmel (10)</span>
                </div>
              </div>
            </div>
            
            {/* Tavsiye */}
            <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
              <h3 className="text-xs font-semibold text-[#d4af37] uppercase tracking-wider mb-3">Tavsiye Seçeneği</h3>
              <RadioGroup
                id="recommendation"
                value={reviewData.recommendation}
                onValueChange={(value: string) => setReviewData({ ...reviewData, recommendation: value })}
                className="space-y-3"
              >
                <div className="flex items-center p-3 rounded-lg hover:bg-[#d4af37]/5 transition-all"
                     style={{ 
                       border: reviewData.recommendation === 'accepted' ? '1px solid #d4af37' : '1px solid #e2e8f0',
                       boxShadow: reviewData.recommendation === 'accepted' ? '0 0 0 1px #d4af37' : 'none'
                     }}>
                  <RadioGroupItem value="accepted" id="accepted" className="mr-3" />
                  <Label htmlFor="accepted" className="flex items-center gap-2 cursor-pointer">
                    <StatusBadge status={ArticleStatus.ACCEPTED} />
                    <span>Makale doğrudan kabul edilmeli</span>
                  </Label>
                </div>
                
                <div className="flex items-center p-3 rounded-lg hover:bg-[#d4af37]/5 transition-all"
                     style={{ 
                       border: reviewData.recommendation === 'revision_required' ? '1px solid #d4af37' : '1px solid #e2e8f0',
                       boxShadow: reviewData.recommendation === 'revision_required' ? '0 0 0 1px #d4af37' : 'none'
                     }}>
                  <RadioGroupItem value="revision_required" id="revision" className="mr-3" />
                  <Label htmlFor="revision" className="flex items-center gap-2 cursor-pointer">
                    <StatusBadge status={ArticleStatus.REVISION_REQUIRED} />
                    <span>Düzeltmeler gerekli</span>
                  </Label>
                </div>
                
                <div className="flex items-center p-3 rounded-lg hover:bg-[#d4af37]/5 transition-all"
                     style={{ 
                       border: reviewData.recommendation === 'rejected' ? '1px solid #d4af37' : '1px solid #e2e8f0',
                       boxShadow: reviewData.recommendation === 'rejected' ? '0 0 0 1px #d4af37' : 'none'
                     }}>
                  <RadioGroupItem value="rejected" id="rejected" className="mr-3" />
                  <Label htmlFor="rejected" className="flex items-center gap-2 cursor-pointer">
                    <StatusBadge status={ArticleStatus.REJECTED} />
                    <span>Makale reddedilmeli</span>
                  </Label>
                </div>
              </RadioGroup>
            </div>
            
            {/* Detaylı Değerlendirme */}
            <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
              <h3 className="text-xs font-semibold text-[#d4af37] uppercase tracking-wider mb-3">Değerlendirme</h3>
              <Textarea
                id="comments"
                value={reviewData.comments}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setReviewData({ ...reviewData, comments: e.target.value })}
                placeholder="Makale hakkında değerlendirmenizi yazın. Önemli bulgular, metodoloji, sonuçlar vb. hakkında yorumlarınızı ekleyin..."
                className="h-72 min-h-[150px] resize-none focus-visible:ring-1 focus-visible:ring-[#d4af37] border-border"
              />
            </div>
          </div>
        )}
        
        <div className="px-6 pb-6 pt-1">
          <Button 
            onClick={onSubmit} 
            className="w-full gap-2 font-medium bg-[#d4af37] hover:bg-[#c9a633] text-white py-6"
            disabled={submittingReview}
          >
            {submittingReview ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Değerlendirme Gönderiliyor...</span>
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                <span>Değerlendirmeyi Gönder</span>
              </>
            )}
          </Button>
          
          {/* PDF İndirme Butonu - Yalnızca form doldurulduğunda görünür */}
          {reviewData.comments && reviewData.recommendation && (
            <div className="mt-3 mb-2 flex justify-center">
              <Button 
                variant="outline" 
                size="sm"
                className="gap-2 border-[#d4af37]/30 text-[#d4af37] hover:bg-[#d4af37]/5"
                onClick={async () => {
                  // PDFDownloadLink'i programatik olarak tetikle
                  if (selectedPaper) {
                    try {
                      // generatePdf'i import etmek gerekiyor
                      const { generatePdf } = await import("./ReviewPdfGenerator");
                      
                      // PDF'i oluştur
                      const { blob } = await generatePdf({
                        trackingNumber: selectedPaper.tracking_number,
                        paperTitle: anonymizedFileName || selectedPaper.original_filename,
                        score: reviewData.score,
                        recommendation: reviewData.recommendation,
                        comments: reviewData.comments
                      });
                      
                      // PDF'leri birleştir
                      await mergeReviewedPdf(blob, selectedPaper.tracking_number);
                      
                      // PDF'i indir
                      const pdfUrl = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = pdfUrl;
                      link.download = `review-${selectedPaper.tracking_number}.pdf`;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      URL.revokeObjectURL(pdfUrl);
                    } catch (error) {
                      console.error("PDF oluşturma hatası:", error);
                    }
                  }
                }}
              >
                <Download className="h-4 w-4" />
                Değerlendirmeyi PDF Olarak İndir
              </Button>
            </div>
          )}
          
          <Button 
            variant="outline" 
            onClick={() => onOpenChange(false)}
            className="w-full mt-2 border-[#d4af37]/50 text-[#d4af37] hover:bg-[#d4af37]/5"
          >
            İptal
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
} 