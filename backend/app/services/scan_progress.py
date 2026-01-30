from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ScanPhase(str, Enum):
    IDLE = "idle"
    REMOVING_IGNORED = "removing_ignored"
    LISTING_FILES = "listing_files"
    CHECKING_METADATA = "checking_metadata"
    CREATING_TASKS = "creating_tasks"


@dataclass
class ScanProgress:
    is_scanning: bool = False
    phase: ScanPhase = ScanPhase.IDLE
    current_file: str = ""
    files_checked: int = 0
    files_found: int = 0
    tasks_created: int = 0
    tasks_removed: int = 0


class ScanProgressManager:
    def __init__(self):
        self._progress = ScanProgress()

    @property
    def progress(self) -> ScanProgress:
        return self._progress

    def start(self):
        self._progress = ScanProgress(
            is_scanning=True, phase=ScanPhase.REMOVING_IGNORED
        )

    def set_phase(self, phase: ScanPhase):
        self._progress.phase = phase

    def set_current_file(self, file: str):
        self._progress.current_file = file

    def increment_checked(self):
        self._progress.files_checked += 1

    def increment_found(self):
        self._progress.files_found += 1

    def set_tasks_created(self, count: int):
        self._progress.tasks_created = count

    def set_tasks_removed(self, count: int):
        self._progress.tasks_removed = count

    def finish(self):
        self._progress.is_scanning = False
        self._progress.phase = ScanPhase.IDLE


scan_progress_manager = ScanProgressManager()
