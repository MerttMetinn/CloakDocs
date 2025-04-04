"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { STATUS_ENDPOINTS, fetchApi, API_BASE_URL, EDITOR_ENDPOINTS, REVIEW_ENDPOINTS } from "@/app/lib/apiConfig"
import { Card, CardContent } from "@/components/ui/card"
import ConfirmDialog from "@/app/components/ui/confirm-dialog"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/app/components/ui/button"
import { FileText, Download, RefreshCw, ArrowLeft, Filter, Eye, Tag, Loader2, Users } from "lucide-react"
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet"
import { StatusBadge, ArticleStatus } from "@/app/lib/articleStatus"

// Hakem kategorilerini import et
import { MAIN_CATEGORIES } from "@/app/data/categories"

interface Paper {
  id: number
  tracking_number: string
  email: string
  original_filename: string
  upload_date: string
  status: string
  download_count: number
}

interface KeywordData {
  manual_keywords: string[]
}

interface Category {
  id: number
  name: string
  icon: string
  subcategories: Subcategory[]
}

interface Subcategory {
  id: number
  name: string
  mainCategory?: string
  mainCategoryId?: number
  icon?: string
  keywords?: string[]
}

// Değerlendirme sonuçlarını göstermek için arayüz ve state tanımlaması ekleyelim
interface ReviewDetails {
  id: number;
  reviewer_id: string;
  subcategory_id: number;
  score: number;
  recommendation: string;
  comments?: string;
  created_at: string;
}

