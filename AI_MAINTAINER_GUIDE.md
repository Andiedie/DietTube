# DietTube AI Maintainer Guide

## Project Overview

DietTube is a self-hosted video transcoding solution for home NAS/media library scenarios. It automatically compresses videos using AV1+Opus codecs for maximum space savings.

## Architecture

### Tech Stack
- **Backend**: Python FastAPI with async SQLAlchemy (SQLite)
- **Frontend**: React + Vite + TailwindCSS (SPA)
- **Transcoding**: FFmpeg with SVT-AV1 and libopus
- **Deployment**: Docker single container

### Directory Structure

```
DietTube/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point with lifespan
│   │   ├── config.py         # Pydantic settings (env vars)
│   │   ├── database.py       # SQLAlchemy async setup
│   │   ├── models.py         # Task and ProcessingStats models
│   │   ├── routers/          # API endpoints
│   │   │   ├── tasks.py      # Task CRUD, scan, progress
│   │   │   ├── settings.py   # Settings read, command preview
│   │   │   └── trash.py      # Trash management
│   │   └── services/         # Business logic
│   │       ├── scanner.py    # Directory scanning, metadata check
│   │       ├── transcoder.py # FFmpeg integration, progress parsing
│   │       ├── verifier.py   # Output validation
│   │       ├── task_manager.py # Async task queue, in-memory progress
│   │       └── recovery.py   # Startup recovery logic
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx          # React entry
│   │   ├── App.tsx           # Layout with navigation
│   │   ├── pages/            # Dashboard, Settings, Trash
│   │   └── lib/              # API client, utilities
│   └── package.json
├── Dockerfile                # Multi-stage build
└── docker-compose.yml        # Example deployment
```

## Key Design Decisions

### In-Memory Progress
Task progress (FPS, ETA, percentage) is stored in `TaskManager._state.current_progress` rather than the database to avoid I/O bottlenecks.

### Recovery Mechanism
On startup, `perform_recovery()`:
1. Resets stuck tasks (status in progress states) to PENDING
2. Cleans temporary processing directory

### Transcoding Pipeline
1. Scanner → finds unprocessed videos via metadata marker
2. Transcoder → FFmpeg with SVT-AV1 + Opus
3. Verifier → duration/size validation
4. Install → move original to trash, replace with new file

### Processing Marker
Files are marked as processed by injecting `DietTube-Processed` into the `comment` metadata field.

## Environment Variables

All settings use `DIETTUBE_` prefix:
- `DIETTUBE_SOURCE_DIR` - Video source directory
- `DIETTUBE_TEMP_DIR` - Processing temp directory
- `DIETTUBE_CONFIG_DIR` - Database storage
- `DIETTUBE_VIDEO_PRESET` - SVT-AV1 preset (0-13)
- `DIETTUBE_VIDEO_CRF` - Quality factor (0-63)
- `DIETTUBE_AUDIO_BITRATE` - Opus bitrate
- `DIETTUBE_MAX_THREADS` - CPU thread limit (0=auto)
- `DIETTUBE_ORIGINAL_FILE_STRATEGY` - "trash" or "archive"

## API Endpoints

- `GET /api/tasks/` - List tasks with pagination
- `GET /api/tasks/progress` - Current task progress (in-memory)
- `GET /api/tasks/stats` - Statistics summary
- `POST /api/tasks/scan` - Trigger directory scan
- `POST /api/tasks/{id}/cancel` - Cancel current task
- `POST /api/tasks/{id}/retry` - Retry failed task
- `GET /api/settings/` - Current settings
- `GET /api/settings/command-preview` - FFmpeg command preview
- `GET /api/trash/` - List trash files
- `POST /api/trash/empty` - Empty trash

## Common Modifications

### Adding new video format support
Edit `config.py` → `video_extensions` set

### Changing encoding parameters
Modify `transcoder.py` → `build_ffmpeg_command()`

### Adding new task states
Update `models.py` → `TaskStatus` enum and handle in `task_manager.py`
