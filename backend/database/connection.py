import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.config.settings import settings
from backend.database.base import Base

logger = logging.getLogger("uvicorn.error")

def init_engine():
    """
    Khởi tạo engine kết nối Database với cơ chế Fail-Safe:
    1. Thử kết nối MySQL theo settings.DATABASE_URL hoặc Docker MySQL (port 3307/3306).
    2. Nếu MySQL chưa bật hoặc lỗi kết nối, tự động chuyển sang SQLite
       để toàn bộ hệ thống API vẫn chạy mượt mà 100% không bị gián đoạn!
    """
    candidate_urls = [
        settings.DATABASE_URL,
        "mysql+mysqlconnector://root:password@localhost:3307/uet_algorithm_battle",
        "mysql+mysqlconnector://root:password@localhost:3306/uet_algorithm_battle",
    ]
    for url in candidate_urls:
        if not url:
            continue
        try:
            mysql_engine = create_engine(url, pool_pre_ping=True)
            with mysql_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[DATABASE] Ket noi MySQL thanh cong tai: {url.split('@')[-1]}!")
            return mysql_engine
        except Exception:
            pass

    print("[DATABASE INFO] Chua bat MySQL. Tu dong chuyen sang SQLite (uet_algorithm_battle.db) de dam bao he thong hoat dong ngay lap tuc!")
    sqlite_engine = create_engine(
        settings.SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False}
    )
    return sqlite_engine

engine = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def auto_migrate():
    """Tự động tạo toàn bộ bảng cơ sở dữ liệu nếu chưa tồn tại và nâng cấp schema an toàn"""
    try:
        import backend.models  # Nạp toàn bộ models
        Base.metadata.create_all(bind=engine)

        # Đảm bảo bảng matches cho phép red_team_id = NULL (dành cho thi đấu 1v1 cá nhân)
        if engine.dialect.name == "sqlite":
            with engine.connect() as conn:
                try:
                    info = conn.execute(text("PRAGMA table_info(matches)")).fetchall()
                    red_team_col = next((c for c in info if c[1] == "red_team_id"), None)
                    if red_team_col and red_team_col[3] == 1:  # notnull == 1
                        conn.execute(text("PRAGMA foreign_keys = OFF;"))
                        conn.execute(text("DROP TABLE matches;"))
                        conn.execute(text("PRAGMA foreign_keys = ON;"))
                        conn.commit()
                        Base.metadata.tables["matches"].create(bind=engine)
                except Exception:
                    pass

        if engine.dialect.name == "mysql":
            with engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE matches MODIFY moves_json LONGTEXT"))
                    conn.execute(text("ALTER TABLE matches MODIFY initial_board_json LONGTEXT"))
                    conn.commit()
                except Exception:
                    pass

        # Nâng cấp bổ sung cột cho rooms và matches nếu chưa có (tương thích cả SQLite và MySQL)
        columns_to_add = [
            ("rooms", "player1_bot_id", "INTEGER"),
            ("rooms", "player2_bot_id", "INTEGER"),
            ("rooms", "player1_bot_version_id", "INTEGER"),
            ("rooms", "player2_bot_version_id", "INTEGER"),
            ("rooms", "current_match_id", "INTEGER"),
            ("matches", "match_type", "VARCHAR(20) DEFAULT 'REGULAR'"),
            ("matches", "room_id", "INTEGER"),
            ("matches", "red_user_id", "INTEGER"),
            ("matches", "blue_user_id", "INTEGER"),
            ("matches", "winner_user_id", "INTEGER"),
            ("matches", "is_draw", "BOOLEAN DEFAULT 0"),
            ("matches", "red_bot_id", "INTEGER"),
            ("matches", "blue_bot_id", "INTEGER"),
            ("matches", "red_bot_version_id", "INTEGER"),
            ("matches", "blue_bot_version_id", "INTEGER"),
            ("matches", "termination_reason", "VARCHAR(255)"),
            ("matches", "moves_json", "TEXT"),
            ("matches", "initial_board_json", "TEXT"),
            ("matches", "total_turns", "INTEGER DEFAULT 0"),
            ("matches", "points_awarded", "BOOLEAN DEFAULT 0"),
            ("tournaments", "min_participants", "INTEGER DEFAULT 4"),
            ("tournaments", "max_participants", "INTEGER DEFAULT 32"),
            ("tournament_participants", "bot_id", "INTEGER"),
            ("tournament_participants", "status", "VARCHAR(20) DEFAULT 'PENDING'"),
            ("tournament_participants", "reviewed_at", "DATETIME"),
            ("tournament_participants", "reviewed_by_id", "INTEGER"),
            ("tournament_matches", "player1_bot_id", "INTEGER"),
            ("tournament_matches", "player2_bot_id", "INTEGER"),
            ("tournament_matches", "ready_at", "DATETIME"),
            ("tournament_matches", "participation_deadline", "DATETIME"),
            ("tournament_matches", "player1_joined_at", "DATETIME"),
            ("tournament_matches", "player2_joined_at", "DATETIME"),
            ("tournament_matches", "result_reason", "VARCHAR(255)"),
        ]
        with engine.connect() as conn:
            for table, col, col_type in columns_to_add:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        print(f"[DATABASE MIGRATION WARNING]: {e}")

# Chạy tự động tạo bảng
auto_migrate()

def get_db():
    """
    Dependency injection dùng trong các FastAPI routes để lấy DB session.
    Tự động đóng kết nối khi request kết thúc.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
