-- Makaleler tablosu
CREATE TABLE IF NOT EXISTS papers (
  id SERIAL PRIMARY KEY,
  tracking_number VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(255) NOT NULL,
  file_path VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255) NOT NULL,
  file_size INTEGER NOT NULL,
  upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(50) DEFAULT 'pending',
  download_count INTEGER DEFAULT 0,
  last_downloaded TIMESTAMP NULL,
  last_updated TIMESTAMP NULL,
  keywords TEXT,
  original_paper_id INTEGER NULL,
  is_revision BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (original_paper_id) REFERENCES papers(id) ON DELETE SET NULL
);

-- Anonimleştirilmiş Dosyalar tablosu
CREATE TABLE IF NOT EXISTS anonymized_files (
  id SERIAL PRIMARY KEY,
  paper_id INTEGER NOT NULL,
  file_path VARCHAR(255) NOT NULL,
  filename VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  download_count INTEGER DEFAULT 0,
  last_downloaded TIMESTAMP NULL,
  anonymization_info TEXT NULL,
  encrypted_examples TEXT NULL,
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Değerlendirmeler tablosu (GÜNCELLENMİŞ)
CREATE TABLE IF NOT EXISTS reviews (
  id SERIAL PRIMARY KEY,
  paper_id INTEGER NOT NULL,
  reviewer_id VARCHAR(50) NOT NULL,
  score INTEGER NOT NULL,
  comments TEXT NOT NULL,
  recommendation VARCHAR(50) NOT NULL,
  review_file_path VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  subcategory_id INTEGER NULL,
  review_document TEXT NULL,
  final_pdf_path VARCHAR(255),         -- Nihai PDF dosyasının yolu
  deanonymized BOOLEAN DEFAULT FALSE,  -- Anonimliğin kaldırılıp kaldırılmadığı
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Mesajlar tablosu
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL,
    sender_email VARCHAR(255) NOT NULL,
    is_from_author BOOLEAN NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Log kayıtları tablosu
CREATE TABLE IF NOT EXISTS paper_logs (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_description TEXT NOT NULL,
    user_email VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    additional_data JSONB NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- İndeksler
CREATE INDEX IF NOT EXISTS papers_tracking_number_idx ON papers(tracking_number);
CREATE INDEX IF NOT EXISTS papers_email_idx ON papers(email);
CREATE INDEX IF NOT EXISTS papers_status_idx ON papers(status);

CREATE INDEX IF NOT EXISTS anonymized_files_paper_id_idx ON anonymized_files(paper_id);

CREATE INDEX IF NOT EXISTS reviews_paper_id_idx ON reviews(paper_id);
CREATE INDEX IF NOT EXISTS reviews_subcategory_id_idx ON reviews(subcategory_id);
CREATE INDEX IF NOT EXISTS reviews_final_pdf_path_idx ON reviews(final_pdf_path);
CREATE INDEX IF NOT EXISTS reviews_deanonymized_idx ON reviews(deanonymized);

CREATE INDEX IF NOT EXISTS messages_paper_id_idx ON messages(paper_id);
CREATE INDEX IF NOT EXISTS messages_sender_email_idx ON messages(sender_email);
CREATE INDEX IF NOT EXISTS messages_is_read_idx ON messages(is_read);

CREATE INDEX IF NOT EXISTS paper_logs_paper_id_idx ON paper_logs(paper_id);
CREATE INDEX IF NOT EXISTS paper_logs_event_type_idx ON paper_logs(event_type);
CREATE INDEX IF NOT EXISTS paper_logs_created_at_idx ON paper_logs(created_at);

-- Açıklamalar
COMMENT ON TABLE papers IS 'Yüklenen makaleler';
COMMENT ON COLUMN papers.id IS 'Makale ID';
COMMENT ON COLUMN papers.tracking_number IS 'Benzersiz takip numarası';
COMMENT ON COLUMN papers.email IS 'Yazarın e-posta adresi';
COMMENT ON COLUMN papers.file_path IS 'Dosya yolu';
COMMENT ON COLUMN papers.original_filename IS 'Orijinal dosya adı';
COMMENT ON COLUMN papers.file_size IS 'Dosya boyutu (bytes)';
COMMENT ON COLUMN papers.upload_date IS 'Yükleme tarihi';
COMMENT ON COLUMN papers.status IS 'Değerlendirme durumu';
COMMENT ON COLUMN papers.download_count IS 'İndirme sayısı';
COMMENT ON COLUMN papers.last_downloaded IS 'Son indirme tarihi';
COMMENT ON COLUMN papers.last_updated IS 'Son güncelleme tarihi';
COMMENT ON COLUMN papers.keywords IS 'Anahtar kelimeler (JSON formatında)';
COMMENT ON COLUMN papers.original_paper_id IS 'Revize edilmiş bir makale ise, orijinal makalenin ID referansı';
COMMENT ON COLUMN papers.is_revision IS 'Makalenin bir revizyon olup olmadığını belirtir';

COMMENT ON TABLE anonymized_files IS 'Anonimleştirilmiş makale dosyaları';
COMMENT ON COLUMN anonymized_files.id IS 'Anonimleştirilmiş dosya ID';
COMMENT ON COLUMN anonymized_files.paper_id IS 'İlgili makale ID';
COMMENT ON COLUMN anonymized_files.file_path IS 'Anonimleştirilmiş dosya yolu';
COMMENT ON COLUMN anonymized_files.filename IS 'Anonimleştirilmiş dosya adı';
COMMENT ON COLUMN anonymized_files.created_at IS 'Oluşturulma tarihi';
COMMENT ON COLUMN anonymized_files.download_count IS 'İndirme sayısı';
COMMENT ON COLUMN anonymized_files.anonymization_info IS 'Anonimleştirme bilgileri (JSON formatında)';
COMMENT ON COLUMN anonymized_files.encrypted_examples IS 'Şifrelenmiş entity örnekleri';

COMMENT ON TABLE reviews IS 'Makale değerlendirmeleri';
COMMENT ON COLUMN reviews.id IS 'Değerlendirme ID';
COMMENT ON COLUMN reviews.paper_id IS 'Değerlendirilen makale ID';
COMMENT ON COLUMN reviews.reviewer_id IS 'Hakem ID';
COMMENT ON COLUMN reviews.score IS 'Değerlendirme puanı';
COMMENT ON COLUMN reviews.comments IS 'Değerlendirme yorumları';
COMMENT ON COLUMN reviews.recommendation IS 'Nihai öneri (kabul/red/revizyon vs.)';
COMMENT ON COLUMN reviews.review_file_path IS 'Değerlendirme dosya yolu';
COMMENT ON COLUMN reviews.subcategory_id IS 'Alt kategori ID';
COMMENT ON COLUMN reviews.review_document IS 'Hakemin yorumlarını içeren metin';
COMMENT ON COLUMN reviews.final_pdf_path IS 'Final PDF dosyasının yolu';
COMMENT ON COLUMN reviews.deanonymized IS 'Anonimliğin kaldırılıp kaldırılmadığı';

COMMENT ON TABLE messages IS 'Yazar ve editör arasındaki mesajlaşmaları içerir';
COMMENT ON COLUMN messages.id IS 'Mesaj ID';
COMMENT ON COLUMN messages.paper_id IS 'İlgili makale ID';
COMMENT ON COLUMN messages.sender_email IS 'Mesajı gönderenin e-posta adresi';
COMMENT ON COLUMN messages.is_from_author IS 'TRUE ise yazar, FALSE ise editör';
COMMENT ON COLUMN messages.subject IS 'Mesajın konusu';
COMMENT ON COLUMN messages.message IS 'Mesaj içeriği';
COMMENT ON COLUMN messages.created_at IS 'Mesajın oluşturulma tarihi';
COMMENT ON COLUMN messages.is_read IS 'Mesajın okunup okunmadığı bilgisi';

COMMENT ON TABLE paper_logs IS 'Makale işlem log kayıtları';
COMMENT ON COLUMN paper_logs.id IS 'Log kaydı ID';
COMMENT ON COLUMN paper_logs.paper_id IS 'İlgili makale ID';
COMMENT ON COLUMN paper_logs.event_type IS 'İşlem türü (UPLOADED, ASSIGNED, REVIEWED vb.)';
COMMENT ON COLUMN paper_logs.event_description IS 'İşlem açıklaması';
COMMENT ON COLUMN paper_logs.user_email IS 'İşlemi yapan kullanıcının e-posta adresi';
COMMENT ON COLUMN paper_logs.created_at IS 'Log kaydının oluşturulma tarihi';
COMMENT ON COLUMN paper_logs.additional_data IS 'İşlemle ilgili ek bilgiler (JSON formatında)';
