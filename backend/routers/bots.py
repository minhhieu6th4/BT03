import os
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.database.connection import get_db
from backend.models.user import User
from backend.dependencies.auth import get_current_user
from backend.services.bot_service import BotService
from backend.schemas.bot import BotResponse, BotDetailResponse, BotVersionResponse

router = APIRouter()

@router.post("/upload")
async def upload_bot(
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    bot_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Nộp Bot Python:
    - Nếu có bot_id: Nộp phiên bản mới (v2, v3...) cho bot đã có.
    - Nếu không có bot_id: Tạo bot mới với phiên bản v1.
    Tự động chạy kiểm tra trong Sandbox và trả về trạng thái READY / INVALID.
    """
    content = await file.read()
    filename = file.filename or "bot.py"

    if bot_id:
        version = BotService.create_new_version(
            db=db,
            user=current_user,
            bot_id=bot_id,
            filename=filename,
            content=content
        )
        return {
            "message": f"Nộp phiên bản v{version.version_number} thành công!",
            "bot_id": bot_id,
            "version_number": version.version_number,
            "status": version.status,
            "validation_error": version.validation_error
        }
    else:
        if not name or not name.strip():
            name = os.path.splitext(filename)[0] or "My Bot"
        bot = BotService.create_bot(
            db=db,
            user=current_user,
            name=name,
            description=description,
            filename=filename,
            content=content
        )
        curr_ver = bot.current_version
        return {
            "message": "Tạo bot và kiểm tra qua Sandbox thành công!",
            "id": bot.id,
            "bot_id": bot.id,
            "name": bot.name,
            "status": bot.status,
            "version_number": curr_ver.version_number if curr_ver else 1,
            "validation_error": curr_ver.validation_error if curr_ver else None
        }

@router.get("/", response_model=List[BotResponse])
@router.get("/my-bots", response_model=List[BotResponse])
def get_my_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách tất cả các bot của người dùng hiện tại"""
    return BotService.list_user_bots(db, current_user.id)

@router.get("/ready", response_model=List[BotResponse])
def get_ready_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các bot hợp lệ (READY) có thể mang đi thi đấu"""
    return BotService.get_ready_bots(db, current_user.id)

@router.get("/{bot_id}", response_model=BotDetailResponse)
def get_bot_details(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xem chi tiết một bot và toàn bộ lịch sử các phiên bản đã nộp"""
    return BotService.get_bot_detail(db, current_user.id, bot_id)

@router.post("/{bot_id}/version")
async def upload_bot_version(
    bot_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Nộp phiên bản mới cho bot đã tồn tại"""
    content = await file.read()
    filename = file.filename or "bot.py"
    version = BotService.create_new_version(
        db=db,
        user=current_user,
        bot_id=bot_id,
        filename=filename,
        content=content
    )
    return {
        "message": f"Nộp phiên bản v{version.version_number} thành công!",
        "bot_id": bot_id,
        "version_number": version.version_number,
        "status": version.status,
        "validation_error": version.validation_error
    }

@router.post("/{bot_id}/revalidate")
def revalidate_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chạy kiểm tra lại Sandbox cho bot"""
    return BotService.revalidate_bot(db, current_user.id, bot_id)

@router.delete("/{bot_id}")
def disable_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Vô hiệu hóa bot"""
    return BotService.disable_bot(db, current_user.id, bot_id)

@router.get("/examples/{bot_type}")
def get_example_bot(bot_type: str):
    """Tải mã nguồn bot mẫu: example, random, greedy"""
    valid_bots = {
        "example": "bots/examples/example_bot.py",
        "random": "bots/examples/random_bot.py",
        "greedy": "bots/examples/greedy_bot.py",
        "aggressive": "bots/examples/aggressive_bot.py",
        "tactical": "bots/examples/tactical_bot.py"
    }
    if bot_type not in valid_bots:
        raise HTTPException(status_code=404, detail="Không tìm thấy bot mẫu yêu cầu")
    
    file_path = os.path.abspath(valid_bots[bot_type])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File bot mẫu không tồn tại")
    
    return FileResponse(file_path, media_type="text/x-python", filename=f"{bot_type}_bot.py")
