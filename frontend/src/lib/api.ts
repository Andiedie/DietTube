const API_BASE = "/api"

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
  archive_dir: string | null
  source_dir: string
  temp_dir: string
  config_dir: string
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

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

export const api = {
  tasks: {
    list: (status?: string, limit = 50, offset = 0) =>
      fetchJSON<TaskListResponse>(
        `${API_BASE}/tasks/?${new URLSearchParams({
          ...(status && { status }),
          limit: String(limit),
          offset: String(offset),
        })}`
      ),
    getProgress: () =>
      fetchJSON<TaskProgress | null>(`${API_BASE}/tasks/progress`),
    getStats: () => fetchJSON<Stats>(`${API_BASE}/tasks/stats`),
    scan: () =>
      fetchJSON<{ message: string }>(`${API_BASE}/tasks/scan`, {
        method: "POST",
      }),
    cancel: (taskId: number) =>
      fetchJSON<{ message: string }>(`${API_BASE}/tasks/${taskId}/cancel`, {
        method: "POST",
      }),
    retry: (taskId: number) =>
      fetchJSON<{ message: string }>(`${API_BASE}/tasks/${taskId}/retry`, {
        method: "POST",
      }),
  },
  settings: {
    get: () => fetchJSON<Settings>(`${API_BASE}/settings/`),
    getCommandPreview: () =>
      fetchJSON<{ command: string }>(`${API_BASE}/settings/command-preview`),
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
}
