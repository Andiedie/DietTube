# DietTube

Self-hosted video transcoding solution using AV1 + Opus for maximum compression. Built for home NAS and media library scenarios.

## Features

- **AV1 Video Encoding** - SVT-AV1 with 10-bit color depth for excellent quality-to-size ratio
- **Opus Audio** - Modern audio codec with configurable bitrate
- **Smart Scanning** - Automatically detects unprocessed videos via metadata markers
- **Web Interface** - Monitor progress, manage queue, adjust settings
- **Docker Ready** - Single container deployment with PUID/PGID support
- **Non-destructive** - Original files moved to trash/archive, never deleted immediately

## Quick Start

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

Open `http://localhost:8000` in your browser.

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

## Volumes

| Path | Description |
|------|-------------|
| `/source` | Video files to process (read/write) |
| `/temp` | Temporary processing directory and trash |
| `/config` | Database and settings storage |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | 1000 | User ID for file permissions |
| `PGID` | 1000 | Group ID for file permissions |
| `DIETTUBE_VIDEO_PRESET` | 6 | SVT-AV1 preset (0-13, lower = slower + better) |
| `DIETTUBE_VIDEO_CRF` | 30 | Quality factor (0-63, lower = better quality) |
| `DIETTUBE_AUDIO_BITRATE` | 64k | Opus audio bitrate |
| `DIETTUBE_MAX_THREADS` | 0 | CPU thread limit (0 = auto) |
| `DIETTUBE_ORIGINAL_FILE_STRATEGY` | trash | `trash` or `archive` |

All settings can also be configured via the web interface.

## Supported Formats

**Input**: `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`, `.ts`, `.mts`, `.m2ts`

**Output**: `.mkv` with AV1 video + Opus audio

## How It Works

1. **Scan** - Click "Scan" to find unprocessed videos in `/source`
2. **Queue** - Videos are added to the processing queue
3. **Transcode** - FFmpeg encodes to AV1 + Opus
4. **Verify** - Output is validated (duration, file size)
5. **Replace** - Original moved to trash, new file takes its place

Processed files are marked with a metadata tag (`DietTube-Processed`) to avoid re-processing.

## Building from Source

```bash
# Clone
git clone https://github.com/Andiedie/DietTube.git
cd DietTube

# Build Docker image
docker build -t diettube .

# Or run locally for development
cd backend && ./dev.sh    # Terminal 1
cd frontend && pnpm dev   # Terminal 2
```

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy (SQLite)
- **Frontend**: React, Vite, TailwindCSS
- **Transcoding**: FFmpeg, SVT-AV1, libopus
- **Container**: Docker with multi-stage build

## License

MIT
