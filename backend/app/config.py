from __future__ import annotations
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    source_dir: Path = Field(default=Path("/source"))
    temp_dir: Path = Field(default=Path("/temp"))
    config_dir: Path = Field(default=Path("/config"))

    db_path: Path = Field(default=None)

    puid: int = Field(default=1000)
    pgid: int = Field(default=1000)

    video_preset: int = Field(default=6, ge=0, le=13)
    video_crf: int = Field(default=30, ge=0, le=63)
    video_film_grain: int = Field(default=0, ge=0, le=50)
    audio_bitrate: str = Field(default="128k")
    max_threads: int = Field(default=0)

    original_file_strategy: str = Field(default="trash")
    archive_dir: Path = Field(default=None)

    diettube_marker: str = Field(default="DietTube-Processed")
    duration_tolerance: float = Field(default=0.01)
    min_file_size: int = Field(default=10240)

    video_extensions: set[str] = Field(
        default={
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
        }
    )

    model_config = {"env_prefix": "DIETTUBE_"}

    def __init__(self, **data):
        super().__init__(**data)
        if self.db_path is None:
            object.__setattr__(self, "db_path", self.config_dir / "diettube.db")

    @property
    def trash_dir(self) -> Path:
        return self.temp_dir / "trash"

    @property
    def processing_dir(self) -> Path:
        return self.temp_dir / "processing"


@lru_cache
def get_settings() -> Settings:
    return Settings()
