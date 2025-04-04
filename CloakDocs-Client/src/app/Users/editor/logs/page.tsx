"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { ArrowLeft, FileText, Search, Loader2, AlertTriangle, Clock, Download, RefreshCw, User } from "lucide-react"
import { Button } from "@/app/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { API_BASE_URL, STATUS_ENDPOINTS } from "@/app/lib/apiConfig"
import ConfirmDialog from "@/app/components/ui/confirm-dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

interface PaperLog {
  id: number
  paper_id: number
  event_type: string
  event_description: string
  user_email: string | null
  created_at: string
  additional_data: Record<string, unknown>
}

interface Paper {
  id: number
  tracking_number: string
  status: string
  email: string
  original_filename?: string
}

interface PaperLogsResponse {
  success: boolean
  paper: Paper
  logs: PaperLog[]
  count: number
  error?: string
}

export default function LogsPage() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)
  const [paperLogs, setPaperLogs] = useState<PaperLog[]>([])
  const [loading, setLoading] = useState(false)
  const [logsLoading, setLogsLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [startDate, setStartDate] = useState<string>("")
  const [endDate, setEndDate] = useState<string>("")
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("all")
  
  // Doğrulama diyaloğu için state
  const [confirmOpen, setConfirmOpen] = useState(false)

  // Makaleleri yükle
  useEffect(() => {
    fetchPapers()
  }, [])

  const fetchPapers = async () => {
    setLoading(true)
    try {
      const response = await fetch(STATUS_ENDPOINTS.PAPERS)
      
      if (!response.ok) {
        throw new Error("Makaleler alınırken bir hata oluştu")
      }
      
      const data = await response.json()
      
      if (data.success) {
        setPapers(data.papers || [])
      } else {
        console.error("API Error:", data.error)
      }
    } catch (error) {
      console.error("Fetch Error:", error)
    } finally {
      setLoading(false)
    }
  }

  // Seçilen makalenin log kayıtlarını getir
  const fetchPaperLogs = async (trackingNumber: string) => {
    if (!trackingNumber) return
    
    setLogsLoading(true)
    try {
      let url = STATUS_ENDPOINTS.LOGS(trackingNumber)
      
      // Filtre parametreleri
      const params = new URLSearchParams()
      
      if (eventTypeFilter && eventTypeFilter !== "all") {
        params.append('event_type', eventTypeFilter)
      }
      
      if (params.toString()) {
        url += `?${params.toString()}`
      }
      
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error("Log kayıtları alınırken bir hata oluştu")
      }
      
      const data: PaperLogsResponse = await response.json()
      
      if (data.success) {
        setPaperLogs(data.logs || [])
        setSelectedPaper(data.paper)
      } else {
        console.error("API Error:", data.error)
        setPaperLogs([])
      }
    } catch (error) {
      console.error("Fetch Error:", error)
      setPaperLogs([])
    } finally {
      setLogsLoading(false)
    }
  }

  // Log raporu indirme
  const downloadLogReport = () => {
    if (!selectedPaper) return
    
    const downloadUrl = `${API_BASE_URL}/editor/download-logs-report/${selectedPaper.tracking_number}`
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
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      })
    } catch {
      return dateString
    }
  }
  
  // İşlem tipi etiketi oluştur
  const getEventTypeBadge = (eventType: string) => {
    const eventTypeMap: Record<string, { class: string, icon: React.ReactNode }> = {
      'UPLOADED': { 
        class: "bg-blue-100 text-blue-800 border-blue-200", 
        icon: <FileText className="h-3 w-3 mr-1" /> 
      },
      'DOWNLOADED': { 
        class: "bg-purple-100 text-purple-800 border-purple-200", 
        icon: <Download className="h-3 w-3 mr-1" /> 
      },
      'REVIEWED': { 
        class: "bg-green-100 text-green-800 border-green-200", 
        icon: <Clock className="h-3 w-3 mr-1" /> 
      },
      'ASSIGNED': { 
        class: "bg-yellow-100 text-yellow-800 border-yellow-200", 
        icon: <User className="h-3 w-3 mr-1" /> 
      },
      'ANONYMIZED': { 
        class: "bg-indigo-100 text-indigo-800 border-indigo-200", 
        icon: <User className="h-3 w-3 mr-1" /> 
      },
      'STATUS_CHANGED': { 
        class: "bg-pink-100 text-pink-800 border-pink-200", 
        icon: <RefreshCw className="h-3 w-3 mr-1" /> 
      }
    }
    
    const eventInfo = eventTypeMap[eventType] || { 
      class: "bg-gray-100 text-gray-800 border-gray-200", 
      icon: <FileText className="h-3 w-3 mr-1" /> 
    }
    
    return (
      <span className={`px-2.5 py-0.5 rounded text-xs font-medium border flex items-center ${eventInfo.class}`}>
        {eventInfo.icon}
        {eventType.replace('_', ' ')}
      </span>
    )
  }

  // E-posta adresini kısalt
  const shortenEmail = (email: string | null) => {
    if (!email) return "-";
    
    if (email.length <= 15) return email;
    
    const atIndex = email.indexOf('@');
    if (atIndex === -1) return email.substring(0, 12) + '...';
    
    const localPart = email.substring(0, atIndex);
    const domain = email.substring(atIndex);
    
    if (localPart.length <= 8) return email.substring(0, 15) + '...';
    
    return localPart.substring(0, 8) + '...' + domain;
  };

  // Arama filtresi
  const filteredPapers = papers.filter(paper => 
    paper.tracking_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    paper.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    paper.status?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    paper.original_filename?.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
  // Tarih aralığı filtresi uygulanabilir log listesi
  const filteredLogs = paperLogs.filter(log => {
    // Tarih filtreleri
    if (startDate || endDate) {
      const logDate = new Date(log.created_at)
      
      if (startDate) {
        const startDateTime = new Date(startDate)
        if (logDate < startDateTime) return false
      }
      
      if (endDate) {
        const endDateTime = new Date(endDate)
        endDateTime.setHours(23, 59, 59, 999) // Günün sonuna ayarla
        if (logDate > endDateTime) return false
      }
    }
    
    return true
  })
  
  // Olay türlerine göre gruplanmış log sayıları
  const eventTypeCounts = paperLogs.reduce((acc, log) => {
    const eventType = log.event_type
    acc[eventType] = (acc[eventType] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="min-h-screen p-4 md:p-6 bg-background">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-between mb-6 gap-4">
          <div className="flex items-center">
            <Link href="/Users/editor" className="mr-4">
              <Button variant="ghost" size="icon" className="h-9 w-9">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <h1 className="text-2xl font-bold text-primary">Makale Log Kayıtları</h1>
          </div>
          
          <div className="flex gap-2">
            {selectedPaper && (
              <Button 
                variant="outline" 
                onClick={() => setConfirmOpen(true)} 
                className="gap-2"
                disabled={paperLogs.length === 0}
              >
                <Download className="h-4 w-4" />
                Rapor İndir
              </Button>
            )}
            
            <Button onClick={fetchPapers} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Yenile
            </Button>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
          {/* Makale Listesi Paneli */}
          <Card className="lg:col-span-1 h-[calc(100vh-200px)] flex flex-col">
            <CardHeader className="pb-3 flex-shrink-0">
              <CardTitle>Makaleler</CardTitle>
              <CardDescription>
                Log kayıtlarını görüntülemek için bir makale seçin
              </CardDescription>
              <div className="relative mt-2">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder="Takip no, e-posta..."
                  className="pl-8"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </CardHeader>
            <CardContent className="flex-grow overflow-hidden p-0">
              {loading ? (
                <div className="flex justify-center items-center h-full">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : filteredPapers.length === 0 ? (
                <div className="flex items-center justify-center h-full p-4 text-center text-muted-foreground">
                  Makale bulunamadı
                </div>
              ) : (
                <div className="h-full overflow-auto border-t">
                  {filteredPapers.map((paper) => (
                    <div
                      key={paper.id}
                      onClick={() => fetchPaperLogs(paper.tracking_number)}
                      className={`px-4 py-3 border-b cursor-pointer hover:bg-muted/50 transition-colors ${
                        selectedPaper?.id === paper.id ? "bg-muted/70" : ""
                      }`}
                    >
                      <div className="font-medium text-sm truncate mb-1">{paper.tracking_number}</div>
                      <div className="flex justify-between items-center">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          paper.status === 'published' ? 'bg-green-100 text-green-800' :
                          paper.status === 'rejected' ? 'bg-red-100 text-red-800' :
                          paper.status === 'anonymized' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {paper.status}
                        </span>
                        <span className="text-xs text-muted-foreground truncate max-w-[120px]">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span>{shortenEmail(paper.email)}</span>
                            </TooltipTrigger>
                            <TooltipContent>
                              <span>{paper.email}</span>
                            </TooltipContent>
                          </Tooltip>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
          
          {/* Log Kayıtları Paneli */}
          <Card className="lg:col-span-3 h-[calc(100vh-200px)] flex flex-col">
            <CardHeader className="pb-3 flex-shrink-0">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle>
                    {selectedPaper 
                      ? `Log Kayıtları - ${selectedPaper.tracking_number}` 
                      : "Log Kayıtları"}
                  </CardTitle>
                  <CardDescription>
                    {selectedPaper 
                      ? `${selectedPaper.email} tarafından yüklenen makalenin işlem kayıtları` 
                      : "Görüntülemek için bir makale seçin"}
                  </CardDescription>
                </div>
                
                {selectedPaper && (
                  <div className="text-xs px-2.5 py-1 rounded-full bg-secondary text-secondary-foreground">
                    {paperLogs.length} log kaydı
                  </div>
                )}
              </div>
            </CardHeader>
            
            <CardContent className="flex-grow pt-0 overflow-hidden">
              {!selectedPaper ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <AlertTriangle className="h-8 w-8 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    Log kayıtlarını görüntülemek için soldaki listeden bir makale seçin
                  </p>
                </div>
              ) : logsLoading ? (
                <div className="flex justify-center items-center h-full">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : paperLogs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <AlertTriangle className="h-8 w-8 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    Bu makale için log kaydı bulunamadı
                  </p>
                </div>
              ) : (
                <div className="h-full flex flex-col">
                  <div className="flex flex-wrap gap-4 mb-4 pb-4 border-b">
                    <div className="flex-1 min-w-[200px]">
                      <div className="text-sm font-medium mb-1.5">İşlem Türü</div>
                      <Select 
                        value={eventTypeFilter} 
                        onValueChange={setEventTypeFilter}
                      >
                        <SelectTrigger className="h-9">
                          <SelectValue placeholder="Tüm kayıtlar" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Tüm kayıtlar</SelectItem>
                          {Object.keys(eventTypeCounts).map(type => (
                            <SelectItem key={type} value={type}>
                              {type.replace('_', ' ')} ({eventTypeCounts[type]})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="flex flex-1 min-w-[200px] gap-2">
                      <div className="flex-1">
                        <div className="text-sm font-medium mb-1.5">Başlangıç</div>
                        <Input
                          type="date"
                          className="h-9"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                        />
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-medium mb-1.5">Bitiş</div>
                        <Input
                          type="date"
                          className="h-9"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                
                  <Tabs defaultValue="logs" className="flex-grow flex flex-col">
                    <TabsList className="w-full justify-start mb-3">
                      <TabsTrigger value="logs" className="flex-1 max-w-[150px]">Log Listesi</TabsTrigger>
                      <TabsTrigger value="summary" className="flex-1 max-w-[150px]">Özet Bilgiler</TabsTrigger>
                    </TabsList>
                    
                    <div className="flex-grow overflow-hidden">
                      <TabsContent value="logs" className="h-full m-0 data-[state=active]:h-full">
                        <div className="h-full border rounded-md overflow-auto">
                          <Table>
                            <TableHeader className="sticky top-0 bg-background shadow-sm z-10">
                              <TableRow>
                                <TableHead className="w-[160px]">Tarih</TableHead>
                                <TableHead className="w-[140px]">İşlem</TableHead>
                                <TableHead className="w-[140px]">Kullanıcı</TableHead>
                                <TableHead>Açıklama</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {filteredLogs.length === 0 ? (
                                <TableRow>
                                  <TableCell colSpan={4} className="h-[200px] text-center text-muted-foreground">
                                    Filtre kriterlerine uygun log kaydı bulunamadı
                                  </TableCell>
                                </TableRow>
                              ) : (
                                filteredLogs.map((log) => (
                                  <TableRow key={log.id} className="group">
                                    <TableCell className="whitespace-nowrap font-mono text-xs">{formatDate(log.created_at)}</TableCell>
                                    <TableCell>{getEventTypeBadge(log.event_type)}</TableCell>
                                    <TableCell className="max-w-[140px]">
                                      {log.user_email ? (
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <span className="truncate block">{shortenEmail(log.user_email)}</span>
                                          </TooltipTrigger>
                                          <TooltipContent>
                                            <span>{log.user_email}</span>
                                          </TooltipContent>
                                        </Tooltip>
                                      ) : (
                                        "-"
                                      )}
                                    </TableCell>
                                    <TableCell className="max-w-[400px]">
                                      <div className="truncate group-hover:whitespace-normal">{log.event_description}</div>
                                    </TableCell>
                                  </TableRow>
                                ))
                              )}
                            </TableBody>
                          </Table>
                        </div>
                      </TabsContent>
                      
                      <TabsContent value="summary" className="h-full m-0 data-[state=active]:h-full">
                        <div className="h-full overflow-auto space-y-6 pr-2">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {Object.entries(eventTypeCounts).map(([type, count]) => (
                              <Card key={type} className="overflow-hidden">
                                <CardContent className="p-0">
                                  <div className="flex items-center p-4">
                                    <div className="mr-3">
                                      {getEventTypeBadge(type)}
                                    </div>
                                    <div className="ml-auto text-2xl font-bold">{count}</div>
                                  </div>
                                  <div className="bg-muted/50 h-1">
                                    <div 
                                      className="bg-primary h-full" 
                                      style={{ 
                                        width: `${(count / paperLogs.length) * 100}%` 
                                      }} 
                                    />
                                  </div>
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                          
                          {/* Zaman çizelgesi */}
                          <div>
                            <h3 className="font-medium mb-3 text-sm">Makale İşlem Zaman Çizelgesi</h3>
                            <div className="border rounded-md p-4">
                              <div className="border-l-2 border-primary/20 pl-4 space-y-5">
                                {paperLogs.slice(0, 7).map((log) => (
                                  <div key={log.id} className="relative">
                                    <div className="absolute -left-6 mt-1.5 h-3 w-3 rounded-full bg-primary"></div>
                                    <div className="flex justify-between mb-1">
                                      <div className="text-sm font-medium">{log.event_type.replace('_', ' ')}</div>
                                      <div className="text-xs text-muted-foreground">{formatDate(log.created_at)}</div>
                                    </div>
                                    <div className="text-sm">{log.event_description}</div>
                                    {log.user_email && (
                                      <div className="text-xs text-muted-foreground mt-1">
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <span>{shortenEmail(log.user_email)}</span>
                                          </TooltipTrigger>
                                          <TooltipContent>
                                            <span>{log.user_email}</span>
                                          </TooltipContent>
                                        </Tooltip>
                                      </div>
                                    )}
                                  </div>
                                ))}
                                
                                {paperLogs.length > 7 && (
                                  <div className="text-center text-sm text-muted-foreground pt-2">
                                    ... ve {paperLogs.length - 7} daha
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </TabsContent>
                    </div>
                  </Tabs>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        
        {/* Log Raporu İndirme Onay Diyaloğu */}
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          onConfirm={downloadLogReport}
          title="Log Raporu İndir"
          description={`
            <p>Makale log raporunu indirmek istediğinize emin misiniz?</p>
            <div class="mt-2 p-3 bg-gray-50 rounded border border-gray-200">
              <div><span class="font-medium">Makale:</span> ${selectedPaper?.tracking_number || ""}</div>
              <div><span class="font-medium">Kayıt Sayısı:</span> ${paperLogs.length} kayıt</div>
              ${startDate || endDate ? `<div><span class="font-medium">Tarih Aralığı:</span> ${startDate || "Başlangıç"} - ${endDate || "Bitiş"}</div>` : ''}
              ${eventTypeFilter !== "all" ? `<div><span class="font-medium">İşlem Türü:</span> ${eventTypeFilter}</div>` : `<div><span class="font-medium">İşlem Türü:</span> Tüm işlem türleri</div>`}
            </div>
            <p class="mt-2">Rapor Excel formatında indirilecektir.</p>
          `}
          confirmText="İndir"
          cancelText="İptal"
        />
      </div>
    </div>
  )
}