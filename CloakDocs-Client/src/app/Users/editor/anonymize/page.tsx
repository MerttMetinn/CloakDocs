"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { ArrowLeft, FileText, Search, Download, Check, AlertTriangle, Loader2, ChevronLeft, ChevronRight, BarChart2 } from "lucide-react"
import { Button } from "@/app/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip"
import { ANONYMIZE_ENDPOINTS, API_BASE_URL, STATUS_ENDPOINTS, fetchApi } from "@/app/lib/apiConfig"
import ConfirmDialog from "@/app/components/ui/confirm-dialog"
import { toast } from "sonner"
import { StatusBadge, ArticleStatus } from "@/app/lib/articleStatus"

interface Paper {
  id: number;
  tracking_number: string;
  original_filename: string;
  upload_date: string;
  status: string;
  download_count: number;
  email: string;
}

interface AnonymizeOptions {
  author_name: boolean;
  contact_info: boolean;
  institution_info: boolean;
}

interface AnonymizationStats {
  options?: string[];
  entities_found?: {
    author_name_count: number;
    contact_info_count: number;
    institution_info_count: number;
  };
  timestamp?: string;
}

interface StatsResponse {
  success: boolean;
  paper: {
    id: number;
    tracking_number: string;
    original_filename: string;
    status: string;
    upload_date: string;
  };
  anonymized_file: {
    id: number;
    filename: string;
    created_at: string;
    download_count: number;
  };
  anonymization_stats: AnonymizationStats;
}

