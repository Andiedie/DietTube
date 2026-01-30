const API_BASE = "/api"

export interface ApiError {
  code: string
  message: string
  details: Record<string, unknown>
}

export class ApiRequestError extends Error {
  code: string
  details: Record<string, unknown>

  constructor(error: ApiError) {
    super(error.message)
    this.name = "ApiRequestError"
    this.code = error.code
    this.details = error.details
  }
}

export interface Task {
  id: number
  source_path: string
  relative_path: string
  status: string
  original_size: number
  new_size: number
  original_duration: number
  new_duration: number
  error_message: string | null
}

export interface TaskProgress {
  task_id: number
  fps: number
  speed: number
  progress: number
  eta_seconds: number
  status: string
}

export interface Stats {
  total_saved_bytes: number
  total_processed_files: number
  pending_count: number
  in_progress_count: number
  completed_count: number
  failed_count: number
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
}

export interface Settings {
  video_preset: number
  video_crf: number
  video_film_grain: number
  audio_bitrate: string
  max_threads: number
  original_file_strategy: string
  archive_dir: string
  source_dir: string
  temp_dir: string
  config_dir: string
  max_long_side: number
  max_short_side: number
  max_fps: number
  min_bitrate_mbps: number
  start_paused: boolean
  scan_ignore_patterns: string
}

export interface SettingsUpdate {
  source_dir?: string
  temp_dir?: string
  config_dir?: string
  video_preset?: number
  video_crf?: number
  video_film_grain?: number
  audio_bitrate?: string
  max_threads?: number
  original_file_strategy?: string
  archive_dir?: string
  max_long_side?: number
  max_short_side?: number
  max_fps?: number
  min_bitrate_mbps?: number
  start_paused?: boolean
  scan_ignore_patterns?: string
}

export interface TrashInfo {
  total_size: number
  file_count: number
}

export interface TrashFile {
  path: string
  size: number
  name: string
}

export interface TrashList {
  files: TrashFile[]
  total_size: number
  file_count: number
}

export interface QueueStatus {
  is_paused: boolean
  is_running: boolean
  has_active_task: boolean
}

export interface ScanProgress {
  is_scanning: boolean
  phase: string
  current_file: string
  files_checked: number
  files_found: number
  tasks_created: number
  tasks_removed: number
}

export interface TaskLog {
  id: number
  level: "info" | "warning" | "error"
  message: string
  created_at: string
}

export interface PermissionTestResult {
  path: string
  exists: boolean
  readable: boolean
  writable: boolean
  error: string | null
}

export interface PermissionTestResponse {
  source: PermissionTestResult
  temp: PermissionTestResult
  config: PermissionTestResult
  archive: PermissionTestResult | null
}

export interface IgnorePatternsTestResponse {
  ignored_files: string[]
  total_count: number
}

export interface PermissionTestRequest {
  source_dir: string
  temp_dir: string
  config_dir: string
  original_file_strategy: string
  archive_dir?: string
}

export interface IgnorePatternsTestRequest {
  source_dir: string
  scan_ignore_patterns: string
}

export interface DirectoryEntry {
  name: string
  path: string
  is_dir: boolean
}

export interface BrowseResponse {
  current_path: string
  parent_path: string | null
  entries: DirectoryEntry[]
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  const data = await response.json()

  if (!response.ok) {
    if (data?.error?.code && data?.error?.message) {
      throw new ApiRequestError(data.error)
    }
    throw new ApiRequestError({
      code: "HTTP_ERROR",
      message: `请求失败 (${response.status})`,
      details: {},
    })
  }

  return data
}

export const api = {
  tasks: {
    list: (params?: {
      status?: string
      search?: string
      limit?: number
      offset?: number
      sort_by?: "created_at" | "updated_at" | "status_priority"
      sort_order?: "asc" | "desc"
    }) =>
      fetchJSON<TaskListResponse>(
        `${API_BASE}/tasks/?${new URLSearchParams({
          ...(params?.status && { status: params.status }),
          ...(params?.search && { search: params.search }),
          ...(params?.sort_by && { sort_by: params.sort_by }),
          ...(params?.sort_order && { sort_order: params.sort_order }),
          limit: String(params?.limit ?? 20),
          offset: String(params?.offset ?? 0),
        })}`
      ),
    getProgress: () =>
      fetchJSON<TaskProgress | null>(`${API_BASE}/tasks/progress`),
    getStats: () => fetchJSON<Stats>(`${API_BASE}/tasks/stats`),
    scan: () =>
      fetchJSON<{ message: string; created: number; removed: number }>(`${API_BASE}/tasks/scan`, {
        method: "POST",
      }),
    getScanProgress: () =>
      fetchJSON<ScanProgress>(`${API_BASE}/tasks/scan/progress`),
    cancel: (taskId: number) =>
      fetchJSON<{ message: string }>(`${API_BASE}/tasks/${taskId}/cancel`, {
        method: "POST",
      }),
    retry: (taskId: number) =>
      fetchJSON<{ message: string }>(`${API_BASE}/tasks/${taskId}/retry`, {
        method: "POST",
      }),
    rollback: (taskId: number) =>
      fetchJSON<{ message: string; restored_path: string }>(
        `${API_BASE}/tasks/${taskId}/rollback`,
        { method: "POST" }
      ),
    getLogs: (taskId: number) =>
      fetchJSON<{ logs: TaskLog[] }>(`${API_BASE}/tasks/${taskId}/logs`),
    getQueueStatus: () =>
      fetchJSON<QueueStatus>(`${API_BASE}/tasks/queue/status`),
    pauseQueue: (immediate = false) =>
      fetchJSON<{ message: string; is_paused: boolean; interrupted: boolean }>(
        `${API_BASE}/tasks/queue/pause`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ immediate }),
        }
      ),
    resumeQueue: () =>
      fetchJSON<{ message: string; is_paused: boolean }>(
        `${API_BASE}/tasks/queue/resume`,
        { method: "POST" }
      ),
  },
  settings: {
    get: () => fetchJSON<Settings>(`${API_BASE}/settings/`),
    update: (settings: SettingsUpdate) =>
      fetchJSON<Settings>(`${API_BASE}/settings/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      }),
    getCommandPreview: () =>
      fetchJSON<{ command: string }>(`${API_BASE}/settings/command-preview`),
    generateCommandPreview: (params: {
      video_preset: number
      video_crf: number
      video_film_grain: number
      audio_bitrate: string
      max_threads: number
    }) =>
      fetchJSON<{ command: string }>(`${API_BASE}/settings/command-preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      }),
    testPermissions: (params: PermissionTestRequest) =>
      fetchJSON<PermissionTestResponse>(`${API_BASE}/settings/test-permissions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      }),
    testIgnorePatterns: (params: IgnorePatternsTestRequest) =>
      fetchJSON<IgnorePatternsTestResponse>(`${API_BASE}/settings/test-ignore-patterns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      }),
  },
  trash: {
    list: () => fetchJSON<TrashList>(`${API_BASE}/trash/`),
    getInfo: () => fetchJSON<TrashInfo>(`${API_BASE}/trash/info`),
    empty: () =>
      fetchJSON<{ message: string; freed_bytes: number }>(
        `${API_BASE}/trash/empty`,
        { method: "POST" }
      ),
  },
  filesystem: {
    browse: (path: string) =>
      fetchJSON<BrowseResponse>(`${API_BASE}/filesystem/browse?path=${encodeURIComponent(path)}`),
  },
}
