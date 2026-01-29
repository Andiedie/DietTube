这是一个根据您的最新要求调整后的 **DietTube V1.0 (最终修订版) PRD**。

本次更新重点完善了**转码策略细节**（流映射）以及**设置页面的交互逻辑**（参数配置与命令预览）。

---

# 产品需求文档 (PRD): DietTube

| 项目 | 内容 |
| --- | --- |
| **产品名称** | DietTube |
| **版本号** | V1.0 (Final Revised) |
| **文档日期** | 2026-01-29 |
| **核心标语** | Give your video library a diet. (为你的视频库瘦身) |
| **产品目标** | 针对家庭 NAS/影音库场景，提供自动化、极致压缩（AV1+Opus）的视频处理方案。在保留字幕、章节和元数据的前提下，通过“无感替换”释放硬盘空间。 |

---

## 1. 技术架构选型 (Tech Stack)

### 1.1 前端 (Frontend)

* **框架:** Next.js (App Router)
* **UI 库:** React + TailwindCSS (极简、高密度信息展示风格)
* **语言:** TypeScript
* **状态同步:** SWR 或 React Query (用于轮询/实时获取任务状态)

### 1.2 后端 (Backend)

* **核心服务:** Python (FastAPI/Flask)
* **数据库:** SQLite (单文件存储)
* **转码引擎:** FFmpeg (必须编译支持 `libsvtav1` 和 `libopus`)

### 1.3 部署架构

* **容器化:** Docker + Docker Compose。
* **目录挂载:** 必须挂载三个路径：源目录 (Source)、临时目录 (Temp)、回收站 (Trash)。

---

## 2. 核心业务流程 (Core Logic)

### 2.1 目录结构与流转

遵循 **“Temp -> Trash -> Source”** 的原子替换逻辑，确保数据安全。

* **Source Path:** 原始库（最终被新文件替换）。
* **Temp Path:** 转码中间产物（必须位于 SSD 以保证 I/O 性能）。
* **Trash Path:** 归档原始文件（保留原始目录结构，支持一键恢复）。

### 2.2 智能扫描与去重 (Scanner)

1. **L1 快速检查:** 比对 `mtime` 和 `size`。
2. **L2 局部哈希:** 仅当 L1 变更时，计算头部+尾部+大小的 Fast Hash。
3. **L3 标记检测:** 使用 `ffprobe` 检查 Metadata 中是否包含 `DietTube` 标记。
* *逻辑:* 只要发现此标记，视为已处理，自动录入数据库状态为 `COMPLETED` 并跳过。



---

## 3. 转码策略与流处理 (Transcoding Strategy)

这是本系统的核心，必须严格执行流映射（Stream Mapping）规则，以确保“瘦身”的同时不丢失功能。

### 3.1 流映射规则 (Stream Mapping)

FFmpeg 命令构建时，必须显式包含以下逻辑：

| 流类型 (Stream) | 处理策略 | 详细说明 |
| --- | --- | --- |
| **Video (视频流)** | **Re-encode (AV1)** | 对应 `libsvtav1`。这是主要的体积压缩来源。 |
| **Audio (音频流)** | **Re-encode (Opus)** | 对应 `libopus`。**不保留源音轨**，所有音频轨道均强制转码为 Opus 以极致节省空间。 |
| **Subtitle (字幕流)** | **Copy (复制)** | 对应 `-c:s copy`。保留所有软字幕轨（SRT/ASS/PGS等）。 |
| **Data/Chapters** | **Copy (复制)** | 保留章节信息（Chapters）和全局元数据。 |
| **Attachments** | **Copy (复制)** | 保留内封字体（Fonts）文件 (对应 `-map 0:t? -c:t copy`)。 |

### 3.2 必须注入的元数据

转码时必须写入以下 Metadata 以支持扫描器的“标记检测”功能：

* `-metadata comment="DietTube"`

---

## 4. 功能模块需求 (Functional Requirements)

### 4.1 设置模块 (Settings) - **本次更新重点**

设置页面不再只是简单的文本框，需要提供结构化的参数配置与实时的命令预览。

#### 4.1.1 视频编码配置 (Video - AV1)

* **Preset (预设):** 下拉选择 (0-13)。
* *默认值:* 4 (推荐平衡点)。
* *说明:* 数值越小越慢体积越小，数值越大越快。


