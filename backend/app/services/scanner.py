from __future__ import annotations
import asyncio
import subprocess
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pathspec

from app.services.settings_service import get_settings
from app.database import async_session_maker
from app.models import Task, TaskStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def build_ffprobe_command(file_path: Path) -> list[str]:
    return [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]


async def get_video_metadata(file_path: Path) -> dict | None:
    cmd = build_ffprobe_command(file_path)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return json.loads(stdout.decode())
    except Exception as e:
        logger.error(f"Failed to get metadata for {file_path}: {e}")
    return None


def is_already_processed(metadata: dict, marker: str) -> bool:
    if not metadata or "format" not in metadata:
        return False
    tags = metadata.get("format", {}).get("tags", {})
    comment = tags.get("comment", "") or tags.get("COMMENT", "")
    return marker in comment


async def scan_directory() -> list[Path]:
    settings = get_settings()
    source_dir = settings.source_path
    extensions = settings.video_extensions
    marker = settings.diettube_marker

    ignore_spec = None
    if settings.scan_ignore_patterns.strip():
        patterns = [
            p.strip() for p in settings.scan_ignore_patterns.split("\n") if p.strip()
        ]
        if patterns:
            ignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    new_files: list[Path] = []

    if not source_dir.exists():
        logger.warning(f"Source directory does not exist: {source_dir}")
        return new_files

    for file_path in source_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in extensions:
            continue

        if ignore_spec:
            relative_path = file_path.relative_to(source_dir)
            if ignore_spec.match_file(str(relative_path)):
                logger.debug(f"Skipping ignored file: {relative_path}")
                continue

        metadata = await get_video_metadata(file_path)
        if metadata and is_already_processed(metadata, marker):
            continue

        new_files.append(file_path)

    return new_files


async def create_tasks_for_files(files: list[Path]) -> int:
    settings = get_settings()
    source_dir = settings.source_path
    created_count = 0

    async with async_session_maker() as session:
        for file_path in files:
            relative_path = file_path.relative_to(source_dir)

            from sqlalchemy import select

            existing = await session.execute(
                select(Task).where(Task.source_path == str(file_path))
            )
            if existing.scalar_one_or_none():
                continue

            task = Task(
                source_path=str(file_path),
                relative_path=str(relative_path),
                status=TaskStatus.PENDING,
                original_size=file_path.stat().st_size,
            )
            session.add(task)
            created_count += 1

        await session.commit()

    return created_count


async def run_scan() -> int:
    logger.info("Starting directory scan...")
    files = await scan_directory()
    logger.info(f"Found {len(files)} unprocessed video files")

    created = await create_tasks_for_files(files)
    logger.info(f"Created {created} new tasks")

    return created


def get_ignored_files(source_dir: str, scan_ignore_patterns: str) -> list[str]:
    """Get list of video files that would be ignored by given patterns.

    Returns relative paths of all video files matching ignore patterns.
    Does not check metadata - purely pattern-based filtering.
    """
    settings = get_settings()
    source_path = Path(source_dir)
    extensions = settings.video_extensions

    if not scan_ignore_patterns.strip():
        return []

    patterns = [p.strip() for p in scan_ignore_patterns.split("\n") if p.strip()]
    if not patterns:
        return []

    ignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    ignored_files: list[str] = []

    if not source_path.exists():
        return []

    for file_path in source_path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in extensions:
            continue

        relative_path = file_path.relative_to(source_path)
        if ignore_spec.match_file(str(relative_path)):
            ignored_files.append(str(relative_path))

    return sorted(ignored_files)
