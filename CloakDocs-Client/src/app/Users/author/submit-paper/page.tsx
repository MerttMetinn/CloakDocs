'use client';

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import FileUploadButton from "./FileUploadButton";
import { PAPER_ENDPOINTS, STATUS_ENDPOINTS, uploadFile, fetchApi } from "@/app/lib/apiConfig";
import { ArticleStatus } from "@/app/lib/articleStatus";

export default function SubmitPaperPage() {
  const searchParams = useSearchParams();
  const isRevision = searchParams.get('revision') === 'true';
  const revisionTrackingNumber = searchParams.get('trackingNumber');
  const revisionEmail = searchParams.get('email');

  const [email, setEmail] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [trackingNumber, setTrackingNumber] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);

  // URL'deki parametrelerden e-posta ve takip numarasını doldur
  useEffect(() => {
    if (isRevision && revisionEmail) {
      setEmail(revisionEmail);
      setTrackingNumber(revisionTrackingNumber);
    }
  }, [isRevision, revisionEmail, revisionTrackingNumber]);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !selectedFile) {
      setError('Lütfen e-posta adresinizi girin ve bir PDF dosyası yükleyin.');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('email', email);
      
      // Revize makale için takip numarası ve durum bilgisini ekle
      if (isRevision && revisionTrackingNumber) {
        formData.append('tracking_number', revisionTrackingNumber);
        formData.append('is_revision', 'true');
      }
      
      // Dosyayı yükle
      const data = await uploadFile(PAPER_ENDPOINTS.UPLOAD, formData);
      
      // Eğer revize dosyası yüklendiyse durumu güncelleyelim
      if (isRevision && revisionTrackingNumber) {
        try {
          await fetchApi(STATUS_ENDPOINTS.UPDATE, {
            method: 'POST',
            body: JSON.stringify({
              tracking_number: revisionTrackingNumber,
              status: ArticleStatus.REVISED
            }),
          });
        } catch (statusError) {
          console.error('Durum güncelleme hatası:', statusError);
          // Ancak ana işlem başarılı oldu, bu yüzden kullanıcıya hata göstermeyelim
        }
      }
      
      setSuccess(true);
      setTrackingNumber(data.trackingNumber || revisionTrackingNumber);
      setEmailSent(data.emailSent);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Bilinmeyen bir hata oluştu';
      setError(errorMessage || 'Dosya yükleme sırasında bir hata oluştu.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center p-4 bg-background">
      <div className="w-full max-w-3xl">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl heading-primary">
            {isRevision ? 'Revize Makale Yükleme' : 'Makale Yükleme'}
          </h1>
          <div className="flex gap-4">
            <Link href="/Users/author" className="link">
              Yazar Sayfası
            </Link>
            <Link href="/" className="link">
              Ana Sayfa
            </Link>
          </div>
        </div>

        {success ? (
          <div className="card mb-8 text-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-status-success mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <h2 className="text-2xl heading-primary mb-4">
              {isRevision ? 'Revize Makale Başarıyla Yüklendi!' : 'Makale Başarıyla Yüklendi!'}
            </h2>
            
            {emailSent ? (
              <div>
                <p className="mb-6 text-text-primary">
                  {isRevision 
                    ? 'Revize makaleniz başarıyla yüklendi. İşlem sonucu ' 
                    : 'Makaleniz başarıyla yüklendi. Takip numaranız '}
                  <strong>{email}</strong> adresine gönderilmiştir.
                </p>
                <p className="mb-6 text-text-primary">
                  Lütfen e-posta kutunuzu kontrol edin. Takip numaranızı kullanarak makalenizin durumunu sorgulayabilirsiniz.
                </p>
              </div>
            ) : trackingNumber ? (
              <div>
                <p className="mb-6 text-text-primary">
                  {isRevision 
                    ? 'Revize makaleniz başarıyla yüklendi.' 
                    : 'Makaleniz başarıyla yüklendi. Lütfen aşağıdaki takip numarasını saklayın:'}
                </p>
                <div className="bg-background-secondary border border-border p-4 rounded-md mb-6">
                  <p className="text-2xl font-mono font-bold text-primary">{trackingNumber}</p>
                </div>
                <p className="text-text-primary mb-6">
                  Bu takip numarası ile makalenizin durumunu sorgulayabilirsiniz.
                </p>
              </div>
            ) : (
              <p className="mb-6 text-text-primary">
                {isRevision 
                  ? 'Revize makaleniz başarıyla yüklendi, ancak onay e-postası gönderilemedi.' 
                  : 'Makaleniz başarıyla yüklendi, ancak takip numarası e-posta ile gönderilemedi.'} 
                Lütfen daha sonra tekrar deneyin.
              </p>
            )}
            
            <div className="flex justify-center gap-4">
              <Link href="/Users/author/check-status" className="button-primary">
                Durum Sorgula
              </Link>
              <button 
                onClick={() => {
                  setSuccess(false);
                  setTrackingNumber(null);
                  setEmailSent(false);
                  setEmail('');
                  setSelectedFile(null);
                }}
                className="button-outline"
              >
                Yeni Makale Yükle
              </button>
            </div>
          </div>
        ) : (
          <div className="card mb-8">
            <h2 className="text-2xl heading-secondary mb-6">
              {isRevision ? 'Revize Makale Yükleme Formu' : 'Makale Yükleme Formu'}
            </h2>
            
            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
                <p className="text-red-700">{error}</p>
              </div>
            )}
            
            {isRevision && (
              <div className="bg-premium/10 border-l-4 border-premium p-4 mb-6">
                <p className="text-premium">
                  Revize makalenizi yüklüyorsunuz. Lütfen gereken düzeltmeleri yaptığınızdan emin olun.
                </p>
              </div>
            )}
            
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="email" className="form-label">
                  E-posta Adresi <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  id="email"
                  className="form-input"
                  placeholder="ornek@universite.edu.tr"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting || isRevision}
                  readOnly={isRevision}
                />
                <p className="form-helper">
                  {isRevision 
                    ? 'Revize makale, orijinal makale ile aynı e-posta adresine bağlı olmalıdır.' 
                    : 'Makale ile ilgili bildirimler ve takip numarası bu e-posta adresine gönderilecektir.'}
                </p>
              </div>
              
              <div>
                <label className="form-label">
                  PDF Dosyası <span className="text-red-500">*</span>
                </label>
                <FileUploadButton
                  onFileSelect={handleFileSelect}
                  selectedFile={selectedFile}
                  disabled={isSubmitting}
                />
                <p className="form-helper">
                  Yalnızca PDF formatındaki dosyalar kabul edilmektedir. Maksimum dosya boyutu 16MB dır.
                </p>
              </div>
              
              <div className="flex justify-end">
                <button 
                  type="submit"
                  className={isRevision ? "button-premium" : "button-primary"}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Yükleniyor...' : (isRevision ? 'Revize Makaleyi Yükle' : 'Makaleyi Yükle')}
                </button>
              </div>
            </form>
          </div>
        )}
        
        <div className="card">
          <h2 className="text-xl heading-secondary mb-4">
            {isRevision ? 'Revize Makale Yükleme Kuralları' : 'Makale Yükleme Kuralları'}
          </h2>
          <ul className="list-disc pl-5 space-y-2 text-text-primary">
            <li>Yalnızca PDF formatındaki dosyalar kabul edilmektedir.</li>
            <li>Maksimum dosya boyutu 16MB dır.</li>
            {isRevision ? (
              <>
                <li>Revize dosyanızda, hakem ve editör önerilerini dikkate aldığınızdan emin olun.</li>
                <li>Değişikliklerin açıkça belirtildiği bir değişiklik listesi eklemeniz tavsiye edilir.</li>
              </>
            ) : (
              <>
                <li>Makalenin anonim değerlendirme için uygun olduğundan emin olun.</li>
                <li>Yüklenen makaleler değerlendirildikten sonra sistematik olarak işlenecektir.</li>
              </>
            )}
            <li>Değerlendirme sonuçları e-posta ile bildirilecektir.</li>
          </ul>
        </div>
      </div>
    </div>
  );
} 