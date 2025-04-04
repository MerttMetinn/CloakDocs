/**
 * API yapılandırma dosyası
 * Bu dosya, frontend'den backend API'ye yapılan isteklerin yönetimini sağlar
 */

// API temel URL'si
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api';

// Makale endpointleri
export const PAPER_ENDPOINTS = {
  UPLOAD: `${API_BASE_URL}/paper/upload`,
  STATUS: `${API_BASE_URL}/paper/status`,
  DOWNLOAD: `${API_BASE_URL}/paper/download`
};

// Durum endpointleri
export const STATUS_ENDPOINTS = {
  PAPERS: `${API_BASE_URL}/status/papers`,
  UPDATE: `${API_BASE_URL}/status/update`,
  COUNTS: `${API_BASE_URL}/status/counts`,
  PAPER_DETAILS: (trackingNumber: string) => `${API_BASE_URL}/status/paper/${trackingNumber}`,
  REVISIONS: (trackingNumber: string) => `${API_BASE_URL}/status/revisions/${trackingNumber}`,
  LOGS: (trackingNumber: string) => `${API_BASE_URL}/status/logs/${trackingNumber}`,
};

// Anonimleştirme endpointleri
export const ANONYMIZE_ENDPOINTS = {
  PROCESS: (trackingNumber: string) => `${API_BASE_URL}/anonymize/process/${trackingNumber}`,
  STATS: (trackingNumber: string) => `${API_BASE_URL}/anonymize/stats/${trackingNumber}`,
  DOWNLOAD: (trackingNumber: string) => `${API_BASE_URL}/anonymize/download/${trackingNumber}`,
  FILES: (trackingNumber: string) => `${API_BASE_URL}/anonymize/files/${trackingNumber}`,
  INFO: (trackingNumber: string) => `${API_BASE_URL}/anonymize/info/${trackingNumber}`,
  MERGE_REVIEW: (trackingNumber: string) => `${API_BASE_URL}/anonymize/merge-review/${trackingNumber}`,
  DOWNLOAD_REVIEWED: (trackingNumber: string) => `${API_BASE_URL}/anonymize/reviewed-paper/${trackingNumber}`,
};

// Editör endpointleri
export const EDITOR_ENDPOINTS = {
  PAPERS: `${API_BASE_URL}/editor/papers`,
  PAPER_DETAILS: (trackingNumber: string) => `${API_BASE_URL}/editor/papers/${trackingNumber}`,
  DOWNLOAD: (trackingNumber: string) => `${API_BASE_URL}/editor/download/${trackingNumber}`,
  MESSAGE: (trackingNumber: string) => `${API_BASE_URL}/editor/message/${trackingNumber}`,
  PAPER_COUNTS: `${API_BASE_URL}/editor/paper-counts`,
  RECENT_PAPERS: `${API_BASE_URL}/editor/recent-papers`,
  RECENT_MESSAGES: `${API_BASE_URL}/editor/recent-messages`,
  ASSIGN_REVIEWER: (trackingNumber: string) => 
    `${API_BASE_URL}/review/assign/${trackingNumber}`,
  REVIEWS: `${API_BASE_URL}/editor/reviews`,
  REVIEW_DETAILS: (reviewId: number) => `${API_BASE_URL}/editor/review/${reviewId}`,
  DOWNLOAD_REVIEW: (reviewId: number) => `${API_BASE_URL}/editor/download-review/${reviewId}`,
  FORWARD_REVIEW: (reviewId: number) => `${API_BASE_URL}/editor/forward-review/${reviewId}`,
  DOWNLOAD_FINAL_PDF: (reviewId: number) => `${API_BASE_URL}/editor/download-final-pdf/${reviewId}`,
  DEANONYMIZE_REVIEW: (reviewId: number) => `${API_BASE_URL}/editor/deanonymize-review/${reviewId}`,
};

// Hakem endpointleri
export const REVIEW_ENDPOINTS = {
  PAPERS: `${API_BASE_URL}/review/papers`,
  DOWNLOAD_PAPER: (trackingNumber: string) => `${API_BASE_URL}/review/download/${trackingNumber}`,
  PAPER_PREVIEW: (trackingNumber: string) => `${API_BASE_URL}/review/preview/${trackingNumber}`,
  SUBMIT_REVIEW: (trackingNumber: string) => `${API_BASE_URL}/review/submit/${trackingNumber}`,
  COMPLETED_REVIEWS: `${API_BASE_URL}/review/completed`,
  REVIEW_STATS: `${API_BASE_URL}/review/stats`,
  UPDATE_REVIEWER: (trackingNumber: string) => `${API_BASE_URL}/review/update-reviewer/${trackingNumber}`,
  GET_REVIEW: `${API_BASE_URL}/review/get-review`,
  PREVIEW_REVIEWED: (trackingNumber: string) => `${API_BASE_URL}/anonymize/reviewed-paper/${trackingNumber}`,
  SUBMIT_TO_EDITOR: (trackingNumber: string) => `${API_BASE_URL}/review/submit-to-editor/${trackingNumber}`,
};

// Mesajlaşma endpointleri
export const MESSAGE_ENDPOINTS = {
  SEND: `${API_BASE_URL}/internal-message`,
  GET_THREAD: (trackingNumber: string) => `${API_BASE_URL}/internal-message/messages/${trackingNumber}`,
  MARK_READ: (messageId: number) => `${API_BASE_URL}/messages/${messageId}/read`,
  ADD_ATTACHMENT: (messageId: number) => `${API_BASE_URL}/messages/${messageId}/attachment`
};

// Yazar mesaj endpointi (Eski versiyon için, uyumluluk amacıyla korundu)
export const AUTHOR_MESSAGE_ENDPOINT = MESSAGE_ENDPOINTS.SEND;

// Yazar endpointleri
export const AUTHOR_ENDPOINTS = {
  DOWNLOAD_REVIEW: (trackingNumber: string) => `${API_BASE_URL}/author/download-review/${trackingNumber}`,
  DOWNLOAD_FINAL_PDF: (trackingNumber: string) => `${API_BASE_URL}/editor/author/download-final-pdf/${trackingNumber}`
};

// Editör mesajlaşma endpointleri
export const EDITOR_MESSAGE_ENDPOINTS = {
  GET_MESSAGES: `${API_BASE_URL}/editor/messages`,
  MARK_READ: (messageId: number) => `${API_BASE_URL}/editor/messages/${messageId}/read`,
  RESPOND: (messageId: number) => `${API_BASE_URL}/editor/messages/${messageId}/respond`,
};

/**
 * API isteği gönderen yardımcı fonksiyon
 * @param endpoint API endpoint
 * @param options Fetch options
 * @returns Promise
 */
export async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || 'API isteği sırasında bir hata oluştu');
  }

  return data;
}

/**
 * Dosya yükleme için API isteği gönderen yardımcı fonksiyon
 * @param endpoint API endpoint
 * @param formData Form verisi
 * @returns Promise
 */
export async function uploadFile(endpoint: string, formData: FormData) {
  const response = await fetch(endpoint, {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || 'Dosya yükleme sırasında bir hata oluştu');
  }

  return data;
} 