"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
import Link from "next/link"
import { ArrowLeft, FileText, User, Home, Loader2, Eye, RefreshCw, Star, Send } from "lucide-react"
import { useParams, useRouter } from "next/navigation"
import { Button } from "@/app/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { REVIEW_ENDPOINTS, ANONYMIZE_ENDPOINTS } from "@/app/lib/apiConfig"
import { toast } from "sonner"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { StatusBadge, ArticleStatus } from "@/app/lib/articleStatus"

// Hakem kategorilerini import et
import { MAIN_CATEGORIES } from "@/app/data/categories"

// Bileşenleri import et
import ReviewSheet from "../components/ReviewSheet"
import PdfPreview from "../components/PdfPreview"
import { generatePdf } from "../components/ReviewPdfGenerator"
import ReviewedPaperSendSheet from "@/app/Users/reviewer/components/ReviewedPaperSendSheet"

// Makale tipi tanımlaması
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

// YENI: Değerlendirme için ReviewData tipi
interface ReviewData {
  score: number;
  comments: string;
  recommendation: string;
}

export default function SubcategoryReviewerPage() {
  const params = useParams();
  const router = useRouter();
  const subcategoryId = Number(params.id);
  
  // State tanımlamaları
  const [assignedPapers, setAssignedPapers] = useState<ReviewPaper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<ReviewPaper | null>(null);
  const [isReviewSheetOpen, setIsReviewSheetOpen] = useState(false);
  const [isPdfPreviewOpen, setIsPdfPreviewOpen] = useState(false);
  const [isSendToEditorSheetOpen, setIsSendToEditorSheetOpen] = useState(false);
  const [showReviewedPdf, setShowReviewedPdf] = useState(false);

  // Form verisi
  const [reviewData, setReviewData] = useState<ReviewData>({
    score: 5,
    comments: "",
    recommendation: "revision_required"
  });

  const [submittingReview, setSubmittingReview] = useState(false);

  // Seçilen alt kategoriyi ve ana kategoriyi bul
  const subcategoryInfo = useMemo(() => 
    MAIN_CATEGORIES.flatMap(category => 
    category.subcategories.map(subcat => ({
      ...subcat,
      mainCategory: category.name,
      mainCategoryId: category.id,
      icon: category.icon
    }))
    ).find(subcat => subcat.id === subcategoryId),
    [subcategoryId]
  );

  // Alt kategori bulunamazsa ana sayfaya yönlendir
  useEffect(() => {
    if (!subcategoryInfo && typeof window !== "undefined") {
      router.push('/Users/reviewer');
    }
  }, [subcategoryInfo, router]);

  // Hakem bilgisini al - artık sabit değerler kullanıyor
  const getReviewer = useCallback((subcatId: number) => {
    if (!subcategoryInfo) return null;
    
    // Backend ile uyumlu hakem ID formatı
    const reviewerId = `${subcatId}-1`;
    
    return {
      id: reviewerId,
      name: `Hakem ${subcatId}.1`,
      title: `${subcategoryInfo.name} Uzmanı`,
      institution: `${subcategoryInfo.mainCategory} Üniversitesi`,
      isAvailable: true,
    };
  }, [subcategoryInfo]);
  
  // Memoize edilen reviewer değeri - her render'da değişmemesi için useMemo kullanıldı
  const reviewer = useMemo(() => 
    subcategoryInfo ? getReviewer(subcategoryId) : null,
    [subcategoryInfo, getReviewer, subcategoryId]
  );
  
  // Anonimleştirilmiş dosya adını getirme fonksiyonu
  const fetchAnonymizedFileNames = async (papers: ReviewPaper[]) => {
    const updatedPapers = [...papers];
    
    for (let i = 0; i < updatedPapers.length; i++) {
      try {
        const response = await fetch(ANONYMIZE_ENDPOINTS.INFO(updatedPapers[i].tracking_number));
        if (!response.ok) continue;
        
        const data = await response.json();
        if (data.success && data.anonymized_file) {
          updatedPapers[i].anonymized_filename = data.anonymized_file.filename;
        }
      } catch (error) {
        console.error('Anonimleştirilmiş dosya bilgisi getirme hatası:', error);
      }
    }
    
    return updatedPapers;
  };
  
  // Hakeme atanmış makaleleri getirme fonksiyonu - useCallback ile sarmalayarak gereksiz yeniden render önlenir
  const fetchAssignedPapers = useCallback(async () => {
    if (!reviewer) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Hata ayıklama: API çağrısı öncesi detayları konsola yazdır
      const apiUrl = `${REVIEW_ENDPOINTS.PAPERS}?reviewer_id=${reviewer.id}&subcategory_id=${subcategoryId}`;
      console.log("API isteği gönderiliyor:", apiUrl);
      console.log("Parametreler:", { reviewer_id: reviewer.id, subcategory_id: subcategoryId });
      
      // REVIEW_ENDPOINTS.PAPERS kullanarak doğru API URL'sini oluştur
      const response = await fetch(apiUrl);
      
      // Hata ayıklama: Yanıt durumunu konsola yazdır
      console.log("API yanıtı alındı, durum kodu:", response.status);
      
      if (!response.ok) {
        const errorData = await response.text();
        console.error("API yanıt hatası:", errorData);
        throw new Error(`Makaleler alınırken bir hata oluştu: ${errorData}`);
      }
      
      const data = await response.json();
      console.log("API yanıt verisi:", data);
      
      if (data.success) {
        // Backend'den gelen verileri işleme - review_status kontrolü yap
        let processedPapers = (data.papers || []).map((paper: ReviewPaper) => {
          // Eğer review_status yoksa makale durumuna göre bir review_status belirle
          if (!paper.review_status) {
            if (paper.status === ArticleStatus.REVIEWED || 
                paper.status === ArticleStatus.ACCEPTED || 
                paper.status === ArticleStatus.REJECTED || 
                paper.status === ArticleStatus.REVISION_REQUIRED) {
              paper.review_status = 'completed';
            } else if (paper.status === ArticleStatus.IN_REVIEW) {
              paper.review_status = 'assigned';
            } else {
              paper.review_status = 'pending';
            }
          }
          return paper;
        });
        
        // Anonimleştirilmiş dosya adlarını çek
        processedPapers = await fetchAnonymizedFileNames(processedPapers);
        
        setAssignedPapers(processedPapers);
        console.log("Makaleler başarıyla alındı:", processedPapers.length, "adet");
      } else {
        setError(data.error || 'Makaleler alınırken bir hata oluştu');
        console.error("API başarısız yanıt:", data.error);
      }
    } catch (err) {
      console.error('Makaleleri getirme hatası:', err);
      setError(err instanceof Error ? err.message : 'Makaleler alınırken bir hata oluştu');
    } finally {
      setLoading(false);
    }
  }, [reviewer, subcategoryId]);
  
  // Hakeme atanmış makaleleri sadece reviewer değiştiğinde getir
  useEffect(() => {
    if (reviewer && subcategoryId) {
      fetchAssignedPapers();
    }
  }, [reviewer, fetchAssignedPapers]);

  
  // Tarih formatı
  const formatDate = (dateString: string) => {
    if (!dateString) return "Belirtilmemiş";
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("tr-TR", {
        year: "numeric",
        month: "long",
        day: "numeric"
      });
    } catch (error) {
      console.error("Tarih formatı hatası:", error);
      return dateString;
    }
  };
  
  // Durum etiketi oluştur
  const getStatusBadge = (status: string, reviewStatus?: string) => {
    // Önce değerlendirme durumuna göre bir badge döndür
    if (reviewStatus) {
      // Değerlendirme durumları için özel mapping
      const reviewStatusMap: Record<string, { status: string }> = {
        'pending': { status: ArticleStatus.PENDING },
        'assigned': { status: ArticleStatus.ASSIGNED },
        'in_progress': { status: ArticleStatus.IN_REVIEW },
        'completed': { status: ArticleStatus.REVIEWED },
      };
      
      const statusInfo = reviewStatusMap[reviewStatus] || { status: ArticleStatus.UNDEFINED };
      
      return <StatusBadge status={statusInfo.status} />;
    }
    
    // Makale durumuna göre badge döndür - doğrudan gelen status değerini kullanalım
    return <StatusBadge status={status} />;
  };

  // Bir makalenin değerlendirilmiş olup olmadığını kontrol et
  const isPaperReviewed = (paper: ReviewPaper) => {
    return paper.status === ArticleStatus.REVIEWED || 
           paper.status === ArticleStatus.ACCEPTED || 
           paper.status === ArticleStatus.REJECTED || 
           paper.status === ArticleStatus.REVISION_REQUIRED;
  };

  // YENI: Değerlendirme formu gönderme işlemi
  const submitReview = async () => {
    if (!selectedPaper || !reviewer) return;
    
    setSubmittingReview(true);
    
    try {
      // Form verilerini hazırla
      const formData = new FormData();
      formData.append("paper_id", selectedPaper.id.toString());
      formData.append("reviewer_id", reviewer.id);
      formData.append("score", reviewData.score.toString());
      formData.append("comments", reviewData.comments);
      
      // Recommendation değerini özel bir şekilde işle - recommendation'ı durum string'i olarak kullan
      const recommendationMap: Record<string, string> = {
        'accepted': ArticleStatus.ACCEPTED,
        'revision_required': ArticleStatus.REVISION_REQUIRED,
        'rejected': ArticleStatus.REJECTED
      };
      
      // Mevcut recommendation değerini durum değerine dönüştür
      const statusRecommendation = recommendationMap[reviewData.recommendation] || ArticleStatus.REVISION_REQUIRED;
      formData.append("recommendation", statusRecommendation);
      
      formData.append("subcategory_id", subcategoryId.toString());
      
      // API endpoint'ini oluştur - tracking_number ile endpoint oluştur
      const reviewEndpoint = REVIEW_ENDPOINTS.SUBMIT_REVIEW(selectedPaper.tracking_number);
      
      // API isteğini gönder
      const response = await fetch(reviewEndpoint, {
        method: "POST",
        body: formData,
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        // Başarılı yanıt
        toast("Makale değerlendirmeniz başarıyla kaydedildi.");
        
        // PDF oluştur ve birleştir
        try {
          // PDF'i oluştur (Bu kısım ReviewSheet.tsx içinde de yapılabilir)
          const { blob } = await generatePdf({
            trackingNumber: selectedPaper.tracking_number,
            paperTitle: selectedPaper.original_filename,
            score: reviewData.score,
            recommendation: reviewData.recommendation,
            comments: reviewData.comments
          });
          
          // PDF'leri birleştir
          const mergeResult = await fetch(ANONYMIZE_ENDPOINTS.MERGE_REVIEW(selectedPaper.tracking_number), {
            method: "POST",
            body: (() => {
              const formData = new FormData();
              formData.append("review_pdf", blob, "review.pdf");
              return formData;
            })()
          });
          
          const mergeData = await mergeResult.json();
          if (mergeResult.ok && mergeData.success) {
            console.log("PDF'ler başarıyla birleştirildi");
          } else {
            console.error("PDF'ler birleştirilemedi:", mergeData.error);
          }
        } catch (pdfError) {
          console.error("PDF oluşturma veya birleştirme hatası:", pdfError);
        }
        
        // Atanmış makaleleri yenile
        fetchAssignedPapers();
        
        // Sheet'i kapat
        setIsReviewSheetOpen(false);
      } else {
        // Hata durumu
        toast(data.error || "Değerlendirme gönderilirken bir hata oluştu.");
      }
    } catch (error) {
      console.error("Değerlendirme gönderme hatası:", error);
      toast("Değerlendirme gönderilirken bir hata oluştu.");
    } finally {
      setSubmittingReview(false);
    }
  };
  
  // YENI: Değerlendirme formunu açma işlemi
  const openReviewSheet = (paper: ReviewPaper) => {
    setSelectedPaper(paper);
    setIsReviewSheetOpen(true);
    
    // Eğer daha önceden değerlendirme varsa, verileri getir
    // (Bu kısmı gerçek API entegrasyonu ile geliştirilebilir)
    fetchPaperReview(paper.id);
  };
  
  // YENI: Makale değerlendirmesini getirme
  const fetchPaperReview = async (paperId: number) => {
    try {
      // Geçici çözüm: API hazır olmadığından try-catch bloğunu kullanarak hatayı yakalayıp varsayılan değerleri atayalım
      // Gerçek API entegrasyonu mevcut olduğunda bu kısım aktif edilebilir
      /*
      const response = await fetch(`${REVIEW_ENDPOINTS.GET_REVIEW}?paper_id=${paperId}&reviewer_id=${reviewer?.id}`);
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.success && data.review) {
          // Varolan değerlendirme verilerini form'a doldur
          setReviewData({
            score: data.review.score || 5,
            comments: data.review.comments || "",
            recommendation: data.review.recommendation || "revision_required"
          });
          return;
        }
      }
      */
      
      // API entegrasyonu olmadığında ya da API yanıt vermediğinde varsayılan değerleri kullan
      console.log(`API henüz aktif değil: Makale ID ${paperId} için varsayılan değerler kullanılıyor`);
      setReviewData({
        score: 5,
        comments: "",
        recommendation: "revision_required"
      });
    } catch (error) {
      console.error("Değerlendirme verisi getirme hatası:", error);
      // Hata durumunda varsayılan değerler
      setReviewData({
        score: 5,
        comments: "",
        recommendation: "revision_required"
      });
    }
  };

  if (!subcategoryInfo || !reviewer) {
    return <div>Yükleniyor...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background/80 p-4 md:p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        <header
          className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b pb-6"
          style={{ borderColor: "var(--border-color)" }}
        >
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Link href="/Users/reviewer">
                <Button
                  variant="ghost"
                  className="p-0 -ml-2"
                  style={{ color: "var(--primary)" }}
                >
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Geri
                </Button>
              </Link>
            </div>
            <h1 className="text-3xl font-bold tracking-tight" style={{ color: "var(--primary)" }}>
              {subcategoryInfo.icon} {subcategoryInfo.name} Hakemi
            </h1>
            <p className="text-sm" style={{ color: "var(--text-primary)" }}>
              {subcategoryInfo.mainCategory} / {subcategoryInfo.name} alanı
            </p>
          </div>
          <Link href="/">
            <Button
              variant="outline"
              className="gap-2 transition-all duration-200 hover:border-accent"
              style={{ borderColor: "var(--border-color)", color: "var(--foreground)" }}
            >
              <Home className="h-4 w-4" />
              Ana Sayfa
            </Button>
          </Link>
        </header>

        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <User className="h-5 w-5" style={{ color: "var(--primary)" }} />
              <h2 className="text-xl font-semibold" style={{ color: "var(--text-technical)" }}>
                Hakem Detayları
              </h2>
            </div>
          </div>
          
          <Card className="border shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-center gap-4">
                <div 
                  className="w-14 h-14 rounded-full flex items-center justify-center flex-shrink-0 text-lg font-bold"
                  style={{ backgroundColor: "color-mix(in srgb, var(--primary), transparent 90%)" }}
                >
                  {reviewer.name.split(' ').map(n => n[0]).join('')}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold" style={{ color: "var(--text-technical)" }}>
                    {reviewer.name}
                  </h3>
                  <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                    {reviewer.title} | {reviewer.institution}
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                      {subcategoryInfo.name} Uzmanı
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-gray-100 text-gray-800 border border-gray-200">
                      {subcategoryInfo.mainCategory}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          {/* Atanmış Makaleler Bölümü */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" style={{ color: "var(--primary)" }} />
              <h2 className="text-xl font-semibold" style={{ color: "var(--text-technical)" }}>
                Atanmış Makaleler
              </h2>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              className="gap-1.5"
              onClick={fetchAssignedPapers}
            >
              <RefreshCw className="h-4 w-4" />
              Yenile
            </Button>
          </div>
          
          <Card className="border shadow-sm">
            <CardContent className="p-6">
              {loading ? (
                <div className="flex justify-center items-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin" style={{ color: "var(--primary)" }} />
                </div>
              ) : error ? (
                <div className="bg-red-100 border border-red-200 p-4 rounded-md text-red-800">
                  <p>{error}</p>
                </div>
              ) : assignedPapers.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 mx-auto mb-4" style={{ color: "var(--muted-foreground)" }} />
                  <h3 className="text-lg font-medium mb-2" style={{ color: "var(--text-technical)" }}>
                    Atanmış Makale Bulunamadı
                  </h3>
                  <p style={{ color: "var(--muted-foreground)" }}>
                    Bu hakem için atanmış veya değerlendirme bekleyen makale bulunmamaktadır.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b" style={{ borderColor: "var(--border-color)" }}>
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                          Takip No
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                          Dosya Adı
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                          Yükleme Tarihi
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                          Durum
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                          İşlemler
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y" style={{ borderColor: "var(--border-color)" }}>
                      {assignedPapers.map((paper) => (
                        <tr key={paper.id}>
                          <td className="px-4 py-3 whitespace-nowrap text-sm" style={{ color: "var(--foreground)" }}>
                            <span className="font-medium">{paper.tracking_number}</span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm max-w-[200px] truncate" style={{ color: "var(--foreground)" }}>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="cursor-help">{paper.anonymized_filename || paper.original_filename}</span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>{paper.anonymized_filename || paper.original_filename}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm" style={{ color: "var(--muted-foreground)" }}>
                            {formatDate(paper.upload_date)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            {getStatusBadge(paper.status, paper.review_status)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm">
                            <div className="flex gap-2">
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-8 w-8 p-0"
                                onClick={() => {
                                  setSelectedPaper(paper);
                                  // Değerlendirilmiş makale için farklı önizleme göster
                                  const isReviewed = isPaperReviewed(paper);
                                  setShowReviewedPdf(isReviewed);
                                  setIsPdfPreviewOpen(true);
                                }}
                                title="Önizle"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              {!isPaperReviewed(paper) && (
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className="h-8 w-8 p-0"
                                  onClick={(e: React.MouseEvent) => {
                                    e.preventDefault();
                                    openReviewSheet(paper);
                                  }}
                                  title="Hızlı Değerlendirme"
                                >
                                  <Star className="h-4 w-4" />
                                </Button>
                              )}
                              {isPaperReviewed(paper) && (
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className="h-8 w-8 p-0"
                                  onClick={() => {
                                    setSelectedPaper(paper);
                                    setIsSendToEditorSheetOpen(true);
                                  }}
                                  title="Değerlendirilmiş Makaleyi Editöre Gönder"
                                >
                                  <Send className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
      
      {/* YENI: Değerlendirme Sheet'i */}
      <ReviewSheet
        isOpen={isReviewSheetOpen}
        onOpenChange={setIsReviewSheetOpen}
        selectedPaper={selectedPaper}
        reviewData={reviewData}
        setReviewData={setReviewData}
        submittingReview={submittingReview}
        onSubmit={submitReview}
      />

      {/* YENI: PDF Önizleme */}
      {selectedPaper && (
        <PdfPreview
          isOpen={isPdfPreviewOpen}
          onOpenChange={setIsPdfPreviewOpen}
          trackingNumber={selectedPaper.tracking_number}
          fileName={selectedPaper.anonymized_filename || selectedPaper.original_filename}
          isReviewed={showReviewedPdf}
        />
      )}

      {/* Değerlendirilmiş Makaleyi Editöre Gönder Sheet'i */}
      <ReviewedPaperSendSheet
        isOpen={isSendToEditorSheetOpen}
        onOpenChange={setIsSendToEditorSheetOpen}
        selectedPaper={selectedPaper}
        subcategoryId={subcategoryId}
        onSendSuccess={fetchAssignedPapers}
      />
    </div>
  )
} 