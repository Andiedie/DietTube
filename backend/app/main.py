from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from app.database import init_db
from app.services.settings_service import settings_manager, get_settings
from app.services.recovery import perform_recovery
from app.services.task_manager import task_manager
from app.routers import tasks, settings as settings_router, trash
from app.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    general_exception_handler,
)

logging.basicConfig(level=logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings_manager.load_from_env()
    settings = get_settings()

    settings.config_path.mkdir(parents=True, exist_ok=True)
    settings.temp_path.mkdir(parents=True, exist_ok=True)
    settings.trash_dir.mkdir(parents=True, exist_ok=True)
    settings.processing_dir.mkdir(parents=True, exist_ok=True)

    await init_db()
    logger.info("Database initialized")

    await settings_manager.load_from_db()
    logger.info("Settings loaded from database")

    await perform_recovery()
    logger.info("Recovery completed")

    task_manager.start()
    logger.info("Task manager started")

    yield

    await task_manager.stop()
    logger.info("Task manager stopped")


app = FastAPI(title="DietTube", version="1.0.0", lifespan=lifespan)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
app.include_router(trash.router, prefix="/api/trash", tags=["trash"])

static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = static_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_path / "index.html")
