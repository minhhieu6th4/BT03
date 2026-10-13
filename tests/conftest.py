import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Đảm bảo đường dẫn gốc của project có trong sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from game.rule_set import RuleSet
from game.game_engine import GameEngine
from game.board import Board
from bots.examples.random_bot import Bot as RandomBot
from bots.examples.greedy_bot import Bot as GreedyBot
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.base import Base
from backend.database.connection import get_db

# Sử dụng StaticPool để toàn bộ connection dùng chung 1 database SQLite in-memory duy nhất
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Nạp models và tạo tất cả bảng
from backend.models import User, Team, TeamMember, Submission, Competition, Round, Group, RuleSet as DBRuleSet, Match, Game, Ranking
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Đè dependency get_db trong FastAPI
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def default_rule_set():
    """Fixture trả về luật chơi mặc định (bàn cờ 9x9)"""
    return RuleSet.default()

@pytest.fixture
def game_engine(default_rule_set):
    """Fixture trả về GameEngine mới tinh với bàn cờ đã được sắp xếp quân"""
    return GameEngine(default_rule_set)

@pytest.fixture
def empty_board():
    """Fixture trả về bàn cờ trống kích thước 9x9"""
    return Board(size=9)

@pytest.fixture
def random_bot():
    """Fixture trả về RandomBot mẫu"""
    return RandomBot()

@pytest.fixture
def greedy_bot():
    """Fixture trả về GreedyBot mẫu"""
    return GreedyBot()

@pytest.fixture
def client():
    """Fixture TestClient để test các API FastAPI"""
    return TestClient(app)

@pytest.fixture
def db_session():
    """Fixture cung cấp DB session riêng biệt cho từng bài test"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

