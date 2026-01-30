from __future__ import annotations
import asyncio
import json
import shutil
from enum import Enum
from pathlib import Path
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import Task, TaskStatus, ProcessingStats, TaskLog
from app.services.task_manager import task_manager, log_broadcaster
from app.services.scanner import run_scan
from app.services.scan_progress import scan_progress_manager
from app.services.settings_service import get_settings
from app.errors import NotFoundError, ValidationError, TaskError

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


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class SortBy(str, Enum):
    created_at = "created_at"
    updated_at = "updated_at"


STATUS_GROUP_MAP = {
    "pending": [TaskStatus.PENDING],
    "in_progress": [
        TaskStatus.SCANNING,
        TaskStatus.TRANSCODING,
        TaskStatus.VERIFYING,
        TaskStatus.INSTALLING,
    ],
    "completed": [TaskStatus.COMPLETED],
    "failed": [TaskStatus.FAILED],
    "cancelled": [TaskStatus.CANCELLED],
    "rolled_back": [TaskStatus.ROLLED_BACK],
}


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: SortBy = SortBy.created_at,
    sort_order: SortOrder = SortOrder.desc,
    db: AsyncSession = Depends(get_db),
):
    """
    查询任务列表

    - status: pending | in_progress | completed | failed | cancelled | rolled_back（可逗号分隔多个）
    - search: 按 relative_path 模糊搜索
    - limit/offset: 分页
    - sort_by: created_at | updated_at
    - sort_order: asc | desc
    """
    query = select(Task)
    count_query = select(func.count(Task.id))

    if status:
        status_list = [s.strip() for s in status.split(",")]
        all_statuses = []
        for s in status_list:
            if s in STATUS_GROUP_MAP:
                all_statuses.extend(STATUS_GROUP_MAP[s])
        if all_statuses:
            query = query.where(Task.status.in_(all_statuses))
            count_query = count_query.where(Task.status.in_(all_statuses))

    if search:
        search_pattern = f"%{search}%"
        query = query.where(Task.relative_path.ilike(search_pattern))
        count_query = count_query.where(Task.relative_path.ilike(search_pattern))

    sort_column = Task.created_at if sort_by == SortBy.created_at else Task.updated_at
    if sort_order == SortOrder.asc:
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

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
    result = await run_scan()
    parts = []
    if result.created > 0:
        parts.append(f"添加 {result.created} 个新任务")
    if result.removed > 0:
        parts.append(f"移除 {result.removed} 个被忽略的任务")
    if not parts:
        message = "扫描完成，无变化"
    else:
        message = "扫描完成，" + "，".join(parts)
    return {
        "message": message,
        "created": result.created,
        "removed": result.removed,
    }


class ScanProgressResponse(BaseModel):
    is_scanning: bool
    phase: str
    current_file: str
    files_checked: int
    files_found: int
    tasks_created: int
    tasks_removed: int


@router.get("/scan/progress", response_model=ScanProgressResponse)
async def get_scan_progress():
    progress = scan_progress_manager.progress
    return ScanProgressResponse(
        is_scanning=progress.is_scanning,
        phase=progress.phase.value,
        current_file=progress.current_file,
        files_checked=progress.files_checked,
        files_found=progress.files_found,
        tasks_created=progress.tasks_created,
        tasks_removed=progress.tasks_removed,
    )


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int):
    progress = task_manager.current_progress
    if progress and progress.task_id == task_id:
        await task_manager.cancel_current_task()
        return {"message": "Task cancellation requested"}
    raise TaskError("该任务当前未在运行", {"task_id": task_id})


@router.post("/{task_id}/retry")
async def retry_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError("任务不存在", {"task_id": task_id})

    if task.status not in [
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.ROLLED_BACK,
    ]:
        raise TaskError(
            "只有失败、已取消或已回滚的任务才能重试",
            {"task_id": task_id, "current_status": task.status.value},
        )

    await db.execute(
        update(Task)
        .where(Task.id == task_id)
        .values(status=TaskStatus.PENDING, error_message=None)
    )
    await db.commit()

    return {"message": "Task queued for retry"}


class QueueStatusResponse(BaseModel):
    is_paused: bool
    is_running: bool
    has_active_task: bool


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status():
    return QueueStatusResponse(
        is_paused=task_manager.is_paused,
        is_running=task_manager.is_running,
        has_active_task=task_manager.current_progress is not None,
    )