export default function EditorPapersPage() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [availableStatuses, setAvailableStatuses] = useState<string[]>([])
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(false)
  const [keywords, setKeywords] = useState<KeywordData | null>(null)
  const [keywordsLoading, setKeywordsLoading] = useState(false)
  const [keywordsError, setKeywordsError] = useState<string | null>(null)
  const [extractingKeywords, setExtractingKeywords] = useState(false)
  const [showReviewerModal, setShowReviewerModal] = useState(false)
  const [recommendedReviewer, setRecommendedReviewer] = useState<Subcategory | null>(null)
  const [reviewerInfo, setReviewerInfo] = useState<{ hasReviewer: boolean; reviewerSubcategory?: Subcategory } | null>(
    null,
  )
  const [changingReviewer, setChangingReviewer] = useState(false)
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [confirmDialogProps, setConfirmDialogProps] = useState<{
    title: string
    description: string
    onConfirm: () => void
  }>({
    title: "",
    description: "",
    onConfirm: () => {},
  })
  const [showReviewDetailsModal, setShowReviewDetailsModal] = useState(false)
  const [reviewDetails, setReviewDetails] = useState<ReviewDetails | null>(null)

  // Makaleleri yükle
  useEffect(() => {
    fetchPapers()
    
    // Tüm durum seçeneklerini hazırlayalım - sadece sık kullanılan ve temel statüler
    setAvailableStatuses([
      ArticleStatus.PENDING,
      ArticleStatus.IN_REVIEW,
      ArticleStatus.REVIEWED,
      ArticleStatus.REVISION_REQUIRED,
      ArticleStatus.REVISED,
      ArticleStatus.ACCEPTED,
      ArticleStatus.REJECTED,
      ArticleStatus.PUBLISHED
    ]);
  }, [])
  
  // Filtre değiştiğinde gösterilen makaleleri JS tarafında filtreleyelim
  useEffect(() => {
    // Bu değişiklik client tarafında yapılacak, API çağrısı yapılmayacak
  }, [statusFilter]);

  // Verileri yükle
  const fetchPapers = async () => {
    setLoading(true)
    setError(null)

    try {
      // Direkt olarak API endpoint'i kullan, filtre olmadan
      const endpoint = STATUS_ENDPOINTS.PAPERS;
      
      try {
        const data = await fetchApi(endpoint);
        
        if (data && data.papers) {
          setPapers(data.papers);
        } else {
          setError("Veri formatı beklendiği gibi değil");
        }
      } catch (err) {
        console.error("Makaleleri yükleme hatası:", err);
        const errorMessage = err instanceof Error ? err.message : "Makaleler yüklenirken bir hata oluştu";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    } catch (generalError) {
      console.error("Genel bir hata oluştu:", generalError);
      setError("Makaleler yüklenirken beklenmeyen bir hata oluştu");
      setLoading(false);
    }
  }

  // Anahtar kelimeleri yükleme
  const loadKeywords = async (trackingNumber: string) => {
    setKeywordsLoading(true)
    setKeywordsError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/paper/keywords/${trackingNumber}`)
      const data = await response.json()

      if (response.ok && data.success) {
        setKeywords(data.keywords)
      } else {
        setKeywords(null)
        if (data.error) {
          setKeywordsError(data.error)
        } else {
          setKeywordsError("Anahtar kelimeler yüklenirken bir hata oluştu")
        }
      }
    } catch (error) {
      console.error("Anahtar kelimeler yüklenirken hata:", error)
      setKeywords(null)
      setKeywordsError("Anahtar kelimeler yüklenirken bir hata oluştu")
    } finally {
      setKeywordsLoading(false)
    }
  }

  // Anahtar kelimeleri çıkarma
  const extractKeywords = async (trackingNumber: string) => {
    setExtractingKeywords(true)
    setKeywordsError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/paper/keywords/${trackingNumber}`, {
        method: "POST",
      })
      const data = await response.json()

      if (response.ok && data.success) {
        setKeywords(data.keywords)
      } else {
        setKeywords(null)
        if (data.error) {
          setKeywordsError(data.error)
        } else {
          setKeywordsError("Anahtar kelimeler çıkarılırken bir hata oluştu")
        }
      }
    } catch (error) {
      console.error("Anahtar kelimeler çıkarılırken hata:", error)
      setKeywords(null)
      setKeywordsError("Anahtar kelimeler çıkarılırken bir hata oluştu")
    } finally {
      setExtractingKeywords(false)
    }
  }

  // Anahtar kelimeye göre alt kategori bulma
  const findSubcategoryByKeyword = (keyword: unknown): Subcategory | null => {
    // keyword null, undefined veya string değilse hata oluşmasını engelle
    if (!keyword || typeof keyword !== 'string') {
      return null;
    }
    
    // Tüm alt kategorileri ve ilişkili anahtar kelimeleri düzleştirelim
    const subcategoriesWithKeywords = MAIN_CATEGORIES.flatMap((category: Category) =>
      category.subcategories.map((subcat: Subcategory) => ({
        ...subcat,
        mainCategory: category.name,
        mainCategoryId: category.id,
        icon: category.icon,
      })),
    )

    // En iyi eşleşmeyi ve puanını tutan değişkenler
    let bestMatch: Subcategory | null = null
    let bestMatchScore = 0

    // Keyword için doğru alt kategoriyi bul
    for (const subcat of subcategoriesWithKeywords) {
      // Önce tam eşleşme kontrol et - alt kategori adı keyword içinde geçiyor mu?
      if (keyword.toLowerCase().includes(subcat.name.toLowerCase())) {
        return subcat // Tam eşleşme varsa hemen döndür
      }

      // Alt kategori adı keyword içinde geçmiyorsa, anahtar kelimelere bak
      if (subcat.keywords && Array.isArray(subcat.keywords)) {
        for (const kw of subcat.keywords) {
          // Tam eşleşme varsa hemen döndür
          if (keyword.toLowerCase() === kw.toLowerCase()) {
            return subcat
          }

          // Kısmi eşleşme varsa puan ver
          if (keyword.toLowerCase().includes(kw.toLowerCase()) || kw.toLowerCase().includes(keyword.toLowerCase())) {
            // Eşleşme puanı - daha uzun kelime eşleşmeleri daha yüksek puan alır
            const matchScore = kw.length

            if (matchScore > bestMatchScore) {
              bestMatchScore = matchScore
              bestMatch = subcat
            }
          }
        }
      }
    }

    return bestMatch // En iyi eşleşmeyi döndür veya eşleşme yoksa null
  }

  // Makaleyi hakeme gönderme
  const sendToReviewer = async (keyword: string, subcategoryId?: number) => {
    try {
      // Bu keyword'e uygun hakem alanını belirlemek için
      // keyword ile ilgili alt kategori ID'sini bulma işlemi

      let subcategory: Subcategory | null = null

      if (subcategoryId) {
        // Eğer subcategoryId belirtilmişse, o ID'ye sahip alt kategoriyi bul
        subcategory =
          MAIN_CATEGORIES.flatMap((category) =>
            category.subcategories.map((subcat) => ({
              ...subcat,
              mainCategory: category.name,
              mainCategoryId: category.id,
              icon: category.icon,
            })),
          ).find((subcat) => subcat.id === subcategoryId) || null
      } else {
        // Keyword'e göre alt kategori bul
        subcategory = findSubcategoryByKeyword(keyword)
      }

      if (!subcategory) {
        // Eğer uygun alt kategori bulunamazsa
        setError(`"${keyword}" anahtar kelimesi için uygun bir hakem kategorisi bulunamadı.`)
        return
      }

      if (selectedPaper) {
        // Makale atama işlemi için yükleme durumunu göster
        setLoading(true)

        // Form verisini hazırla
        const formData = new FormData()
        formData.append("reviewer_id", `${subcategory.id}-1`) // "subcategory_id-1" formatında hakem ID'si
        formData.append("subcategory_id", subcategory.id.toString())

        // API endpointini al
        const assignEndpoint = EDITOR_ENDPOINTS.ASSIGN_REVIEWER(selectedPaper.tracking_number)

        // API isteğini gönder
        const response = await fetch(assignEndpoint, {
          method: "POST",
          body: formData,
        })

        const data = await response.json()

        if (response.ok && data.success) {
          // Başarılı yanıt
          setError(`Makale "${subcategory.name}" alanındaki hakeme başarıyla gönderildi. Durum "İncelemede" olarak güncellenmiştir.`)

          // Makale listesini güncelle
          fetchPapers()

          // Detay panelini kapat
          setIsDetailOpen(false)
        } else {
          // Hata durumunda
          setError(`Hata: ${data.error || "Makale hakeme gönderilirken bir sorun oluştu"}`)
        }

        setLoading(false)
      }
    } catch (error) {
      console.error("Hakeme gönderme hatası:", error)
      setError("Makale hakeme gönderilirken bir hata oluştu.")
      setLoading(false)
    }
  }

  // Makalenin değerlendirme sonucunu getiren fonksiyon
  // Not: Şu an için kullanılmıyor, ileride değerlendirme detayları görüntülemek için kullanılabilir
  /*
  const fetchReviewResult = async (trackingNumber: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/editor/review-result/${trackingNumber}`)
      
      if (!response.ok) {
        console.error("Değerlendirme sonucu getirme başarısız:", response.status)
        return null
      }
      
      const data = await response.json()
      
      if (data.success && data.review) {
        return data.review
      }
      
      return null
    } catch (error) {
      console.error("Değerlendirme sonucu getirme hatası:", error)
      return null
    }
  }
  */

  // Makale detaylarını göster
  const showPaperDetails = async (paper: Paper) => {
    setSelectedPaper(paper)
    setIsDetailOpen(true)
    setKeywords(null)
    setKeywordsError(null)
    setReviewerInfo(null)
    
    // Makale durumuna göre içeriği hazırla
    if (paper.status === 'anonymized' || paper.status === 'in_review') {
      // Anahtar kelimeleri yükle (anonimleştirilmiş veya incelemede ise)
      loadKeywords(paper.tracking_number)
    }
    
    if (paper.status === 'in_review' || paper.status === 'reviewed' || 
        paper.status === 'accepted' || paper.status === 'rejected' || 
        paper.status === 'revision_required') {
      // Hakem bilgisini kontrol et
      checkPaperReviewStatus(paper.tracking_number)
    }
  }

  // Tarih formatı
  const formatDate = (dateString: string) => {
    if (!dateString) return "Belirtilmemiş"

    try {
      const date = new Date(dateString)
      return date.toLocaleDateString("tr-TR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    } catch (error) {
      console.error("Tarih formatı hatası:", error)
      return dateString
    }
  }

  // Durum etiketi oluştur
  const getStatusBadge = (status: string) => {
    // ArticleStatus bileşenini kullanarak makale durumunu görselleştir
    return <StatusBadge status={status} />;
  }

  // Makale indirme
  const handleDownload = (trackingNumber: string) => {
    // Editör için /editor/download endpoint'ini kullanarak indirme
    const downloadUrl = `${API_BASE_URL}/editor/download/${trackingNumber}`
    window.open(downloadUrl, "_blank")
  }

  // Anahtar kelimelere göre en uygun hakemleri bulan fonksiyon
  const findBestReviewerForAllKeywords = (keywords: string[]): Subcategory | null => {
    // Sonuçları toplamak için hakem skorları
    const reviewerScores = new Map<number, { score: number; subcategory: Subcategory }>()

    // Tüm anahtar kelimeler için en iyi eşleşmeleri bul
    for (const keyword of keywords) {
      const subcategory = findSubcategoryByKeyword(keyword)
      if (subcategory) {
        const currentScore = reviewerScores.get(subcategory.id)?.score || 0
        reviewerScores.set(subcategory.id, {
          score: currentScore + 1,
          subcategory,
        })
      }
    }

    // En yüksek skoru olan hakemi bul
    let bestReviewer: Subcategory | null = null
    let bestScore = 0

    reviewerScores.forEach((data) => {
      if (data.score > bestScore) {
        bestScore = data.score
        bestReviewer = data.subcategory
      }
    })

    return bestReviewer
  }

  // Anahtar kelimelere göre hakem önerilerini oluşturan fonksiyon
  const generateReviewerRecommendations = () => {
    if (!keywords) return null

    // Sadece manuel anahtar kelimeleri kullan
    const allKeywords = keywords.manual_keywords || []

    if (allKeywords.length === 0) {
      return (
        <div className="space-y-3">
          <div className="text-sm text-gray-600 py-2">
            Anahtar kelimeler bulunamadı veya çıkarılamadı. Lütfen manuel olarak hakem seçiniz.
          </div>
          <div className="flex justify-end mt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowReviewerModal(true)}
            >
              <Users className="h-4 w-4 mr-2" />
              Hakem Seç
            </Button>
          </div>
        </div>
      )
    }

    // Her anahtar kelime için uygun hakemleri bul ve skor ver
    const reviewerScores = new Map<number, { score: number; subcategory: Subcategory }>()

    for (const keyword of allKeywords) {
      const subcategory = findSubcategoryByKeyword(keyword)
      if (subcategory) {
        const currentScore = reviewerScores.get(subcategory.id)?.score || 0
        reviewerScores.set(subcategory.id, {
          score: currentScore + 1,
          subcategory,
        })
      }
    }

    // Skorları sırala ve en iyi 3 öneriyi al
    const sortedReviewers = Array.from(reviewerScores.values())
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)

    if (sortedReviewers.length === 0) {
      return (
        <div className="space-y-3">
          <div className="text-sm text-gray-600 py-2">
            Anahtar kelimeler için uygun bir hakem bulunamadı. Lütfen manuel olarak hakem seçiniz.
          </div>
          <div className="flex justify-end mt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowReviewerModal(true)}
            >
              <Users className="h-4 w-4 mr-2" />
              Hakem Seç
            </Button>
          </div>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-600">Makalenin anahtar kelimelerine göre önerilen hakemler:</p>

        {sortedReviewers.map((item, index) => (
          <div
            key={item.subcategory.id}
            className={`p-4 rounded-md border ${
              index === 0 ? "bg-green-50 border-green-200" : "bg-gray-50 border-gray-200"
            }`}
          >
            <div className="flex flex-col space-y-3">
              <div>
                <h4 className={`text-sm font-medium ${index === 0 ? "text-green-800" : "text-gray-800"}`}>
                  {index === 0 && "🥇 "}
                  {item.subcategory.name}
                  <span className="ml-2 text-xs font-normal bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded-full">
                    Eşleşme: {Math.round((item.score / allKeywords.length) * 100)}%
                  </span>
                </h4>
                <p className="text-xs text-gray-600 mt-1">
                  {item.subcategory.mainCategory} / {item.subcategory.name}
                </p>
                {item.subcategory.keywords && (
                  <p className="text-xs text-gray-500 mt-1">
                    <span className="font-medium">İlgili anahtar kelimeler: </span>
                    {item.subcategory.keywords.slice(0, 3).join(", ")}
                    {item.subcategory.keywords.length > 3 ? "..." : ""}
                  </p>
                )}
              </div>
              <div className="flex justify-center pt-2">
                <Button
                  size="sm"
                  variant={index === 0 ? "default" : "outline"}
                  className={`min-w-[180px] whitespace-nowrap text-xs px-2 py-1.5 ${index === 0 ? "bg-green-600 hover:bg-green-700 text-white" : ""}`}
                  onClick={() => handleConfirmSendToReviewer(item.subcategory.name, item.subcategory.id)}
                >
                  {index === 0 ? "Önerilen Hakeme Gönder" : "Seç"}
                </Button>
              </div>
            </div>
          </div>
        ))}

        <div className="grid grid-cols-2 gap-4 mt-4">
          <Button
            variant="outline"
            className="min-w-[180px] w-full text-xs whitespace-nowrap px-2 py-1.5"
            onClick={() => {
              setRecommendedReviewer(sortedReviewers[0]?.subcategory || null)
              setShowReviewerModal(true)
            }}
          >
            
            Diğer Hakemleri Görüntüle
          </Button>
          
          {keywords.manual_keywords && keywords.manual_keywords.length > 0 && (
            <Button
              onClick={() => {
                const allKeywords = keywords.manual_keywords || []
                if (allKeywords.length > 0) {
                  const bestSubcat = findBestReviewerForAllKeywords(allKeywords)
                  if (bestSubcat) {
                    handleConfirmSendToReviewer(bestSubcat.name, bestSubcat.id)
                  } else {
                    alert("Uygun bir hakem bulunamadı.")
                  }
                }
              }}
              className="bg-primary hover:bg-primary/90 text-white min-w-[180px] w-full text-xs whitespace-nowrap px-2 py-1.5"
            >
              Önerilen Hakeme Gönder
            </Button>
          )}
        </div>
      </div>
    )
  }

  // Makalenin hakem durumunu kontrol et
  const checkPaperReviewStatus = async (trackingNumber: string) => {
    try {
      // Makalenin reviews tablosunda kaydı var mı kontrol et
      const response = await fetch(`${API_BASE_URL}/editor/check-review-status/${trackingNumber}`)

      if (!response.ok) {
        console.error("Hakem durumu kontrolü başarısız:", response.status)
        return
      }

      const data = await response.json()

      if (data.success) {
        if (data.has_reviewer) {
          // Hakem bulunmuşsa, hakem alt kategorisini bul
          const reviewerSubcategoryId = data.review?.subcategory_id

          if (reviewerSubcategoryId) {
            const subcategory = MAIN_CATEGORIES.flatMap((category) =>
              category.subcategories.map((subcat) => ({
                ...subcat,
                mainCategory: category.name,
                mainCategoryId: category.id,
                icon: category.icon,
              })),
            ).find((subcat) => subcat.id === reviewerSubcategoryId)

            setReviewerInfo({
              hasReviewer: true,
              reviewerSubcategory: subcategory,
            })
          } else {
            setReviewerInfo({ hasReviewer: true })
          }
        } else {
          setReviewerInfo({ hasReviewer: false })
        }
      }
    } catch (error) {
      console.error("Hakem durumu kontrolü hatası:", error)
    }
  }

  // Hakem değiştirme fonksiyonu
  const updateReviewer = async (subcategoryId: number) => {
    try {
      if (!selectedPaper) return

      setChangingReviewer(true)

      // Form verisini hazırla
      const formData = new FormData()
      formData.append("new_reviewer_id", `${subcategoryId}-1`) // "subcategory_id-1" formatında hakem ID'si
      formData.append("subcategory_id", subcategoryId.toString())

      // API endpointini al
      const updateEndpoint = REVIEW_ENDPOINTS.UPDATE_REVIEWER(selectedPaper.tracking_number)

      // API isteğini gönder
      const response = await fetch(updateEndpoint, {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (response.ok && data.success) {
        // Başarılı yanıt
        const updatedSubcategory = MAIN_CATEGORIES.flatMap((category) =>
          category.subcategories.map((subcat) => ({
            ...subcat,
            mainCategory: category.name,
            mainCategoryId: category.id,
            icon: category.icon,
          })),
        ).find((subcat) => subcat.id === subcategoryId)

        setError(`Makalenin hakemi "${updatedSubcategory?.name || "Seçilen"}" alanındaki hakeme başarıyla değiştirildi.`)

        // Reviewer bilgisini güncelle
        setReviewerInfo({
          hasReviewer: true,
          reviewerSubcategory: updatedSubcategory,
        })

        // Makale listesini güncelle
        fetchPapers()

        // Modal'ı kapat
        setShowReviewerModal(false)
      } else {
        // Hata durumunda
        setError(`Hata: ${data.error || "Hakem değiştirilirken bir sorun oluştu"}`)
      }
    } catch (error) {
      console.error("Hakem değiştirme hatası:", error)
      setError("Hakem değiştirilirken bir hata oluştu.")
    } finally {
      setChangingReviewer(false)
    }
  }

  // Function to handle confirmation before sending to reviewer
  const handleConfirmSendToReviewer = (subcategoryName: string, subcategoryId: number) => {
    setConfirmDialogProps({
      title: "Hakeme Gönder",
      description: `Makaleyi "${subcategoryName}" alanındaki hakeme göndermek istiyor musunuz?`,
      onConfirm: () => {
        sendToReviewer("", subcategoryId)
      },
    })
    setConfirmDialogOpen(true)
  }

  // Function to handle confirmation before updating reviewer
  const handleConfirmUpdateReviewer = (subcategoryName: string, subcategoryId: number) => {
    setConfirmDialogProps({
      title: "Hakem Değiştir",
      description: `Hakemi "${subcategoryName}" alanındaki hakem ile değiştirmek istiyor musunuz?`,
      onConfirm: () => {
        updateReviewer(subcategoryId)
      },
    })
    setConfirmDialogOpen(true)
  }

  // Add a function to handle closing the reviewer modal after confirmation
  const handleConfirmSendToReviewerAndCloseModal = (subcategoryName: string, subcategoryId: number) => {
    setConfirmDialogProps({
      title: "Hakeme Gönder",
      description: `Makaleyi "${subcategoryName}" alanındaki hakeme göndermek istiyor musunuz?`,
      onConfirm: () => {
        sendToReviewer("", subcategoryId)
        setShowReviewerModal(false)
      },
    })
    setConfirmDialogOpen(true)
  }

  // Değerlendirme detaylarını getiren fonksiyon
  const fetchReviewDetails = async (trackingNumber: string) => {
    try {
      // Makalenin değerlendirme detaylarını getir
      const response = await fetch(`${API_BASE_URL}/editor/check-review-status/${trackingNumber}`)

      if (!response.ok) {
        console.error("Değerlendirme detayları getirme başarısız:", response.status)
        return null
      }

      const data = await response.json()

      if (data.success && data.has_reviewer && data.review) {
        setReviewDetails(data.review)
        setShowReviewDetailsModal(true)
        return data.review
      }

      return null
    } catch (error) {
      console.error("Değerlendirme detayları getirme hatası:", error)
      return null
    }
  }

  return (
    <div className="min-h-screen p-4 bg-background">
      <ConfirmDialog
        open={confirmDialogOpen}
        onOpenChange={setConfirmDialogOpen}
        title={confirmDialogProps.title}
        description={confirmDialogProps.description}
        onConfirm={confirmDialogProps.onConfirm}
      />
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <Link href="/Users/editor" className="mr-4">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <h1 className="text-2xl font-bold text-primary">Tüm Makaleler</h1>
          </div>

          <div className="flex gap-2">
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => document.getElementById("statusFilterDropdown")?.classList.toggle("hidden")}
              >
                <Filter className="h-4 w-4" />
                {statusFilter ? getStatusBadge(statusFilter) : "Tüm Durumlar"}
              </Button>
              <div
                id="statusFilterDropdown"
                className="hidden absolute right-0 mt-2 w-56 rounded-md shadow-lg bg-white dark:bg-background-secondary ring-1 ring-black ring-opacity-5 divide-y divide-gray-100 focus:outline-none z-10"
              >
                <div className="py-1">
                  <button
                    onClick={() => {
                      setStatusFilter(null)
                      document.getElementById("statusFilterDropdown")?.classList.add("hidden")
                    }}
                    className="text-left w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900"
                  >
                    Tüm Durumlar
                  </button>
                  
                  {availableStatuses.map((status) => (
                    <button
                      key={status}
                      onClick={() => {
                        setStatusFilter(status)
                        document.getElementById("statusFilterDropdown")?.classList.add("hidden")
                      }}
                      className="text-left w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 flex items-center"
                    >
                      <div className="mr-2">
                        <StatusBadge status={status} />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <Button variant="outline" size="sm" className="gap-1.5" onClick={fetchPapers}>
              <RefreshCw className="h-4 w-4" />
              Yenile
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-4">
            <AlertTitle>Bilgi</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
          </div>
        ) : papers.length === 0 ? (
          <Card className="mb-4">
            <CardContent className="py-12">
              <div className="text-center text-gray-500">
                <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-medium">Makale bulunamadı</h3>
                <p className="mt-1">Bu kriterlere uygun makale bulunmamaktadır.</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="overflow-x-auto bg-white rounded-lg border border-border shadow-sm">
            <table className="w-full">
              <thead className="bg-background-secondary border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Takip No
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Dosya Adı
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Gönderim Tarihi
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Durum
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    İşlemler
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {papers
                  .filter(paper => !statusFilter || paper.status.toLowerCase() === statusFilter.toLowerCase())
                  .map((paper) => (
                  <tr key={paper.id}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span className="font-medium text-foreground">{paper.tracking_number}</span>
                    </td>
                    <td className="px-4 py-3 text-sm truncate max-w-[200px]">
                      <span className="text-foreground">{paper.original_filename}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span className="text-muted-foreground">{formatDate(paper.upload_date)}</span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      {getStatusBadge(paper.status)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right space-x-1">
                      <Button variant="ghost" size="icon" title="İndir" onClick={() => handleDownload(paper.tracking_number)}>
                        <Download className="h-4 w-4 text-muted-foreground" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Detaylar"
                        onClick={() => showPaperDetails(paper)}
                      >
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Makale Detayları Sheet */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent className="sm:max-w-md bg-white p-0 overflow-auto">
          <div className="bg-gradient-to-r from-primary/90 to-primary p-6 text-white">
            <SheetTitle className="text-xl font-semibold text-white">Makale Detayları</SheetTitle>
            <p className="text-white/80 text-sm font-mono mt-1">{selectedPaper?.tracking_number}</p>
          </div>

          {selectedPaper && (
            <div className="px-6 py-5">
              <div className="space-y-6">
                <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
                  <h3 className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">Dosya Adı</h3>
                  <div className="flex items-center">
                    <FileText className="h-4 w-4 mr-2 text-muted-foreground" />
                    <p className="text-foreground font-medium">{selectedPaper.original_filename}</p>
                  </div>
                </div>

                <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
                  <h3 className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">Takip Numarası</h3>
                  <div className="flex items-center">
                    <div className="bg-primary/10 text-primary px-3 py-2 rounded-md font-mono font-medium text-sm w-full flex items-center justify-between">
                      {selectedPaper.tracking_number}
                      <span className="text-primary/60 text-xs bg-primary/5 px-1.5 py-0.5 rounded">ID</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all flex-1">
                    <h3 className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">Yazar</h3>
                    <div className="flex items-center">
                      <div className="h-8 w-8 rounded-full bg-accent/10 text-accent flex items-center justify-center mr-2 flex-shrink-0">
                        {selectedPaper.email.charAt(0).toUpperCase()}
                      </div>
                      <p
                        className="text-foreground text-sm overflow-hidden text-ellipsis whitespace-nowrap"
                        title={selectedPaper.email}
                      >
                        {selectedPaper.email.length > 20
                          ? selectedPaper.email.substring(0, 20) + "..."
                          : selectedPaper.email}
                      </p>
                    </div>
                  </div>

                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all flex-1">
                    <h3 className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">İndirme</h3>
                    <div className="flex items-center">
                      <Download className="h-4 w-4 mr-2 text-accent" />
                      <p className="text-foreground font-medium">{selectedPaper.download_count || 0} kez</p>
                    </div>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all flex-1">
                    <h3 className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">Yükleme Tarihi</h3>
                    <div className="flex items-center">
                      <p className="text-foreground">{formatDate(selectedPaper.upload_date)}</p>
                    </div>
                  </div>

                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all flex-1">
                    <h3 className="text-xs font-semibold text-primary uppercase tracking-wider mb-2">Durum</h3>
                    <div>{getStatusBadge(selectedPaper.status)}</div>
                  </div>
                </div>

                {/* Beklemede durumunda olan makaleler için Anonimleştirme butonu */}
                {selectedPaper.status === 'pending' && (
                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
                    <h3 className="text-xs font-semibold text-primary uppercase tracking-wider mb-3">Makale İşlemleri</h3>
                    <div className="p-3 rounded-md bg-yellow-50 border border-yellow-200">
                      <p className="text-yellow-800 mb-2">
                        Bu makale henüz anonimleştirilmemiş durumda ve hakem atama işlemine hazır değil.
                      </p>
                      <Link href={`/Users/editor/anonymize?trackingNumber=${selectedPaper.tracking_number}`} passHref>
                        <Button className="w-full mt-2 bg-yellow-500 hover:bg-yellow-600 text-white">
                          Anonimleştirme Sayfasına Git
                        </Button>
                      </Link>
                    </div>
                  </div>
                )}

                {/* Anahtar Kelimeler Bölümü - Sadece anonimleştirilmiş ve incelemede olan makaleler için göster */}
                {(selectedPaper.status === 'anonymized' || selectedPaper.status === 'in_review') && (
                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs font-semibold text-primary uppercase tracking-wider">Anahtar Kelimeler</h3>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1"
                        onClick={() => extractKeywords(selectedPaper.tracking_number)}
                        disabled={extractingKeywords}
                      >
                        {extractingKeywords ? (
                          <>
                            <Loader2 className="h-3 w-3 animate-spin" />
                            İşleniyor...
                          </>
                        ) : (
                          <>
                            <Tag className="h-3 w-3" />
                            {keywords ? "Yeniden İşle" : "İşle"}
                          </>
                        )}
                      </Button>
                    </div>

                    {keywordsLoading ? (
                      <div className="flex justify-center py-4">
                        <Loader2 className="h-5 w-5 animate-spin text-primary" />
                      </div>
                    ) : keywordsError ? (
                      <div className="text-sm text-muted-foreground">
                        <p className="text-status-error mb-2">{keywordsError}</p>
                        <p>Anahtar kelimeleri çıkarmak için &quot;İşle&quot; butonuna tıklayın.</p>
                      </div>
                    ) : keywords ? (
                      <div className="space-y-3">
                        {keywords.manual_keywords && keywords.manual_keywords.length > 0 && (
                          <div>
                            <h4 className="text-xs font-medium mb-1">Anahtar Kelimeler</h4>
                            <div className="flex flex-wrap gap-1">
                              {keywords.manual_keywords.map((keyword, idx) => (
                                <span key={idx} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground">
                        <p>Henüz anahtar kelimelere erişilemedi.</p>
                        <p>Anahtar kelimeleri çıkarmak için &quot;İşle&quot; butonuna tıklayın.</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Hakem Önerisi ve Seçim Bölümü - Anahtar kelimeler işlendikten sonra göster */}
                {selectedPaper.status === 'anonymized' && keywords && (
                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all mt-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs font-semibold text-primary uppercase tracking-wider">
                        Hakeme Gönder
                      </h3>
                    </div>

                    {/* Anahtar kelimelere göre önerilen hakemler */}
                    {generateReviewerRecommendations()}
                  </div>
                )}

                {/* Atanmış Hakem Bilgisi - Sadece "in_review" durumundaki makaleler için göster */}
                {selectedPaper.status === 'in_review' && (
                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all mt-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs font-semibold text-primary uppercase tracking-wider">
                        Atanmış Hakem
                      </h3>
                    </div>

                    {!reviewerInfo ? (
                      <div className="flex justify-center py-4">
                        <Loader2 className="h-5 w-5 animate-spin text-primary" />
                      </div>
                    ) : reviewerInfo.hasReviewer ? (
                      <div className="space-y-4">
                        <div className="p-3 rounded-md bg-blue-50 border border-blue-200">
                          <p className="text-blue-800 mb-2">
                            Bu makale{" "}
                            {reviewerInfo.reviewerSubcategory ? (
                              <span className="font-medium">{reviewerInfo.reviewerSubcategory.name}</span>
                            ) : (
                              "bir"
                            )}{" "}
                            konusu hakemine gönderilmiştir.
                          </p>

                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full mt-2"
                            onClick={() => setShowReviewerModal(true)}
                          >
                            <RefreshCw className="h-3 w-3 mr-2" />
                            Hakem Değiştir
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground">
                        <p>Bu makale için atanmış bir hakem bulunamadı.</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Değerlendirme Sonucu - Sadece değerlendirilmiş, kabul edilmiş, reddedilmiş veya revizyon gerektirenler için */}
                {(selectedPaper.status === 'reviewed' || selectedPaper.status === 'accepted' || 
                  selectedPaper.status === 'rejected' || selectedPaper.status === 'revision_required') && (
                  <div className="bg-background/50 rounded-lg p-4 border border-border/30 hover:border-border/50 transition-all">
                    <h3 className="text-xs font-semibold text-primary uppercase tracking-wider mb-3">Değerlendirme Sonucu</h3>
                    
                    {!reviewerInfo ? (
                      <div className="flex justify-center py-4">
                        <Loader2 className="h-5 w-5 animate-spin text-primary" />
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <div className={`p-3 rounded-md ${
                          selectedPaper.status === 'accepted' ? 'bg-green-50 border border-green-200' :
                          selectedPaper.status === 'rejected' ? 'bg-red-50 border border-red-200' :
                          selectedPaper.status === 'revision_required' ? 'bg-orange-50 border border-orange-200' :
                          'bg-blue-50 border border-blue-200'
                        }`}>
                          <p className={`mb-2 ${
                            selectedPaper.status === 'accepted' ? 'text-green-800' :
                            selectedPaper.status === 'rejected' ? 'text-red-800' :
                            selectedPaper.status === 'revision_required' ? 'text-orange-800' :
                            'text-blue-800'
                          }`}>
                            Bu makale{" "}
                            {reviewerInfo.reviewerSubcategory ? (
                              <span className="font-medium">{reviewerInfo.reviewerSubcategory.name}</span>
                            ) : (
                              "bir hakem"
                            )}{" "}
                            tarafından değerlendirilmiştir.
                          </p>
                          
                          <div className="flex items-center mt-3">
                            <span className="text-sm text-muted-foreground mr-2">Sonuç:</span>
                            <span className={`text-sm font-medium px-2.5 py-0.5 rounded ${
                              selectedPaper.status === 'accepted' ? 'bg-green-100 text-green-800' :
                              selectedPaper.status === 'rejected' ? 'bg-red-100 text-red-800' :
                              selectedPaper.status === 'revision_required' ? 'bg-orange-100 text-orange-800' :
                              'bg-blue-100 text-blue-800'
                            }`}>
                              {
                                selectedPaper.status === 'accepted' ? 'Kabul Edildi' :
                                selectedPaper.status === 'rejected' ? 'Reddedildi' :
                                selectedPaper.status === 'revision_required' ? 'Revizyon Gerekli' :
                                'Değerlendirildi'
                              }
                            </span>
                          </div>
                          
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full mt-4"
                            onClick={() => fetchReviewDetails(selectedPaper.tracking_number)}
                          >
                            Değerlendirme Detaylarını Görüntüle
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="px-6 pb-6 pt-1">
            <Button
              onClick={() => handleDownload(selectedPaper?.tracking_number || "")}
              className="w-full bg-primary hover:bg-primary/90 text-white gap-2 py-6"
            >
              <Download className="h-4 w-4" />
              Makaleyi İndir
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Hakem Seçim Modalı */}
      {showReviewerModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full max-h-[90vh] overflow-auto">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Hakem Seçimi</h3>
              <p className="text-sm text-gray-600 mt-1">
                Makale için {reviewerInfo?.hasReviewer ? "yeni bir hakem" : "uygun hakem"} seçiniz
              </p>
            </div>

            <div className="p-4">
              {recommendedReviewer && (
                <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md">
                  <h4 className="text-sm font-semibold text-green-800 mb-1">Önerilen Hakem</h4>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-green-700">{recommendedReviewer.name}</p>
                      <p className="text-xs text-green-600 mt-1">
                        {recommendedReviewer.mainCategory} / {recommendedReviewer.name}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      className="bg-green-600 hover:bg-green-700 text-white min-w-[110px] whitespace-nowrap"
                      onClick={() => {
                        if (reviewerInfo?.hasReviewer) {
                          updateReviewer(recommendedReviewer.id)
                        } else {
                          sendToReviewer("", recommendedReviewer.id)
                          setShowReviewerModal(false)
                        }
                      }}
                      disabled={changingReviewer}
                    >
                      {changingReviewer ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          İşleniyor...
                        </>
                      ) : (
                        <>Seç ve Gönder</>
                      )}
                    </Button>
                  </div>
                </div>
              )}

              <h4 className="text-sm font-semibold mb-2">Tüm Hakemler</h4>
              <div className="space-y-2 max-h-[50vh] overflow-auto pr-2">
                {MAIN_CATEGORIES.map((category) => (
                  <div key={category.id} className="mb-3">
                    <h5 className="text-xs font-semibold text-gray-700 mb-1 border-b pb-1">{category.name}</h5>
                    <div className="space-y-2 pl-2">
                      {category.subcategories.map((subcategory) => (
                        <div
                          key={subcategory.id}
                          className={`p-2 rounded-md cursor-pointer flex items-center justify-between ${
                            recommendedReviewer && recommendedReviewer.id === subcategory.id
                              ? "bg-green-50 border border-green-200"
                              : "hover:bg-gray-50 border border-gray-100"
                          }`}
                        >
                          <div>
                            <p className="text-sm font-medium">{subcategory.name}</p>
                            <p className="text-xs text-gray-500">
                              {subcategory.keywords && subcategory.keywords.length > 0
                                ? subcategory.keywords.slice(0, 3).join(", ") +
                                  (subcategory.keywords.length > 3 ? "..." : "")
                                : "Anahtar kelime yok"}
                            </p>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              if (reviewerInfo?.hasReviewer) {
                                handleConfirmUpdateReviewer(subcategory.name, subcategory.id)
                              } else {
                                handleConfirmSendToReviewerAndCloseModal(subcategory.name, subcategory.id)
                              }
                            }}
                            disabled={changingReviewer}
                            className="min-w-[70px] whitespace-nowrap"
                          >
                            {changingReviewer ? <Loader2 className="h-3 w-3 animate-spin" /> : <>Seç</>}
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t border-gray-200 p-4 flex justify-end">
              <Button variant="outline" onClick={() => setShowReviewerModal(false)}>
                İptal
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Değerlendirme Detayları Modalı */}
      {showReviewDetailsModal && reviewDetails && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full max-h-[90vh] overflow-auto">
            <div className="p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Değerlendirme Detayları</h3>
            </div>

            <div className="p-4">
              <div className="space-y-4">
                {reviewDetails.score > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-semibold mb-1">Değerlendirme Puanı</h4>
                    <div className="flex items-center">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            reviewDetails.score >= 7 ? 'bg-green-500' :
                            reviewDetails.score >= 5 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${(reviewDetails.score / 10) * 100}%` }}
                        ></div>
                      </div>
                      <span className="ml-3 text-sm font-medium">{reviewDetails.score}/10</span>
                    </div>
                  </div>
                )}

                <div className="mb-4">
                  <h4 className="text-sm font-semibold mb-1">Öneri</h4>
                  <div className="p-2 rounded bg-gray-50 border">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      reviewDetails.recommendation === 'accept' ? 'bg-green-100 text-green-800' :
                      reviewDetails.recommendation === 'reject' ? 'bg-red-100 text-red-800' :
                      reviewDetails.recommendation === 'revision_required' ? 'bg-orange-100 text-orange-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {reviewDetails.recommendation === 'accept' ? 'Kabul' :
                       reviewDetails.recommendation === 'reject' ? 'Red' :
                       reviewDetails.recommendation === 'revision_required' ? 'Revizyon Gerekli' :
                       reviewDetails.recommendation}
                    </span>
                  </div>
                </div>

                {reviewDetails.comments && (
                  <div className="mb-4">
                    <h4 className="text-sm font-semibold mb-1">Yorumlar</h4>
                    <div className="p-3 rounded bg-gray-50 border">
                      <p className="text-sm whitespace-pre-wrap">{reviewDetails.comments}</p>
                    </div>
                  </div>
                )}

                <div className="mb-4">
                  <h4 className="text-sm font-semibold mb-1">Değerlendirme Tarihi</h4>
                  <p className="text-sm">{formatDate(reviewDetails.created_at)}</p>
                </div>
              </div>
            </div>

            <div className="border-t border-gray-200 p-4 flex justify-end">
              <Button variant="outline" onClick={() => setShowReviewDetailsModal(false)}>
                Kapat
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

