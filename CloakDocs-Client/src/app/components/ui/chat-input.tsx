"use client"

import React, { useEffect, useRef } from "react"
import { cn } from "@/app/lib/utils"

export type ChatInputProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>

export const ChatInput = React.forwardRef<HTMLTextAreaElement, ChatInputProps>(
  ({ className, onChange, ...props }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement | null>(null)

    // Auto-resize textarea based on content
    const adjustTextareaHeight = () => {
      const textarea = textareaRef.current
      if (textarea) {
        textarea.style.height = "auto"
        textarea.style.height = `${Math.min(textarea.scrollHeight, 300)}px`
      }
    }

    // Handle changes and adjust textarea height
    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onChange?.(e)
      adjustTextareaHeight()
    }

    // Handle key combinations
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Send with Enter (unless Shift is pressed for new line)
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        const form = textareaRef.current?.closest("form")
        if (form) {
          form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }))
        }
      }
    }

    // Adjust textarea height on mount and when value changes
    useEffect(() => {
      adjustTextareaHeight()
    }, [props.value])

    return (
      <textarea
        ref={(node) => {
          // Merge refs
          if (typeof ref === "function") ref(node)
          else if (ref) ref.current = node
          textareaRef.current = node
        }}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        className={cn(
          "flex w-full rounded-md bg-background text-sm resize-none placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        rows={1}
        {...props}
      />
    )
  },
)

ChatInput.displayName = "ChatInput"

