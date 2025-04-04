import React from "react";
import Link from "next/link";

export default function AuthorPage() {
  return (
    <div className="min-h-screen flex flex-col items-center p-4 bg-background">
      <div className="w-full max-w-4xl">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl heading-primary">Yazar Sayfası</h1>
          <Link href="/" className="link">
            Ana Sayfa
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          <Link href="/Users/author/submit-paper" className="block">
            <div className="card h-full">
              <h2 className="text-2xl heading-primary mb-4">Makale Yükle</h2>
              <p className="mb-6 text-text-primary">
                Akademik makalenizi PDF formatında yükleyin. Üyelik gerekmez, sadece geçerli bir e-posta adresi gereklidir.
              </p>
              <ul className="list-disc pl-5 mb-6 space-y-2 text-text-primary">
                <li>PDF formatında makale yükleme</li>
                <li>Eşsiz takip numarası alma</li>
                <li>Kolay süreç takibi</li>
              </ul>
              <div className="mt-auto">
                <span className="button-primary inline-block">Makale Yükle</span>
              </div>
            </div>
          </Link>

          <Link href="/Users/author/check-status" className="block">
            <div className="card h-full">
              <h2 className="text-2xl heading-accent mb-4">Makale Durumu Sorgula</h2>
              <p className="mb-6 text-text-primary">
                Daha önce yüklediğiniz makalenizin değerlendirme sürecini takip edin ve sonuçları görüntüleyin.
              </p>
              <ul className="list-disc pl-5 mb-6 space-y-2 text-text-primary">
                <li>Makale takip numarası ile sorgulama</li>
                <li>Değerlendirme sürecini takip etme</li>
                <li>Hakem geri bildirimlerini görüntüleme</li>
                <li>Revize makale yükleme imkanı</li>
              </ul>
              <div className="mt-auto">
                <span className="button-accent inline-block">Durum Sorgula</span>
              </div>
            </div>
          </Link>
        </div>

        <div className="card">
          <h2 className="text-xl heading-secondary mb-4">Bilgilendirme</h2>
          <p className="mb-4 text-text-primary">
            Makale yükleme işlemi tamamlandığında, size bir takip numarası verilecektir. Bu numara ile makalenizin durumunu sorgulayabilir ve değerlendirme sürecini takip edebilirsiniz.
          </p>
          <p className="text-text-primary">
            Değerlendirme süreci tamamlandığında, sonuçlar ve hakem geri bildirimleri e-posta adresinize gönderilecektir. Ayrıca, takip numaranız ile sistem üzerinden de sonuçları görüntüleyebilirsiniz.
          </p>
        </div>
      </div>
    </div>
  );
} 