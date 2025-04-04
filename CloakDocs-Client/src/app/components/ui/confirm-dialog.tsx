"use client"

import * as Dialog from '@radix-ui/react-dialog'
import { Button } from '@/app/components/ui/button'

export interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  title: string
  description: string
  confirmText?: string
  cancelText?: string
}

export default function ConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  confirmText = "Onayla",
  cancelText = "İptal"
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Dialog.Content className="fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
          <Dialog.Title className="text-lg font-medium text-gray-900">
            {title}
          </Dialog.Title>
          <Dialog.Description className="text-sm text-gray-600 mt-2">
            <span dangerouslySetInnerHTML={{ __html: description }} />
          </Dialog.Description>

          <div className="mt-6 flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {cancelText}
            </Button>
            <Button onClick={() => {
              onConfirm()
              onOpenChange(false)
            }}>
              {confirmText}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}