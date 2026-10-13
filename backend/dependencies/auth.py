from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from backend.database.connection import get_db
from backend.config.settings import settings
from backend.models.user import User

# OAuth2PasswordBearer tự động trích xuất Token từ header HTTP (Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependency lấy thông tin User hiện tại từ JWT Token.
    Áp dụng ở các API cần đăng nhập.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực Token (Invalid or Expired Token)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Giải mã Token bằng SECRET_KEY
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        # Bắt các lỗi như Hết hạn (ExpiredSignatureError) hoặc Sai chữ ký
        raise credentials_exception
        
    # Truy vấn cơ sở dữ liệu để lấy Object User
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
        
    return user
