from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timedelta
import jwt
import bcrypt

from backend.config.settings import settings
from backend.models.user import User
from backend.schemas.user import UserCreate

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a UTF-8 password without silently truncating bcrypt input."""
        pwd_bytes = password.encode("utf-8")
        if len(pwd_bytes) > 72:
            raise HTTPException(status_code=422, detail="Mật khẩu không được vượt quá 72 byte UTF-8")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Kiểm tra mật khẩu khớp với hash"""
        try:
            password_bytes = plain_password.encode("utf-8")
            if len(password_bytes) > 72:
                return False
            return bcrypt.checkpw(
                password_bytes,
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False

    @staticmethod
    def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
    @staticmethod
    def register_user(db: Session, user_data: UserCreate):
        db_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username hoặc email đã tồn tại")
        
        # Băm mật khẩu an toàn
        hashed_password = AuthService.hash_password(user_data.password)
        new_user = User(username=user_data.username, email=user_data.email, hashed_password=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str):
        user = db.query(User).filter(User.username == username).first()
        if not user or not AuthService.verify_password(password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Sai username hoặc password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Tài khoản đã bị vô hiệu hóa")
        if settings.EMAIL_VERIFICATION_REQUIRED and not user.email_verified:
            raise HTTPException(status_code=403, detail="Vui lòng xác minh email trước khi đăng nhập")
        return user
