import Link from "next/link"

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background">
      <main className="max-w-6xl w-full mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-5xl heading-primary mb-4">Akademik Makale Değerlendirme Sistemi</h1>
          <p className="text-lg text-text-primary max-w-3xl mx-auto">
            Bu sistem, akademik makalelerin yüklenmesi, değerlendirilmesi ve yönetilmesi için tasarlanmıştır.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          <Link href="/Users/author" className="block transform transition-transform hover:scale-105 duration-300">
            <div className="card h-full flex flex-col hover:shadow-lg border-t-4 border-primary">
              <div className="flex-1 p-6">
                <h3 className="text-2xl heading-primary mb-3">Yazar Girişi</h3>
                <p className="text-text-primary mb-6">Makale yüklemek veya durumunu sorgulamak için</p>
                <div className="mt-auto">
                  <span className="button-primary inline-block">Devam Et</span>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/Users/editor" className="block transform transition-transform hover:scale-105 duration-300">
            <div className="card h-full flex flex-col hover:shadow-lg border-t-4 border-accent">
              <div className="flex-1 p-6">
                <h3 className="text-2xl heading-accent mb-3">Editör Girişi</h3>
                <p className="text-text-primary mb-6">Makaleleri yönetmek ve değerlendirme sürecini izlemek için</p>
                <div className="mt-auto">
                  <span className="button-accent inline-block">Devam Et</span>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/Users/reviewer" className="block transform transition-transform hover:scale-105 duration-300">
          <div className="card h-full flex flex-col hover:shadow-lg" style={{ borderTop: '4px solid #d4af37' }}>
              <div className="flex-1 p-6">
                <h3 className="text-2xl heading-premium mb-3">Hakem Girişi</h3>
                <p className="text-text-primary mb-6">Makaleleri değerlendirmek ve geri bildirim vermek için</p>
                <div className="mt-auto">
                  <span className="button-referee inline-block">Devam Et</span>
                </div>
              </div>
            </div>
          </Link>
        </div>

        <div className="card p-8 border-l-4 border-text-technical">
          <h2 className="text-3xl heading-secondary mb-6">Sistem Hakkında</h2>
          <p className="mb-6 text-lg text-text-primary">
            Bu akademik makale değerlendirme sistemi, makalelerin anonim olarak değerlendirilmesini sağlayan güvenli bir
            platformdur. Yazarlar makalelerini yükleyebilir, editörler süreci yönetebilir ve hakemler değerlendirme
            yapabilir.
          </p>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 text-text-primary">
            <li className="flex items-start">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6 text-primary mr-2 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Yazarlar için üyelik gerektirmeyen kolay makale yükleme</span>
            </li>
            <li className="flex items-start">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6 text-primary mr-2 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Editörler için gelişmiş makale yönetim araçları</span>
            </li>
            <li className="flex items-start">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6 text-primary mr-2 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Hakemler için anonim değerlendirme sistemi</span>
            </li>
            <li className="flex items-start">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6 text-primary mr-2 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Güvenli ve şeffaf değerlendirme süreci</span>
            </li>
          </ul>
        </div>
      </main>
    </div>
  )
}

