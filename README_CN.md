# DietTube

<p align="center">
  <img src="assets/logo.png" alt="DietTube Logo" width="200">
</p>

<p align="center">
  使用 AV1 + Opus 编码的自托管视频转码方案，实现极致压缩。<br>
  专为家庭 NAS 和媒体库场景设计。
</p>

<p align="center">
  <a href="README.md">English</a>
</p>

## 功能特性

- **AV1 视频编码** - 使用 SVT-AV1 10-bit 色深，获得出色的质量体积比
- **Opus 音频** - 现代音频编码，可配置码率
- **智能扫描** - 通过元数据标记自动识别未处理的视频
- **Web 界面** - 监控进度、管理队列、调整设置
- **Docker 部署** - 单容器部署，支持 PUID/PGID
- **非破坏性** - 原始文件移动到回收站/归档，不会立即删除

## 快速开始

```bash
docker run -d \
  --name diettube \
  -p 8000:8000 \
  -e PUID=1000 \
  -e PGID=1000 \
  -v /path/to/videos:/source \
  -v /path/to/temp:/temp \
  -v /path/to/config:/config \
  ghcr.io/andiedie/diettube:latest
```

在浏览器中打开 `http://localhost:8000`。

## Docker Compose

```yaml
services:
  diettube:
    image: ghcr.io/andiedie/diettube:latest
    container_name: diettube
    ports:
      - "8000:8000"
    environment:
      - PUID=1000
      - PGID=1000
    volumes:
      - /path/to/videos:/source
      - /path/to/temp:/temp
      - /path/to/config:/config
    restart: unless-stopped
```

## 挂载目录

| 路径 | 说明 |
|------|------|
| `/source` | 待处理的视频文件目录（读写） |
| `/temp` | 临时处理目录和回收站 |
| `/config` | 数据库和设置存储 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PUID` | 1000 | 文件权限的用户 ID |
| `PGID` | 1000 | 文件权限的组 ID |
| `DIETTUBE_VIDEO_PRESET` | 6 | SVT-AV1 预设（0-13，越小越慢但质量越好） |
| `DIETTUBE_VIDEO_CRF` | 30 | 质量系数（0-63，越小质量越好） |
| `DIETTUBE_VIDEO_FILM_GRAIN` | 0 | 合成胶片颗粒强度（0-50） |
| `DIETTUBE_AUDIO_BITRATE` | 64k | Opus 音频码率 |
| `DIETTUBE_MAX_THREADS` | 0 | CPU 线程限制（0 = 自动） |
| `DIETTUBE_ORIGINAL_FILE_STRATEGY` | trash | `trash`（回收站）或 `archive`（归档） |
| `DIETTUBE_ARCHIVE_DIR` | | 归档目录路径（策略为 `archive` 时使用） |
| `DIETTUBE_MAX_LONG_SIDE` | 0 | 长边最大像素（0 = 不限制） |
| `DIETTUBE_MAX_SHORT_SIDE` | 0 | 短边最大像素（0 = 不限制） |
| `DIETTUBE_START_PAUSED` | false | 启动时暂停队列 |
| `DIETTUBE_SCAN_IGNORE_PATTERNS` | | 扫描时忽略的文件/目录模式（每行一个，支持 gitignore 语法） |

所有设置也可以通过 Web 界面进行配置。

## 支持的格式

**输入**: `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.ts`, `.mts`, `.m2ts`

**输出**: `.mkv`（AV1 视频 + Opus 音频）

## 工作流程

1. **扫描** - 点击「扫描」在 `/source` 中查找未处理的视频
2. **入队** - 视频被添加到处理队列
3. **转码** - FFmpeg 编码为 AV1 + Opus
4. **校验** - 验证输出文件（时长、文件大小）
5. **替换** - 原始文件移动到回收站，新文件取代其位置

已处理的文件会被添加元数据标记（`DietTube-Processed`）以避免重复处理。

## 从源码构建

```bash
# 克隆
git clone https://github.com/Andiedie/DietTube.git
cd DietTube

# 构建 Docker 镜像
docker build -t diettube -f docker/Dockerfile .

# 或本地开发运行
cd backend && ./dev.sh    # 终端 1
cd frontend && pnpm dev   # 终端 2
```

## 技术栈

- **后端**: Python, FastAPI, SQLAlchemy (SQLite)
- **前端**: React, Vite, TailwindCSS
- **转码**: FFmpeg, SVT-AV1, libopus
- **容器**: Docker 多阶段构建

## 许可证

MIT
