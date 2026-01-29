from __future__ import annotations
import asyncio
import subprocess
import logging
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TranscodeProgress:
    fps: float = 0.0
    speed: float = 0.0
    progress: float = 0.0
    eta_seconds: float = 0.0
    current_time: float = 0.0
    total_duration: float = 0.0


@dataclass
class TranscodeResult:
    success: bool
    output_path: Path | None = None
    error_message: str = ""


def build_ffmpeg_command(
    input_path: Path, output_path: Path, duration: float
) -> list[str]:
    settings = get_settings()

    cmd = [
        "ffmpeg",
        "-y",
        "-progress",
        "pipe:1",
        "-i",
        str(input_path),
    ]

    cmd.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-map",
            "0:s?",
            "-map",
            "0:t?",
        ]
    )

    cmd.extend(
        [
            "-c:v",
            "libsvtav1",
            "-preset",
            str(settings.video_preset),
            "-crf",
            str(settings.video_crf),
            "-svtav1-params",
            f"film-grain={settings.video_film_grain}",
            "-pix_fmt",
            "yuv420p",
        ]
    )

    cmd.extend(
        [
            "-c:a",
            "libopus",
            "-b:a",
            settings.audio_bitrate,
            "-vbr",
            "on",
        ]
    )

    cmd.extend(
        [
            "-c:s",
            "copy",
            "-c:t",
            "copy",
        ]
    )

    cmd.extend(
        [
            "-metadata",
            f"comment={settings.diettube_marker}",
        ]
    )

    if settings.max_threads > 0:
        cmd.extend(["-threads", str(settings.max_threads)])

    cmd.append(str(output_path))

    return cmd


def parse_progress_line(line: str, total_duration: float) -> TranscodeProgress | None:
    progress = TranscodeProgress(total_duration=total_duration)

    fps_match = re.search(r"fps=(\d+\.?\d*)", line)
    if fps_match:
        progress.fps = float(fps_match.group(1))

    speed_match = re.search(r"speed=(\d+\.?\d*)x", line)
    if speed_match:
        progress.speed = float(speed_match.group(1))

    time_match = re.search(r"out_time_ms=(\d+)", line)
    if time_match:
        progress.current_time = int(time_match.group(1)) / 1_000_000
        if total_duration > 0:
            progress.progress = min(progress.current_time / total_duration, 1.0)

            if progress.speed > 0:
                remaining = total_duration - progress.current_time
                progress.eta_seconds = remaining / progress.speed

    return progress


async def transcode_file(
    input_path: Path,
    output_path: Path,
    duration: float,
    on_progress: Callable[[TranscodeProgress], None] | None = None,
    cancel_event: asyncio.Event | None = None,
) -> TranscodeResult:
    cmd = build_ffmpeg_command(input_path, output_path, duration)
    logger.info(f"Starting transcode: {' '.join(cmd)}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    progress_buffer = ""

    try:
        while True:
            if cancel_event and cancel_event.is_set():
                process.terminate()
                await process.wait()
                if output_path.exists():
                    output_path.unlink()
                return TranscodeResult(success=False, error_message="Cancelled by user")

            try:
                chunk = await asyncio.wait_for(
                    process.stdout.read(1024),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                if process.returncode is not None:
                    break
                continue

            if not chunk:
                break

            progress_buffer += chunk.decode("utf-8", errors="ignore")

            while "\n" in progress_buffer:
                line, progress_buffer = progress_buffer.split("\n", 1)
                if on_progress:
                    progress = parse_progress_line(line, duration)
                    if progress:
                        on_progress(progress)

        await process.wait()

        if process.returncode != 0:
            stderr = await process.stderr.read()
            error_msg = stderr.decode("utf-8", errors="ignore")
            logger.error(f"FFmpeg failed: {error_msg}")
            if output_path.exists():
                output_path.unlink()
            return TranscodeResult(success=False, error_message=error_msg[-500:])

        return TranscodeResult(success=True, output_path=output_path)

    except Exception as e:
        logger.exception(f"Transcode error: {e}")
        if output_path.exists():
            output_path.unlink()
        return TranscodeResult(success=False, error_message=str(e))


def get_ffmpeg_command_preview() -> str:
    settings = get_settings()
    cmd = build_ffmpeg_command(Path("/input.mkv"), Path("/output.mkv"), 0)
    return " ".join(cmd)
