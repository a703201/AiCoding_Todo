"""
自定义异常层次

提供语义化的异常类型，替代裸 ValueError，方便上层精确捕获和处理。
"""


class AppException(Exception):
    """应用基础异常，所有业务异常继承自此。"""

    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(message)


# ── 资源类异常 ──


class NotFoundException(AppException):
    """资源不存在。"""

    def __init__(self, message: str = "资源未找到"):
        super().__init__(message, code=404)


class ConflictException(AppException):
    """资源冲突（如唯一键重复）。"""

    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, code=409)


# ── 校验类异常 ──


class ValidationException(AppException):
    """输入校验失败。"""

    def __init__(self, message: str = "请求参数有误"):
        super().__init__(message, code=400)


# ── 业务类异常 ──


class BusinessException(AppException):
    """业务逻辑异常。"""

    def __init__(self, message: str = "操作失败"):
        super().__init__(message, code=422)
