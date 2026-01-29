from __future__ import annotations
import shutil
import logging

from sqlalchemy import select, update

from app.services.settings_service import get_settings
from app.database import async_session_maker
from app.models import Task, TaskStatus

logger = logging.getLogger(__name__)


async def perform_recovery():
    settings = get_settings()

    async with async_session_maker() as session:
        in_progress_statuses = [
            TaskStatus.SCANNING,
            TaskStatus.TRANSCODING,
            TaskStatus.VERIFYING,
            TaskStatus.INSTALLING,
        ]

        result = await session.execute(
            select(Task).where(Task.status.in_(in_progress_statuses))
        )
        stuck_tasks = result.scalars().all()

        for task in stuck_tasks:
            logger.warning(f"Resetting stuck task {task.id}: {task.source_path}")
            await session.execute(
                update(Task)
                .where(Task.id == task.id)
                .values(
                    status=TaskStatus.PENDING,
                    error_message="Reset after system restart",
                )
            )

        await session.commit()

        if stuck_tasks:
            logger.info(f"Reset {len(stuck_tasks)} stuck tasks to pending")

    processing_dir = settings.processing_dir
    if processing_dir.exists():
        for item in processing_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    logger.info(f"Cleaned up temporary file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    logger.info(f"Cleaned up temporary directory: {item}")
            except Exception as e:
                logger.error(f"Failed to clean up {item}: {e}")

    logger.info("Recovery completed")
