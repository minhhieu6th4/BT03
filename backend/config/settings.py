import os
from typing import List

try:
    from pydantic_settings import BaseSettings  # type: ignore[import-not-found]
except ImportError:
    from pydantic import BaseSettings  # type: ignore[import-not-found]

# Tính toán tuyệt đối thư mục gốc của project (UET-Algorithm-Battle)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class Settings(BaseSettings):
    # App Config
    PROJECT_NAME: str = "UET Algorithm Battle API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # Database Config
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost/uet_algorithm_battle")
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 5
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE_SECONDS: int = 1800
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    MATCH_EXECUTION_MODE: str = "auto"
    MATCH_QUEUE_NAME: str = "matches"
    MATCH_JOB_TIMEOUT_SECONDS: int = 900
    
    # Canonical Absolute Paths
    PROJECT_ROOT: str = PROJECT_ROOT
    BASE_DIR: str = os.path.join(PROJECT_ROOT, "backend")
    SUBMISSIONS_DIR: str = os.path.join(PROJECT_ROOT, "bots", "submissions")
    MATCH_LOGS_DIR: str = os.path.join(PROJECT_ROOT, "match_logs")
    CONFIGS_DIR: str = os.path.join(PROJECT_ROOT, "configs")
    SQLITE_FALLBACK_URL: str = f"sqlite:///{os.path.join(PROJECT_ROOT, 'uet_algorithm_battle.db')}"
    
    # JWT Authentication Config
    SECRET_KEY: str = "super-secret-key-for-uet-battle"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    EMAIL_VERIFICATION_REQUIRED: bool = False
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True
    FRONTEND_BASE_URL: str = "http://127.0.0.1:5500"
    
    # CORS (Hỗ trợ cả 127.0.0.1 và localhost trên các cổng thường dùng)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        env_file_encoding = 'utf-8'
        case_sensitive = True

settings = Settings()

if settings.ENVIRONMENT.lower() == "production":
    if (
        settings.SECRET_KEY == "super-secret-key-for-uet-battle"
        or settings.SECRET_KEY.lower().startswith(("replace_", "change_me"))
        or len(settings.SECRET_KEY) < 32
    ):
        raise RuntimeError("Production requires a unique SECRET_KEY of at least 32 characters.")
    if settings.MATCH_EXECUTION_MODE.lower() != "queued":
        raise RuntimeError("Production requires MATCH_EXECUTION_MODE=queued.")

# Đảm bảo các thư mục cần thiết luôn tồn tại
os.makedirs(settings.SUBMISSIONS_DIR, exist_ok=True)
os.makedirs(settings.MATCH_LOGS_DIR, exist_ok=True)
