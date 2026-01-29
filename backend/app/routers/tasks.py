from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import Task, TaskStatus, ProcessingStats
from app.services.task_manager import task_manager
from app.services.scanner import run_scan

router = APIRouter()


class TaskResponse(BaseModel):
    id: int
    source_path: str
    relative_path: str
    status: str
    original_size: int
    new_size: int
    original_duration: float
    new_duration: float
    error_message: Optional[str]

    class Config:
        from_attributes = True


class TaskProgressResponse(BaseModel):
    task_id: int
    fps: float
    speed: float
    progress: float
    eta_seconds: float
    status: str


class StatsResponse(BaseModel):
    total_saved_bytes: int
    total_processed_files: int
    pending_count: int
    in_progress_count: int
    completed_count: int
    failed_count: int


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Task)
    count_query = select(func.count(Task.id))

    if status:
        try:
            status_enum = TaskStatus(status)
            query = query.where(Task.status == status_enum)
            count_query = count_query.where(Task.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
    )


@router.get("/progress", response_model=Optional[TaskProgressResponse])
async def get_current_progress():
    progress = task_manager.current_progress
    if not progress:
        return None
    return TaskProgressResponse(
        task_id=progress.task_id,
        fps=progress.fps,
        speed=progress.speed,
        progress=progress.progress,
        eta_seconds=progress.eta_seconds,
        status=progress.status,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    stats_result = await db.execute(select(ProcessingStats).limit(1))
    stats = stats_result.scalar_one_or_none()

    pending = await db.execute(
        select(func.count(Task.id)).where(Task.status == TaskStatus.PENDING)
    )
    in_progress = await db.execute(
        select(func.count(Task.id)).where(
            Task.status.in_(
                [
                    TaskStatus.SCANNING,
                    TaskStatus.TRANSCODING,
                    TaskStatus.VERIFYING,
                    TaskStatus.INSTALLING,
                ]
            )
        )
    )
    completed = await db.execute(
        select(func.count(Task.id)).where(Task.status == TaskStatus.COMPLETED)
    )
    failed = await db.execute(
        select(func.count(Task.id)).where(Task.status == TaskStatus.FAILED)
    )

    return StatsResponse(
        total_saved_bytes=stats.total_saved_bytes if stats else 0,
        total_processed_files=stats.total_processed_files if stats else 0,
        pending_count=pending.scalar() or 0,
        in_progress_count=in_progress.scalar() or 0,
        completed_count=completed.scalar() or 0,
        failed_count=failed.scalar() or 0,
    )


@router.post("/scan")
async def trigger_scan():
    created = await run_scan()
    return {"message": f"Scan complete, created {created} new tasks"}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int):
    progress = task_manager.current_progress
    if progress and progress.task_id == task_id:
        await task_manager.cancel_current_task()
        return {"message": "Task cancellation requested"}
    raise HTTPException(status_code=400, detail="Task is not currently running")


@router.post("/{task_id}/retry")
async def retry_task(task_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import update

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=400, detail="Only failed or cancelled tasks can be retried"
        )

    await db.execute(
        update(Task)
        .where(Task.id == task_id)
        .values(status=TaskStatus.PENDING, error_message=None)
    )
    await db.commit()

    return {"message": "Task queued for retry"}