export default function AnonymizePage() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [activeTab, setActiveTab] = useState("pending")
  const [anonymizingPaper, setAnonymizingPaper] = useState<string | null>(null)
  const [selectedOptions, setSelectedOptions] = useState<AnonymizeOptions>({
    author_name: false,
    contact_info: false,
    institution_info: false
  })
  
  // Sayfalama için state
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 5
  
  // Doğrulama diyaloğu için state
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [selectedTrackingNumber, setSelectedTrackingNumber] = useState<string>("")
  const [selectedFileName, setSelectedFileName] = useState<string>("")

  // İstatistik görüntüleme için state
  const [statsOpen, setStatsOpen] = useState(false)
  const [statsLoading, setStatsLoading] = useState(false)
  const [statsData, setStatsData] = useState<StatsResponse | null>(null)

  // Makaleleri yükle
  useEffect(() => {
    fetchPapers()
  }, [activeTab])

  const fetchPapers = async () => {
    setLoading(true)
    
    try {
      // Filtre olmadan tüm makaleleri getir
      const endpoint = STATUS_ENDPOINTS.PAPERS
      
      try {
        const data = await fetchApi(endpoint)
        
        if (data && data.papers) {
          // Tüm makaleleri al, filtrelemeyi client tarafında yap
          if (activeTab === "pending") {
            // Sadece bekleyen makaleleri göster
            setPapers(data.papers.filter((paper: Paper) => paper.status === ArticleStatus.PENDING))
          } else {
            // Anonimleştirilmiş makaleleri göster
            setPapers(data.papers.filter((paper: Paper) => paper.status === ArticleStatus.ANONYMIZED))
          }
        } else {
          console.error("Veri formatı beklendiği gibi değil")
          toast.error("Beklenmeyen veri formatı: Makaleler alınamadı")
        }
      } catch (error) {
        console.error("Makaleleri yükleme hatası:", error)
        toast.error("Makaleler yüklenirken bir hata oluştu: " + (error instanceof Error ? error.message : "Bilinmeyen hata"))
        setPapers([])
      } finally {
        setLoading(false)
      }
    } catch (generalError) {
      console.error("Genel bir hata oluştu:", generalError)
      toast.error("Makaleler yüklenirken beklenmeyen bir hata oluştu")
      setPapers([])
      setLoading(false)
    }
  }

  // Anonimleştirme seçeneklerini güncelle
  const handleOptionChange = (option: keyof AnonymizeOptions) => {
    setSelectedOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }))
  }

  // Seçili seçenekleri kontrol et
  const hasSelectedOptions = () => {
    return Object.values(selectedOptions).some(value => value)
  }

  // Makale indirme
  const handleDownload = (trackingNumber: string) => {
    // Editör için /editor/download endpoint'ini kullanarak indirme
    const downloadUrl = `${API_BASE_URL}/editor/download/${trackingNumber}`
    window.open(downloadUrl, "_blank")
  }
  
  // Anonimleştirilmiş dosya indirme
  const handleAnonymizedDownload = (trackingNumber: string) => {
    const downloadUrl = ANONYMIZE_ENDPOINTS.DOWNLOAD(trackingNumber)
    window.open(downloadUrl, '_blank')
  }
  
  // Anonimleştirme onay diyaloğunu göster
  const showAnonymizeConfirm = (trackingNumber: string, fileName: string) => {
    if (!hasSelectedOptions()) {
      toast.error("Lütfen en az bir anonimleştirme seçeneği seçin")
      return
    }
    
    setSelectedTrackingNumber(trackingNumber)
    setSelectedFileName(fileName)
    setConfirmOpen(true)
  }
  
  // Makaleyi anonimleştir
  const anonymizePaper = async () => {
    if (!selectedTrackingNumber) return
    
    setAnonymizingPaper(selectedTrackingNumber)
    try {
      // Seçili seçenekleri diziye dönüştür
      const selectedOptionsArray = Object.entries(selectedOptions)
        .filter(([, value]) => value)
        .map(([key]) => key)

      const data = await fetchApi(ANONYMIZE_ENDPOINTS.PROCESS(selectedTrackingNumber), {
        method: 'POST',
        body: JSON.stringify({
          options: selectedOptionsArray
        })
      })
      
      if (data.success) {
        toast.success("Makale başarıyla anonimleştirildi")
        fetchPapers() // Listeyi yenile
        // Seçenekleri sıfırla
        setSelectedOptions({
          author_name: false,
          contact_info: false,
          institution_info: false
        })
        
        // İstatistikleri göster
        viewAnonymizationStats(selectedTrackingNumber)
      } else {
        toast.error(data.error || 'Anonimleştirme işlemi sırasında bir sorun oluştu')
      }
    } catch (error) {
      console.error("Anonimleştirme hatası:", error)
      toast.error("Makaleyi anonimleştirirken bir hata oluştu")
    } finally {
      setAnonymizingPaper(null)
      setConfirmOpen(false)
    }
  }

  // Anonimleştirme istatistiklerini getir ve göster
  const viewAnonymizationStats = async (trackingNumber: string) => {
    setStatsLoading(true)
    
    try {
      const data = await fetchApi(ANONYMIZE_ENDPOINTS.STATS(trackingNumber))
      
      if (data.success) {
        setStatsData(data)
        setStatsOpen(true)
      } else {
        toast.error(data.error || "İstatistikler alınamadı")
      }
    } catch (error) {
      console.error("İstatistik alma hatası:", error)
      toast.error("Anonimleştirme istatistikleri alınırken bir hata oluştu")
    } finally {
      setStatsLoading(false)
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
        day: "numeric"
      })
    } catch (error) {
      console.error("Tarih formatı hatası:", error)
      return dateString
    }
  }
  
  // Durum etiketi oluştur
  const getStatusBadge = (status: string) => {
    return <StatusBadge status={status} />
  }

  // Arama filtresi
  const filteredPapers = papers.filter(paper => 
    paper.tracking_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
    paper.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    paper.email.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
  // Sayfalama hesaplamaları
  const totalPages = Math.ceil(filteredPapers.length / itemsPerPage)
  const indexOfLastItem = currentPage * itemsPerPage
  const indexOfFirstItem = indexOfLastItem - itemsPerPage
  const currentItems = filteredPapers.slice(indexOfFirstItem, indexOfLastItem)
  
  // Sayfa değiştirme fonksiyonu
  const paginate = (pageNumber: number) => {
    setCurrentPage(pageNumber)
  }
  
  // Sonraki ve önceki sayfa fonksiyonları
  const nextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(prev => prev + 1)
    }
  }
  
  const prevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(prev => prev - 1)
    }
  }
  
  // Arama yapıldığında ilk sayfaya dön
  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm, activeTab])

  return (
    <div className="min-h-screen p-4 bg-background">
      <TooltipProvider delayDuration={300}>
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center">
              <Link href="/Users/editor" className="mr-4">
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <h1 className="text-2xl font-bold text-primary">Makale Anonimleştirme</h1>
            </div>
            
            <Button onClick={fetchPapers} className="gap-2">
              <FileText className="h-4 w-4" />
              Makaleleri Yenile
            </Button>
          </div>
          
          <Card className="mb-6">
            <CardHeader className="pb-3">
              <CardTitle>Makale Anonimleştirme Aracı</CardTitle>
              <CardDescription>
                Makaleleri hakemlere göndermeden önce yazarların kişisel bilgilerini kaldırarak anonimleştirin
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row gap-4">
                  <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="search"
                      placeholder="Makale ara: Takip numarası, dosya adı veya e-posta..."
                      className="pl-8"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                  </div>
                  
                  <Tabs defaultValue="pending" className="w-[300px]" value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="pending">Bekleyenler</TabsTrigger>
                      <TabsTrigger value="anonymized">Anonimleştirilmiş</TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>

                {/* Anonimleştirme Seçenekleri */}
                <div className="space-y-2">
                  <h3 className="text-sm font-medium">Anonimleştirilecek Bilgiler</h3>
                  <p className="text-xs text-muted-foreground mb-2">
                    İşleme dahil etmek istediğiniz anonimleştirme seçeneklerini işaretleyin. En az bir seçenek seçilmelidir.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="author_name"
                        checked={selectedOptions.author_name}
                        onChange={() => handleOptionChange('author_name')}
                        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <label htmlFor="author_name" className="text-sm">
                        Yazar Ad-Soyad
                      </label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="contact_info"
                        checked={selectedOptions.contact_info}
                        onChange={() => handleOptionChange('contact_info')}
                        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <label htmlFor="contact_info" className="text-sm">
                        Yazar İletişim Bilgileri
                      </label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="institution_info"
                        checked={selectedOptions.institution_info}
                        onChange={() => handleOptionChange('institution_info')}
                        className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      />
                      <label htmlFor="institution_info" className="text-sm">
                        Yazar Kurum Bilgileri
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          {loading ? (
            <div className="flex flex-col justify-center items-center py-20 bg-muted/20 rounded-lg border">
              <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
              <p className="text-muted-foreground">Makaleler yükleniyor...</p>
            </div>
          ) : filteredPapers.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center p-10">
                <div className="rounded-full bg-primary/10 p-4 mb-5">
                  <AlertTriangle className="h-8 w-8 text-primary" />
                </div>
                <h3 className="text-xl font-semibold mb-3">Makale Bulunamadı</h3>
                <p className="text-muted-foreground text-center max-w-md mb-5">
                  Aradığınız kriterlere uygun makale bulunamadı. Filtreleri temizlemeyi veya yeni makaleler yüklemeyi deneyebilirsiniz.
                </p>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setSearchTerm("")
                    if (activeTab !== "all") {
                      setActiveTab("all")
                    } else {
                      fetchPapers()
                    }
                  }}
                  className="gap-2"
                >
                  <FileText className="h-4 w-4" />
                  Tüm Makaleleri Göster
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader className="bg-muted/50">
                  <TableRow>
                    <TableHead className="font-semibold">Takip No</TableHead>
                    <TableHead className="font-semibold">Dosya Adı</TableHead>
                    <TableHead className="font-semibold">E-posta</TableHead>
                    <TableHead className="font-semibold whitespace-nowrap">Yükleme Tarihi</TableHead>
                    <TableHead className="font-semibold">Durum</TableHead>
                    <TableHead className="text-right font-semibold">İşlemler</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentItems.map((paper) => (
                    <TableRow key={paper.id} className="hover:bg-muted/30 transition-colors">
                      <TableCell className="font-medium w-[120px]">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="truncate block text-primary">
                              {paper.tracking_number}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-[300px] break-all text-xs">
                            <p>{paper.tracking_number}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TableCell>
                      <TableCell className="max-w-[180px]">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="truncate block">
                              {paper.original_filename}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-[350px] break-all text-xs">
                            <p>{paper.original_filename}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TableCell>
                      <TableCell className="max-w-[180px]">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="truncate block text-muted-foreground">
                              {paper.email}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-[350px] break-all text-xs">
                            <p>{paper.email}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">{formatDate(paper.upload_date)}</TableCell>
                      <TableCell>{getStatusBadge(paper.status)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="gap-1 h-8 px-3"
                            onClick={() => activeTab === "pending" 
                              ? handleDownload(paper.tracking_number)
                              : (paper.status === ArticleStatus.ANONYMIZED 
                                ? handleAnonymizedDownload(paper.tracking_number) 
                                : handleDownload(paper.tracking_number))
                            }
                          >
                            <Download className="h-4 w-4" />
                            <span>İndir</span>
                          </Button>
                          
                          {paper.status === ArticleStatus.ANONYMIZED && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="gap-1 h-8 px-3"
                              onClick={() => viewAnonymizationStats(paper.tracking_number)}
                            >
                              <BarChart2 className="h-4 w-4" />
                              <span>İstatistikler</span>
                            </Button>
                          )}
                          
                          <Button 
                            variant={paper.status === ArticleStatus.ANONYMIZED ? "ghost" : "default"}
                            size="sm" 
                            className="gap-1 h-8 px-3"
                            onClick={() => showAnonymizeConfirm(paper.tracking_number, paper.original_filename)}
                            disabled={anonymizingPaper === paper.tracking_number || paper.status === ArticleStatus.ANONYMIZED}
                          >
                            {anonymizingPaper === paper.tracking_number ? (
                              <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                <span>İşleniyor...</span>
                              </>
                            ) : paper.status === ArticleStatus.ANONYMIZED ? (
                              <>
                                <Check className="h-4 w-4" />
                                <span>Anonimleştirildi</span>
                              </>
                            ) : (
                              <>
                                <FileText className="h-4 w-4" />
                                <span>Anonimleştir</span>
                              </>
                            )}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              
              {/* Sayfalama */}
              {filteredPapers.length > itemsPerPage && (
                <div className="flex flex-col sm:flex-row items-center justify-between px-4 py-3 border-t bg-muted/20 gap-4">
                  <div className="text-sm text-muted-foreground order-2 sm:order-1">
                    Toplam <span className="font-medium">{filteredPapers.length}</span> makaleden{" "}
                    <span className="font-medium">{indexOfFirstItem + 1}</span>-
                    <span className="font-medium">
                      {indexOfLastItem > filteredPapers.length ? filteredPapers.length : indexOfLastItem}
                    </span>{" "}
                    arası gösteriliyor
                  </div>
                  
                  <div className="flex gap-1 order-1 sm:order-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={prevPage}
                      disabled={currentPage === 1}
                      className="h-8 w-8 p-0"
                      aria-label="Önceki sayfa"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    
                    {Array.from({ length: totalPages }, (_, i) => (
                      <Button
                        key={i + 1}
                        variant={currentPage === i + 1 ? "default" : "outline"}
                        size="sm"
                        onClick={() => paginate(i + 1)}
                        className={`h-8 w-8 p-0 ${
                          // 5'ten fazla sayfa varsa, bazı sayfa numaralarını gösterme
                          totalPages > 5 &&
                          i + 1 !== 1 &&
                          i + 1 !== totalPages &&
                          (i + 1 < currentPage - 1 || i + 1 > currentPage + 1) &&
                          i + 1 !== currentPage
                            ? "hidden"
                            : ""
                        }`}
                        aria-label={`Sayfa ${i + 1}`}
                        aria-current={currentPage === i + 1 ? "page" : undefined}
                      >
                        {i + 1}
                      </Button>
                    ))}
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={nextPage}
                      disabled={currentPage === totalPages}
                      className="h-8 w-8 p-0"
                      aria-label="Sonraki sayfa"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Anonimleştirme Onay Diyaloğu */}
          <ConfirmDialog
            open={confirmOpen}
            onOpenChange={setConfirmOpen}
            onConfirm={anonymizePaper}
            title="Makaleyi Anonimleştir"
            description={`
              <p>"<strong>${selectedFileName}</strong>" adlı makaleyi anonimleştirmek istediğinize emin misiniz?</p>
              <p class="mt-2">Bu işlem, makaleden yazar bilgilerini kaldıracak ve hakeme gönderilmeye hazır hale getirecektir.</p>
              <div class="mt-4 p-3 bg-muted/30 rounded-md">
                <p class="font-medium mb-2">Anonimleştirilecek Bilgiler:</p>
                <ul class="list-disc pl-5 space-y-1 text-sm">
                  ${selectedOptions.author_name ? '<li>Yazar Ad-Soyad</li>' : ''}
                  ${selectedOptions.contact_info ? '<li>Yazar İletişim Bilgileri</li>' : ''}
                  ${selectedOptions.institution_info ? '<li>Yazar Kurum Bilgileri</li>' : ''}
                </ul>
              </div>
            `}
            confirmText="Anonimleştir"
            cancelText="İptal"
          />
          
          {/* Anonimleştirme İstatistikleri Modalı */}
          <div className={`fixed inset-0 bg-black/50 flex items-center justify-center z-50 ${statsOpen ? 'block' : 'hidden'}`}>
            <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto">
              <div className="p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold">Anonimleştirme İstatistikleri</h2>
                  <button 
                    onClick={() => setStatsOpen(false)} 
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                
                {statsLoading ? (
                  <div className="flex flex-col items-center justify-center py-12">
                    <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
                    <p className="text-muted-foreground">İstatistikler yükleniyor...</p>
                  </div>
                ) : statsData ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                      <div className="border rounded-lg p-4">
                        <h3 className="text-sm font-medium mb-2 text-muted-foreground">Makale Bilgileri</h3>
                        <p className="text-sm mb-1">
                          <span className="font-medium">Dosya:</span> {statsData.paper.original_filename}
                        </p>
                        <p className="text-sm mb-1">
                          <span className="font-medium">Takip No:</span> {statsData.paper.tracking_number}
                        </p>
                        <p className="text-sm">
                          <span className="font-medium">Yükleme Tarihi:</span> {formatDate(statsData.paper.upload_date)}
                        </p>
                      </div>
                      <div className="border rounded-lg p-4">
                        <h3 className="text-sm font-medium mb-2 text-muted-foreground">Anonimleştirme Bilgileri</h3>
                        <p className="text-sm mb-1">
                          <span className="font-medium">İşlem Tarihi:</span> {formatDate(statsData.anonymization_stats.timestamp || '')}
                        </p>
                        <p className="text-sm mb-1">
                          <span className="font-medium">İndirme Sayısı:</span> {statsData.anonymized_file.download_count}
                        </p>
                        <div className="flex mt-2">
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="gap-1 text-xs h-7"
                            onClick={() => handleAnonymizedDownload(statsData.paper.tracking_number)}
                          >
                            <Download className="h-3 w-3" />
                            <span>Anonimleştirilmiş Dosyayı İndir</span>
                          </Button>
                        </div>
                      </div>
                    </div>
                    
                    <div className="border rounded-lg p-4">
                      <h3 className="text-sm font-medium mb-4 text-muted-foreground">Anonimleştirme Sonuçları</h3>
                      
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 text-center">
                          <p className="text-lg font-bold text-blue-600 mb-1">
                            {statsData.anonymization_stats.entities_found?.author_name_count || 0}
                          </p>
                          <p className="text-xs text-blue-600">Yazar Adı Bulundu</p>
                        </div>
                        <div className="bg-green-50 border border-green-100 rounded-lg p-4 text-center">
                          <p className="text-lg font-bold text-green-600 mb-1">
                            {statsData.anonymization_stats.entities_found?.contact_info_count || 0}
                          </p>
                          <p className="text-xs text-green-600">İletişim Bilgisi Bulundu</p>
                        </div>
                        <div className="bg-purple-50 border border-purple-100 rounded-lg p-4 text-center">
                          <p className="text-lg font-bold text-purple-600 mb-1">
                            {statsData.anonymization_stats.entities_found?.institution_info_count || 0}
                          </p>
                          <p className="text-xs text-purple-600">Kurum Bilgisi Bulundu</p>
                        </div>
                      </div>
                      
                      <div className="mt-6">
                        <h4 className="text-sm font-medium mb-2">Kullanılan Anonimleştirme Seçenekleri</h4>
                        <div className="flex flex-wrap gap-2">
                          {statsData.anonymization_stats.options?.map((option) => (
                            <span 
                              key={option} 
                              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground"
                            >
                              {option === 'author_name' && 'Yazar Adı'}
                              {option === 'contact_info' && 'İletişim Bilgisi'}
                              {option === 'institution_info' && 'Kurum Bilgisi'}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex justify-end gap-2 mt-4">
                      <Button variant="outline" onClick={() => setStatsOpen(false)}>
                        Kapat
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12">
                    <AlertTriangle className="h-10 w-10 text-yellow-500 mb-4" />
                    <p className="text-muted-foreground text-center">
                      İstatistik bilgileri bulunamadı. 
                      Bu makale henüz anonimleştirilmemiş olabilir.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </TooltipProvider>
    </div>
  )
} 