class PauseRequest(BaseModel):
    immediate: bool = False


@router.post("/queue/pause")
async def pause_queue(request: PauseRequest | None = None):
    task_manager.pause()
    immediate = request.immediate if request else False
    if immediate and task_manager.current_progress:
        await task_manager.cancel_current_task()
        return {
            "message": "队列已暂停，当前任务已中断",
            "is_paused": True,
            "interrupted": True,
        }
    return {
        "message": "队列已暂停，当前任务完成后停止",
        "is_paused": True,
        "interrupted": False,
    }


@router.post("/queue/resume")
async def resume_queue():
    task_manager.resume()
    return {"message": "队列已继续", "is_paused": False}


@router.post("/{task_id}/rollback")
async def rollback_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """回滚已完成的任务：恢复原始文件，删除转码后的文件，状态改为已回滚"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundError("任务不存在", {"task_id": task_id})

    if task.status != TaskStatus.COMPLETED:
        raise TaskError(
            "只有已完成的任务才能回滚",
            {"task_id": task_id, "current_status": task.status.value},
        )

    settings = get_settings()
    source_path = Path(task.source_path)
    transcoded_path = source_path.with_suffix(".mkv")
    relative_path = Path(task.relative_path)

    # 查找原始文件：先检查 trash，再检查 archive
    original_backup = None
    backup_locations = [settings.trash_dir / relative_path]
    if settings.archive_dir:
        backup_locations.append(Path(settings.archive_dir) / relative_path)

    for loc in backup_locations:
        if loc.exists():
            original_backup = loc
            break

    if not original_backup:
        raise TaskError(
            "原始文件不存在，无法回滚",
            {"searched_paths": [str(p) for p in backup_locations]},
        )

    # 删除转码后的文件
    if transcoded_path.exists():
        transcoded_path.unlink()

    # 恢复原始文件
    source_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(original_backup), str(source_path))

    # 清理空目录
    try:
        original_backup.parent.rmdir()
    except OSError:
        pass  # 目录非空，忽略

    # 更新统计数据
    saved_bytes = task.original_size - task.new_size
    stats_result = await db.execute(select(ProcessingStats).limit(1))
    stats = stats_result.scalar_one_or_none()
    if stats:
        await db.execute(
            update(ProcessingStats)
            .where(ProcessingStats.id == stats.id)
            .values(
                total_saved_bytes=ProcessingStats.total_saved_bytes - saved_bytes,
                total_processed_files=ProcessingStats.total_processed_files - 1,
            )
        )

    # 更新任务状态为已回滚
    await db.execute(
        update(Task).where(Task.id == task_id).values(status=TaskStatus.ROLLED_BACK)
    )
    await db.commit()

    return {
        "message": "任务已回滚，原始文件已恢复",
        "restored_path": str(source_path),
    }


class TaskLogResponse(BaseModel):
    id: int
    level: str
    message: str
    created_at: str

    class Config:
        from_attributes = True


class TaskLogsResponse(BaseModel):
    logs: list[TaskLogResponse]


@router.get("/{task_id}/logs", response_model=TaskLogsResponse)
async def get_task_logs(task_id: int, db: AsyncSession = Depends(get_db)):
    """获取任务执行日志"""
    # 先检查任务是否存在
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("任务不存在", {"task_id": task_id})

    # 获取日志
    logs_result = await db.execute(
        select(TaskLog).where(TaskLog.task_id == task_id).order_by(TaskLog.created_at)
    )
    logs = logs_result.scalars().all()

    return TaskLogsResponse(
        logs=[
            TaskLogResponse(
                id=log.id,
                level=log.level.value,
                message=log.message,
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ]
    )


@router.get("/{task_id}/logs/stream")
async def stream_task_logs(task_id: int, db: AsyncSession = Depends(get_db)):
    """SSE 流式推送任务日志"""
    # 先检查任务是否存在
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundError("任务不存在", {"task_id": task_id})

    async def event_generator():
        queue = log_broadcaster.subscribe(task_id)
        try:
            while True:
                try:
                    # 等待新日志，超时 30 秒发送心跳
                    log_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(log_data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            log_broadcaster.unsubscribe(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
