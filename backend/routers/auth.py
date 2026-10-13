from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.models.user import User
from backend.schemas.user import UserCreate, UserResponse
from backend.services.auth_service import AuthService

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """API đăng ký tài khoản người chơi"""
    return AuthService.register_user(db, user)

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """API đăng nhập trả về JWT Token"""
    user = AuthService.authenticate_user(db, form_data.username, form_data.password)
    access_token = AuthService.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
