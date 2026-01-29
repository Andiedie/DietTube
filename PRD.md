# 产品需求文档 (PRD): DietTube

| 项目 | 内容 |
| --- | --- |
| **产品名称** | DietTube |
| **版本号** | **V1.2 (Archive Strategy Edition)** |
| **文档日期** | 2026-01-29 |
| **核心标语** | Give your video library a diet. (为你的视频库瘦身) |
| **产品目标** | 针对家庭 NAS/影音库场景，提供自动化、极致压缩（AV1+Opus）的视频处理方案。在保留字幕、章节和元数据的前提下，通过“无感替换”释放硬盘空间。 |

---

## 1. 技术架构选型 (Tech Stack)

### 1.1 总体架构

采用 **All-in-One 单容器架构**。前端构建为静态资源，由后端 Python 服务直接托管。

### 1.2 前端 (Frontend)

* **框架:** Next.js (App Router) + React.
* **UI 库:** TailwindCSS (高密度信息展示).
* **构建:** Static Export (`output: 'export'`)，产物存放于后端 `/static` 目录。

### 1.3 后端 (Backend)

* **核心服务:** Python (FastAPI).
* **职责:** 业务调度、FFmpeg 封装、静态资源托管、API 响应。
* **数据库:** SQLite (存储于 `/config/db.sqlite`)。
* **转码引擎:** FFmpeg (需编译支持 `libsvtav1`, `libopus`).

### 1.4 部署环境 (Deployment)

* **运行方式:** `docker run` (单容器)。
* **目录挂载 (Volumes):**
1. `/data/source`: **源视频库** (NAS/HDD)。
2. `/data/temp`: **工作空间** (SSD，高速读写)。
3. `/config`: **配置持久化** (数据库、日志、配置文件)。



---

## 2. 核心业务流程 (Core Logic)

### 2.1 目录结构自动化

系统启动时，后端自动在 `/data/temp` 下维护以下结构：

* `/data/temp/processing`: 存放转码中的临时 AV1 文件。
* `/data/temp/trash`: 存放被替换下来的源文件（仅在“回收站模式”下使用）。

### 2.2 任务流转逻辑 (Pipeline)

1. **Scanner (扫描):**
* 扫描 `/data/source`。
* **跳过逻辑:** 检查 `mtime`/`size` 变更 -> 检查 Metadata 是否包含 `DietTube` 标记。


2. **Transcode (转码):**
* 读取源文件 -> 转码输出至 `/data/temp/processing/<RelPath>/file.mkv`。


3. **Verify (校验):**
* 简单验证输出文件的完整性（如时长对比、流完整性）。


4. **Handle Original (源文件处理 - 分支策略):**
* *根据用户设置（详见 4.1.5）执行移动操作。*
* **情况 A (回收站):** 移动至 `/data/temp/trash/...`。
* **情况 B (指定归档):** 移动至用户指定的路径（如 `/data/source/_backup/...`）。


5. **Install (部署):**
* 将 `/data/temp/processing` 中的新文件移动至 `/data/source`，覆盖原始路径。
* 向数据库写入状态 `COMPLETED`。



---

## 3. 转码策略 (Transcoding Strategy)

必须严格执行流映射，确保功能无损。

| 流类型 | 处理动作 | 详细说明 |
| --- | --- | --- |
| **Video** | **Re-encode (AV1)** | 编码器: `libsvtav1`。核心压缩来源。 |
| **Audio** | **Re-encode (Opus)** | 编码器: `libopus`。**强制转码所有音轨**以极致节省空间。 |
| **Subtitle** | **Copy** | 保留所有软字幕 (SRT, ASS, PGS)。 |
| **Data/Fonts** | **Copy** | 保留章节信息和内封字体附件。 |
| **Metadata** | **Inject** | 必须注入 `-metadata comment="DietTube"` 以供扫描器识别。 |

---

## 4. 功能模块需求 (Functional Requirements)

### 4.1 设置页面 (Settings)

#### 4.1.1 视频配置 (Video)

* **Preset:** 0-13 (默认: 4)。
* **CRF:** 0-63 (默认: 32)。
* **Film Grain:** 0-50 (默认: 8)。
* **10-bit:** 强制开启。

#### 4.1.2 音频配置 (Audio)

* **Bitrate:** (默认: 64k)。
* **VBR:** On/Off (默认: On)。

#### 4.1.3 实时命令预览

* 提供只读代码块，根据上述配置实时拼接展示 FFmpeg 命令字符串。

#### 4.1.4 高级自定义

* 输入框：允许追加自定义 FFmpeg 参数 (如 `-vf scale=1280:-2`)。

#### 4.1.5 源文件处理策略 (Original File Handling) - **关键逻辑**

* **Mode (模式选择):**
* `Move to Trash` (默认): 源文件移入 `/data/temp/trash`。
* `Move to Directory`: 源文件移入指定目录。


* **Target Path (目标路径):**
* 当选择 `Move to Directory` 时必填。
* 用户需输入容器内路径 (例如 `/data/source/_backup`)。
* *提示:* "请确保路径已挂载且可写。"



### 4.2 仪表盘 (Dashboard)

* **Space Saved:** 累计节省空间。
* **Queue Status:** 排队中 / 处理中 / 已完成 / 失败。
* **Trash Size:** 仅统计 `/data/temp/trash` 的占用大小。

### 4.3 回收站 (Trash Bin)

* **显示范围:** 仅列出 `/data/temp/trash` 目录下的文件。
* **清空操作 (Purge):** 点击“Empty Trash”时，仅删除 `/data/temp/trash` 下的内容。
* *注意:* 若用户配置了“Move to Directory”，则源文件不在回收站管辖范围内，该操作不会影响已归档的文件。



---

## 5. 研发实施细节 (Implementation Notes)

### 5.1 Dockerfile 构建策略 (Multi-stage)

```dockerfile
# Stage 1: Build Frontend
FROM node:18-alpine AS frontend
WORKDIR /app
COPY ./frontend .
RUN npm install && npm run build
# 产出物在 /app/out 或 /app/.next/static

# Stage 2: Final Image
FROM python:3.11-slim
# 安装 FFmpeg (需包含 libsvtav1, libopus)
RUN apt-get update && apt-get install -y ffmpeg ... 

WORKDIR /app
COPY ./backend .
RUN pip install -r requirements.txt

# 将前端产物拷入后端静态目录
COPY --from=frontend /app/out /app/static

# 单一入口
CMD ["python", "main.py"]

```

### 5.2 路径保持算法 (Python)

在移动源文件到 Trash 或 Archive 时，必须保留相对路径结构，防止同名文件冲突。

```python
import os, shutil

def archive_original_file(config, source_full_path, rel_path):
    """
    config.mode: 'TRASH' | 'CUSTOM'
    config.custom_path: string (e.g., '/data/source/_backup')
    source_full_path: '/data/source/Movies/Avatar.mkv'
    rel_path: 'Movies/Avatar.mkv'
    """
    
    if config.mode == 'TRASH':
        base_dir = "/data/temp/trash"
    else:
        base_dir = config.custom_path

    # 拼接目标全路径: /data/temp/trash/Movies/Avatar.mkv
    target_full_path = os.path.join(base_dir, rel_path)
    
    # 确保父目录存在
    os.makedirs(os.path.dirname(target_full_path), exist_ok=True)
    
    # 执行移动
    shutil.move(source_full_path, target_full_path)

```

### 5.3 用户启动命令参考

```bash
docker run -d \
  --name diettube \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /mnt/media:/data/source \
  -v /mnt/ssd/temp:/data/temp \
  -v ./config:/config \
  diettube:latest

```

**(完)**