from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.settings_service import get_settings, settings_manager
from app.services.transcoder import get_ffmpeg_command_preview, build_command_preview

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
