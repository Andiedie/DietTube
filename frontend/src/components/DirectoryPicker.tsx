import { useState, useEffect } from "react"
import { Folder, FolderOpen, ChevronUp, Loader2 } from "lucide-react"
import { Dialog, DialogButton } from "./Dialog"
import { api } from "@/lib/api"

interface DirectoryPickerProps {
  open: boolean
  onClose: () => void
  onSelect: (path: string) => void
  initialPath?: string
  title?: string
}

export function DirectoryPicker({
  open,
  onClose,
  onSelect,
  initialPath = "/",
  title = "选择目录",
}: DirectoryPickerProps) {
  const [currentPath, setCurrentPath] = useState(initialPath)
  const [parentPath, setParentPath] = useState<string | null>(null)
  const [entries, setEntries] = useState<{ name: string; path: string }[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setCurrentPath(initialPath || "/")
    }
  }, [open, initialPath])

  useEffect(() => {
    if (!open) return

    const loadDirectory = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.filesystem.browse(currentPath)
        setCurrentPath(data.current_path)
        setParentPath(data.parent_path)
        setEntries(data.entries.filter((e) => e.is_dir))
      } catch {
        setError("无法加载目录")
      } finally {
        setLoading(false)
      }
    }

    loadDirectory()
  }, [open, currentPath])

  const handleSelect = () => {
    onSelect(currentPath)
    onClose()
  }

  const handleNavigate = (path: string) => {
    setCurrentPath(path)
  }

  const handleGoUp = () => {
    if (parentPath) {
      setCurrentPath(parentPath)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={title}>
      <div className="space-y-3">
        <div className="flex items-center gap-2 p-2 bg-[hsl(var(--muted))] rounded text-sm font-mono overflow-hidden">
          <Folder className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">{currentPath}</span>
        </div>

        <div className="border border-[hsl(var(--border))] rounded-lg max-h-64 overflow-y-auto">
          {parentPath && (
            <button
              onClick={handleGoUp}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[hsl(var(--accent))] text-left border-b border-[hsl(var(--border))]"
            >
              <ChevronUp className="w-4 h-4" />
              <span className="text-[hsl(var(--muted-foreground))]">..</span>
            </button>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-[hsl(var(--muted-foreground))]" />
            </div>
          ) : error ? (
            <div className="py-4 text-center text-red-500 text-sm">{error}</div>
          ) : entries.length === 0 ? (
            <div className="py-4 text-center text-[hsl(var(--muted-foreground))] text-sm">
              无子目录
            </div>
          ) : (
            entries.map((entry) => (
              <button
                key={entry.path}
                onClick={() => handleNavigate(entry.path)}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[hsl(var(--accent))] text-left"
              >
                <FolderOpen className="w-4 h-4 text-[hsl(var(--primary))]" />
                <span className="truncate">{entry.name}</span>
              </button>
            ))
          )}
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <DialogButton onClick={onClose}>取消</DialogButton>
          <DialogButton variant="primary" onClick={handleSelect}>
            选择此目录
          </DialogButton>
        </div>
      </div>
    </Dialog>
  )
}
