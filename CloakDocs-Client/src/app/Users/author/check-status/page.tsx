"use client"

import type React from "react"
import { useState, useEffect } from "react"
import Link from "next/link"
import { PAPER_ENDPOINTS, MESSAGE_ENDPOINTS, STATUS_ENDPOINTS, AUTHOR_ENDPOINTS } from "@/app/lib/apiConfig"
import MessageChat from "@/app/components/ui/MessageChat"
import { Button } from "@/app/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Search, FileText, Calendar, AlertCircle, RefreshCw, History, Download } from "lucide-react"
import { StatusBadge, ArticleStatus } from "@/app/lib/articleStatus"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"

interface PaperStatus {
  tracking_number: string
  email: string
  original_filename: string
  status: string
  last_updated: string
  submission_date: string
  comments?: string
  upload_date?: string
  id?: number
  upload_date_formatted?: string
  author_can_download?: boolean
}

export default function CheckStatusPage() {
  const [trackingNumber, setTrackingNumber] = useState("")
  const [email, setEmail] = useState("")
  const [paperData, setPaperData] = useState<PaperStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Mesaj gönderme durumu
  const [messageSuccess, setMessageSuccess] = useState(false)
  const [messageError, setMessageError] = useState<string | null>(null)
  const [isMessageSending, setIsMessageSending] = useState(false)
  
  // Revizyon geçmişi durumu
  const [revisions, setRevisions] = useState<PaperStatus[]>([])
  const [loadingRevisions, setLoadingRevisions] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!trackingNumber || !email) {
      setError("Lütfen takip numarası ve e-posta adresinizi girin.")
      return
    }

    setLoading(true)
    setError(null)
    setPaperData(null)

    try {
      const response = await fetch(
        `${PAPER_ENDPOINTS.STATUS}?trackingNumber=${encodeURIComponent(trackingNumber)}&email=${encodeURIComponent(email)}`,
      )
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Makale bulunamadı.")
      }

      setPaperData(data.paper)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Bir hata oluştu. Lütfen tekrar deneyin."
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  // Mesaj gönderme işlemi
  const handleMessageSubmit = async (data: {
    trackingNumber: string
    subject: string
    message: string
  }) => {
    setIsMessageSending(true)
    setMessageSuccess(false)
    setMessageError(null)

    try {
      // Takip numarasını doğrudan paperData'dan alıyoruz
      if (!paperData) {
        throw new Error("Makale bilgisi bulunamadı")
      }

      // Backend'in beklediği formatta veri hazırlama
      const messageData = {
        trackingNumber: paperData.tracking_number,
        subject: data.subject,
        message: data.message,
      }

      // API isteği - site içi mesajlaşma için yeni ENDPOINT kullanımı
      const response = await fetch(MESSAGE_ENDPOINTS.SEND, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(messageData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        const errorMessage = errorData.detail || errorData.error || "Mesaj gönderilirken bir hata oluştu"
        throw new Error(errorMessage)
      }

      setMessageSuccess(true)
    } catch (error) {
      setMessageError(error instanceof Error ? error.message : "Mesaj gönderilirken bir hata oluştu")
    } finally {
      setIsMessageSending(false)
    }
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return "Tarih belirlenmedi"

    try {
      // Tarihin çeşitli formatlarını destekle
      let date;
      
      // Eğer upload_date_formatted zaten varsa, onu doğrudan kullan
      if (dateString.includes('.')) {
        return dateString; // Zaten formatlanmış tarih
      }
      
      // ISO formatı (YYYY-MM-DD HH:MM:SS)
      if (dateString.includes('-') && dateString.includes(':')) {
        date = new Date(dateString);
      } 
      // Timestamp formatı
      else if (!isNaN(Number(dateString))) {
        date = new Date(Number(dateString));
      }
      // Diğer durumlar
      else {
        date = new Date(dateString);
      }
      
      if (isNaN(date.getTime())) {
        console.error('Geçersiz tarih:', dateString);
        return "Geçersiz tarih";
      }

      return date.toLocaleDateString("tr-TR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    } catch (error) {
      console.error("Tarih formatı hatası:", error, "Gelen tarih:", dateString);
      return "Tarih formatı hatası";
    }
  }

  // Revizyon listesini getir
  const fetchRevisions = async (trackingNumber: string) => {
    if (!trackingNumber) return;
    
    setLoadingRevisions(true);
    
    try {
      console.log(`Revizyon getiriliyor: ${trackingNumber}`);
      const response = await fetch(STATUS_ENDPOINTS.REVISIONS(trackingNumber));
      const data = await response.json();
      
      if (!response.ok) {
        console.error(`Revizyon listesi alınamadı. Durum kodu: ${response.status}`, data);
        throw new Error(data.error || "Revizyon listesi alınamadı");
      }
      
      console.log("Alınan revizyonlar:", data.revisions || []);
      setRevisions(data.revisions || []);
    } catch (error) {
      console.error("Revizyon listesi getirme hatası:", error);
      setRevisions([]);
    } finally {
      setLoadingRevisions(false);
    }
  }

  // Makale bilgileri başarıyla alındığında revizyonları da getir
  useEffect(() => {
    if (paperData) {
      fetchRevisions(paperData.tracking_number);
    }
  }, [paperData]);
  
  // Final PDF'i indirme fonksiyonu (yeni eklenen)
  const downloadFinalPdf = (trackingNumber: string) => {
    if (!trackingNumber) return;
    
    // API endpoint'i kullanarak final PDF'i indir (editör endpointi üzerinden)
    window.open(AUTHOR_ENDPOINTS.DOWNLOAD_FINAL_PDF(trackingNumber), '_blank');
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <h1 className="text-3xl font-bold text-primary mb-2">Makale Durumu Sorgula</h1>
        <p className="text-muted-foreground mb-8">
          Makalenizin güncel durumunu kontrol edin ve editörlerle iletişime geçin.
        </p>

        <Card className="mb-8 border-border shadow-sm bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl text-primary">Makale Bilgilerinizi Girin</CardTitle>
            <CardDescription>
              Takip numarası ve e-posta adresiniz ile makalenizin durumunu sorgulayabilirsiniz.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="trackingNumber" className="block text-sm font-medium mb-1 text-foreground">
                    Takip Numarası <span className="text-status-error">*</span>
                  </label>
                  <input
                    type="text"
                    id="trackingNumber"
                    className="w-full p-2 border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent bg-background"
                    placeholder="TR-2023-00001"
                    required
                    value={trackingNumber}
                    onChange={(e) => setTrackingNumber(e.target.value)}
                  />
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium mb-1 text-foreground">
                    E-posta Adresi <span className="text-status-error">*</span>
                  </label>
                  <input
                    type="email"
                    id="email"
                    className="w-full p-2 border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent bg-background"
                    placeholder="ornek@email.com"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <Button type="submit" className="bg-accent hover:bg-accent/90 text-white" disabled={loading}>
                  {loading ? (
                    <>
                      <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"></span>
                      Sorgulanıyor...
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      Sorgula
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {error && (
          <div className="bg-status-error/10 border border-status-error/30 p-4 mb-6 rounded-md text-status-error">
            <p className="flex items-center">
              <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
              <span>{error}</span>
            </p>
          </div>
        )}

        {/* Makale bilgileri */}
        {paperData && (
          <div className="space-y-8">
            <Tabs defaultValue="details" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="details">Makale Bilgileri</TabsTrigger>
                <TabsTrigger value="revisions" disabled={revisions.length <= 1}>
                  <History className="w-4 h-4 mr-2" />
                  Revizyon Geçmişi
                  {revisions.length > 1 && <span className="ml-2 inline-flex items-center justify-center w-5 h-5 text-xs font-bold rounded-full bg-premium/20 text-premium">{revisions.length - 1}</span>}
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="details">
                <Card className="border-border shadow-sm overflow-hidden bg-card">
                  <div className="border-b border-border bg-background-secondary p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-xl font-bold text-primary">Makale Bilgileri</h2>
                        {paperData.last_updated && (
                          <p className="text-sm text-muted-foreground">Son güncelleme: {formatDate(paperData.last_updated)}</p>
                        )}
                      </div>
                      <div>
                        {paperData.status && (
                          <StatusBadge status={paperData.status} />
                        )}
                      </div>
                    </div>
                  </div>

                  <CardContent className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-muted-foreground">Takip Numarası</p>
                        <p className="text-lg font-medium flex items-center">
                          <FileText className="h-4 w-4 mr-2 text-accent" />
                          {paperData.tracking_number}
                        </p>
                      </div>

                      <div className="space-y-1">
                        <p className="text-sm font-medium text-muted-foreground">Dosya Adı</p>
                        <p className="text-lg font-medium truncate">{paperData.original_filename}</p>
                      </div>

                      <div className="space-y-1">
                        <p className="text-sm font-medium text-muted-foreground">Gönderim Tarihi</p>
                        <p className="flex items-center">
                          <Calendar className="h-4 w-4 mr-2 text-accent" />
                          {formatDate(paperData.upload_date || paperData.submission_date)}
                        </p>
                      </div>

                      <div className="space-y-1">
                        <p className="text-sm font-medium text-muted-foreground">E-posta</p>
                        <p className="truncate">{paperData.email}</p>
                      </div>
                    </div>

                    {paperData.comments && (
                      <div className="mt-6 pt-6 border-t border-border">
                        <p className="text-sm font-medium text-muted-foreground mb-2">Editör Notu</p>
                        <div className="p-4 bg-background-secondary rounded-md border border-border">
                          <p className="text-foreground whitespace-pre-wrap">{paperData.comments}</p>
                        </div>
                      </div>
                    )}
                    
                    {(paperData.status === "forwarded" || paperData.status === "reviewed") && (
                      <div className="mt-6 pt-6 border-t border-border">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-foreground">Hakem Değerlendirme Raporu</p>
                          <div className="flex gap-2">
                            <Button
                              variant="default"
                              size="sm"
                              className="flex items-center gap-2"
                              onClick={() => downloadFinalPdf(paperData.tracking_number)}
                            >
                              <Download className="w-4 h-4" />
                              Final PDF İndir
                            </Button>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground mt-2">
                          Hakem tarafından değerlendirilen makalenizin orijinal makale ile değerlendirme raporu içeren final PDF dosyasını indirebilirsiniz.
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
            
                {/* Makale Durumu Kartı */}
                {paperData.status === ArticleStatus.REVISION_REQUIRED && (
                  <Card className="mt-4 border-premium/30 shadow-sm overflow-hidden bg-premium/5">
                    <CardContent className="p-6">
                      <div className="flex flex-col md:flex-row md:items-center gap-4 justify-between">
                        <div>
                          <h3 className="text-xl font-bold mb-2 text-premium flex items-center">
                            <RefreshCw className="w-5 h-5 mr-2" />
                            Makale Revizyonu Gerekli
                          </h3>
                          <p className="text-muted-foreground mb-4">
                            Değerlendirme sonucunda makalenizde düzeltmeler yapılması gerektiği belirtilmiştir. 
                            Lütfen editör notlarını inceleyip gerekli düzenlemeleri yaptıktan sonra makalenizi tekrar yükleyiniz.
                          </p>
                        </div>
                        <div className="shrink-0">
                          <Link href={{
                            pathname: "/Users/author/submit-paper",
                            query: { 
                              revision: "true", 
                              trackingNumber: paperData?.tracking_number,
                              email: paperData?.email
                            }
                          }} className="button-premium flex items-center gap-2">
                            <RefreshCw className="w-4 h-4" />
                            <span>Revize Makale Yükle</span>
                          </Link>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
              
              <TabsContent value="revisions">
                <Card className="border-border shadow-sm overflow-hidden bg-card">
                  <div className="border-b border-border bg-background-secondary p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-xl font-bold text-primary">Revizyon Geçmişi</h2>
                        <p className="text-sm text-muted-foreground">
                          Makalenin tüm sürümleri ve revizyonları
                        </p>
                      </div>
                    </div>
                  </div>

                  <CardContent className="p-6">
                    {loadingRevisions ? (
                      <div className="flex items-center justify-center py-10">
                        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
                        <span className="ml-2">Revizyon geçmişi yükleniyor...</span>
                      </div>
                    ) : revisions.length <= 1 ? (
                      <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
                        <History className="h-12 w-12 mb-4 opacity-30" />
                        <p>Bu makale için henüz revizyon bulunmuyor.</p>
                      </div>
                    ) : (
                      <Accordion type="single" collapsible className="w-full">
                        {revisions.map((revision, index) => (
                          <AccordionItem key={revision.id || index} value={`rev-${revision.id || index}`} className="border-b border-border">
                            <AccordionTrigger className="hover:no-underline">
                              <div className="flex items-center justify-between w-full pr-4">
                                <div className="flex items-center">
                                  <span className={`w-6 h-6 rounded-full flex items-center justify-center mr-3 text-xs font-medium ${index === 0 ? 'bg-primary/10 text-primary' : 'bg-premium/10 text-premium'}`}>
                                    {index === 0 ? 'O' : `R${index}`}
                                  </span>
                                  <span className="font-medium">
                                    {index === 0 ? 'Orijinal Makale' : `Revizyon ${index}`}
                                  </span>
                                </div>
                                <div className="flex items-center gap-4">
                                  <span className="text-xs text-muted-foreground">
                                    {revision.upload_date_formatted || formatDate(revision.upload_date || revision.submission_date)}
                                  </span>
                                  <StatusBadge status={revision.status} />
                                </div>
                              </div>
                            </AccordionTrigger>
                            <AccordionContent className="px-4 pt-2 pb-4">
                              <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <div className="space-y-1">
                                    <p className="text-sm font-medium text-muted-foreground">Takip Numarası</p>
                                    <p className="font-medium">{revision.tracking_number}</p>
                                  </div>
                                  <div className="space-y-1">
                                    <p className="text-sm font-medium text-muted-foreground">Dosya Adı</p>
                                    <p className="font-medium truncate">{revision.original_filename}</p>
                                  </div>
                                </div>
                                
                                {revision.comments && (
                                  <div className="pt-2">
                                    <p className="text-sm font-medium text-muted-foreground mb-1">Editör Notu</p>
                                    <div className="p-3 bg-background-secondary rounded-md border border-border text-sm">
                                      <p className="text-foreground whitespace-pre-wrap">{revision.comments}</p>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        ))}
                      </Accordion>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>

            <Card className="border-border shadow-sm bg-card">
              <CardHeader className="pb-2">
                <CardTitle className="text-xl text-accent">Editör İle Yazışma</CardTitle>
                <CardDescription>
                  Makaleniz hakkında sorularınız veya açıklamalarınız için editörle iletişime geçebilirsiniz.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <MessageChat
                  paperData={{
                    tracking_number: paperData.tracking_number,
                    original_filename: paperData.original_filename,
                    email: paperData.email,
                  }}
                  onSubmit={handleMessageSubmit}
                  messageSuccess={messageSuccess}
                  messageError={messageError}
                  isMessageSending={isMessageSending}
                  size="full"
                  threadEndpoint={MESSAGE_ENDPOINTS.GET_THREAD(paperData.tracking_number)}
                />
              </CardContent>
            </Card>
          </div>
        )}

        <div className="mt-8 text-center">
          <Link href="/" className="text-accent hover:text-accent/80 hover:underline inline-flex items-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Ana Sayfaya Dön
          </Link>
        </div>
      </div>
    </div>
  )
}

