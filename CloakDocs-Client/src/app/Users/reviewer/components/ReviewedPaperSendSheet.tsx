"use client"

import { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/app/components/ui/button";
import { Send, FileText, FileCheck, X, Loader2 } from "lucide-react";
import { REVIEW_ENDPOINTS } from "@/app/lib/apiConfig";
import { toast } from "sonner";
import { StatusBadge } from "@/app/lib/articleStatus";

interface ReviewPaper {
  id: number;
  tracking_number: string;
  original_filename: string;
  upload_date: string;
  status: string;
  download_count: number;
  review_status?: string;
  anonymized_filename?: string;
}

interface ReviewDetailData {
  score: number;
  recommendation: string;
  comments: string;
  created_at: string;
}

interface ReviewedPaperSendSheetProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  selectedPaper: ReviewPaper | null;
  reviewDetails?: ReviewDetailData | null;
  subcategoryId?: string | number;
  onSendSuccess?: () => void;
}

export default function ReviewedPaperSendSheet({
  isOpen,
  onOpenChange,
  selectedPaper,
  reviewDetails,
  subcategoryId,
  onSendSuccess
}: ReviewedPaperSendSheetProps) {
  const [sending, setSending] = useState(false);
  const [reviewInfo, setReviewInfo] = useState<ReviewDetailData | null>(null);

  // Değerlendirme detaylarını al (props'tan gelmiyorsa)
  useEffect(() => {
    if (reviewDetails) {
      setReviewInfo(reviewDetails);
      return;
    }
    
    if (selectedPaper && isOpen) {
      fetchReviewDetails();
    }
  }, [selectedPaper, isOpen, reviewDetails]);

  const fetchReviewDetails = async () => {
    if (!selectedPaper) return;
    
    try {
      const response = await fetch(`${REVIEW_ENDPOINTS.GET_REVIEW}?tracking_number=${selectedPaper.tracking_number}`);
      const data = await response.json();
      
      if (response.ok && data.success && data.review) {
        setReviewInfo(data.review);
      }
    } catch (error) {
      console.error("Değerlendirme detayları getirme hatası:", error);
    }
  };

  // Değerlendirilmiş makaleyi editöre gönderme işlemi
  const handleSendToEditor = async () => {
    if (!selectedPaper) return;

    try {
      setSending(true);

      // Form data oluştur
      const formData = new FormData();
      
      // Eğer subcategoryId props'tan geldiyse onu kullan
      if (subcategoryId) {
        formData.append('reviewer_id', `${subcategoryId}-1`); // "subcategory_id-1" formatında hakem ID'si
      }
      
      // API isteği
      const response = await fetch(REVIEW_ENDPOINTS.SUBMIT_TO_EDITOR(selectedPaper.tracking_number), {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Sheet'i kapat
        onOpenChange(false);
        
        // Başarı mesajı göster
        toast.success("Değerlendirme editöre başarıyla gönderildi");
        
        // Callback fonksiyonu çağır (varsa)
        if (onSendSuccess) {
          onSendSuccess();
        }
      } else {
        // Hata mesajı göster
        toast.error(data.error || "Değerlendirme editöre gönderilirken bir sorun oluştu");
      }
    } catch (error) {
      console.error('Editöre gönderme hatası:', error);
      toast.error("Değerlendirme editöre gönderilirken bir hata oluştu");
    } finally {
      setSending(false);
    }
  };

  // Tavsiye durumuna göre renkler ve metinler
  const getRecommendationStyles = (recommendation: string) => {
    switch(recommendation?.toLowerCase()) {
      case 'accept':
        return {
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800',
          text: 'Kabul'
        };
      case 'reject':
        return {
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          text: 'Red'
        };
      case 'revision_required':
        return {
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-200',
          textColor: 'text-orange-800',
          text: 'Revizyon Gerekli'
        };
      default:
        return {
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          textColor: 'text-blue-800',
          text: recommendation || 'Belirtilmemiş'
        };
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return "Tarih belirlenmedi";

    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("tr-TR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch (error) {
      console.error("Tarih formatı hatası:", error);
      return dateString;
    }
  };

  // Puan rengini belirle
  const getScoreColor = (score: number) => {
    if (score >= 8) return "text-green-700";
    if (score >= 6) return "text-yellow-700";
    if (score >= 4) return "text-orange-700";
    return "text-red-700";
  };

  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-md overflow-y-auto p-0">
        <div className="bg-gradient-to-r from-[#5e72e4]/90 to-[#5e72e4] p-6 text-white">
          <SheetTitle className="text-xl font-semibold text-white flex items-center gap-2">
            <Send className="h-5 w-5" />
            Değerlendirilmiş Makaleyi Editöre Gönder
          </SheetTitle>
          {selectedPaper && (
            <p className="text-white/80 text-sm font-mono mt-1">{selectedPaper.tracking_number}</p>
          )}
        </div>
        
        {selectedPaper && (
          <div className="px-6 py-5 space-y-6">
            <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
              <h3 className="text-xs font-semibold text-[#5e72e4] uppercase tracking-wider mb-3">Makale Bilgileri</h3>
              <div className="flex items-center mb-3">
                <FileText className="h-5 w-5 mr-2 text-[#5e72e4]" />
                <span className="text-sm font-medium truncate">{selectedPaper.original_filename}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Takip No</p>
                  <p className="font-medium">{selectedPaper.tracking_number}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Durum</p>
                  <StatusBadge status={selectedPaper.status} />
                </div>
              </div>
            </div>
            
            {reviewInfo ? (
              <div className="space-y-6">
                <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
                  <h3 className="text-xs font-semibold text-[#5e72e4] uppercase tracking-wider mb-3">Değerlendirme Özeti</h3>
                  
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    {reviewInfo.score > 0 && (
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Değerlendirme Puanı</p>
                        <div className="flex items-center">
                          <span className={`text-xl font-bold ${getScoreColor(reviewInfo.score)}`}>
                            {reviewInfo.score}/10
                          </span>
                          <div className="ml-2 flex-1 h-2 bg-gray-200 rounded">
                            <div 
                              className={`h-2 rounded ${
                                reviewInfo.score >= 8 ? 'bg-green-500' : 
                                reviewInfo.score >= 6 ? 'bg-yellow-500' : 
                                reviewInfo.score >= 4 ? 'bg-orange-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${reviewInfo.score * 10}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Tavsiye</p>
                      {reviewInfo.recommendation && (
                        <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                          getRecommendationStyles(reviewInfo.recommendation).bgColor
                        } ${getRecommendationStyles(reviewInfo.recommendation).textColor}`}>
                          {getRecommendationStyles(reviewInfo.recommendation).text}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Değerlendirme Tarihi</p>
                    <p className="text-sm">{formatDate(reviewInfo.created_at)}</p>
                  </div>
                </div>
                
                {reviewInfo.comments && (
                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
                    <h3 className="text-xs font-semibold text-[#5e72e4] uppercase tracking-wider mb-3">Değerlendirme Notları</h3>
                    <div className="bg-gray-50 p-4 rounded-md border border-gray-200 text-sm whitespace-pre-wrap max-h-60 overflow-y-auto">
                      {reviewInfo.comments}
                    </div>
                  </div>
                )}
                
                <div className={`rounded-lg p-4 ${
                  getRecommendationStyles(reviewInfo.recommendation || '').bgColor
                } ${getRecommendationStyles(reviewInfo.recommendation || '').borderColor} border`}>
                  <div className="flex items-start">
                    <div className="shrink-0 mr-3 mt-1">
                      <FileCheck className={`h-5 w-5 ${getRecommendationStyles(reviewInfo.recommendation || '').textColor}`} />
                    </div>
                    <div>
                      <p className={`font-medium ${getRecommendationStyles(reviewInfo.recommendation || '').textColor}`}>
                        Değerlendirme tamamlandı
                      </p>
                      <p className="text-sm mt-1">
                        Bu makale için hakem değerlendirmesi tamamlanmıştır. Değerlendirmeyi editöre göndererek süreci ilerletebilirsiniz.
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="flex justify-between pt-4">
                  <Button 
                    variant="outline" 
                    onClick={() => onOpenChange(false)}
                    disabled={sending}
                  >
                    <X className="h-4 w-4 mr-2" />
                    İptal
                  </Button>
                  
                  <Button 
                    onClick={handleSendToEditor}
                    disabled={sending}
                    className="bg-[#5e72e4] hover:bg-[#4c60cc] text-white"
                  >
                    {sending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Gönderiliyor...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-2" />
                        Editöre Gönder
                      </>
                    )}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 space-y-4">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#5e72e4] border-t-transparent"></div>
                <p className="text-muted-foreground">Değerlendirme bilgileri yükleniyor...</p>
              </div>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
} 