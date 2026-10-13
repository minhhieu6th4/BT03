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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+mysqlconnector://root:@localhost/uet_algorithm_battle")
    
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

# Đảm bảo các thư mục cần thiết luôn tồn tại
os.makedirs(settings.SUBMISSIONS_DIR, exist_ok=True)
os.makedirs(settings.MATCH_LOGS_DIR, exist_ok=True)
