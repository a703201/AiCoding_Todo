"""
应用配置管理

遵循 12-Factor App 原则：配置通过环境变量注入，不硬编码。
支持 development / testing / production 三套环境。
"""
import os


class BaseConfig:
    """基础配置，所有环境共享。"""

    # ── Flask 核心 ──
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ── 常量 ──
    VALID_PRIORITIES: frozenset = frozenset({"low", "medium", "high"})
    VALID_CATEGORIES: frozenset = frozenset({"personal", "work", "study", "health", "other"})
    TITLE_MIN_LENGTH: int = 1
    TITLE_MAX_LENGTH: int = 200
    TAG_NAME_MAX_LENGTH: int = 50

    # ── 缓存 ──
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = 30  # 秒

    # ── 日志 ──
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "/app/logs")

    # ── CORS ──
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")


class DevelopmentConfig(BaseConfig):
    """开发环境配置。"""
    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "sqlite:///todo.db")


class TestingConfig(BaseConfig):
    """测试环境配置（自动创建临时 SQLite 数据库）。"""
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"


class ProductionConfig(BaseConfig):
    """生产环境配置。"""
    DEBUG: bool = False
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL", "postgresql://todo_user:todo_password@db:5432/todo_db"
    )
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 20)),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", 30)),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", 3600)),
    }


# ── 配置映射 ──
config_by_name: dict = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
