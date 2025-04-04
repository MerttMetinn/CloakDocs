"use client"

import { useState, type FormEvent } from "react"
import { CornerDownLeft, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/app/components/ui/button"
import { ChatInput } from "@/app/components/ui/chat-input"
import { ChatBubble, ChatBubbleMessage } from "@/app/components/ui/chat-bubble"
import { ChatMessageList } from "@/app/components/ui/chat-message-list"

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

interface StandaloneChatProps {
  paperData: {
    tracking_number: string
    original_filename: string
  }
  onSubmit: (data: EditorMessage) => Promise<void>
  messageSuccess: boolean
  messageError: string | null
  isMessageSending: boolean
}

export default function StandaloneChat({
  paperData,
  onSubmit,
  messageSuccess,
  messageError,
  isMessageSending,
}: StandaloneChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [subject, setSubject] = useState("")
  const [messageContent, setMessageContent] = useState("")
  const [isCollapsed, setIsCollapsed] = useState(false)

  const toggleCollapse = () => setIsCollapsed(!isCollapsed)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    if (!subject.trim() || !messageContent.trim()) {
      return
    }

    // Add new message
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

      // Clear form fields after successful submission
      setMessageContent("")
    } catch (error) {
      console.error("Message sending error:", error)
    }
  }

  return (
    <div className="w-full h-[500px] border border-border rounded-lg shadow-md flex flex-col bg-white overflow-hidden">
      <div className="flex items-center justify-between p-3 border-b border-border bg-muted">
        <div className="flex flex-col">
          <h3 className="text-xl font-semibold">Editör İle Yazışma</h3>
          <p className="text-sm text-muted-foreground">
            {paperData.tracking_number} - {paperData.original_filename}
          </p>
        </div>
        <div className="flex gap-1">
          <button
            onClick={toggleCollapse}
            className="rounded p-1 text-muted-foreground hover:bg-muted/80 hover:text-foreground transition-colors"
          >
            {isCollapsed ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          <div className="flex-1 overflow-y-auto bg-white">
            {messageSuccess && (
              <div className="flex items-center bg-green-100 border border-green-500 p-3 m-3 rounded">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5 text-green-600 mr-3"
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
                <p className="text-green-700">
                  Mesajınız başarıyla gönderildi. Editör yanıtı burada görüntülenecektir.
                </p>
              </div>
            )}

            {messageError && (
              <div className="flex items-center bg-red-100 border border-red-500 p-3 m-3 rounded">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5 text-red-600 mr-3"
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
                <p className="text-red-700">{messageError}</p>
              </div>
            )}

            <ChatMessageList className="px-3 py-2 bg-white">
              {messages.map((message) => (
                <ChatBubble key={message.id} variant={message.sender === "user" ? "sent" : "received"}>
                  <ChatBubbleMessage
                    variant={message.sender === "user" ? "sent" : "received"}
                    className={
                      message.sender === "user" ? "bg-primary shadow-sm" : "bg-muted border border-border shadow-sm"
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
                  <ChatBubbleMessage isLoading variant="sent" className="bg-primary/90 shadow-sm" />
                </ChatBubble>
              )}
            </ChatMessageList>
          </div>

          <div className="border-t border-border bg-white">
            <form
              onSubmit={handleSubmit}
              className="relative bg-white shadow-md focus-within:ring-1 focus-within:ring-primary/30"
            >
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

              <ChatInput
                value={messageContent}
                onChange={(e) => setMessageContent(e.target.value)}
                placeholder="Mesajınızı yazın..."
                className="min-h-14 resize-none bg-white border-0 p-3 shadow-none focus-visible:ring-0 focus:outline-none"
                required
                disabled={isMessageSending}
              />

              <div className="flex items-center p-3 pt-2 justify-end bg-white">
                <Button type="submit" size="sm" className="gap-1.5" disabled={isMessageSending}>
                  {isMessageSending ? "Gönderiliyor..." : "Mesaj Gönder"}
                  <CornerDownLeft className="size-3.5" />
                </Button>
              </div>
            </form>
          </div>
        </>
      )}
    </div>
  )
}

