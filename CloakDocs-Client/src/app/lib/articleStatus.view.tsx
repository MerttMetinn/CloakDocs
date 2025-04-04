import { CheckCircle, Clock, Edit, FileText, Search, Send, X, AlertCircle, RefreshCw } from "lucide-react"
import React from "react"
import { ArticleStatus, StatusConfig } from "./articleStatus.config"

// Makale durumlarını görsel stillerle eşleştiren fonksiyon
export function getStatusConfig(status: string): StatusConfig {
  // Durumu normalize et (küçük harf, boşluk ve alt çizgileri standardize et)
  const normalizedStatus = (status || "").toLowerCase().trim()
  
  // Durum mapping - her durumun görsel temsilini tanımlar
  const statusMap: Record<string, StatusConfig> = {
    // Ana makale durumları
    [ArticleStatus.DRAFT]: {
      color: "text-gray-600",
      bgColor: "bg-gray-100",
      borderColor: "border-gray-300",
      icon: <FileText className="h-5 w-5" />,
      text: "Taslak",
      description: "Makale henüz tamamlanmamış, düzenleme aşamasında"
    },
    [ArticleStatus.PENDING]: {
      color: "text-status-warning",
      bgColor: "bg-status-warning/10",
      borderColor: "border-status-warning/30",
      icon: <Clock className="h-5 w-5" />,
      text: "Beklemede",
      description: "Makale gönderildi, değerlendirme süreci başlamadı"
    },
    [ArticleStatus.IN_REVIEW]: {
      color: "text-status-info",
      bgColor: "bg-status-info/10",
      borderColor: "border-status-info/30",
      icon: <Search className="h-5 w-5" />,
      text: "İncelemede",
      description: "Makale hakem değerlendirme sürecinde"
    },
    [ArticleStatus.REVIEWED]: {
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      borderColor: "border-blue-200",
      icon: <CheckCircle className="h-5 w-5" />,
      text: "Değerlendirildi",
      description: "Hakem değerlendirmesi tamamlandı, editör incelemesi bekliyor"
    },
    [ArticleStatus.REVISION_REQUIRED]: {
      color: "text-premium",
      bgColor: "bg-premium/10",
      borderColor: "border-premium/30",
      icon: <RefreshCw className="h-5 w-5" />,
      text: "Revizyon Gerekli",
      description: "Makalede düzeltmeler yapılması gerekiyor"
    },
    [ArticleStatus.REVISED]: {
      color: "text-purple-600",
      bgColor: "bg-purple-50",
      borderColor: "border-purple-200",
      icon: <Edit className="h-5 w-5" />,
      text: "Revize Edildi",
      description: "Revizyon tamamlandı, yeniden değerlendirme bekleniyor"
    },
    [ArticleStatus.FORWARDED]: {
      color: "text-teal-600",
      bgColor: "bg-teal-50",
      borderColor: "border-teal-200",
      icon: <Send className="h-5 w-5" />,
      text: "İletildi",
      description: "Değerlendirme sonuçları yazara iletildi"
    },
    [ArticleStatus.ACCEPTED]: {
      color: "text-status-success",
      bgColor: "bg-status-success/10",
      borderColor: "border-status-success/30",
      icon: <CheckCircle className="h-5 w-5" />,
      text: "Kabul Edildi",
      description: "Makale kabul edildi, yayın sürecinde"
    },
    [ArticleStatus.REJECTED]: {
      color: "text-status-error",
      bgColor: "bg-status-error/10",
      borderColor: "border-status-error/30",
      icon: <X className="h-5 w-5" />,
      text: "Reddedildi",
      description: "Makale reddedildi"
    },
    [ArticleStatus.PUBLISHED]: {
      color: "text-green-700",
      bgColor: "bg-green-50",
      borderColor: "border-green-300",
      icon: <CheckCircle className="h-5 w-5" />,
      text: "Yayınlandı",
      description: "Makale dergide yayınlandı"
    },
    
    // Alt durumlar ve özel durumlar
    [ArticleStatus.ASSIGNED]: {
      color: "text-amber-600",
      bgColor: "bg-amber-50",
      borderColor: "border-amber-200",
      icon: <Send className="h-5 w-5" />,
      text: "Hakem Atandı",
      description: "Makaleye hakem atandı, inceleme bekleniyor"
    },
    [ArticleStatus.ANONYMIZED]: {
      color: "text-sky-600",
      bgColor: "bg-sky-50",
      borderColor: "border-sky-200",
      icon: <FileText className="h-5 w-5" />,
      text: "Anonimleştirildi",
      description: "Makale anonimleştirildi, hakeme atanmaya hazır"
    },
    [ArticleStatus.UNDER_EDITOR_REVIEW]: {
      color: "text-indigo-600",
      bgColor: "bg-indigo-50",
      borderColor: "border-indigo-200",
      icon: <Search className="h-5 w-5" />,
      text: "Editör İncelemesinde",
      description: "Makale editör tarafından inceleniyor"
    },
    [ArticleStatus.WAITING_AUTHOR_RESPONSE]: {
      color: "text-orange-600",
      bgColor: "bg-orange-50",
      borderColor: "border-orange-200",
      icon: <Clock className="h-5 w-5" />,
      text: "Yazar Yanıtı Bekleniyor",
      description: "Yazardan yanıt bekleyen işlem var"
    },
    [ArticleStatus.WITHDRAWN]: {
      color: "text-gray-600",
      bgColor: "bg-gray-100",
      borderColor: "border-gray-300",
      icon: <X className="h-5 w-5" />,
      text: "Geri Çekildi",
      description: "Makale yazar tarafından geri çekildi"
    },
    
    // Belirsiz durum
    [ArticleStatus.UNDEFINED]: {
      color: "text-gray-700",
      bgColor: "bg-gray-100",
      borderColor: "border-gray-300",
      icon: <AlertCircle className="h-5 w-5" />,
      text: "Belirsiz",
      description: "Makale durumu belirsiz"
    }
  }
  
  // Eğer durum yukarıdaki listeye dahil değilse, varsayılan olarak belirsiz durumu döndür
  return statusMap[normalizedStatus] || statusMap[ArticleStatus.UNDEFINED]
}

// Makale durumunu görsel bileşen olarak döndüren yardımcı fonksiyon
export function StatusBadge({ status }: { status: string }) {
  const statusConfig = getStatusConfig(status)
  
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-md ${statusConfig.bgColor} ${statusConfig.color} border ${statusConfig.borderColor}`}>
      {statusConfig.icon}
      <span className="font-medium">{statusConfig.text}</span>
    </div>
  )
}

// articleStatus.ts dosyasındaki fonksiyonları ve tipleri dışa aktar
export { ArticleStatus, type StatusConfig } from "./articleStatus.config"
export { getNextPossibleStatuses } from "./articleStatus.config" 