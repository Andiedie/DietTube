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
} from "lucide-react"
import { api, type Task, type TaskProgress } from "@/lib/api"
import { formatBytes, formatDuration, cn } from "@/lib/utils"

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
  return (
    <div className="w-full">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-[hsl(var(--muted-foreground))]">{status}</span>
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
          Processing Task #{progress.task_id}
        </h3>
        <div className="flex items-center space-x-4 text-sm text-[hsl(var(--muted-foreground))]">
          <span>FPS: {progress.fps.toFixed(1)}</span>
          <span>Speed: {progress.speed.toFixed(2)}x</span>
          <span>ETA: {formatDuration(progress.eta_seconds)}</span>
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
      label: "Pending",
    },
    transcoding: {
      icon: Loader2,
      className: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
      label: "Transcoding",
    },
    verifying: {
      icon: Search,
      className: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
      label: "Verifying",
    },
    installing: {
      icon: RefreshCw,
      className: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
      label: "Installing",
    },
    completed: {
      icon: CheckCircle2,
      className: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      label: "Completed",
    },
    failed: {
      icon: XCircle,
      className: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
      label: "Failed",
    },
    cancelled: {
      icon: XCircle,
      className: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
      label: "Cancelled",
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

function TaskRow({ task }: { task: Task }) {
  const queryClient = useQueryClient()
  const retryMutation = useMutation({
    mutationFn: () => api.tasks.retry(task.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
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
          <span className="text-green-600 dark:text-green-400">
            {formatBytes(task.new_size)}
            <span className="text-xs ml-1">(-{savedPercent.toFixed(1)}%)</span>
          </span>
        ) : (
          "-"
        )}
      </td>
      <td className="px-4 py-3 text-sm">
        {task.status === "failed" || task.status === "cancelled" ? (
          <button
            onClick={() => retryMutation.mutate()}
            disabled={retryMutation.isPending}
            className="flex items-center text-[hsl(var(--primary))] hover:underline disabled:opacity-50"
          >
            <RotateCcw className="w-3 h-3 mr-1" />
            Retry
          </button>
        ) : null}
        {task.error_message && (
          <span
            className="text-red-500 text-xs truncate max-w-[200px] block"
            title={task.error_message}
          >
            {task.error_message}
          </span>
        )}
      </td>
    </tr>
  )
}

export default function Dashboard() {
  const queryClient = useQueryClient()

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
    queryKey: ["tasks"],
    queryFn: () => api.tasks.list(undefined, 20),
  })

  const scanMutation = useMutation({
    mutationFn: api.tasks.scan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      queryClient.invalidateQueries({ queryKey: ["stats"] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
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
          Scan for Videos
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Space Saved"
          value={formatBytes(stats?.total_saved_bytes || 0)}
          icon={HardDrive}
          description={`${stats?.total_processed_files || 0} files processed`}
        />
        <StatCard
          title="Pending"
          value={String(stats?.pending_count || 0)}
          icon={Clock}
        />
        <StatCard
          title="Completed"
          value={String(stats?.completed_count || 0)}
          icon={CheckCircle2}
        />
        <StatCard
          title="Failed"
          value={String(stats?.failed_count || 0)}
          icon={AlertCircle}
        />
      </div>

      {progress && <CurrentProgress progress={progress} />}

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-[hsl(var(--border))]">
          <h3 className="font-semibold flex items-center">
            <FileVideo className="w-4 h-4 mr-2" />
            Task Queue
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[hsl(var(--muted))]">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  File
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  Status
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  Original
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  New Size
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {tasksData?.tasks.map((task) => (
                <TaskRow key={task.id} task={task} />
              ))}
              {(!tasksData || tasksData.tasks.length === 0) && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-[hsl(var(--muted-foreground))]"
                  >
                    No tasks yet. Click "Scan for Videos" to find files.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
