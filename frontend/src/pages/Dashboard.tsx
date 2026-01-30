import { useState, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  HardDrive,
  FileVideo,
  Clock,
  AlertCircle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Search,
  XCircle,
  RotateCcw,
  Pause,
  Play,
  ChevronLeft,
  ChevronRight,
  Undo2,
  FileText,
} from "lucide-react"
import { api, type Task, type TaskProgress, type TaskLog, ApiRequestError } from "@/lib/api"
import { formatBytes, formatDuration, cn } from "@/lib/utils"
import { useToast } from "@/components/Toast"
import { Dialog, DialogButton } from "@/components/Dialog"

function StatCard({
  title,
  value,
  icon: Icon,
  description,
}: {
  title: string
  value: string
  icon: React.ElementType
  description?: string
}) {
  return (
    <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {description && (
            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
              {description}
            </p>
          )}
        </div>
        <Icon className="w-8 h-8 text-[hsl(var(--primary))]" />
      </div>
    </div>
  )
}

function ProgressBar({ progress, status }: { progress: number; status: string }) {
  const statusLabels: Record<string, string> = {
    transcoding: "转码中",
    verifying: "校验中",
    installing: "安装中",
  }
  return (
    <div className="w-full">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-[hsl(var(--muted-foreground))]">
          {statusLabels[status] || status}
        </span>
        <span className="font-medium">{(progress * 100).toFixed(1)}%</span>
      </div>
      <div className="w-full bg-[hsl(var(--secondary))] rounded-full h-2">
        <div
          className="bg-[hsl(var(--primary))] h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress * 100}%` }}
        />
      </div>
    </div>
  )
}

function CurrentProgress({ progress }: { progress: TaskProgress }) {
  return (
    <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold flex items-center">
          <Loader2 className="w-4 h-4 mr-2 animate-spin text-[hsl(var(--primary))]" />
          正在处理任务 #{progress.task_id}
        </h3>
        <div className="flex items-center space-x-4 text-sm text-[hsl(var(--muted-foreground))]">
          <span>FPS: {progress.fps.toFixed(1)}</span>
          <span>速度: {progress.speed.toFixed(2)}x</span>
          <span>剩余: {formatDuration(progress.eta_seconds)}</span>
        </div>
      </div>
      <ProgressBar progress={progress.progress} status={progress.status} />
    </div>
  )
}

function TaskStatusBadge({ status }: { status: string }) {
  const statusConfig: Record<
    string,
    { icon: React.ElementType; className: string; label: string }
  > = {
    pending: {
      icon: Clock,
      className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
      label: "等待中",
    },
    transcoding: {
      icon: Loader2,
      className: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
      label: "转码中",
    },
    verifying: {
      icon: Search,
      className: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
      label: "校验中",
    },
    installing: {
      icon: RefreshCw,
      className: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
      label: "安装中",
    },
    completed: {
      icon: CheckCircle2,
      className: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      label: "已完成",
    },
    failed: {
      icon: XCircle,
      className: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
      label: "失败",
    },
    cancelled: {
      icon: XCircle,
      className: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
      label: "已取消",
    },
    rolled_back: {
      icon: Undo2,
      className: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
      label: "已回滚",
    },
  }

  const config = statusConfig[status] || statusConfig.pending
  const Icon = config.icon

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium",
        config.className
      )}
    >
      <Icon
        className={cn("w-3 h-3 mr-1", status === "transcoding" && "animate-spin")}
      />
      {config.label}
    </span>
  )
}

