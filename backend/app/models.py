from __future__ import annotations
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    Enum as SqlEnum,
    ForeignKey,
)
from sqlalchemy.sql import func
from app.database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    TRANSCODING = "transcoding"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_path = Column(String, nullable=False, unique=True)
    relative_path = Column(String, nullable=False)
    status = Column(SqlEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    original_size = Column(Integer, default=0)
    new_size = Column(Integer, default=0)
    original_duration = Column(Float, default=0.0)
    new_duration = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level = Column(SqlEnum(LogLevel), default=LogLevel.INFO, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class ProcessingStats(Base):
    __tablename__ = "processing_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    total_saved_bytes = Column(Integer, default=0)
    total_processed_files = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