* **CRF (质量系数):** 滑动条/输入框 (0-63)。
* *默认值:* 32。
* *说明:* 建议范围 24-35。


* **Film Grain (胶片颗粒):** 滑动条 (0-50)。
* *默认值:* 8。
* *说明:* 用于掩盖低码率瑕疵，保留纹理质感。


* **10-bit Color:** 开关 (Toggle)。
* *默认:* 开启 (强制 `-pix_fmt yuv420p10le` 以防止色带)。



#### 4.1.2 音频编码配置 (Audio - Opus)

* **Bitrate (码率):** 输入框/下拉选择。
* *默认值:* 64k (kbps)。
* *策略:* 应用于所有音频轨道。


* **VBR:** 开关 (Toggle)，默认开启。

#### 4.1.3 实时命令预览 (Live Command Preview)

在配置项下方，放置一个**只读的代码块 (Code Block)**，根据用户上述的选择，实时拼接并展示最终将执行的 FFmpeg 命令参数。

* *目的:* 让硬核用户确认参数是否符合预期，增加透明度。
* *展示格式示例:*
```bash
ffmpeg -i INPUT -map 0 \
  -c:v libsvtav1 -preset 4 -crf 32 -svtav1-params tune=0:film-grain=8 -pix_fmt yuv420p10le \
  -c:a libopus -b:a 64k -vbr on \
  -c:s copy -c:d copy -map_metadata 0 \
  -metadata comment="DietTube" \
  OUTPUT

```



#### 4.1.4 高级自定义 (Advanced Override)

* 提供一个“自定义参数追加”输入框，允许用户输入额外的 FFmpeg 参数（如 `-vf scale=...`），追加在输出文件之前。

---

### 4.2 仪表盘 (Dashboard)

* **KPI 卡片:**
* **Space Reclaimed:** 累计节省空间。
* **Current Ratio:** 整体压缩率 (例如: 原 100GB -> 现 40GB，显示 "60% Saved")。


* **任务监控:**
* 必须区分展示：`Pending` (排队中), `Processing` (处理中), `Success` (已完成), `Failed` (失败)。



### 4.3 回收站 (Trash Bin)

* **逻辑:** 物理移动，非删除。
* **操作:**
* **Restore (恢复):** 将 Trash 中的文件移回 Source，覆盖当前的 AV1 文件。
* **Purge (清空):** 彻底删除 Trash 中的文件，释放物理空间。



---

## 5. 研发实施细节 (Implementation Notes)

### 5.1 FFmpeg 命令构建逻辑 (Python 伪代码)

后端必须动态构建命令，以适配多轨道情况。最稳妥的“保留所有流但转码视音频”的通用命令如下：

```python
cmd = [
    "ffmpeg", "-y", "-i", input_path,
    
    # 1. 映射所有流
    "-map", "0",
    
    # 2. 视频流配置 (AV1)
    "-c:v", "libsvtav1",
    "-preset", str(user_config.preset),
    "-crf", str(user_config.crf),
    "-svtav1-params", f"tune=0:enable-overlays=1:scd=1:film-grain={user_config.film_grain}",
    "-pix_fmt", "yuv420p10le" if user_config.10bit else "yuv420p",
    
    # 3. 音频流配置 (Opus - 强制转码所有音频轨)
    "-c:a", "libopus",
    "-b:a", f"{user_config.audio_bitrate}k",
    "-vbr", "on",
    
    # 4. 字幕与数据流 (复制)
    "-c:s", "copy",
    "-c:d", "copy",   # Data streams (chapters)
    "-c:t", "copy",   # Attachments (fonts)
    
    # 5. 元数据保留与注入
    "-map_metadata", "0",
    "-metadata", "comment=DietTube", # 关键标记
    
    output_temp_path
]

```

### 5.2 异常处理

* **字幕格式不兼容风险:** 某些极其罕见的位图字幕（如 DVD sub）在 MKV 容器中通常能 `copy`，但在极少数情况下可能报错。研发需捕获 FFmpeg stderr，若因字幕报错，可考虑 fallback 策略（如丢弃字幕或尝试转码字幕），但在 V1.0 中建议直接**标记任务失败**，让人工介入，避免破坏数据。

### 5.3 进度追踪

* 解析 FFmpeg 输出的 `frame=... fps=... time=... size=...` 行，通过 WebSocket 推送给前端，计算百分比（当前时间 / 总时长）。

**(完)**