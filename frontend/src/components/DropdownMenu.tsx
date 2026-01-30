import { useState, useRef, useEffect, type ReactNode } from "react"
import { MoreHorizontal } from "lucide-react"
import { cn } from "@/lib/utils"

interface DropdownMenuProps {
  children: ReactNode
  trigger?: ReactNode
}

export function DropdownMenu({ children, trigger }: DropdownMenuProps) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside)
    }
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [open])

  return (
    <div ref={menuRef} className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="p-1.5 rounded hover:bg-[hsl(var(--accent))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
      >
        {trigger ?? <MoreHorizontal className="w-4 h-4" />}
      </button>
      {open && (
        <div className="absolute right-0 mt-1 min-w-[140px] bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-md shadow-lg z-50 py-1 animate-in fade-in slide-in-from-top-1">
          {children}
        </div>
      )}
    </div>
  )
}

interface DropdownItemProps {
  onClick: () => void
  disabled?: boolean
  variant?: "default" | "danger"
  icon?: React.ElementType
  children: ReactNode
}

export function DropdownItem({
  onClick,
  disabled,
  variant = "default",
  icon: Icon,
  children,
}: DropdownItemProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left",
        "hover:bg-[hsl(var(--accent))] disabled:opacity-50 disabled:cursor-not-allowed",
        variant === "danger" && "text-red-600 dark:text-red-400"
      )}
    >
      {Icon && <Icon className="w-3.5 h-3.5" />}
      {children}
    </button>
  )
}

export function DropdownSeparator() {
  return <div className="my-1 border-t border-[hsl(var(--border))]" />
}
