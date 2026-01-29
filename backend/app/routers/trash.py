from __future__ import annotations
import shutil
from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path

from app.services.settings_service import get_settings

router = APIRouter()


class TrashInfoResponse(BaseModel):
    total_size: int
    file_count: int


class TrashFileResponse(BaseModel):
    path: str
    size: int
    name: str


class TrashListResponse(BaseModel):
    files: list[TrashFileResponse]
    total_size: int
    file_count: int


def get_trash_files() -> list[tuple[Path, int]]:
    settings = get_settings()
    trash_dir = settings.trash_dir

    files = []
    if trash_dir.exists():
        for item in trash_dir.rglob("*"):
            if item.is_file():
                files.append((item, item.stat().st_size))

    return files


@router.get("/", response_model=TrashListResponse)
async def list_trash():
    files = get_trash_files()
    settings = get_settings()

    return TrashListResponse(
        files=[
            TrashFileResponse(
                path=str(f.relative_to(settings.trash_dir)),
                size=s,
                name=f.name,
            )
            for f, s in files
        ],
        total_size=sum(s for _, s in files),
        file_count=len(files),
    )


@router.get("/info", response_model=TrashInfoResponse)
async def get_trash_info():
    files = get_trash_files()
    return TrashInfoResponse(
        total_size=sum(s for _, s in files),
        file_count=len(files),
    )


@router.post("/empty")
async def empty_trash():
    settings = get_settings()
    trash_dir = settings.trash_dir

    deleted_count = 0
    freed_bytes = 0

    if trash_dir.exists():
        for item in list(trash_dir.iterdir()):
            try:
                if item.is_file():
                    freed_bytes += item.stat().st_size
                    item.unlink()
                    deleted_count += 1
                elif item.is_dir():
                    for f in item.rglob("*"):
                        if f.is_file():
                            freed_bytes += f.stat().st_size
                            deleted_count += 1
                    shutil.rmtree(item)
            except Exception:
                pass

    return {
        "message": f"Deleted {deleted_count} files",
        "freed_bytes": freed_bytes,
    }