function TaskRow({ task, onError, onSuccess }: { task: Task; onError: (msg: string) => void; onSuccess: (msg: string) => void }) {
  const queryClient = useQueryClient()
  const [showRollbackDialog, setShowRollbackDialog] = useState(false)
  const [showLogsDialog, setShowLogsDialog] = useState(false)
  const [logs, setLogs] = useState<TaskLog[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const logsContainerRef = useRef<HTMLDivElement | null>(null)

  // 清理 SSE 连接
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  // 自动滚动到底部
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }, [logs])

  const handleShowLogs = async () => {
    setShowLogsDialog(true)
    setLogsLoading(true)
    try {
      // 先获取历史日志
      const result = await api.tasks.getLogs(task.id)
      setLogs(result.logs)

      // 如果任务正在进行中，订阅实时日志
      const isActive = ["transcoding", "verifying", "installing"].includes(task.status)
      if (isActive) {
        // 关闭旧连接
        if (eventSourceRef.current) {
          eventSourceRef.current.close()
        }
        // 建立 SSE 连接
        const es = new EventSource(`/api/tasks/${task.id}/logs/stream`)
        eventSourceRef.current = es

        es.onmessage = (event) => {
          try {
            const newLog = JSON.parse(event.data) as TaskLog
            setLogs((prev) => [...prev, newLog])
          } catch {
            // 忽略解析错误
          }
        }

        es.onerror = () => {
          es.close()
        }
      }
    } catch (error) {
      const message = error instanceof ApiRequestError ? error.message : "获取日志失败"
      onError(message)
    } finally {
      setLogsLoading(false)
    }
  }

  const handleCloseLogsDialog = () => {
    setShowLogsDialog(false)
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }

  const retryMutation = useMutation({
    mutationFn: () => api.tasks.retry(task.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
    onError: (error) => {
      const message = error instanceof ApiRequestError ? error.message : "重试失败"
      onError(message)
    },
  })

  const rollbackMutation = useMutation({
    mutationFn: () => api.tasks.rollback(task.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      queryClient.invalidateQueries({ queryKey: ["stats"] })
      setShowRollbackDialog(false)
      onSuccess("已回滚，原始文件已恢复")
    },
    onError: (error) => {
      const message = error instanceof ApiRequestError ? error.message : "回滚失败"
      setShowRollbackDialog(false)
      onError(message)
    },
  })

  const savedBytes = task.new_size > 0 ? task.original_size - task.new_size : 0
  const savedPercent =
    task.original_size > 0 ? (savedBytes / task.original_size) * 100 : 0

  return (
    <tr className="border-b border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))/50]">
      <td className="px-4 py-3 text-sm max-w-md truncate" title={task.relative_path}>
        {task.relative_path}
      </td>
      <td className="px-4 py-3">
        <TaskStatusBadge status={task.status} />
      </td>
      <td className="px-4 py-3 text-sm text-right">
        {formatBytes(task.original_size)}
      </td>
      <td className="px-4 py-3 text-sm text-right">
        {task.new_size > 0 ? (
          <span className={savedPercent >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
            {formatBytes(task.new_size)}
            <span className="text-xs ml-1">
              ({savedPercent >= 0 ? "-" : "+"}{Math.abs(savedPercent).toFixed(1)}%)
            </span>
          </span>
        ) : (
          "-"
        )}
      </td>
      <td className="px-4 py-3 text-sm">
        <div className="flex items-center gap-2">
          {task.status !== "pending" && (
            <button
              onClick={handleShowLogs}
              className="flex items-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:underline"
              title="查看日志"
            >
              <FileText className="w-3 h-3 mr-1" />
              日志
            </button>
          )}
          {(task.status === "failed" || task.status === "cancelled" || task.status === "rolled_back") ? (
            <button
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              className="flex items-center text-[hsl(var(--primary))] hover:underline disabled:opacity-50"
            >
              <RotateCcw className="w-3 h-3 mr-1" />
              重试
            </button>
          ) : null}
          {task.status === "completed" ? (
            <button
              onClick={() => setShowRollbackDialog(true)}
              disabled={rollbackMutation.isPending}
              className="flex items-center text-orange-600 dark:text-orange-400 hover:underline disabled:opacity-50"
            >
              <Undo2 className="w-3 h-3 mr-1" />
              回滚
            </button>
          ) : null}
        </div>
        {task.error_message && (
          <span
            className="text-red-500 text-xs truncate max-w-[200px] block mt-1"
            title={task.error_message}
          >
            {task.error_message}
          </span>
        )}

        <Dialog
          open={showLogsDialog}
          onClose={handleCloseLogsDialog}
          title={`任务日志 - ${task.relative_path}`}
        >
          <div ref={logsContainerRef} className="max-h-96 overflow-y-auto">
            {logsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--muted-foreground))]" />
              </div>
            ) : logs.length === 0 ? (
              <p className="text-center text-[hsl(var(--muted-foreground))] py-8">
                暂无日志
              </p>
            ) : (
              <div className="font-mono text-xs">
                {logs.map((log) => (
                  <div
                    key={log.id}
                    className={cn(
                      "px-2 py-0.5",
                      log.level === "error" && "bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200",
                      log.level === "warning" && "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200",
                      log.level === "info" && "text-[hsl(var(--foreground))]"
                    )}
                  >
                    <span className="text-[hsl(var(--muted-foreground))] mr-2">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </span>
                    {log.message}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex justify-end pt-4">
            <DialogButton variant="secondary" onClick={handleCloseLogsDialog}>
              关闭
            </DialogButton>
          </div>
        </Dialog>

        <Dialog
          open={showRollbackDialog}
          onClose={() => setShowRollbackDialog(false)}
          title="确认回滚"
        >
          <div className="space-y-4">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              回滚将执行以下操作：
            </p>
            <ul className="text-sm space-y-2 list-disc list-inside text-[hsl(var(--foreground))]">
              <li>删除当前的转码文件</li>
              <li>从回收站/归档目录恢复原始文件</li>
              <li>统计数据中减去此任务节省的空间</li>
            </ul>
            <p className="text-sm font-medium text-[hsl(var(--foreground))]">
              文件：{task.relative_path}
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <DialogButton variant="secondary" onClick={() => setShowRollbackDialog(false)}>
                取消
              </DialogButton>
              <DialogButton
                variant="danger"
                onClick={() => rollbackMutation.mutate()}
                disabled={rollbackMutation.isPending}
              >
                {rollbackMutation.isPending ? "回滚中..." : "确认回滚"}
              </DialogButton>
            </div>
          </div>
        </Dialog>
      </td>
    </tr>
  )
}

export default function Dashboard() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()
  const [showPauseDialog, setShowPauseDialog] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [currentPage, setCurrentPage] = useState(0)
  const [pageSize, setPageSize] = useState(20)

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: api.tasks.getStats,
  })

  const { data: progress } = useQuery({
    queryKey: ["progress"],
    queryFn: api.tasks.getProgress,
    refetchInterval: 1000,
  })

  const { data: tasksData } = useQuery({
    queryKey: ["tasks", searchQuery, currentPage, pageSize],
    queryFn: () => api.tasks.list({
      search: searchQuery || undefined,
      limit: pageSize,
      offset: currentPage * pageSize,
    }),
  })

  const { data: queueStatus } = useQuery({
    queryKey: ["queueStatus"],
    queryFn: api.tasks.getQueueStatus,
  })

  const scanMutation = useMutation({\n    mutationFn: api.tasks.scan,\n    onSuccess: (data) => {\n      queryClient.invalidateQueries({ queryKey: [\"tasks\"] })\n      queryClient.invalidateQueries({ queryKey: [\"stats\"] })\n      addToast(data.message, \"success\")\n    },\n    onError: (error) => {\n      const message = error instanceof ApiRequestError ? error.message : \"扫描失败\"\n      addToast(message, \"error\")\n    },\n  })

  const pauseMutation = useMutation({
    mutationFn: (immediate: boolean) => api.tasks.pauseQueue(immediate),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["queueStatus"] })
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      setShowPauseDialog(false)
      addToast(data.interrupted ? "队列已暂停，当前任务已中断" : "队列已暂停", "info")
    },
    onError: (error) => {
      const message = error instanceof ApiRequestError ? error.message : "暂停失败"
      addToast(message, "error")
    },
  })

  const resumeMutation = useMutation({
    mutationFn: api.tasks.resumeQueue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queueStatus"] })
      addToast("队列已继续", "success")
    },
    onError: (error) => {
      const message = error instanceof ApiRequestError ? error.message : "继续失败"
      addToast(message, "error")
    },
  })

  const isPaused = queueStatus?.is_paused ?? false
  const hasActiveTask = queueStatus?.has_active_task ?? false

  const handlePauseClick = () => {
    if (hasActiveTask) {
      setShowPauseDialog(true)
    } else {
      pauseMutation.mutate(false)
    }
  }

  return (
    <div className="space-y-6">
      <Dialog
        open={showPauseDialog}
        onClose={() => setShowPauseDialog(false)}
        title="暂停队列"
      >
        <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
          当前有任务正在转码中，请选择暂停方式：
        </p>
        <div className="space-y-2">
          <button
            onClick={() => pauseMutation.mutate(false)}
            disabled={pauseMutation.isPending}
            className="w-full text-left px-4 py-3 rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))] disabled:opacity-50"
          >
            <p className="font-medium">完成后暂停</p>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              等待当前任务完成后暂停队列
            </p>
          </button>
          <button
            onClick={() => pauseMutation.mutate(true)}
            disabled={pauseMutation.isPending}
            className="w-full text-left px-4 py-3 rounded-lg border border-red-300 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50"
          >
            <p className="font-medium text-red-600 dark:text-red-400">立即中断</p>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              中断当前任务并暂停队列（任务将标记为失败）
            </p>
          </button>
        </div>
        <div className="mt-4 flex justify-end">
          <DialogButton onClick={() => setShowPauseDialog(false)}>
            取消
          </DialogButton>
        </div>
      </Dialog>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">仪表盘</h1>
        <div className="flex items-center gap-2">
          {isPaused ? (
            <button
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {resumeMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              继续队列
            </button>
          ) : (
            <button
              onClick={handlePauseClick}
              disabled={pauseMutation.isPending}
              className="flex items-center px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50"
            >
              {pauseMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Pause className="w-4 h-4 mr-2" />
              )}
              暂停队列
            </button>
          )}
          <button
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
            className="flex items-center px-4 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md hover:opacity-90 disabled:opacity-50"
          >
            {scanMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Search className="w-4 h-4 mr-2" />
            )}
            扫描视频
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="已节省空间"
          value={formatBytes(stats?.total_saved_bytes || 0)}
          icon={HardDrive}
          description={`已处理 ${stats?.total_processed_files || 0} 个文件`}
        />
        <StatCard
          title="等待中"
          value={String(stats?.pending_count || 0)}
          icon={Clock}
        />
        <StatCard
          title="已完成"
          value={String(stats?.completed_count || 0)}
          icon={CheckCircle2}
        />
        <StatCard
          title="失败"
          value={String(stats?.failed_count || 0)}
          icon={AlertCircle}
        />
      </div>

      {progress && <CurrentProgress progress={progress} />}

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-[hsl(var(--border))] flex items-center justify-between">
          <h3 className="font-semibold flex items-center">
            <FileVideo className="w-4 h-4 mr-2" />
            任务队列
            {tasksData && (
              <span className="ml-2 text-sm font-normal text-[hsl(var(--muted-foreground))]">
                (共 {tasksData.total} 个)
              </span>
            )}
          </h3>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--muted-foreground))]" />
              <input
                type="text"
                placeholder="搜索文件名..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setCurrentPage(0)
                }}
                className="pl-9 pr-3 py-1.5 w-48 text-sm rounded border border-[hsl(var(--border))] bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
              />
            </div>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setCurrentPage(0)
              }}
              className="px-2 py-1.5 text-sm rounded border border-[hsl(var(--border))] bg-[hsl(var(--background))]"
            >
              <option value={10}>10 条/页</option>
              <option value={20}>20 条/页</option>
              <option value={50}>50 条/页</option>
              <option value={100}>100 条/页</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[hsl(var(--muted))]">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  文件
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  状态
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  原始大小
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  新大小
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              {tasksData?.tasks.map((task) => (
                <TaskRow key={task.id} task={task} onError={(msg) => addToast(msg, "error")} onSuccess={(msg) => addToast(msg, "success")} />
              ))}
              {(!tasksData || tasksData.tasks.length === 0) && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-[hsl(var(--muted-foreground))]"
                  >
                    {searchQuery ? "没有匹配的任务" : "暂无任务，点击「扫描视频」查找文件"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {tasksData && tasksData.total > pageSize && (
          <div className="px-4 py-3 border-t border-[hsl(var(--border))] flex items-center justify-between">
            <span className="text-sm text-[hsl(var(--muted-foreground))]">
              显示 {currentPage * pageSize + 1}-{Math.min((currentPage + 1) * pageSize, tasksData.total)} / {tasksData.total}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
                disabled={currentPage === 0}
                className="p-1.5 rounded border border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))] disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm px-2">
                {currentPage + 1} / {Math.ceil(tasksData.total / pageSize)}
              </span>
              <button
                onClick={() => setCurrentPage((p) => p + 1)}
                disabled={(currentPage + 1) * pageSize >= tasksData.total}
                className="p-1.5 rounded border border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))] disabled:opacity-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
