import { type ReactNode } from "react"
import { X } from "lucide-react"

interface DialogProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}

export function Dialog({ open, onClose, title, children }: DialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      <div className="relative bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg shadow-xl max-w-md w-full mx-4 animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))]">
          <h3 className="font-semibold">{title}</h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[hsl(var(--accent))]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  )
}

interface DialogButtonProps {
  onClick: () => void
  variant?: "primary" | "secondary" | "danger"
  disabled?: boolean
  children: ReactNode
}

export function DialogButton({
  onClick,
  variant = "secondary",
  disabled,
  children,
}: DialogButtonProps) {
  const styles = {
    primary:
      "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90",
    secondary:
      "bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))] hover:bg-[hsl(var(--accent))]",
    danger: "bg-red-600 text-white hover:bg-red-700",
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 rounded-md font-medium disabled:opacity-50 ${styles[variant]}`}
    >
      {children}
    </button>
  )
}
