"use client"

import React, { useEffect, useRef } from "react"
import { cn } from "@/app/lib/utils"

export interface ChatMessageListProps extends React.HTMLAttributes<HTMLDivElement> {
  scrollBehavior?: ScrollBehavior
  scrollToBottom?: boolean
}

export const ChatMessageList = React.forwardRef<HTMLDivElement, ChatMessageListProps>(
  ({ className, scrollBehavior = "smooth", scrollToBottom = true, ...props }, ref) => {
    const innerRef = useRef<HTMLDivElement>(null)

    const scrollToBottomFunc = () => {
      if (innerRef.current && scrollToBottom) {
        const lastMessage = innerRef.current.lastElementChild
        lastMessage?.scrollIntoView({
          behavior: scrollBehavior,
          block: "end",
        })
      }
    }

    // Auto-scroll when new messages are added
    useEffect(() => {
      scrollToBottomFunc()
    }, [props.children])

    return (
      <div
        ref={(node) => {
          if (typeof ref === "function") ref(node)
          else if (ref) ref.current = node
          innerRef.current = node
        }}
        className={cn("flex h-full w-full flex-col overflow-y-auto overscroll-none", className)}
        {...props}
      />
    )
  },
)

ChatMessageList.displayName = "ChatMessageList"

