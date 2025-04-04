"use client"

import React, { useState } from "react"
import { XIcon, ChevronDownIcon, ChevronUpIcon } from 'lucide-react'
import { cn } from "@/app/lib/utils"

type ExpandableChatSize = "sm" | "md" | "lg" | "xl" | "full"
type ExpandableChatPosition = "bottom-right" | "bottom-left"

interface ExpandableChatProps {
  children: React.ReactNode
  icon?: React.ReactNode
  size?: ExpandableChatSize
  position?: ExpandableChatPosition
  className?: string
}

interface ExpandableChatHeaderProps {
  children: React.ReactNode
  className?: string
}

interface ExpandableChatBodyProps {
  children: React.ReactNode
  className?: string
}

interface ExpandableChatFooterProps {
  children: React.ReactNode
  className?: string
}

const sizeMap: Record<ExpandableChatSize, string> = {
  sm: "w-80 h-96",
  md: "w-96 h-[450px]",
  lg: "w-[450px] h-[600px]",
  xl: "w-[550px] h-[650px]",
  full: "w-full h-full",
}

// Update the positionMap to ensure proper spacing and positioning
const positionMap: Record<ExpandableChatPosition, string> = {
  'bottom-right': 'right-4 bottom-4',
  'bottom-left': 'left-4 bottom-4'
};

// Update the ExpandableChat component to fix transparency and positioning issues
export function ExpandableChat({
  children,
  icon,
  size = 'md',
  position = 'bottom-right',
  className
}: ExpandableChatProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const toggleOpen = () => setIsOpen(!isOpen);
  const toggleCollapse = () => setIsCollapsed(!isCollapsed);

  return (
    <div className={cn("fixed z-50", positionMap[position], className)}>
      {isOpen ? (
        <div className={cn(
          "bg-background border border-border rounded-lg overflow-hidden shadow-lg flex flex-col",
          isCollapsed ? "h-12" : sizeMap[size]
        )}>
          <div className="flex items-center justify-between p-3 border-b border-border bg-muted">
            <div className="flex-1">
              {React.Children.map(children, child => {
                if (React.isValidElement(child) && child.type === ExpandableChatHeader) {
                  return child;
                }
                return null;
              })}
            </div>
            <div className="flex gap-1">
              <button 
                onClick={toggleCollapse} 
                className="rounded p-1 text-muted-foreground hover:bg-muted/80 hover:text-foreground transition-colors"
              >
                {isCollapsed ? (
                  <ChevronUpIcon className="h-4 w-4" />
                ) : (
                  <ChevronDownIcon className="h-4 w-4" />
                )}
              </button>
              <button 
                onClick={toggleOpen} 
                className="rounded p-1 text-muted-foreground hover:bg-muted/80 hover:text-foreground transition-colors"
              >
                <XIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
          
          {!isCollapsed && (
            <>
              <div className="flex-1 overflow-y-auto bg-background">
                {React.Children.map(children, child => {
                  if (React.isValidElement(child) && child.type === ExpandableChatBody) {
                    return child;
                  }
                  return null;
                })}
              </div>
              <div className="border-t border-border bg-background">
                {React.Children.map(children, child => {
                  if (React.isValidElement(child) && child.type === ExpandableChatFooter) {
                    return child;
                  }
                  return null;
                })}
              </div>
            </>
          )}
        </div>
      ) : (
        <button
          onClick={toggleOpen}
          className="flex items-center justify-center h-12 w-12 rounded-full bg-primary text-primary-foreground shadow-md hover:bg-primary/90 transition-colors"
        >
          {icon || <ChatIcon className="h-6 w-6" />}
        </button>
      )}
    </div>
  );
}

export function ExpandableChatHeader({ children, className }: ExpandableChatHeaderProps) {
  return <div className={cn("text-sm font-medium", className)}>{children}</div>
}

export function ExpandableChatBody({ children, className }: ExpandableChatBodyProps) {
  return <div className={cn("p-3", className)}>{children}</div>
}

export function ExpandableChatFooter({ children, className }: ExpandableChatFooterProps) {
  return <div className={cn("", className)}>{children}</div>
}

function ChatIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  )
}
