// src/lib/db.ts
import { Pool } from 'pg';

// Veritabanı bağlantı havuzu
const pool = new Pool({
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  host: process.env.POSTGRES_HOST,
  port: parseInt(process.env.POSTGRES_PORT || '5432'),
  database: process.env.POSTGRES_DATABASE,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

// Veritabanı sorgusu çalıştırma yardımcı fonksiyonu
export async function query(text: string, params?: unknown[]) {
  const start = Date.now();
  const res = await pool.query(text, params);
  const duration = Date.now() - start;
  
  console.log('Sorgu süresi:', duration, 'ms', { text, params });
  
  return res;
}

// Makale kaydetme fonksiyonu
export async function savePaper(paperData: {
  trackingNumber: string;
  email: string;
  filePath: string;
  originalFilename: string;
  fileSize: number;
}) {
  const { trackingNumber, email, filePath, originalFilename, fileSize } = paperData;
  
  const result = await query(
    'INSERT INTO papers (tracking_number, email, file_path, original_filename, file_size) VALUES ($1, $2, $3, $4, $5) RETURNING id',
    [trackingNumber, email, filePath, originalFilename, fileSize]
  );
  
  return result.rows[0].id;
}

// Takip numarasına göre makale getirme fonksiyonu
export async function getPaperByTrackingNumber(trackingNumber: string) {
  const result = await query(
    'SELECT * FROM papers WHERE tracking_number = $1',
    [trackingNumber]
  );
  
  return result.rows[0] || null;
}

// İndirme sayısını artırma fonksiyonu
export async function incrementDownloadCount(trackingNumber: string) {
  const result = await query(
    'UPDATE papers SET download_count = download_count + 1, last_downloaded = CURRENT_TIMESTAMP WHERE tracking_number = $1 RETURNING *',
    [trackingNumber]
  );
  
  return result.rows[0] || null;
}