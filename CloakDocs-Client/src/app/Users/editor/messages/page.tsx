"use client";

import type React from "react";
import { useState, useEffect } from "react";
import Link from "next/link";
import { EDITOR_MESSAGE_ENDPOINTS } from "@/app/lib/apiConfig";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/app/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Mail,
  Home,
  LayoutDashboard,
  X,
  Send,
  Loader2,
  MessageSquare,
  Clock,
  User,
  FileText,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  CheckCircle,
} from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface AuthorMessage {
  id: number;
  paper_id: number;
  tracking_number: string;
  subject: string;
  message: string;
  email: string;
  created_at: string;
  is_read: boolean;
  responded_at: string | null;
  response_message: string | null;
  original_filename: string;
}

export default function EditorMessagesPage() {
  const [messages, setMessages] = useState<AuthorMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedMessage, setSelectedMessage] = useState<AuthorMessage | null>(
    null
  );
  const [responseText, setResponseText] = useState("");
  const [isSendingResponse, setIsSendingResponse] = useState(false);
  const [responseSuccess, setResponseSuccess] = useState(false);
  const [responseError, setResponseError] = useState<string | null>(null);
  const [isMetadataOpen, setIsMetadataOpen] = useState(true);

  useEffect(() => {
    loadMessages();
  }, []);

  const loadMessages = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(EDITOR_MESSAGE_ENDPOINTS.GET_MESSAGES);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Mesajlar yüklenirken bir hata oluştu.");
      }

      setMessages(data.messages);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Bilinmeyen bir hata oluştu";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReadMessage = async (messageId: number) => {
    const message = messages.find((m) => m.id === messageId);
    if (!message) return;

    setSelectedMessage(message);
    setIsMetadataOpen(true); // Open metadata panel when selecting a new message

    if (!message.is_read) {
      try {
        const response = await fetch(
          EDITOR_MESSAGE_ENDPOINTS.MARK_READ(messageId),
          {
            method: "POST",
          }
        );

        if (!response.ok) {
          const data = await response.json();
          throw new Error(
            data.error || "Mesaj okundu işaretlenirken bir hata oluştu."
          );
        }

        setMessages(
          messages.map((m) =>
            m.id === messageId ? { ...m, is_read: true } : m
          )
        );
      } catch (error) {
        console.error("Mesaj okundu işaretleme hatası:", error);
      }
    }
  };

  const handleSendResponse = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedMessage || !responseText.trim()) {
      setResponseError("Lütfen bir yanıt yazın.");
      return;
    }

    setIsSendingResponse(true);
    setResponseError(null);
    setResponseSuccess(false);

    try {
      const response = await fetch(
        EDITOR_MESSAGE_ENDPOINTS.RESPOND(selectedMessage.id),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            response: responseText,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Yanıt gönderilirken bir hata oluştu.");
      }

      setMessages(
        messages.map((m) =>
          m.id === selectedMessage.id
            ? {
                ...m,
                responded_at: new Date().toISOString(),
                response_message: responseText,
              }
            : m
        )
      );

      setResponseSuccess(true);
      setResponseText("");
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Bilinmeyen bir hata oluştu";
      setResponseError(errorMessage);
    } finally {
      setIsSendingResponse(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatShortDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-background/80 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold tracking-tight text-primary">
              Yazar Mesajları
            </h1>
            <p className="text-muted-foreground">
              Yazarlardan gelen mesajları yönetin ve yanıtlayın
            </p>
          </div>
          <div className="flex gap-3">
            <Link href="/Users/editor">
              <Button variant="outline" size="sm">
                <LayoutDashboard className="mr-2 h-4 w-4" />
                Editör Paneli
              </Button>
            </Link>
            <Link href="/">
              <Button variant="outline" size="sm">
                <Home className="mr-2 h-4 w-4" />
                Ana Sayfa
              </Button>
            </Link>
          </div>
        </div>

        {error && (
          <Card className="mb-4 border border-red-500/50 bg-red-100 dark:bg-red-900/30 shadow-md">
            <CardContent className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <X className="h-5 w-5 text-red-600 dark:text-red-400" />
                <p className="text-red-800 dark:text-red-300 font-medium">
                  {error}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  onClick={loadMessages}
                  variant="outline"
                  size="sm"
                  className="border-red-400 text-red-700 dark:text-red-300 hover:bg-red-200/30 dark:hover:bg-red-800/40"
                >
                  Yeniden Dene
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setError(null)}
                  className="text-red-700 dark:text-red-400 hover:bg-red-200/40 dark:hover:bg-red-800/40"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {responseSuccess && (
          <Card className="mb-4 border border-green-500/50 bg-green-100 dark:bg-green-900/30 shadow-md">
            <CardContent className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                <p className="text-green-800 dark:text-green-300 font-medium">
                  Yanıtınız başarıyla gönderildi.
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setResponseSuccess(false)}
                className="text-green-700 dark:text-green-400 hover:bg-green-200/40 dark:hover:bg-green-800/40"
              >
                <X className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <Card className="shadow-sm h-[calc(100vh-12rem)] flex flex-col overflow-hidden">
              <CardHeader className="pb-3 flex-shrink-0">
                <CardTitle className="text-xl flex items-center">
                  <Mail className="mr-2 h-5 w-5 text-primary" />
                  Gelen Mesajlar
                </CardTitle>
                <div className="flex justify-between items-center">
                  <CardDescription>
                    {messages.length} mesaj bulunuyor
                  </CardDescription>
                  <Button
                    onClick={loadMessages}
                    variant="ghost"
                    size="sm"
                    className="hover:bg-primary/10"
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Yenile
                  </Button>
                </div>
              </CardHeader>
              <Separator />

              {isLoading ? (
                <div className="flex-1 flex justify-center items-center p-6">
                  <Loader2 className="h-8 w-8 text-primary animate-spin" />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex-1 flex justify-center items-center p-6 text-center">
                  <div className="space-y-2">
                    <MessageSquare className="h-12 w-12 text-muted-foreground/30 mx-auto" />
                    <p className="text-muted-foreground">
                      Henüz hiç mesaj bulunmuyor.
                    </p>
                  </div>
                </div>
              ) : (
                <ScrollArea className="flex-1 h-[calc(100vh-20rem)]">
                  <div className="p-3 pb-4 space-y-2">
                    {messages.map((message, index) => (
                      <div
                        key={message.id}
                        onClick={() => handleReadMessage(message.id)}
                        className={`
                          p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md
                          ${
                            selectedMessage?.id === message.id
                              ? "bg-primary/5 border-primary shadow-sm"
                              : message.is_read
                              ? "bg-card hover:bg-accent/5 border-border"
                              : "bg-primary/5 hover:bg-primary/10 border-primary/20 font-medium"
                          }
                          ${index === messages.length - 1 ? "mb-8" : ""}
                        `}
                      >
                        <div className="flex justify-between items-start mb-1.5">
                          <span className="font-medium truncate max-w-[70%] text-foreground">
                            {message.subject}
                          </span>
                          {!message.is_read && (
                            <Badge
                              variant="default"
                              className="ml-2 bg-primary text-primary-foreground"
                            >
                              Yeni
                            </Badge>
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground mb-2 line-clamp-2">
                          {message.message}
                        </div>
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span className="font-mono truncate max-w-[60%]">
                            {message.tracking_number}
                          </span>
                          <span>{formatShortDate(message.created_at)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </Card>
          </div>

          <div className="lg:col-span-2">
            <Card className="shadow-sm h-[calc(100vh-12rem)] flex flex-col">
              {selectedMessage ? (
                <>
                  <CardHeader className="pb-3">
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-xl text-primary">
                        {selectedMessage.subject}
                      </CardTitle>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setSelectedMessage(null)}
                        className="h-8 w-8"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    <CardDescription>
                      Makale:{" "}
                      <span className="font-mono text-primary">
                        {selectedMessage.tracking_number}
                      </span>
                    </CardDescription>
                  </CardHeader>
                  <Separator />

                  <ScrollArea className="flex-1">
                    <div className="p-3 pb-4 space-y-2">
                      <Collapsible
                        open={isMetadataOpen}
                        onOpenChange={setIsMetadataOpen}
                        className="border rounded-lg overflow-hidden"
                      >
                        <CollapsibleTrigger asChild>
                          <div className="flex justify-between items-center p-3 bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors">
                            <span className="font-medium">Mesaj Detayları</span>
                            {isMetadataOpen ? (
                              <ChevronUp className="h-4 w-4 text-muted-foreground" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                          <div className="p-3 space-y-2 bg-muted/10">
                            <div className="grid grid-cols-2 gap-2">
                              <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                <span className="text-sm text-muted-foreground">
                                  Gönderen:
                                </span>
                                <span className="text-sm font-medium truncate">
                                  {selectedMessage.email}
                                </span>
                              </div>

                              <div className="flex items-center gap-2">
                                <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                <span className="text-sm text-muted-foreground">
                                  Makale:
                                </span>
                                <span className="text-sm font-mono text-primary truncate">
                                  {selectedMessage.tracking_number}
                                </span>
                              </div>

                              <div className="flex items-center gap-2">
                                <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                <span className="text-sm text-muted-foreground">
                                  Dosya:
                                </span>
                                <span className="text-sm font-medium truncate">
                                  {selectedMessage.original_filename}
                                </span>
                              </div>

                              <div className="flex items-center gap-2">
                                <Clock className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                                <span className="text-sm text-muted-foreground">
                                  Tarih:
                                </span>
                                <span className="text-sm truncate">
                                  {formatDate(selectedMessage.created_at)}
                                </span>
                              </div>
                            </div>
                          </div>
                        </CollapsibleContent>
                      </Collapsible>

                      <div>
                        <h3 className="text-lg font-semibold mb-3 text-foreground flex items-center gap-2">
                          <MessageSquare className="h-5 w-5 text-primary" />
                          Mesaj
                        </h3>
                        <div className="bg-muted/50 p-4 rounded-lg whitespace-pre-wrap text-foreground">
                          {selectedMessage.message}
                        </div>
                      </div>

                      {selectedMessage.response_message ? (
                        <div>
                          <h3 className="text-lg font-semibold mb-3 text-primary flex items-center gap-2">
                            <Send className="h-5 w-5" />
                            Yanıtınız
                          </h3>
                          <div className="bg-primary/5 border border-primary/20 p-4 rounded-lg whitespace-pre-wrap">
                            {selectedMessage.response_message}
                          </div>
                          <div className="text-right text-sm text-muted-foreground mt-2 flex items-center justify-end gap-2">
                            <Clock className="h-3 w-3" />
                            {selectedMessage.responded_at
                              ? formatDate(selectedMessage.responded_at)
                              : "Gönderildi"}
                          </div>
                        </div>
                      ) : (
                        <div>
                          <h3 className="text-lg font-semibold mb-3 text-primary flex items-center gap-2">
                            <Send className="h-5 w-5" />
                            Yanıt Yaz
                          </h3>

                          {responseError && (
                            <div className="bg-destructive/10 border-l-4 border-destructive p-4 mb-4 rounded-r-lg">
                              <p className="text-destructive">
                                {responseError}
                              </p>
                            </div>
                          )}

                          <form
                            onSubmit={handleSendResponse}
                            className="space-y-4"
                          >
                            <Textarea
                              className="min-h-[150px] resize-none"
                              placeholder="Yanıtınızı buraya yazın..."
                              value={responseText}
                              onChange={(e) => setResponseText(e.target.value)}
                              disabled={isSendingResponse}
                              required
                            />

                            <div className="flex justify-end">
                              <Button
                                type="submit"
                                disabled={isSendingResponse}
                                className="bg-primary hover:bg-primary/90"
                              >
                                {isSendingResponse ? (
                                  <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Gönderiliyor...
                                  </>
                                ) : (
                                  <>
                                    <Send className="mr-2 h-4 w-4" />
                                    Yanıtı Gönder
                                  </>
                                )}
                              </Button>
                            </div>
                          </form>
                        </div>
                      )}
                    </div>
                  </ScrollArea>
                </>
              ) : (
                <div className="flex-1 flex flex-col justify-center items-center p-6">
                  <div className="text-center space-y-3 max-w-md">
                    <div className="bg-primary/10 p-4 rounded-full inline-flex mx-auto">
                      <Mail className="h-10 w-10 text-primary" />
                    </div>
                    <h3 className="text-xl font-medium">
                      Sol taraftan bir mesaj seçin
                    </h3>
                    <p className="text-muted-foreground">
                      Yazarlardan gelen mesajları görüntülemek ve yanıtlamak
                      için listeden bir mesaj seçin.
                    </p>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
