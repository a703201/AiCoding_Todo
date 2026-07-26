"""
错误处理模块

提供全局错误处理器注册和自定义异常类。
"""
from app.errors.handlers import register_error_handlers
from app.exceptions import (
    AppException,
    NotFoundException,
    ConflictException,
    ValidationException,
    BusinessException,
)

__all__ = [
    "register_error_handlers",
    "AppException",
    "NotFoundException",
    "ConflictException",
    "ValidationException",
    "BusinessException",
]
