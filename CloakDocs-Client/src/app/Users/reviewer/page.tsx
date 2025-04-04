"use client"

import { useState } from "react"
import Link from "next/link"
import { Users, BookOpen, User, ExternalLink, Check, Home, Info } from "lucide-react"

import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

import { Button } from "@/app/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

// Hakem kategorilerini import et
import { MAIN_CATEGORIES } from "@/app/data/categories"

export default function ReviewerSelectionPage() {
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null)
  const [open, setOpen] = useState(false)

  // Seçilen kategorinin alt kategorilerini bul
  const selectedCategoryData = selectedCategory ? MAIN_CATEGORIES.find((cat) => cat.id === selectedCategory) : null

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background/80 p-4 md:p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        <header
          className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b pb-6"
          style={{ borderColor: "var(--border-color)" }}
        >
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight" style={{ color: "var(--primary)" }}>
              Hakem Paneli
            </h1>
            <p className="text-sm" style={{ color: "var(--text-primary)" }}>
              Lütfen uzmanlık alanınıza uygun kategoriden devam ediniz
            </p>
          </div>
          <Link href="/">
            <Button
              variant="outline"
              className="gap-2 transition-all duration-200 hover:border-accent"
              style={{ borderColor: "var(--border-color)", color: "var(--foreground)" }}
            >
              <Home className="h-4 w-4" />
            Ana Sayfa
            </Button>
          </Link>
        </header>

        <section className="space-y-6">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5" style={{ color: "var(--primary)" }} />
            <h2 className="text-xl font-semibold" style={{ color: "var(--text-technical)" }}>
              Hakem Alanları
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-[300px_1fr] gap-6">
            {/* Ana Kategori Seçimi */}
            <Card
              className="border shadow-sm"
              style={{ backgroundColor: "var(--background-secondary)", borderColor: "var(--border-color)" }}
            >
              <CardHeader className="pb-3">
                <CardTitle className="text-base" style={{ color: "var(--text-technical)" }}>
                  Ana Kategori
                </CardTitle>
                <CardDescription style={{ color: "var(--text-primary)", opacity: 0.75 }}>
                  Uzmanlık alanınızı seçin
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Popover open={open} onOpenChange={setOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={open}
                      className="w-full justify-between transition-all duration-200"
                      style={{
                        borderColor: "var(--border-color)",
                        color: "var(--foreground)",
                        backgroundColor: "var(--background)",
                      }}
                    >
                      <span className="truncate" title={selectedCategory ? MAIN_CATEGORIES.find((cat) => cat.id === selectedCategory)?.name : ""}>
                        {selectedCategory
                          ? MAIN_CATEGORIES.find((cat) => cat.id === selectedCategory)?.name
                          : "Kategori seçiniz"}
                      </span>
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent
                    className="w-[300px] p-0"
                    align="start"
                    style={{
                      backgroundColor: "var(--background-secondary)",
                      borderColor: "var(--border-color)",
                    }}
                  >
                    <Command style={{ backgroundColor: "var(--background-secondary)" }}>
                      <CommandInput placeholder="Kategori ara..." />
                      <CommandList>
                        <CommandEmpty>Kategori bulunamadı.</CommandEmpty>
                        <CommandGroup>
                          {MAIN_CATEGORIES.map((category) => (
                            <CommandItem
                              key={category.id}
                              value={category.name}
                              onSelect={() => {
                                setSelectedCategory(category.id === selectedCategory ? null : category.id)
                                setOpen(false)
                              }}
                              className="cursor-pointer"
                            >
                              <div className="flex items-center gap-2 w-full">
                                <span className="text-base">{category.icon}</span>
                                <span>{category.name}</span>
                                {selectedCategory === category.id && (
                                  <Check className="ml-auto h-4 w-4" style={{ color: "var(--accent)" }} />
          )}
        </div>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </CardContent>
            </Card>

            {/* Alt Kategoriler */}
            {selectedCategoryData ? (
              <Card
                className="border shadow-sm"
                style={{
                  backgroundColor: "var(--background-secondary)",
                  borderColor: "var(--border-color)",
                }}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{selectedCategoryData.icon}</span>
                      <CardTitle style={{ color: "var(--text-technical)" }}>{selectedCategoryData.name}</CardTitle>
                    </div>
                    <Badge
                      variant="outline"
                      className="ml-auto"
                      style={{
                        borderColor: "var(--accent)",
                        color: "var(--accent)",
                        backgroundColor: "transparent",
                      }}
                    >
                      {selectedCategoryData.subcategories.length} alt kategori
                    </Badge>
                  </div>
                  <CardDescription style={{ color: "var(--text-primary)", opacity: 0.75 }}>
                    Alt kategori seçerek devam edin
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {selectedCategoryData.subcategories.map((subcat) => (
                      <Link key={subcat.id} href={`/Users/reviewer/${subcat.id}`} className="block w-full">
                        <div
                          className="flex justify-between items-center p-3 rounded-md transition-all duration-200 border"
                          style={{
                            borderColor: "var(--border-color)",
                            backgroundColor: "var(--background)",
                            color: "var(--foreground)",
                          }}
                          onMouseOver={(e) => {
                            e.currentTarget.style.borderColor = "var(--accent)"
                            e.currentTarget.style.backgroundColor = "color-mix(in srgb, var(--accent), transparent 95%)"
                          }}
                          onMouseOut={(e) => {
                            e.currentTarget.style.borderColor = "var(--border-color)"
                            e.currentTarget.style.backgroundColor = "var(--background)"
                          }}
                        >
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4" style={{ color: "var(--primary)" }} />
                            <span>{subcat.name}</span>
                          </div>
                          <ExternalLink className="h-4 w-4" style={{ color: "var(--text-primary)", opacity: 0.5 }} />
                        </div>
                      </Link>
                    ))}
                    </div>
                </CardContent>
              </Card>
            ) : (
              <Card
                className="border-dashed flex items-center justify-center"
                style={{
                  backgroundColor: "color-mix(in srgb, var(--background-secondary), transparent 50%)",
                  borderColor: "var(--border-color)",
                }}
              >
                <CardContent className="py-8 text-center">
                  <div
                    className="mx-auto w-12 h-12 rounded-full flex items-center justify-center mb-4"
                    style={{ backgroundColor: "color-mix(in srgb, var(--primary), transparent 90%)" }}
                  >
                    <BookOpen className="h-6 w-6" style={{ color: "var(--primary)" }} />
                  </div>
                  <h3 className="text-lg font-medium mb-2" style={{ color: "var(--text-technical)" }}>
                    Alt Kategoriler
                  </h3>
                  <p className="max-w-md mx-auto" style={{ color: "var(--text-primary)", opacity: 0.75 }}>
                    Lütfen önce sol taraftan bir ana kategori seçin. Seçiminize göre ilgili alt kategoriler burada
                    görüntülenecektir.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </section>

        <Card
          className="mt-8"
          style={{
            backgroundColor: "var(--background-secondary)",
            borderColor: "var(--border-color)",
            boxShadow: "0 1px 3px var(--shadow-color)",
          }}
        >
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Info className="h-5 w-5" style={{ color: "var(--accent)" }} />
              <CardTitle style={{ color: "var(--text-technical)" }}>Hakem Bilgilendirmesi</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4" style={{ color: "var(--text-primary)" }}>
            <p>
              Hakem olarak sisteme giriş yaptığınızda, uzmanlık alanınıza uygun makaleleri değerlendirmeniz
              istenecektir.
            </p>
            <p>Değerlendirme sürecinde şu adımları izleyeceksiniz:</p>
            <ol className="list-decimal list-inside space-y-2 ml-4">
              <li>Makaleyi incelemek ve indirmek</li>
              <li>Değerlendirme formunu doldurmak</li>
              <li>İsteğe bağlı olarak dosya yüklemek</li>
              <li>Tavsiye kararınızı belirtmek</li>
            </ol>
            <p className="font-medium mt-4" style={{ color: "var(--primary)" }}>
              Lütfen yukarıdaki kategorilerden uzmanlık alanınızı seçerek devam edin.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 

