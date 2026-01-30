from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models import AppSettings

logger = logging.getLogger(__name__)

SETTINGS_KEYS = [
    "source_dir",
    "temp_dir",
    "config_dir",
    "video_preset",
    "video_crf",
    "video_film_grain",
    "audio_bitrate",
    "max_threads",
    "original_file_strategy",
    "archive_dir",
    "max_long_side",
    "max_short_side",
    "max_fps",
    "start_paused",
    "scan_ignore_patterns",
]


@dataclass
class RuntimeSettings:
    source_dir: str = "/source"
    temp_dir: str = "/temp"
    config_dir: str = "/config"
    video_preset: int = 6
    video_crf: int = 30
    video_film_grain: int = 0
    audio_bitrate: str = "64k"
    max_threads: int = 0
    original_file_strategy: str = "trash"
    archive_dir: str = ""
    max_long_side: int = 0
    max_short_side: int = 0
    max_fps: int = 30
    start_paused: bool = False
    scan_ignore_patterns: str = ""

    diettube_marker: str = field(default="DietTube-Processed", repr=False)
    duration_tolerance: float = field(default=0.01, repr=False)
    min_file_size: int = field(default=10240, repr=False)
    video_extensions: set[str] = field(
        default_factory=lambda: {
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".ts",
            ".mts",
            ".m2ts",
        },
        repr=False,
    )

    @property
    def source_path(self) -> Path:
        return Path(self.source_dir)

    @property
    def temp_path(self) -> Path:
        return Path(self.temp_dir)

    @property
    def config_path(self) -> Path:
        return Path(self.config_dir)

    @property
    def trash_dir(self) -> Path:
        return self.temp_path / "trash"

    @property
    def processing_dir(self) -> Path:
        return self.temp_path / "processing"

    @property
    def db_path(self) -> Path:
        return self.config_path / "diettube.db"

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in SETTINGS_KEYS}


class SettingsManager:
    def __init__(self):
        self._settings = RuntimeSettings()
        self._initialized = False

    @property
    def current(self) -> RuntimeSettings:
        return self._settings

    def load_from_env(self):
        import os

        env_mapping = {
            "DIETTUBE_SOURCE_DIR": "source_dir",
            "DIETTUBE_TEMP_DIR": "temp_dir",
            "DIETTUBE_CONFIG_DIR": "config_dir",
            "DIETTUBE_VIDEO_PRESET": ("video_preset", int),
            "DIETTUBE_VIDEO_CRF": ("video_crf", int),
            "DIETTUBE_VIDEO_FILM_GRAIN": ("video_film_grain", int),
            "DIETTUBE_AUDIO_BITRATE": "audio_bitrate",
            "DIETTUBE_MAX_THREADS": ("max_threads", int),
            "DIETTUBE_ORIGINAL_FILE_STRATEGY": "original_file_strategy",
            "DIETTUBE_ARCHIVE_DIR": "archive_dir",
            "DIETTUBE_MAX_LONG_SIDE": ("max_long_side", int),
            "DIETTUBE_MAX_SHORT_SIDE": ("max_short_side", int),
            "DIETTUBE_MAX_FPS": ("max_fps", int),
            "DIETTUBE_START_PAUSED": (
                "start_paused",
                lambda x: x.lower() in ("true", "1", "yes"),
            ),
            "DIETTUBE_SCAN_IGNORE_PATTERNS": "scan_ignore_patterns",
        }

        for env_key, target in env_mapping.items():
            value = os.environ.get(env_key)
            if value is not None:
                if isinstance(target, tuple):
                    attr_name, converter = target
                    setattr(self._settings, attr_name, converter(value))
                else:
                    setattr(self._settings, target, value)

        logger.info(f"Loaded settings from environment: {self._settings}")

    async def load_from_db(self):
        try:
            async with async_session_maker() as session:
                result = await session.execute(select(AppSettings))
                db_settings = {row.key: row.value for row in result.scalars().all()}

                for key in SETTINGS_KEYS:
                    if key in db_settings:
                        value = db_settings[key]
                        current_value = getattr(self._settings, key)
                        if isinstance(current_value, bool):
                            setattr(
                                self._settings,
                                key,
                                value.lower() in ("true", "1", "yes"),
                            )
                        elif isinstance(current_value, int):
                            setattr(self._settings, key, int(value))
                        else:
                            setattr(self._settings, key, value)

                self._initialized = True
                logger.info(f"Loaded settings from database: {self._settings}")
        except Exception as e:
            logger.warning(f"Failed to load settings from database: {e}")

    async def save_to_db(self, updates: dict[str, Any]):
        async with async_session_maker() as session:
            for key, value in updates.items():
                if key not in SETTINGS_KEYS:
                    continue

                str_value = str(value)

                result = await session.execute(
                    select(AppSettings).where(AppSettings.key == key)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    await session.execute(
                        update(AppSettings)
                        .where(AppSettings.key == key)
                        .values(value=str_value)
                    )
                else:
                    session.add(AppSettings(key=key, value=str_value))

                current_value = getattr(self._settings, key)
                if isinstance(current_value, int):
                    setattr(self._settings, key, int(value))
                else:
                    setattr(self._settings, key, str_value)

            await session.commit()
            logger.info(f"Settings updated: {updates}")


settings_manager = SettingsManager()


def get_settings() -> RuntimeSettings:
    return settings_manager.current
