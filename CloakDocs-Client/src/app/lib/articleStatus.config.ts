import type { ReactNode } from "react"

// Tüm sistem genelinde kullanılacak makale durumları enum
export enum ArticleStatus {
  // Ana makale durumları
  DRAFT = "draft",
  PENDING = "pending",
  IN_REVIEW = "in_review",
  REVIEWED = "reviewed",
  REVISION_REQUIRED = "revision_required",
  REVISED = "revised",
  FORWARDED = "forwarded",
  ACCEPTED = "accepted",
  REJECTED = "rejected",
  PUBLISHED = "published",
  
  // Alt durumlar veya özel durumlar 
  ASSIGNED = "assigned", // Hakem atanmış, inceleme sürecinde
  ANONYMIZED = "anonymized", // Makale anonimleştirildi, hakeme atanmaya hazır
  UNDER_EDITOR_REVIEW = "under_editor_review", // Editör kontrolünde
  WAITING_AUTHOR_RESPONSE = "waiting_author_response", // Yazar yanıtı bekliyor
  WITHDRAWN = "withdrawn", // Yazar tarafından geri çekilmiş
  
  // Belirsiz durumlar
  UNDEFINED = "undefined"
}

// Statüye göre renk, ikon ve metin bilgilerini içeren yapı
export interface StatusConfig {
  color: string
  bgColor: string
  borderColor: string
  icon: ReactNode
  text: string
  description: string
}

// Süreç akışı için bir sonraki olası durumları döndüren fonksiyon
export function getNextPossibleStatuses(currentStatus: string): ArticleStatus[] {
  const status = currentStatus.toLowerCase() as ArticleStatus
  
  switch(status) {
    case ArticleStatus.DRAFT:
      return [ArticleStatus.PENDING]
      
    case ArticleStatus.PENDING:
      return [ArticleStatus.IN_REVIEW, ArticleStatus.REJECTED, ArticleStatus.UNDER_EDITOR_REVIEW]
      
    case ArticleStatus.IN_REVIEW:
      return [ArticleStatus.REVIEWED]
      
    case ArticleStatus.REVIEWED:
      return [ArticleStatus.FORWARDED, ArticleStatus.REVISION_REQUIRED, ArticleStatus.ACCEPTED, ArticleStatus.REJECTED]
      
    case ArticleStatus.REVISION_REQUIRED:
      return [ArticleStatus.REVISED, ArticleStatus.WITHDRAWN]
      
    case ArticleStatus.REVISED:
      return [ArticleStatus.IN_REVIEW]
      
    case ArticleStatus.FORWARDED:
      return [ArticleStatus.WAITING_AUTHOR_RESPONSE]
      
    case ArticleStatus.ACCEPTED:
      return [ArticleStatus.PUBLISHED]
      
    case ArticleStatus.REJECTED:
      return []
      
    case ArticleStatus.PUBLISHED:
      return []
      
    case ArticleStatus.ANONYMIZED:
      return [ArticleStatus.ASSIGNED]
      
    default:
      return []
  }
} 