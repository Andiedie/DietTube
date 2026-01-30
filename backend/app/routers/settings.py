from __future__ import annotations
import os
import uuid
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.settings_service import get_settings, settings_manager
from app.services.transcoder import get_ffmpeg_command_preview, build_command_preview
from app.services.scanner import get_ignored_files

router = APIRouter()


class SettingsResponse(BaseModel):
    source_dir: str
    temp_dir: str
    config_dir: str
    video_preset: int
    video_crf: int
    video_film_grain: int
    audio_bitrate: str
    max_threads: int
    original_file_strategy: str
    archive_dir: str
    max_long_side: int
    max_short_side: int
    start_paused: bool
    scan_ignore_patterns: str


class SettingsUpdate(BaseModel):
    source_dir: Optional[str] = None
    temp_dir: Optional[str] = None
    config_dir: Optional[str] = None
    video_preset: Optional[int] = None
    video_crf: Optional[int] = None
    video_film_grain: Optional[int] = None
    audio_bitrate: Optional[str] = None
    max_threads: Optional[int] = None
    original_file_strategy: Optional[str] = None
    archive_dir: Optional[str] = None
    max_long_side: Optional[int] = None
    max_short_side: Optional[int] = None
    start_paused: Optional[bool] = None
    scan_ignore_patterns: Optional[str] = None


class CommandPreviewResponse(BaseModel):
    command: str


@router.get("/", response_model=SettingsResponse)
async def get_current_settings():
    settings = get_settings()
    return SettingsResponse(
        source_dir=settings.source_dir,
        temp_dir=settings.temp_dir,
        config_dir=settings.config_dir,
        video_preset=settings.video_preset,
        video_crf=settings.video_crf,
        video_film_grain=settings.video_film_grain,
        audio_bitrate=settings.audio_bitrate,
        max_threads=settings.max_threads,
        original_file_strategy=settings.original_file_strategy,
        archive_dir=settings.archive_dir or "",
        max_long_side=settings.max_long_side,
        max_short_side=settings.max_short_side,
        start_paused=settings.start_paused,
        scan_ignore_patterns=settings.scan_ignore_patterns,
    )


@router.put("/", response_model=SettingsResponse)
async def update_settings(updates: SettingsUpdate):
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}

    if update_dict:
        await settings_manager.save_to_db(update_dict)

    settings = get_settings()
    return SettingsResponse(
        source_dir=settings.source_dir,
        temp_dir=settings.temp_dir,
        config_dir=settings.config_dir,
        video_preset=settings.video_preset,
        video_crf=settings.video_crf,
        video_film_grain=settings.video_film_grain,
        audio_bitrate=settings.audio_bitrate,
        max_threads=settings.max_threads,
        original_file_strategy=settings.original_file_strategy,
        archive_dir=settings.archive_dir or "",
        max_long_side=settings.max_long_side,
        max_short_side=settings.max_short_side,
        start_paused=settings.start_paused,
        scan_ignore_patterns=settings.scan_ignore_patterns,
    )


@router.get("/command-preview", response_model=CommandPreviewResponse)
async def get_command_preview():
    return CommandPreviewResponse(command=get_ffmpeg_command_preview())


class CommandPreviewRequest(BaseModel):
    video_preset: int
    video_crf: int
    video_film_grain: int
    audio_bitrate: str
    max_threads: int


@router.post("/command-preview", response_model=CommandPreviewResponse)
async def generate_command_preview(request: CommandPreviewRequest):
    command = build_command_preview(
        video_preset=request.video_preset,
        video_crf=request.video_crf,
        video_film_grain=request.video_film_grain,
        audio_bitrate=request.audio_bitrate,
        max_threads=request.max_threads,
    )
    return CommandPreviewResponse(command=command)


class PermissionTestResult(BaseModel):
    path: str
    exists: bool
    readable: bool
    writable: bool
    error: Optional[str] = None


class PermissionTestResponse(BaseModel):
    source: PermissionTestResult
    temp: PermissionTestResult
    config: PermissionTestResult
    archive: Optional[PermissionTestResult] = None


def test_directory_permissions(path_str: str) -> PermissionTestResult:
    if not path_str:
        return PermissionTestResult(
            path=path_str,
            exists=False,
            readable=False,
            writable=False,
            error="Path not configured",
        )

    path = Path(path_str)
    result = PermissionTestResult(
        path=path_str,
        exists=path.exists(),
        readable=False,
        writable=False,
    )

    if not path.exists():
        result.error = "Directory does not exist"
        return result

    result.readable = os.access(path, os.R_OK)
    if not result.readable:
        result.error = "No read permission"
        return result

    test_file = path / f".diettube_permission_test_{uuid.uuid4().hex}"
    try:
        test_file.write_text("test")
        test_file.unlink()
        result.writable = True
    except PermissionError:
        result.error = "No write permission"
    except Exception as e:
        result.error = str(e)

    return result


class PermissionTestRequest(BaseModel):
    source_dir: str
    temp_dir: str
    config_dir: str
    original_file_strategy: str
    archive_dir: Optional[str] = None


@router.post("/test-permissions", response_model=PermissionTestResponse)
async def test_permissions(request: PermissionTestRequest):
    response = PermissionTestResponse(
        source=test_directory_permissions(request.source_dir),
        temp=test_directory_permissions(request.temp_dir),
        config=test_directory_permissions(request.config_dir),
    )

    if request.original_file_strategy == "archive" and request.archive_dir:
        response.archive = test_directory_permissions(request.archive_dir)

    return response


class IgnorePatternsTestRequest(BaseModel):
    source_dir: str
    scan_ignore_patterns: str


class IgnorePatternsTestResponse(BaseModel):
    ignored_files: list[str]
    total_count: int


@router.post("/test-ignore-patterns", response_model=IgnorePatternsTestResponse)
async def test_ignore_patterns(request: IgnorePatternsTestRequest):
    ignored = get_ignored_files(request.source_dir, request.scan_ignore_patterns)
    return IgnorePatternsTestResponse(
        ignored_files=ignored,
        total_count=len(ignored),
    )
