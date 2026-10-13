import os
import sys

# Đảm bảo Python có thể import từ thư mục gốc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.connection import engine
from backend.database.base import Base

# Bắt buộc import toàn bộ Models để Base.metadata nhận diện được
from backend.models import (
    User, Team, TeamMember, Submission, Competition,
    Round, Group, RuleSet, Match, Game, Ranking
)

def init_db():
    print("Dang ket noi MySQL va tao cac bang (Tables)...")
    try:
        # Lệnh này sẽ quét toàn bộ models và tự động CREATE TABLE nếu chưa có
        Base.metadata.create_all(bind=engine)
        print("Khoi tao cau truc bang Database thanh cong!")
    except Exception as e:
        print("Loi khi khoi tao Database:", e)
        print("\nGoi y: Hay chac chan ban da bat MySQL Server va tao san database ten la 'uet_algorithm_battle'.")

if __name__ == "__main__":
    init_db()
