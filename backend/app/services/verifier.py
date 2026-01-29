from __future__ import annotations
import logging
from pathlib import Path
from dataclasses import dataclass

from app.services.scanner import get_video_metadata
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class VerifyResult:
    success: bool
    error_message: str = ""
    new_duration: float = 0.0
    new_size: int = 0


async def verify_output(
    source_path: Path,
    output_path: Path,
    original_duration: float,
) -> VerifyResult:
    settings = get_settings()

    if not output_path.exists():
        return VerifyResult(success=False, error_message="Output file does not exist")

    new_size = output_path.stat().st_size
    if new_size < settings.min_file_size:
        return VerifyResult(
            success=False,
            error_message=f"Output file too small: {new_size} bytes (min: {settings.min_file_size})",
        )

    metadata = await get_video_metadata(output_path)
    if not metadata:
        return VerifyResult(
            success=False, error_message="Failed to read output file metadata"
        )

    streams = metadata.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    if not has_video:
        return VerifyResult(
            success=False, error_message="Output file has no video stream"
        )

    format_info = metadata.get("format", {})
    new_duration = float(format_info.get("duration", 0))

    if original_duration > 0:
        duration_diff = abs(new_duration - original_duration) / original_duration
        if duration_diff > settings.duration_tolerance:
            return VerifyResult(
                success=False,
                error_message=f"Duration mismatch: {duration_diff:.2%} (tolerance: {settings.duration_tolerance:.2%})",
            )

    return VerifyResult(
        success=True,
        new_duration=new_duration,
        new_size=new_size,
    )
