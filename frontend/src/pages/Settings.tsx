import { useQuery } from "@tanstack/react-query"
import { Settings as SettingsIcon, Terminal, Folder } from "lucide-react"
import { api } from "@/lib/api"

function SettingRow({
  label,
  value,
  description,
}: {
  label: string
  value: string | number
  description?: string
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-[hsl(var(--border))] last:border-0">
      <div>
        <p className="font-medium">{label}</p>
        {description && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {description}
          </p>
        )}
      </div>
      <span className="text-[hsl(var(--muted-foreground))] font-mono bg-[hsl(var(--muted))] px-3 py-1 rounded">
        {value}
      </span>
    </div>
  )
}

export default function Settings() {
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: api.settings.get,
    refetchInterval: false,
  })

  const { data: commandPreview } = useQuery({
    queryKey: ["commandPreview"],
    queryFn: api.settings.getCommandPreview,
    refetchInterval: false,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center">
        <SettingsIcon className="w-6 h-6 mr-2 text-[hsl(var(--primary))]" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <Folder className="w-5 h-5 mr-2" />
          Directory Configuration
        </h2>
        <div className="space-y-2">
          <SettingRow
            label="Source Directory"
            value={settings?.source_dir || "-"}
            description="Where your video files are located"
          />
          <SettingRow
            label="Temp Directory"
            value={settings?.temp_dir || "-"}
            description="For processing and trash storage"
          />
          <SettingRow
            label="Config Directory"
            value={settings?.config_dir || "-"}
            description="Database and configuration files"
          />
        </div>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Video Encoding Settings</h2>
        <div className="space-y-2">
          <SettingRow
            label="Preset"
            value={settings?.video_preset ?? "-"}
            description="SVT-AV1 encoding speed (0=slowest/best, 13=fastest)"
          />
          <SettingRow
            label="CRF"
            value={settings?.video_crf ?? "-"}
            description="Constant Rate Factor (0=lossless, 63=worst)"
          />
          <SettingRow
            label="Film Grain"
            value={settings?.video_film_grain ?? "-"}
            description="Synthetic grain synthesis (0-50)"
          />
        </div>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Audio Settings</h2>
        <div className="space-y-2">
          <SettingRow
            label="Bitrate"
            value={settings?.audio_bitrate || "-"}
            description="Opus audio bitrate"
          />
        </div>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Processing Settings</h2>
        <div className="space-y-2">
          <SettingRow
            label="Max Threads"
            value={settings?.max_threads === 0 ? "Auto" : settings?.max_threads ?? "-"}
            description="CPU threads for encoding (0=auto)"
          />
          <SettingRow
            label="Original File Strategy"
            value={settings?.original_file_strategy || "-"}
            description="What to do with original files after processing"
          />
          {settings?.archive_dir && (
            <SettingRow
              label="Archive Directory"
              value={settings.archive_dir}
              description="Where to move original files"
            />
          )}
        </div>
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <Terminal className="w-5 h-5 mr-2" />
          FFmpeg Command Preview
        </h2>
        <pre className="bg-[hsl(var(--muted))] p-4 rounded-lg overflow-x-auto text-sm font-mono whitespace-pre-wrap break-all">
          {commandPreview?.command || "Loading..."}
        </pre>
      </div>

      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <p className="text-sm text-yellow-800 dark:text-yellow-200">
          Settings are configured via environment variables. Restart the container to apply changes.
        </p>
      </div>
    </div>
  )
}
