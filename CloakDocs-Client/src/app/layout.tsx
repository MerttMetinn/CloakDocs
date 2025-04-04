import type { Metadata } from "next";
import { Inter, Roboto_Serif } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "./context/ThemeContext";
import ThemeToggleWrapper from "./components/ThemeToggleWrapper";
import { SpeedInsights } from "@vercel/speed-insights/next"
import { Analytics } from "@vercel/analytics/react"

const inter = Inter({ 
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const robotoSerif = Roboto_Serif({ 
  variable: "--font-roboto-serif",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Akademik Makale Değerlendirme Sistemi",
  description: "Akademik makalelerin yüklenmesi, değerlendirilmesi ve yönetilmesi için platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${robotoSerif.variable} antialiased`}
        suppressHydrationWarning
      >
        <SpeedInsights />
        <ThemeProvider>
          <ThemeToggleWrapper />
          <div className="relative">
            {children}
            <Analytics />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
