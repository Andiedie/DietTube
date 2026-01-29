from __future__ import annotations
import asyncio
import subprocess
import logging
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable

from app.services.settings_service import get_settings

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
            "yuv420p10le",
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
            "-ac",
            "2",
        ]
    )

    cmd.extend(
        [
            "-c:s",
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


def parse_progress_line(
    line: str, total_duration: float, accumulator: dict
) -> TranscodeProgress | None:
    """解析 FFmpeg 进度行，累积到 accumulator 中，遇到 progress= 行时返回完整进度"""
    line = line.strip()
    if not line or "=" not in line:
        return None

    key, _, value = line.partition("=")
    key = key.strip()
    value = value.strip()

    if key == "fps":
        try:
            accumulator["fps"] = float(value)
        except ValueError:
            pass
    elif key == "speed":
        if value != "N/A":
            speed_match = re.search(r"([\d.]+)x", value)
            if speed_match:
                try:
                    accumulator["speed"] = float(speed_match.group(1))
                except ValueError:
                    pass
    elif key == "out_time_ms":
        try:
            accumulator["current_time"] = int(value) / 1_000_000
        except ValueError:
            pass
    elif key == "progress":
        current_time = accumulator.get("current_time", 0)
        speed = accumulator.get("speed", 0)
        progress_pct = 0.0
        eta = 0.0

        if total_duration > 0 and current_time > 0:
            progress_pct = min(current_time / total_duration, 1.0)
            if speed > 0:
                remaining = total_duration - current_time
                eta = remaining / speed

        return TranscodeProgress(
            fps=accumulator.get("fps", 0),
            speed=speed,
            progress=progress_pct,
            eta_seconds=eta,
            current_time=current_time,
            total_duration=total_duration,
        )

    return None


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
        stderr=subprocess.DEVNULL,
    )

    progress_buffer = ""
    progress_accumulator: dict = {}

    assert process.stdout is not None

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
                    progress = parse_progress_line(line, duration, progress_accumulator)
                    if progress:
                        on_progress(progress)

        await process.wait()

        if process.returncode != 0:
            if output_path.exists():
                output_path.unlink()
            return TranscodeResult(
                success=False,
                error_message=f"FFmpeg exited with code {process.returncode}",
            )

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


def build_command_preview(
    video_preset: int,
    video_crf: int,
    video_film_grain: int,
    audio_bitrate: str,
    max_threads: int,
) -> str:
    settings = get_settings()

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        "/input.mkv",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-map",
        "0:s?",
        "-c:v",
        "libsvtav1",
        "-preset",
        str(video_preset),
        "-crf",
        str(video_crf),
        "-svtav1-params",
        f"film-grain={video_film_grain}",
        "-pix_fmt",
        "yuv420p10le",
        "-c:a",
        "libopus",
        "-b:a",
        audio_bitrate,
        "-vbr",
        "on",
        "-ac",
        "2",
        "-c:s",
        "copy",
        "-metadata",
        f"comment={settings.diettube_marker}",
    ]

    if max_threads > 0:
        cmd.extend(["-threads", str(max_threads)])

    cmd.append("/output.mkv")

    return " ".join(cmd)
