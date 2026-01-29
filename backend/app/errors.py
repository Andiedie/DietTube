from __future__ import annotations
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Any
import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(
        self, message: str = "资源不存在", details: dict[str, Any] | None = None
    ):
        super().__init__(message, "NOT_FOUND", 404, details)


class ValidationError(AppError):
    def __init__(
        self, message: str = "参数验证失败", details: dict[str, Any] | None = None
    ):
        super().__init__(message, "VALIDATION_ERROR", 400, details)


class TaskError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, "TASK_ERROR", 400, details)


class FileSystemError(AppError):
    def __init__(
        self, message: str = "文件操作失败", details: dict[str, Any] | None = None
    ):
        super().__init__(message, "FILESYSTEM_ERROR", 500, details)


class TranscodeError(AppError):
    def __init__(
        self, message: str = "转码失败", details: dict[str, Any] | None = None
    ):
        super().__init__(message, "TRANSCODE_ERROR", 500, details)


ERROR_MESSAGES = {
    "TASK_NOT_FOUND": "任务不存在",
    "TASK_NOT_RUNNING": "该任务当前未在运行",
    "TASK_CANNOT_RETRY": "只有失败或已取消的任务才能重试",
    "INVALID_STATUS": "无效的任务状态",
    "SCAN_FAILED": "扫描目录失败",
    "SOURCE_DIR_NOT_FOUND": "源目录不存在，请检查配置",
    "TRANSCODE_FAILED": "视频转码失败",
    "VERIFY_FAILED": "视频校验失败",
    "FILE_TOO_SMALL": "输出文件过小，可能转码失败",
    "DURATION_MISMATCH": "视频时长不匹配，转码可能不完整",
    "NO_VIDEO_STREAM": "输出文件中未检测到视频流",
    "SETTINGS_SAVE_FAILED": "保存设置失败",
    "TRASH_EMPTY_FAILED": "清空回收站失败",
}


def get_error_message(code: str, default: str = "操作失败") -> str:
    return ERROR_MESSAGES.get(code, default)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        f"AppError: {exc.code} - {exc.message}", extra={"details": exc.details}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": message,
                "details": {},
            },
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误，请稍后重试",
                "details": {},
            },
        },
    )
