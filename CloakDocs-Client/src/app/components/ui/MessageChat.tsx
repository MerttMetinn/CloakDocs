"use client"

import { useState, type FormEvent, useEffect, useRef } from "react"
import { Send, CornerDownLeft, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/app/components/ui/button"
import { ChatBubble, ChatBubbleMessage } from "@/app/components/ui/chat-bubble"
import { ChatInput } from "@/app/components/ui/chat-input"

interface Message {
  id: number
  content: string
  sender: "user" | "editor"
  timestamp: Date
  subject?: string
}

interface EditorMessage {
  trackingNumber: string
  subject: string
  message: string
}

interface MessageChatProps {
  paperData: {
    tracking_number: string
    original_filename: string
    email?: string
  }
  onSubmit: (data: EditorMessage) => Promise<void>
  position?: "bottom-right" | "bottom-left"
  size?: "sm" | "md" | "lg" | "xl" | "full"
  messageSuccess: boolean
  messageError: string | null
  isMessageSending: boolean
  threadEndpoint?: string
}

export default function MessageChat({
  paperData,
  onSubmit,
  messageSuccess,
  messageError,
  isMessageSending,
  threadEndpoint,
}: MessageChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [subject, setSubject] = useState("")
  const [messageContent, setMessageContent] = useState("")
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const toggleCollapse = () => setIsCollapsed(!isCollapsed)

  // Scroll to bottom when new messages are added
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  // Mesaj listesini yükle (endpoint varsa)
  useEffect(() => {
    const fetchMessages = async () => {
      if (!threadEndpoint) return

      setIsLoadingMessages(true)
      try {
        console.log("Mesajlar endpoint'e istek yapılıyor:", threadEndpoint);
        
        // Normal fetch ile deneme yapalım
        const response = await fetch(threadEndpoint, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        });
        
        console.log("Yanıt durumu:", response.status, response.statusText);
        
        if (!response.ok) {
          throw new Error(`HTTP Hata! Durum: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("Alınan veri:", data);

        // Gelen verileri uygun formata dönüştür
        if (data.messages && Array.isArray(data.messages)) {
          const formattedMessages = data.messages.map((msg: {
            id: number;
            message: string;
            is_from_author: boolean;
            created_at: string;
            subject?: string;
          }) => ({
            id: msg.id,
            content: msg.message,
            sender: msg.is_from_author ? "user" : "editor",
            timestamp: new Date(msg.created_at),
            subject: msg.subject,
          }))

          setMessages(formattedMessages)
          setTimeout(scrollToBottom, 100)
        }
      } catch (error) {
        console.error("Mesaj geçmişi yüklenirken hata:", error)
      } finally {
        setIsLoadingMessages(false)
      }
    }

    fetchMessages()
  }, [threadEndpoint])

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    if (!subject.trim() || !messageContent.trim()) {
      return
    }

    // Add new message with a more unique ID
    const newMessage: Message = {
      id: Date.now() + Math.floor(Math.random() * 1000000),
      content: messageContent,
      sender: "user",
      timestamp: new Date(),
      subject: subject,
    }

    setMessages((prev) => [...prev, newMessage])

    try {
      // Send message
      await onSubmit({
        trackingNumber: paperData.tracking_number,
        subject,
        message: messageContent,
      })

      // Clear message content after successful submission
      setMessageContent("")
      // Keep the subject for potential follow-up messages
    } catch (error) {
      console.error("Message sending error:", error)
    }
  }

  return (
    <div className="w-full border border-border rounded-lg shadow-sm overflow-hidden bg-white">
      <div className="flex items-center justify-between p-3 border-b border-border bg-background-secondary">
        <div className="flex flex-col">
          <h3 className="text-lg font-medium text-primary">Mesajlaşma Paneli</h3>
          <p className="text-xs text-muted-foreground">{paperData.tracking_number}</p>
        </div>
        <button
          onClick={toggleCollapse}
          className="rounded-full p-1.5 text-muted-foreground hover:bg-muted/80 hover:text-foreground transition-colors"
          aria-label={isCollapsed ? "Genişlet" : "Daralt"}
        >
          {isCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </button>
      </div>

      {!isCollapsed && (
        <>
          <div className="h-[350px] overflow-y-auto bg-white p-4">
            {messageSuccess && (
              <div className="flex items-center bg-status-success/10 border border-status-success/30 p-3 mb-4 rounded-md">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5 text-status-success mr-3 flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-status-success text-sm">
                  Mesajınız başarıyla gönderildi. Editör yanıtı burada görüntülenecektir.
                </p>
              </div>
            )}

            {messageError && (
              <div className="flex items-center bg-status-error/10 border border-status-error/30 p-3 mb-4 rounded-md">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5 text-status-error mr-3 flex-shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-status-error text-sm">{messageError}</p>
              </div>
            )}

            {isLoadingMessages ? (
              <div className="flex justify-center items-center h-32">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-center p-4">
                <div className="bg-accent/10 rounded-full p-3 mb-3">
                  <Send className="h-6 w-6 text-accent" />
                </div>
                <p className="text-muted-foreground">
                  Henüz mesaj yok. İlk mesajı göndermek için aşağıdaki formu kullanın.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <ChatBubble key={message.id} variant={message.sender === "user" ? "sent" : "received"}>
                    <ChatBubbleMessage
                      variant={message.sender === "user" ? "sent" : "received"}
                      className={
                        message.sender === "user"
                          ? "bg-accent text-white shadow-sm"
                          : "bg-background-secondary border border-border shadow-sm"
                      }
                    >
                      {message.subject && (
                        <div className="font-medium mb-1 border-b pb-1 border-white/10">{message.subject}</div>
                      )}
                      <div className="whitespace-pre-wrap">{message.content}</div>
                      <div className="text-[10px] text-right mt-1 opacity-70">
                        {message.timestamp.toLocaleTimeString("tr-TR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </ChatBubbleMessage>
                  </ChatBubble>
                ))}

                {isMessageSending && (
                  <ChatBubble variant="sent">
                    <ChatBubbleMessage isLoading variant="sent" className="bg-accent/80 shadow-sm" />
                  </ChatBubble>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          <div className="border-t border-border bg-white">
            <form onSubmit={handleSubmit} className="relative bg-white focus-within:ring-1 focus-within:ring-accent/30">
              <div className="p-3 border-b border-border">
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="Konu..."
                  className="w-full bg-transparent border-0 focus:ring-0 focus:outline-none p-0 placeholder:text-muted-foreground"
                  required
                  disabled={isMessageSending}
                />
              </div>

              <div className="p-3">
                <ChatInput
                  value={messageContent}
                  onChange={(e) => setMessageContent(e.target.value)}
                  placeholder="Mesajınızı yazın..."
                  className="min-h-[80px] resize-none bg-white border border-border rounded-md p-2 shadow-none focus-visible:ring-1 focus-visible:ring-accent focus-visible:border-accent"
                  required
                  disabled={isMessageSending}
                />
              </div>

              <div className="flex items-center p-3 pt-0 justify-between bg-white">
                <div className="text-xs text-muted-foreground">Enter tuşu ile gönder, Shift+Enter ile yeni satır</div>
                <Button
                  type="submit"
                  size="sm"
                  className="gap-1.5 bg-accent hover:bg-accent/90 text-white"
                  disabled={isMessageSending}
                >
                  {isMessageSending ? (
                    <>
                      <span className="mr-2 inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"></span>
                      Gönderiliyor...
                    </>
                  ) : (
                    <>
                      Gönder
                      <CornerDownLeft className="size-3.5" />
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </>
      )}
    </div>
  )
}

