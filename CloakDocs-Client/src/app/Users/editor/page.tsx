'use client';

import React from "react";
import Link from "next/link";

export default function EditorPage() {
  return (
    <div className="min-h-screen flex flex-col items-center p-4 bg-background">
      <div className="w-full max-w-6xl">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl heading-accent">Editör Paneli</h1>
          <Link href="/" className="link">
            Ana Sayfa
          </Link>
        </div>

        <div className="card mb-8">
          <h2 className="text-2xl heading-secondary mb-6">Menü</h2>
          <div className="space-y-4">
            <Link href="/Users/editor/papers" className="block p-4 border border-border rounded-lg hover:bg-background-secondary transition-colors">
              <div className="font-medium">Tüm Makaleler</div>
              <div className="text-sm text-text-primary mt-1">Sisteme yüklenen tüm makaleleri görüntüleyebilir ve indirebilirsiniz</div>
            </Link>

            <Link href="/Users/editor/anonymize" className="block p-4 border border-border rounded-lg hover:bg-background-secondary transition-colors">
              <div className="font-medium">Makaleyi Anonimleştir</div>
              <div className="text-sm text-text-primary mt-1">Makaleyi Hakemlere Göndermeden önce anonimleştirirsiniz</div>
            </Link>

            <Link href="/Users/editor/reviews" className="block p-4 border border-border rounded-lg hover:bg-background-secondary transition-colors">
              <div className="font-medium">Hakemlerden Gelen İncelemeler</div>
              <div className="text-sm text-text-primary mt-1">Değerlendirilmiş makalelerin hakemlerden gelen incelemelerini yazarlara iletebilirsiniz</div>
            </Link>

            <Link href="/Users/editor/messages" className="block p-4 border border-border rounded-lg hover:bg-background-secondary transition-colors">
              <div className="font-medium">Mesajlar</div>
              <div className="text-sm text-text-primary mt-1">Yazar mesajlarını görüntüle</div>
            </Link>

            <Link href="/Users/editor/logs" className="block p-4 border border-border rounded-lg hover:bg-background-secondary transition-colors">
              <div className="font-medium">Log Kayıtları</div>
              <div className="text-sm text-text-primary mt-1">Sistemde tutulan makalelerin log kaydını inceleyebilirsiniz</div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
} 