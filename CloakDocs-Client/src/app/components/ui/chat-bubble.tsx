"use client"

import type React from "react"
import { cn } from "@/app/lib/utils"

interface ChatBubbleProps {
  variant?: "sent" | "received"
  className?: string
  children: React.ReactNode
}

interface ChatBubbleAvatarProps {
  className?: string
  children: React.ReactNode
}

interface ChatBubbleMessageProps {
  variant?: "sent" | "received"
  className?: string
  children?: React.ReactNode
  isLoading?: boolean
}

export function ChatBubble({ variant = "received", className, children, ...props }: ChatBubbleProps) {
  return (
    <div
      className={cn("flex items-end gap-2 mb-4", variant === "sent" ? "justify-end" : "justify-start", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export function ChatBubbleAvatar({ className, children, ...props }: ChatBubbleAvatarProps) {
  return (
    <div
      className={cn(
        "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full bg-background-secondary",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function ChatBubbleMessage({
  variant = "received",
  className,
  children,
  isLoading = false,
  ...props
}: ChatBubbleMessageProps) {
  return (
    <div
      className={cn(
        "rounded-lg px-4 py-3 max-w-[85%] text-sm",
        variant === "sent"
          ? "bg-accent text-white rounded-tr-none"
          : "bg-background-secondary text-foreground rounded-tl-none",
        className,
      )}
      {...props}
    >
      {isLoading ? (
        <div className="flex gap-1 items-center justify-center">
          <div className="h-2 w-2 bg-current rounded-full animate-bounce [animation-delay:-0.3s] opacity-70"></div>
          <div className="h-2 w-2 bg-current rounded-full animate-bounce [animation-delay:-0.15s] opacity-80"></div>
          <div className="h-2 w-2 bg-current rounded-full animate-bounce opacity-90"></div>
        </div>
      ) : (
        children
      )}
    </div>
  )
}

