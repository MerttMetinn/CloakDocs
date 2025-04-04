"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { ArrowLeft, FileText, Search, Download, Send, Eye, AlertTriangle, Loader2, CheckCircle, Calendar, User, Copy } from "lucide-react"
import { Button } from "@/app/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { API_BASE_URL, EDITOR_ENDPOINTS } from "@/app/lib/apiConfig"
import ConfirmDialog from "@/app/components/ui/confirm-dialog"

interface Review {
  id: number;
  paper_id: number;
  tracking_number: string;
  original_filename: string;
  score: number;
  recommendation: string;
  reviewer_id: string;
  subcategory_id: number;
  created_at: string;
  forwarded_to_author?: boolean;
  deanonymized?: boolean;
  isLoading?: boolean;
  finalPdfCreated?: boolean;
}

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<Review[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [activeTab, setActiveTab] = useState("pending")
  const [forwardingReview, setForwardingReview] = useState<number | null>(null)
  
  // Doğrulama diyaloğu için state
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [selectedReviewId, setSelectedReviewId] = useState<number | null>(null)
  const [selectedReviewDetails, setSelectedReviewDetails] = useState<{
    title: string;
    score: number;
    trackingNumber: string;
  } | null>(null)

  // Filtreleme seçenekleri
  const [filterStatus, setFilterStatus] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState("date") // date, score, recommendation
  const [sortOrder, setSortOrder] = useState("desc") // asc, desc

  // İncelemeleri yükle
  useEffect(() => {
    fetchReviews()
  }, [activeTab])

  const fetchReviews = async () => {
    setLoading(true)
    try {
      // Hakemlerden gelen incelemeleri getir
      const response = await fetch(
        `${API_BASE_URL}/editor/reviews?status=${activeTab === "pending" ? "reviewed" : "all"}`
      )
      
      if (!response.ok) {
        throw new Error("İncelemeler alınırken bir hata oluştu")
      }
      
      const data = await response.json()
      
      if (data.success) {
        // API'den gelen verilere varsayılan değerler ekleyelim
        const reviewsWithDefaults = (data.reviews || []).map((review: Review) => ({
          ...review,
          forwarded_to_author: review.forwarded_to_author || false,
          deanonymized: review.deanonymized || false,
        }))
        setReviews(reviewsWithDefaults)
      } else {
        console.error("API Error:", data.error)
      }
    } catch (error) {
      console.error("Fetch Error:", error)
    } finally {
      setLoading(false)
    }
  }
  
  // İncelemeyi yazara iletme onay diyaloğunu göster
  const showForwardConfirm = (review: Review) => {
    setSelectedReviewId(review.id)
    setSelectedReviewDetails({
      title: review.original_filename,
      score: review.score,
      trackingNumber: review.tracking_number,
    })
    setConfirmOpen(true)
  }

  // İncelemeyi yazara ilet
  const forwardReviewToAuthor = async () => {
    if (!selectedReviewId) return
    
    setForwardingReview(selectedReviewId)
    try {
      const response = await fetch(`${API_BASE_URL}/editor/forward-review/${selectedReviewId}`, {
        method: 'POST',
      })
      
      const data = await response.json()
      
      if (response.ok && data.success) {
        alert(`İnceleme başarıyla yazara iletildi.`)
        fetchReviews() // Listeyi yenile
      } else {
        alert(`Hata: ${data.error || 'İnceleme yazara iletilirken bir sorun oluştu'}`)
      }
    } catch (error) {
      console.error("İnceleme iletme hatası:", error)
      alert("İnceleme yazara iletilirken bir hata oluştu.")
    } finally {
      setForwardingReview(null)
    }
  }

  // İnceleme dosyasını indir
  const downloadReview = (reviewId: number) => {
    const downloadUrl = `${API_BASE_URL}/editor/download-review/${reviewId}`
    window.open(downloadUrl, '_blank')
  }

  // Tarih formatı
  const formatDate = (dateString: string) => {
    if (!dateString) return "Belirtilmemiş"
    
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString("tr-TR", {
        year: "numeric",
        month: "long",
        day: "numeric"
      })
    } catch (error) {
      console.error("Tarih formatı hatası:", error)
      return dateString
    }
  }
  
  // Arama ve filtreler uygulanmış değerlendirmeler
  const getFilteredReviews = () => {
    let filtered = [...reviews]
    
    // Metin araması uygula
    if (searchTerm) {
      filtered = filtered.filter(review => 
        review.tracking_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        review.original_filename?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        review.reviewer_id?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }
    
    // Durum filtresi uygula
    if (filterStatus) {
      filtered = filtered.filter(review => 
        filterStatus === 'forwarded' ? review.forwarded_to_author :
        filterStatus === 'pending' ? !review.forwarded_to_author : true
      )
    }
    
    // Sıralama uygula
    filtered.sort((a, b) => {
      if (sortBy === 'date') {
        const dateA = new Date(a.created_at).getTime()
        const dateB = new Date(b.created_at).getTime()
        return sortOrder === 'asc' ? dateA - dateB : dateB - dateA
      }
      
      if (sortBy === 'score') {
        return sortOrder === 'asc' ? a.score - b.score : b.score - a.score
      }
      
      return 0
    })
    
    return filtered
  }
  
  const filteredReviews = getFilteredReviews()

  // Anonimleştirmeyi kaldırma işlemi
  const handleDeanonymize = async (review: Review) => {
    try {
      // Butonun bulunduğu review kartında loading göster
      const updatedReviews = reviews.map(r => 
        r.id === review.id ? {...r, isLoading: true} : r
      )
      setReviews(updatedReviews)
      
      // API isteği yap
      const response = await fetch(EDITOR_ENDPOINTS.DEANONYMIZE_REVIEW(review.id), {
        method: 'POST',
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || "Anonimleştirme kaldırılırken bir hata oluştu");
      }
      
      if (!data.success || !data.review) {
        throw new Error("Sunucudan geçersiz yanıt alındı");
      }
      
      // İşlem başarılı olduğunda review'ı güncelle
      const successReviews = reviews.map(r => 
        r.id === review.id ? {
          ...r, 
          deanonymized: data.review.deanonymized,
          final_pdf_path: data.review.final_pdf_path,
          isLoading: false,
          finalPdfCreated: true
        } : r
      )
      setReviews(successReviews)
      
      // Başarı mesajı göster
      alert("Anonimlik başarıyla kaldırıldı ve final PDF oluşturuldu.")
      
    } catch (error) {
      console.error("Anonimleştirmeyi kaldırma hatası:", error)
      alert(error instanceof Error ? error.message : "Anonimleştirme kaldırılırken bir hata oluştu.")
      
      // Hata durumunda loading'i kaldır
      const errorReviews = reviews.map(r => 
        r.id === review.id ? {...r, isLoading: false} : r
      )
      setReviews(errorReviews)
    }
  }

  // Final PDF'i indir
  const downloadFinalPdf = (review: Review) => {
    // Final PDF'i indirmek için API endpoint'i
    const downloadUrl = EDITOR_ENDPOINTS.DOWNLOAD_FINAL_PDF(review.id);
    window.open(downloadUrl, '_blank');
  }

  return (
    <div className="min-h-screen p-4 bg-background">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <Link href="/Users/editor" className="mr-4">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <h1 className="text-2xl font-bold text-primary">Hakem İncelemeleri</h1>
          </div>
          
          <Button onClick={fetchReviews} className="gap-2">
            <FileText className="h-4 w-4" />
            İncelemeleri Yenile
          </Button>
        </div>
        
        <Card className="mb-6">
          <CardHeader className="pb-3">
            <CardTitle>Hakem İncelemeleri Yönetimi</CardTitle>
            <CardDescription>
              Hakemlerden gelen makale incelemelerini görüntüleyin ve yazarlara iletin
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="search"
                    placeholder="İnceleme ara: Takip numarası, dosya adı veya hakem ID..."
                    className="pl-8"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                
                <Tabs defaultValue="pending" className="w-[300px]" value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="pending">Değerlendirilmiş</TabsTrigger>
                    <TabsTrigger value="all">Tüm İncelemeler</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
              
              {/* Ek filtreler */}
              <div className="flex flex-col sm:flex-row gap-4 pt-2">
                <select 
                  className="px-3 py-2 rounded-md border border-input bg-background"
                  value={filterStatus || ''}
                  onChange={(e) => setFilterStatus(e.target.value || null)}
                >
                  <option value="">Tüm Durumlar</option>
                  <option value="forwarded">Yazara İletilmiş</option>
                  <option value="pending">İletilmemiş</option>
                </select>
                
                <select 
                  className="px-3 py-2 rounded-md border border-input bg-background"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                >
                  <option value="date">Tarihe Göre Sırala</option>
                  <option value="score">Puana Göre Sırala</option>
                </select>
                
                <Button 
                  variant="outline" 
                  onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                  className="gap-1"
                >
                  {sortOrder === 'asc' ? 'Artan' : 'Azalan'} 
                  <ArrowLeft className={`h-4 w-4 transition-transform ${sortOrder === 'asc' ? 'rotate-90' : '-rotate-90'}`} />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {loading ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : filteredReviews.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center p-6">
              <div className="rounded-full bg-primary/10 p-3 mb-4">
                <AlertTriangle className="h-6 w-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">İnceleme Bulunamadı</h3>
              <p className="text-muted-foreground text-center max-w-md">
                Aradığınız kriterlere uygun hakem incelemesi bulunamadı. Filtreleri temizlemeyi veya yeni incelemeleri yüklemeyi deneyebilirsiniz.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {filteredReviews.map((review) => (
              <Card key={review.id} className={review.forwarded_to_author ? 'border-green-200' : ''}>
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-base font-medium flex items-center">
                        <FileText className="h-4 w-4 mr-2" /> 
                        <span className="truncate">{review.original_filename}</span>
                      </CardTitle>
                      <CardDescription className="flex items-center mt-1">
                        <Copy className="h-3 w-3 mr-1" /> 
                        <code className="text-xs bg-slate-100 px-1 py-0.5 rounded">{review.tracking_number}</code>
                      </CardDescription>
                    </div>
                    <div>
                      {review.forwarded_to_author ? (
                        <div className="flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                          <CheckCircle className="h-3 w-3 mr-1" /> Yazara İletildi
                        </div>
                      ) : (
                        <div className="flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                          <Send className="h-3 w-3 mr-1" /> İletim Bekliyor
                        </div>
                      )}
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent className="pb-3">
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="flex flex-col space-y-1">
                      <span className="text-xs text-muted-foreground">Hakem</span>
                      <div className="flex items-center">
                        <User className="h-3 w-3 mr-1 text-muted-foreground" />
                        <span className="text-sm font-medium">{review.reviewer_id}</span>
                      </div>
                    </div>
                    
                    <div className="flex flex-col space-y-1">
                      <span className="text-xs text-muted-foreground">Değerlendirme Tarihi</span>
                      <div className="flex items-center">
                        <Calendar className="h-3 w-3 mr-1 text-muted-foreground" />
                        <span className="text-sm">{formatDate(review.created_at)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mb-2">
                    <div className="flex flex-col space-y-1">
                      <span className="text-xs text-muted-foreground">Değerlendirme Puanı</span>
                      <div className="flex items-center">
                        <span className="text-xl font-bold text-primary">{review.score}</span>
                        <span className="text-sm text-muted-foreground ml-1">/10</span>
                        <div className="ml-2 flex-1 h-2 bg-gray-200 rounded overflow-hidden">
                          <div 
                            className={`h-2 ${
                              review.score >= 8 ? 'bg-green-500' : 
                              review.score >= 6 ? 'bg-blue-500' : 
                              review.score >= 4 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${review.score * 10}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
                
                <CardFooter className="pt-0 pb-3">
                  <div className="flex flex-col gap-2 w-full">
                    <div className="grid grid-cols-2 gap-2 w-full">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="flex items-center justify-center gap-1 h-auto py-1.5 whitespace-nowrap text-xs"
                          onClick={() => handleDeanonymize(review)}
                          disabled={review.deanonymized || review.isLoading}
                        >
                        {review.isLoading ? (
                          <>
                            <Loader2 className="h-4 w-4 flex-shrink-0" />
                            <span className="whitespace-nowrap">İşleniyor...</span>
                          </>
                        ) : review.deanonymized ? (
                          <>
                            <CheckCircle className="h-4 w-4 flex-shrink-0" />
                            <span className="whitespace-nowrap">Anonimlik Kaldırıldı</span>
                          </>
                        ) : (
                          <>
                            <Eye className="h-4 w-4 flex-shrink-0" />
                            <span className="whitespace-nowrap">Anonimliği Kaldır</span>
                          </>
                        )}
                        </Button>
                        
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="flex items-center justify-center gap-1 h-auto py-1.5 whitespace-nowrap text-xs"
                          onClick={() => downloadReview(review.id)}
                        >
                          <Download className="h-4 w-4 flex-shrink-0" />
                          <span className="whitespace-nowrap">İndir</span>
                        </Button>
                    </div>
                    
                    {review.deanonymized && review.finalPdfCreated && !review.forwarded_to_author && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex items-center justify-center gap-1 h-auto py-1.5 w-full whitespace-nowrap text-xs"
                        onClick={() => downloadFinalPdf(review)}
                      >
                        <Download className="h-4 w-4 flex-shrink-0" />
                        <span className="whitespace-nowrap">Final PDF&apos;i İndir</span>
                      </Button>
                    )}
                    
                    <Button 
                      variant={review.forwarded_to_author ? "outline" : "default"}
                      size="sm" 
                      className="flex items-center justify-center gap-1 h-auto py-1.5 w-full whitespace-nowrap text-xs"
                      onClick={() => showForwardConfirm(review)}
                      disabled={forwardingReview === review.id || review.forwarded_to_author || !review.deanonymized}
                    >
                      {forwardingReview === review.id ? (
                        <>
                          <Loader2 className="h-4 w-4 flex-shrink-0 animate-spin" />
                          <span className="whitespace-nowrap">İletiliyor</span>
                        </>
                      ) : review.forwarded_to_author ? (
                        <>
                          <CheckCircle className="h-4 w-4 flex-shrink-0" />
                          <span className="whitespace-nowrap">İletildi</span>
                        </>
                      ) : !review.deanonymized ? (
                        <>
                          <Send className="h-4 w-4 flex-shrink-0" />
                          <span className="whitespace-nowrap text-xs">Önce Anonimliği Kaldırın</span>
                        </>
                      ) : (
                        <>
                          <Send className="h-4 w-4 flex-shrink-0" />
                          <span className="whitespace-nowrap">Yazara İlet</span>
                        </>
                      )}
                    </Button>
                  </div>
                </CardFooter>
              </Card>
                ))}
          </div>
        )}
        
        {/* İnceleme Yazara İletme Onay Diyaloğu */}
        <ConfirmDialog 
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          onConfirm={forwardReviewToAuthor}
          title="İncelemeyi Yazara İlet"
          description={selectedReviewDetails ? 
            `<p>"<strong>${selectedReviewDetails.title}</strong>" başlıklı makaleye ait hakem değerlendirmesini yazara iletmek istediğinize emin misiniz?</p>
            <div class="mt-2 p-3 bg-gray-50 rounded border border-gray-200">
              <div><span class="font-medium">Takip Numarası:</span> ${selectedReviewDetails.trackingNumber}</div>
              <div><span class="font-medium">Değerlendirme Puanı:</span> ${selectedReviewDetails.score}/10</div>
            </div>
            <p class="mt-2">Bu işlem:</p>
            <ul class="list-disc pl-5 mt-1">
              <li>Hakem değerlendirmesini yazara iletecek</li>
              <li>Yazara e-posta bildirimi gönderilecek</li>
              <li>Makale durumu "İletildi" olarak güncellenecek</li>
            </ul>` : 
            ""
          }
          confirmText="Yazara İlet"
          cancelText="İptal"
        />
      </div>
    </div>
  )
} 