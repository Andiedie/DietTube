import { useState, useEffect, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Settings as SettingsIcon,
  Terminal,
  Folder,
  Save,
  Loader2,
  CheckCircle2,
  XCircle,
  ShieldCheck,
} from "lucide-react"
import {
  api,
  type Settings as SettingsType,
  type PermissionTestResponse,
  ApiRequestError,
} from "@/lib/api"
import { useToast } from "@/components/Toast"

function SettingInput({
  label,
  value,
  onChange,
  description,
  type = "text",
  min,
  max,
}: {
  label: string
  value: string | number
  onChange: (value: string | number) => void
  description?: string
  type?: "text" | "number"
  min?: number
  max?: number
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-[hsl(var(--border))] last:border-0">
      <div className="flex-1">
        <p className="font-medium">{label}</p>
        {description && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {description}
          </p>
        )}
      </div>
      <input
        type={type}
        value={value}
        onChange={(e) =>
          onChange(type === "number" ? Number(e.target.value) : e.target.value)
        }
        min={min}
        max={max}
        className="w-48 px-3 py-1.5 rounded border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-right font-mono focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
      />
    </div>
  )
}

function SettingSelect({
  label,
  value,
  onChange,
  options,
  description,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: { value: string; label: string }[]
  description?: string
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-[hsl(var(--border))] last:border-0">
      <div className="flex-1">
        <p className="font-medium">{label}</p>
        {description && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {description}
          </p>
        )}
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-48 px-3 py-1.5 rounded border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-right font-mono focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export default function Settings() {
  const queryClient = useQueryClient()
  const { addToast } = useToast()
  const [formData, setFormData] = useState<SettingsType | null>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [permissionResults, setPermissionResults] =
    useState<PermissionTestResponse | null>(null)
  const [testingPermissions, setTestingPermissions] = useState(false)

  const { data: settings, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: api.settings.get,
    refetchInterval: false,
  })

  const previewParams = useMemo(() => {
    if (!formData) return null
    return {
      video_preset: formData.video_preset,
      video_crf: formData.video_crf,
      video_film_grain: formData.video_film_grain,
      audio_bitrate: formData.audio_bitrate,
      max_threads: formData.max_threads,
    }
  }, [formData?.video_preset, formData?.video_crf, formData?.video_film_grain, formData?.audio_bitrate, formData?.max_threads])

  const { data: commandPreview } = useQuery({
    queryKey: ["commandPreview", previewParams],
    queryFn: () => previewParams ? api.settings.generateCommandPreview(previewParams) : null,
    enabled: !!previewParams,
    refetchInterval: false,
  })

  const updateMutation = useMutation({
    mutationFn: api.settings.update,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] })
      setHasChanges(false)
      addToast("设置已保存", "success")
    },
    onError: (error) => {
      const message = error instanceof ApiRequestError ? error.message : "保存设置失败"
      addToast(message, "error")
    },
  })

  useEffect(() => {
    if (settings && !formData) {
      setFormData(settings)
    }
  }, [settings, formData])

  const handleChange = <K extends keyof SettingsType>(
    key: K,
    value: SettingsType[K]
  ) => {
    if (formData) {
      setFormData({ ...formData, [key]: value })
      setHasChanges(true)
    }
  }

  const handleSave = () => {
    if (formData) {
      updateMutation.mutate(formData)
    }
  }

  const handleReset = () => {
    if (settings) {
      setFormData(settings)
      setHasChanges(false)
    }
  }

  const handleTestPermissions = async () => {
    setTestingPermissions(true)
    try {
      const results = await api.settings.testPermissions()
      setPermissionResults(results)
      const allOk = results.source.writable && results.temp.writable && results.config.writable &&
        (!results.archive || results.archive.writable)
      addToast(allOk ? "所有目录权限正常" : "部分目录权限存在问题", allOk ? "success" : "error")
    } catch {
      addToast("权限测试失败", "error")
    } finally {
      setTestingPermissions(false)
    }
  }

  if (isLoading || !formData) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--muted-foreground))]" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <SettingsIcon className="w-6 h-6 mr-2 text-[hsl(var(--primary))]" />
          <h1 className="text-2xl font-bold">设置</h1>
        </div>
        {hasChanges && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              className="px-4 py-2 border border-[hsl(var(--border))] rounded-md hover:bg-[hsl(var(--accent))]"
            >
              重置
            </button>
            <button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="flex items-center px-4 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md hover:opacity-90 disabled:opacity-50"
            >
              {updateMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              保存更改
            </button>
          </div>
        )}
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <Folder className="w-5 h-5 mr-2" />
          目录配置
        </h2>
        <div className="space-y-2">
          <SettingInput
            label="源目录"
            value={formData.source_dir}
            onChange={(v) => handleChange("source_dir", String(v))}
            description="视频文件所在的目录"
          />
          <SettingInput
            label="临时目录"
            value={formData.temp_dir}
            onChange={(v) => handleChange("temp_dir", String(v))}
            description="用于处理和回收站存储"
          />
          <SettingInput
            label="配置目录"
            value={formData.config_dir}
            onChange={(v) => handleChange("config_dir", String(v))}
            description="数据库和配置文件存储"
          />
        </div>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <ShieldCheck className="w-5 h-5 mr-2" />
          权限测试
        </h2>
        <p className="text-sm text-[hsl(var(--muted-foreground))] mb-4">
          测试各目录的读写权限，确保应用能正常工作
        </p>
        <button
          onClick={handleTestPermissions}
          disabled={testingPermissions}
          className="flex items-center px-4 py-2 border border-[hsl(var(--border))] rounded-md hover:bg-[hsl(var(--accent))] disabled:opacity-50"
        >
          {testingPermissions ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <ShieldCheck className="w-4 h-4 mr-2" />
          )}
          测试目录权限
        </button>

        {permissionResults && (
          <div className="mt-4 space-y-2">
            {(
              [
                ["source", "源目录"],
                ["temp", "临时目录"],
                ["config", "配置目录"],
                ["archive", "归档目录"],
              ] as const
            ).map(([key, label]) => {
              const result = permissionResults[key]
              if (!result) return null
              const ok = result.exists && result.readable && result.writable
              return (
                <div
                  key={key}
                  className={`flex items-center justify-between p-3 rounded-md ${
                    ok
                      ? "bg-green-50 dark:bg-green-900/20"
                      : "bg-red-50 dark:bg-red-900/20"
                  }`}
                >
                  <div className="flex items-center">
                    {ok ? (
                      <CheckCircle2 className="w-4 h-4 mr-2 text-green-600" />
                    ) : (
                      <XCircle className="w-4 h-4 mr-2 text-red-600" />
                    )}
                    <span className="font-medium">{label}</span>
                    <span className="ml-2 text-sm text-[hsl(var(--muted-foreground))] font-mono">
                      {result.path}
                    </span>
                  </div>
                  <div className="text-sm">
                    {ok ? (
                      <span className="text-green-600">读写正常</span>
                    ) : (
                      <span className="text-red-600">{result.error}</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">视频编码设置</h2>
        <div className="space-y-2">
          <SettingInput
            label="预设速度"
            value={formData.video_preset}
            onChange={(v) => handleChange("video_preset", Number(v))}
            description="SVT-AV1 编码速度（0=最慢/最佳，13=最快）"
            type="number"
            min={0}
            max={13}
          />
          <SettingInput
            label="质量系数 (CRF)"
            value={formData.video_crf}
            onChange={(v) => handleChange("video_crf", Number(v))}
            description="恒定质量因子（0=无损，63=最差）"
            type="number"
            min={0}
            max={63}
          />
          <SettingInput
            label="胶片颗粒"
            value={formData.video_film_grain}
            onChange={(v) => handleChange("video_film_grain", Number(v))}
            description="合成颗粒强度（0-50）"
            type="number"
            min={0}
            max={50}
          />
          <SettingInput
            label="最大长边"
            value={formData.max_long_side}
            onChange={(v) => handleChange("max_long_side", Number(v))}
            description="限制输出视频长边像素（0=不限制）"
            type="number"
            min={0}
          />
          <SettingInput
            label="最大短边"
            value={formData.max_short_side}
            onChange={(v) => handleChange("max_short_side", Number(v))}
            description="限制输出视频短边像素（0=不限制）"
            type="number"
            min={0}
          />
        </div>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">音频设置</h2>
        <div className="space-y-2">
          <SettingInput
            label="码率"
            value={formData.audio_bitrate}
            onChange={(v) => handleChange("audio_bitrate", String(v))}
            description="Opus 音频码率（如 128k、192k）"
          />
        </div>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">处理设置</h2>
        <div className="space-y-2">
          <SettingInput
            label="最大线程数"
            value={formData.max_threads}
            onChange={(v) => handleChange("max_threads", Number(v))}
            description="编码使用的 CPU 线程数（0=自动）"
            type="number"
            min={0}
          />
          <SettingSelect
            label="源文件策略"
            value={formData.original_file_strategy}
            onChange={(v) => handleChange("original_file_strategy", v)}
            description="处理完成后如何处理原始文件"
            options={[
              { value: "trash", label: "移动到回收站" },
              { value: "archive", label: "移动到归档目录" },
            ]}
          />
          {formData.original_file_strategy === "archive" && (
            <SettingInput
              label="归档目录"
              value={formData.archive_dir}
              onChange={(v) => handleChange("archive_dir", String(v))}
              description="原始文件的归档位置"
            />
          )}
        </div>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <Terminal className="w-5 h-5 mr-2" />
          FFmpeg 命令预览
        </h2>
        <pre className="bg-[hsl(var(--muted))] p-4 rounded-lg overflow-x-auto text-sm font-mono whitespace-pre-wrap break-all">
          {commandPreview?.command || "加载中..."}
        </pre>
      </div>

      {hasChanges && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            您有未保存的更改，点击「保存更改」以应用。
          </p>
        </div>
      )}
    </div>
  )
}
