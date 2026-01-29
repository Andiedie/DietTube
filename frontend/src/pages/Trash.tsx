import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2, AlertTriangle, Loader2, FileVideo } from "lucide-react"
import { api } from "@/lib/api"
import { formatBytes } from "@/lib/utils"

export default function Trash() {
  const queryClient = useQueryClient()

  const { data: trashList, isLoading } = useQuery({
    queryKey: ["trash"],
    queryFn: api.trash.list,
  })

  const emptyMutation = useMutation({
    mutationFn: api.trash.empty,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trash"] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Trash2 className="w-6 h-6 mr-2 text-[hsl(var(--primary))]" />
          <h1 className="text-2xl font-bold">回收站</h1>
        </div>
        {trashList && trashList.file_count > 0 && (
          <button
            onClick={() => emptyMutation.mutate()}
            disabled={emptyMutation.isPending}
            className="flex items-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
          >
            {emptyMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4 mr-2" />
            )}
            清空回收站
          </button>
        )}
      </div>

      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">总大小</p>
            <p className="text-3xl font-bold">
              {formatBytes(trashList?.total_size || 0)}
            </p>
          </div>
          <div>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">文件数</p>
            <p className="text-3xl font-bold">{trashList?.file_count || 0}</p>
          </div>
        </div>

        {trashList && trashList.file_count > 0 && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-2 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                  警告
                </p>
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  这些是已处理视频的原始文件。清空回收站将永久删除它们，
                  释放 <strong>{formatBytes(trashList.total_size)}</strong> 的磁盘空间。
                </p>
              </div>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--muted-foreground))]" />
          </div>
        ) : trashList && trashList.files.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[hsl(var(--muted))]">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                    文件
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase">
                    大小
                  </th>
                </tr>
              </thead>
              <tbody>
                {trashList.files.map((file, index) => (
                  <tr
                    key={index}
                    className="border-b border-[hsl(var(--border))] hover:bg-[hsl(var(--accent))/50]"
                  >
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center">
                        <FileVideo className="w-4 h-4 mr-2 text-[hsl(var(--muted-foreground))]" />
                        <span className="truncate max-w-md" title={file.path}>
                          {file.path}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-right">
                      {formatBytes(file.size)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
            <Trash2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>回收站是空的</p>
          </div>
        )}
      </div>
    </div>
  )
}
