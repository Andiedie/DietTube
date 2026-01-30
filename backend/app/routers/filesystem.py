from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class DirectoryEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class BrowseResponse(BaseModel):
    current_path: str
    parent_path: str | None
    entries: list[DirectoryEntry]


@router.get("/browse", response_model=BrowseResponse)
async def browse_directory(path: str = Query(default="/")):
    target = Path(path).resolve()

    if not target.exists():
        target = Path("/")

    if not target.is_dir():
        target = target.parent

    parent_path = str(target.parent) if target != target.parent else None

    entries: list[DirectoryEntry] = []
    try:
        for item in sorted(
            target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
        ):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                entries.append(
                    DirectoryEntry(
                        name=item.name,
                        path=str(item),
                        is_dir=True,
                    )
                )
    except PermissionError:
        pass

    return BrowseResponse(
        current_path=str(target),
        parent_path=parent_path,
        entries=entries,
    )
