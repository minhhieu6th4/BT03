from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.user import User
from backend.schemas.user import UserCreate, UserResponse, PasswordChange
from backend.services.auth_service import AuthService
from backend.services.account_service import AccountService
from backend.config.settings import settings
from backend.dependencies.auth import get_current_user
from backend.models.account_token import AccountToken

class EmailRequest(BaseModel):
    email: EmailStr

class TokenRequest(BaseModel):
    token: str

class PasswordResetRequest(TokenRequest):
    new_password: str = Field(min_length=8, max_length=72)

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """API đăng ký tài khoản người chơi"""
    return AuthService.register_user(db, user)

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """API đăng nhập trả về JWT Token"""
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    access_token = AuthService.create_access_token(data={"sub": user.username, "uid": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verification/request")
def request_email_verification(data: EmailRequest, db: Session = Depends(get_db)):
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        raise HTTPException(status_code=503, detail="Chưa cấu hình dịch vụ gửi email")
    user = db.query(User).filter(User.email == data.email).first()
    if user and not user.email_verified:
        AccountService.send_token(db, user, "VERIFY_EMAIL")
    return {"message": "Nếu tài khoản cần xác minh, email hướng dẫn đã được gửi."}

@router.post("/verification/confirm")
def verify_email(data: TokenRequest, db: Session = Depends(get_db)):
    token = AccountService.consume_token(db, data.token, "VERIFY_EMAIL")
    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    user.email_verified = True
    db.commit()
    return {"message": "Email đã được xác minh."}

@router.post("/password-reset/request")
def request_password_reset(data: EmailRequest, db: Session = Depends(get_db)):
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        raise HTTPException(status_code=503, detail="Chưa cấu hình dịch vụ gửi email")
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        AccountService.send_token(db, user, "RESET_PASSWORD")
    return {"message": "Nếu email tồn tại, hướng dẫn đặt lại mật khẩu đã được gửi."}

@router.post("/password-reset/confirm")
def reset_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    token = AccountService.consume_token(db, data.token, "RESET_PASSWORD")
    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    user.hashed_password = AuthService.hash_password(data.new_password)
    db.query(AccountToken).filter(
        AccountToken.user_id == user.id,
        AccountToken.purpose == "RESET_PASSWORD",
        AccountToken.used_at.is_(None),
    ).update({AccountToken.used_at: datetime.utcnow()})
    db.commit()
    return {"message": "Mật khẩu đã được cập nhật."}

@router.post("/password/change")
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not AuthService.verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác")
    current_user.hashed_password = AuthService.hash_password(data.new_password)
    db.commit()
    return {"message": "Mật khẩu đã được thay đổi."}
