# DietTube AI Maintainer Guide

## Project Overview

DietTube is a self-hosted video transcoding solution for home NAS/media library scenarios. It automatically compresses videos using AV1+Opus codecs for maximum space savings.

## Architecture

### Tech Stack
- **Backend**: Python FastAPI with async SQLAlchemy (SQLite)
- **Frontend**: React + Vite + TailwindCSS (SPA)
- **Transcoding**: FFmpeg with SVT-AV1 (10-bit) and libopus
- **Deployment**: Docker single container with PUID/PGID support

### Directory Structure

```
DietTube/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point with lifespan
│   │   ├── database.py          # SQLAlchemy async setup
│   │   ├── models.py            # Task and ProcessingStats models
│   │   ├── errors.py            # Unified error handling (AppError, NotFoundError, etc.)
│   │   ├── routers/             # API endpoints
│   │   │   ├── tasks.py         # Task CRUD, scan, progress, queue pause/resume
│   │   │   ├── settings.py      # Settings read/update, command preview
│   │   │   └── trash.py         # Trash management
│   │   └── services/            # Business logic
│   │       ├── scanner.py       # Directory scanning, metadata check
│   │       ├── transcoder.py    # FFmpeg integration, progress parsing
│   │       ├── verifier.py      # Output validation
│   │       ├── task_manager.py  # Async task queue, pause/resume, in-memory progress
│   │       ├── recovery.py      # Startup recovery logic
│   │       └── settings_service.py  # Runtime settings management (THE settings system)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # React entry
│   │   ├── App.tsx              # Layout with navigation
│   │   ├── pages/               # Dashboard, Settings, Trash
│   │   ├── components/          # Toast, Dialog, Pagination, etc.
│   │   └── lib/                 # API client, utilities
│   └── package.json
├── Dockerfile                   # Multi-stage build with PUID/PGID
├── docker-entrypoint.sh         # User permission handling
└── docker-compose.yml           # Example deployment
```

## Key Design Decisions

### Settings System (IMPORTANT)

**Use `settings_service.py`, NOT `config.py`** (config.py has been removed).

The settings system works as follows:
1. `RuntimeSettings` class holds all configurable options
2. Settings are persisted to database (`settings` table) as JSON
3. On startup, settings load from DB (or use defaults)
4. Changes via API take effect immediately (no restart needed)
5. Environment variables (`DIETTUBE_*`) are read at startup as initial defaults

Key file: `backend/app/services/settings_service.py`

### In-Memory Progress
Task progress (FPS, ETA, percentage) is stored in `TaskManager._state.current_progress` rather than the database to avoid I/O bottlenecks.

### Recovery Mechanism
On startup, `perform_recovery()`:
1. Resets stuck tasks (status in progress states) to PENDING
2. Cleans temporary processing directory

### Transcoding Pipeline
1. Scanner → finds unprocessed videos via metadata marker
2. Transcoder → FFmpeg with SVT-AV1 (10-bit `yuv420p10le`) + Opus
3. Verifier → duration/size validation (1% tolerance, min 10KB)
4. Install → move original to trash/archive, replace with new file

### Processing Marker
Files are marked as processed by injecting `DietTube-Processed` into the `comment` metadata field.

### Error Handling
Unified error system in `errors.py`:
- `AppError` - base class
- `NotFoundError` - 404 errors
- `ValidationError` - 400 errors  
- `TaskError` - task-specific errors

API error response format:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

## Settings Reference

All settings are managed via `RuntimeSettings` in `settings_service.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `source_dir` | `/source` | Video source directory |
| `temp_dir` | `/temp` | Processing temp directory |
| `config_dir` | `/config` | Database storage |
| `video_preset` | 6 | SVT-AV1 preset (0-13, lower=slower+better) |
| `video_crf` | 30 | Quality factor (0-63, lower=better quality) |
| `video_film_grain` | 0 | Film grain synthesis (0-50) |
| `audio_bitrate` | 64k | Opus audio bitrate |
| `max_threads` | 0 | CPU thread limit (0=auto) |
| `original_file_strategy` | trash | "trash" or "archive" |
| `archive_dir` | null | Archive directory (when strategy=archive) |
| `diettube_marker` | DietTube-Processed | Metadata marker string |
| `duration_tolerance` | 0.01 | Max duration difference (1%) |
| `min_file_size` | 10240 | Minimum output size (10KB) |

Environment variables use `DIETTUBE_` prefix (e.g., `DIETTUBE_VIDEO_CRF=28`).

## API Endpoints

### Tasks
- `GET /api/tasks/` - List tasks with pagination and search
- `GET /api/tasks/progress` - Current task progress (in-memory)
- `GET /api/tasks/stats` - Statistics summary
- `GET /api/tasks/queue/status` - Queue pause state
- `POST /api/tasks/scan` - Trigger directory scan
- `POST /api/tasks/{id}/cancel` - Cancel current task
- `POST /api/tasks/{id}/retry` - Retry failed/cancelled task
- `POST /api/tasks/queue/pause` - Pause queue (with optional interrupt_current)
- `POST /api/tasks/queue/resume` - Resume queue

### Settings
- `GET /api/settings/` - Current settings
- `PUT /api/settings/` - Update settings (persisted to DB)
- `POST /api/settings/command-preview` - FFmpeg command preview (accepts temp settings)

### Trash
- `GET /api/trash/` - List trash files
- `POST /api/trash/empty` - Empty trash

## Frontend Components

### Pages
- `Dashboard.tsx` - Task list with search, pagination, pause dialog
- `Settings.tsx` - Settings form with live command preview
- `Trash.tsx` - Trash file management

### Key Components
- `Toast.tsx` - Notification system (success/error/info)
- `Dialog.tsx` - Modal dialogs
- `Pagination.tsx` - Pagination controls
- `PageSizeSelector.tsx` - Items per page selector

### API Client
`lib/api.ts` - Centralized API client with error handling

## Common Modifications

### Adding new video format support
Edit `settings_service.py` → `video_extensions` set in `RuntimeSettings`

### Changing encoding parameters
Modify `transcoder.py` → `build_ffmpeg_command()`

Note: 10-bit color depth is hardcoded as `yuv420p10le` for AV1 quality benefits.

### Adding new task states
Update `models.py` → `TaskStatus` enum and handle in `task_manager.py`

### Adding new settings
1. Add field to `RuntimeSettings` class in `settings_service.py`
2. Add to `SETTINGS_FIELDS` list if it should be persisted
3. Update frontend `Settings.tsx` form

## Docker Deployment

### PUID/PGID Support
The container supports running as a specific user via environment variables:
- `PUID` - User ID (default: 1000)
- `PGID` - Group ID (default: 1000)

This is handled by `docker-entrypoint.sh` using `gosu`.

### Volume Mounts
```yaml
volumes:
  - ./source:/source      # Video files
  - ./temp:/temp          # Processing temp
  - ./config:/config      # Database
```

## Development

### Local Development
```bash
# Backend
cd backend && ./dev.sh

# Frontend  
cd frontend && pnpm dev

# Test environment setup
./scripts/setup-test-env.sh
```

### Building Docker Image
```bash
docker build -t diettube .
docker run -p 8000:8000 \
  -e PUID=1000 -e PGID=1000 \
  -v ./data/source:/source \
  -v ./data/temp:/temp \
  -v ./data/config:/config \
  diettube
```
