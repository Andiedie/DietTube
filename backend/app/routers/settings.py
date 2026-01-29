from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from app.config import get_settings
from app.services.transcoder import get_ffmpeg_command_preview

router = APIRouter()


class SettingsResponse(BaseModel):
    video_preset: int
    video_crf: int
    video_film_grain: int
    audio_bitrate: str
    max_threads: int
    original_file_strategy: str
    archive_dir: Optional[str]
    source_dir: str
    temp_dir: str
    config_dir: str


class SettingsUpdate(BaseModel):
    video_preset: Optional[int] = None
    video_crf: Optional[int] = None
    video_film_grain: Optional[int] = None
    audio_bitrate: Optional[str] = None
    max_threads: Optional[int] = None
    original_file_strategy: Optional[str] = None
    archive_dir: Optional[str] = None


class CommandPreviewResponse(BaseModel):
    command: str


@router.get("/", response_model=SettingsResponse)
async def get_current_settings():
    settings = get_settings()
    return SettingsResponse(
        video_preset=settings.video_preset,
        video_crf=settings.video_crf,
        video_film_grain=settings.video_film_grain,
        audio_bitrate=settings.audio_bitrate,
        max_threads=settings.max_threads,
        original_file_strategy=settings.original_file_strategy,
        archive_dir=str(settings.archive_dir) if settings.archive_dir else None,
        source_dir=str(settings.source_dir),
        temp_dir=str(settings.temp_dir),
        config_dir=str(settings.config_dir),
    )


@router.get("/command-preview", response_model=CommandPreviewResponse)
async def get_command_preview():
    return CommandPreviewResponse(command=get_ffmpeg_command_preview())
