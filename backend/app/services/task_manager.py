from __future__ import annotations
import asyncio
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select, update, func as sql_func, delete

from app.services.settings_service import get_settings
from app.database import async_session_maker
from app.models import Task, TaskStatus, ProcessingStats, TaskLog, LogLevel
from app.services.scanner import get_video_metadata
from app.services.transcoder import (
    transcode_file,
    TranscodeProgress,
    build_ffmpeg_command,
    resolve_resolution,
)
from app.services.verifier import verify_output

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class TaskProgress:
    task_id: int = 0
    fps: float = 0.0
    speed: float = 0.0
    progress: float = 0.0
    eta_seconds: float = 0.0
    status: str = ""


@dataclass
class TaskManagerState:
    is_running: bool = False
    is_paused: bool = False
    current_task_id: int | None = None
    current_progress: TaskProgress | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    pause_event: asyncio.Event = field(default_factory=asyncio.Event)
    worker_task: asyncio.Task | None = None

    def __post_init__(self):
        self.pause_event.set()


class TaskManager:
    def __init__(self):
        self._state = TaskManagerState()

    @property
    def is_running(self) -> bool:
        return self._state.is_running

    @property
    def is_paused(self) -> bool:
        return self._state.is_paused

    @property
    def current_progress(self) -> TaskProgress | None:
        return self._state.current_progress

    def start(self):
        if self._state.is_running:
            return
        self._state.is_running = True
        self._state.cancel_event.clear()
        self._state.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("TaskManager started")

    async def stop(self):
        self._state.is_running = False
        self._state.cancel_event.set()
        self._state.pause_event.set()
        if self._state.worker_task:
            self._state.worker_task.cancel()
            try:
                await self._state.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("TaskManager stopped")

    def pause(self):
        if not self._state.is_paused:
            self._state.is_paused = True
            self._state.pause_event.clear()
            logger.info("TaskManager paused")

    def resume(self):
        if self._state.is_paused:
            self._state.is_paused = False
            self._state.pause_event.set()
            logger.info("TaskManager resumed")

    async def cancel_current_task(self):
        self._state.cancel_event.set()

    async def _worker_loop(self):
        while self._state.is_running:
            try:
                await self._state.pause_event.wait()

                task = await self._get_next_pending_task()
                if task is None:
                    await asyncio.sleep(5)
                    continue

                self._state.cancel_event.clear()
                await self._process_task(task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Worker loop error: {e}")
                await asyncio.sleep(5)

    async def _get_next_pending_task(self) -> Task | None:
        async with async_session_maker() as session:
            result = await session.execute(
                select(Task)
                .where(Task.status == TaskStatus.PENDING)
                .order_by(Task.created_at)
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _process_task(self, task: Task):
        settings = get_settings()
        self._state.current_task_id = task.id
        self._state.current_progress = TaskProgress(
            task_id=task.id, status="transcoding"
        )

        source_path = Path(task.source_path)
        output_path = source_path.with_suffix(".mkv")
        temp_output = settings.processing_dir / f"{task.id}_{source_path.stem}.mkv"

        async with async_session_maker() as session:
            await session.execute(delete(TaskLog).where(TaskLog.task_id == task.id))
            await session.commit()

        try:
            await self._log(task.id, f"开始处理: {task.relative_path}")
            await self._log(task.id, f"原始文件大小: {task.original_size:,} 字节")

            await self._update_task_status(task.id, TaskStatus.TRANSCODING)

            metadata = await get_video_metadata(source_path)
            if metadata:
                await self._log_media_info(task.id, metadata)
            original_duration = (
                float(metadata.get("format", {}).get("duration", 0)) if metadata else 0
            )

            target_resolution = None
            if metadata:
                streams = metadata.get("streams", [])
                for stream in streams:
                    if stream.get("codec_type") == "video":
                        width = stream.get("width", 0)
                        height = stream.get("height", 0)
                        if width > 0 and height > 0:
                            target_resolution = resolve_resolution(
                                width,
                                height,
                                settings.max_long_side,
                                settings.max_short_side,
                            )
                            if target_resolution:
                                await self._log(
                                    task.id,
                                    f"缩放: {width}x{height} -> {target_resolution[0]}x{target_resolution[1]}",
                                )
                        break

            await self._update_task_duration(task.id, original_duration)

            ffmpeg_cmd = build_ffmpeg_command(
                source_path, temp_output, original_duration, target_resolution
            )
            await self._log(task.id, f"ffmpeg: {' '.join(ffmpeg_cmd)}")

            await self._log(
                task.id,
                f"开始转码 (preset={settings.video_preset}, crf={settings.video_crf})",
            )

            def on_progress(p: TranscodeProgress):
                if self._state.current_progress:
                    self._state.current_progress.fps = p.fps
                    self._state.current_progress.speed = p.speed
                    self._state.current_progress.progress = p.progress
                    self._state.current_progress.eta_seconds = p.eta_seconds

            result = await transcode_file(
                source_path,
                temp_output,
                original_duration,
                on_progress=on_progress,
                cancel_event=self._state.cancel_event,
            )

            if not result.success:
                # 用户主动取消时，将任务重置为等待状态
                if result.error_message == "Cancelled by user":
                    await self._log(
                        task.id, "任务被用户取消，已重置为等待状态", LogLevel.WARNING
                    )
                    await self._reset_task_to_pending(task.id)
                    return
                await self._log(
                    task.id, f"转码失败: {result.error_message}", LogLevel.ERROR
                )
                await self._fail_task(task.id, result.error_message)
                return

            await self._log(task.id, "转码完成，开始校验")
            await self._update_task_status(task.id, TaskStatus.VERIFYING)
            self._state.current_progress.status = "verifying"

            verify_result = await verify_output(
                source_path, temp_output, original_duration
            )
            if not verify_result.success:
                await self._log(
                    task.id, f"校验失败: {verify_result.error_message}", LogLevel.ERROR
                )
                if temp_output.exists():
                    temp_output.unlink()
                await self._fail_task(task.id, verify_result.error_message)
                return

            await self._log(
                task.id, f"校验通过，新文件大小: {verify_result.new_size:,} 字节"
            )
            await self._update_task_status(task.id, TaskStatus.INSTALLING)
            self._state.current_progress.status = "installing"

            await self._log(
                task.id, f"移动原始文件到: {settings.original_file_strategy}"
            )
            await self._handle_original_file(source_path, task.relative_path)

            shutil.move(str(temp_output), str(output_path))

            saved_bytes = task.original_size - verify_result.new_size
            saved_percent = (
                (saved_bytes / task.original_size * 100)
                if task.original_size > 0
                else 0
            )
            await self._log(
                task.id, f"处理完成，节省: {saved_bytes:,} 字节 ({saved_percent:.1f}%)"
            )

            await self._complete_task(
                task.id,
                verify_result.new_size,
                verify_result.new_duration,
                saved_bytes,
            )

        except Exception as e:
            logger.exception(f"Task {task.id} failed: {e}")
            await self._log(task.id, f"处理异常: {str(e)}", LogLevel.ERROR)
            if temp_output.exists():
                temp_output.unlink()
            await self._fail_task(task.id, str(e))
        finally:
            self._state.current_task_id = None
            self._state.current_progress = None

    async def _handle_original_file(self, source_path: Path, relative_path: str):
        settings = get_settings()

        if settings.original_file_strategy == "trash":
            dest_dir = settings.trash_dir / Path(relative_path).parent
        else:
            if settings.archive_dir:
                dest_dir = settings.archive_dir / Path(relative_path).parent
            else:
                dest_dir = settings.trash_dir / Path(relative_path).parent

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / source_path.name

        shutil.move(str(source_path), str(dest_path))
        logger.info(f"Moved original to: {dest_path}")

    async def _update_task_status(self, task_id: int, status: TaskStatus):
        async with async_session_maker() as session:
            await session.execute(
                update(Task).where(Task.id == task_id).values(status=status)
            )
            await session.commit()

    async def _update_task_duration(self, task_id: int, duration: float):
        async with async_session_maker() as session:
            await session.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(original_duration=duration)
            )
            await session.commit()

    async def _fail_task(self, task_id: int, error_message: str):
        async with async_session_maker() as session:
            await session.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(status=TaskStatus.FAILED, error_message=error_message)
            )
            await session.commit()
        logger.error(f"Task {task_id} failed: {error_message}")

    async def _reset_task_to_pending(self, task_id: int):
        async with async_session_maker() as session:
            await session.execute(
                update(Task).where(Task.id == task_id).values(status=TaskStatus.PENDING)
            )
            await session.commit()
        logger.info(f"Task {task_id} reset to pending")

    async def _complete_task(
        self,
        task_id: int,
        new_size: int,
        new_duration: float,
        saved_bytes: int,
    ):
        async with async_session_maker() as session:
            await session.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(
                    status=TaskStatus.COMPLETED,
                    new_size=new_size,
                    new_duration=new_duration,
                    error_message=None,
                )
            )

            result = await session.execute(select(ProcessingStats).limit(1))
            stats = result.scalar_one_or_none()

            if stats:
                await session.execute(
                    update(ProcessingStats)
                    .where(ProcessingStats.id == stats.id)
                    .values(
                        total_saved_bytes=ProcessingStats.total_saved_bytes
                        + saved_bytes,
                        total_processed_files=ProcessingStats.total_processed_files + 1,
                    )
                )
            else:
                new_stats = ProcessingStats(
                    total_saved_bytes=saved_bytes,
                    total_processed_files=1,
                )
                session.add(new_stats)

            await session.commit()

        logger.info(f"Task {task_id} completed, saved {saved_bytes} bytes")

    async def _log(self, task_id: int, message: str, level: LogLevel = LogLevel.INFO):
        async with async_session_maker() as session:
            log_entry = TaskLog(task_id=task_id, level=level, message=message)
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)
            log_broadcaster.broadcast(
                task_id,
                {
                    "id": log_entry.id,
                    "level": level.value,
                    "message": message,
                    "created_at": log_entry.created_at.isoformat()
                    if log_entry.created_at
                    else "",
                },
            )

    async def _log_media_info(self, task_id: int, metadata: dict):
        import json

        await self._log(task_id, f"ffprobe:\n{json.dumps(metadata, indent=2)}")


class LogBroadcaster:
    """日志广播器，管理 SSE 连接"""

    def __init__(self):
        self._subscribers: dict[int, list[asyncio.Queue]] = {}

    def subscribe(self, task_id: int) -> asyncio.Queue:
        """订阅指定任务的日志"""
        queue: asyncio.Queue = asyncio.Queue()
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: int, queue: asyncio.Queue):
        """取消订阅"""
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
                if not self._subscribers[task_id]:
                    del self._subscribers[task_id]
            except ValueError:
                pass

    def broadcast(self, task_id: int, log_data: dict):
        """广播日志到所有订阅者"""
        if task_id in self._subscribers:
            for queue in self._subscribers[task_id]:
                try:
                    queue.put_nowait(log_data)
                except asyncio.QueueFull:
                    pass


log_broadcaster = LogBroadcaster()
task_manager = TaskManager()
