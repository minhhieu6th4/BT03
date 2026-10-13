from fastapi import Depends, HTTPException, status
from backend.models.user import User
from backend.dependencies.auth import get_current_user

def get_current_admin(current_user: User = Depends(get_current_user)):
    """
    Dependency phân quyền (Authorization).
    Sử dụng lại hàm get_current_user, sau đó kiểm tra cờ is_admin.
    Áp dụng ở các API bảo mật (tạo giải đấu, xóa bot, v.v.)
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập bị từ chối: Chỉ Admin mới có thể gọi API này."
        )
    return current_user
