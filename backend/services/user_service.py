from sqlalchemy.orm import Session
from backend.models.user import User

class UserService:
    @staticmethod
    def get_user_by_id(db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()
