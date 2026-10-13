import os
import hashlib
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.models.bot import Bot, BotVersion
from backend.models.user import User
from backend.config.settings import settings
from judge.validator import BotValidator

class BotService:
    @staticmethod
    def _ensure_user_storage(user_id: int) -> str:
        """Tạo và trả về đường dẫn lưu trữ file bot riêng cho từng người dùng"""
        storage_dir = os.path.join(settings.SUBMISSIONS_DIR, f"user_{user_id}")
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir

    @staticmethod
    def _validate_uploaded_file(filename: str, content: bytes):
        """Kiểm tra phần mở rộng và kích thước file an toàn"""
        if not filename.endswith(".py"):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file mã nguồn Python có phần mở rộng .py")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="File tải lên rỗng (0 bytes)")

        max_size = 1024 * 1024  # 1 MB
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="Dung lượng file vượt quá giới hạn 1MB")

    @staticmethod
    def create_bot(
        db: Session,
        user: User,
        name: str,
        description: Optional[str],
        filename: str,
        content: bytes
    ) -> Bot:
        """Tạo bot mới và phiên bản v1, chạy kiểm tra trong Sandbox"""
        BotService._validate_uploaded_file(filename, content)
        
        cleaned_name = name.strip()
        if not cleaned_name:
            raise HTTPException(status_code=400, detail="Tên bot không được để trống")

        # 1. Tạo bản ghi Bot
        bot = Bot(
            user_id=user.id,
            name=cleaned_name,
            description=description.strip() if description else None,
            status="VALIDATING"
        )
        db.add(bot)
        db.flush()

        # 2. Lưu file an toàn
        user_dir = BotService._ensure_user_storage(user.id)
        saved_filename = f"bot_{bot.id}_v1.py"
        file_path = os.path.abspath(os.path.join(user_dir, saved_filename))
        
        with open(file_path, "wb") as f:
            f.write(content)

        file_hash = hashlib.sha256(content).hexdigest()

        # 3. Tạo bản ghi BotVersion v1
        version = BotVersion(
            bot_id=bot.id,
            version_number=1,
            file_path=file_path,
            file_hash=file_hash,
            status="VALIDATING"
        )
        db.add(version)
        db.flush()

        bot.current_version_id = version.id

        # 4. Chạy kiểm tra tự động trong Sandbox
        is_valid, message = BotValidator.validate_execution(file_path, timeout=2.0)
        if is_valid:
            version.status = "READY"
            version.validation_error = None
            bot.status = "READY"
        else:
            version.status = "INVALID"
            version.validation_error = message
            bot.status = "INVALID"

        db.commit()
        db.refresh(bot)
        return bot

    @staticmethod
    def create_new_version(
        db: Session,
        user: User,
        bot_id: int,
        filename: str,
        content: bytes
    ) -> BotVersion:
        """Tải lên phiên bản mới cho một bot hiện có mà không làm mất lịch sử phiên bản cũ"""
        BotService._validate_uploaded_file(filename, content)

        bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user.id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Không tìm thấy bot hoặc bạn không sở hữu bot này")

        # Xác định số phiên bản tiếp theo
        latest_version = (
            db.query(BotVersion)
            .filter(BotVersion.bot_id == bot.id)
            .order_by(BotVersion.version_number.desc())
            .first()
        )
        next_ver_num = (latest_version.version_number + 1) if latest_version else 1

        # Lưu file mới
        user_dir = BotService._ensure_user_storage(user.id)
        saved_filename = f"bot_{bot.id}_v{next_ver_num}.py"
        file_path = os.path.abspath(os.path.join(user_dir, saved_filename))

        with open(file_path, "wb") as f:
            f.write(content)

        file_hash = hashlib.sha256(content).hexdigest()

        # Tạo BotVersion mới
        version = BotVersion(
            bot_id=bot.id,
            version_number=next_ver_num,
            file_path=file_path,
            file_hash=file_hash,
            status="VALIDATING"
        )
        db.add(version)
        db.flush()

        bot.current_version_id = version.id
        bot.status = "VALIDATING"

        # Chạy kiểm tra Sandbox cho phiên bản mới
        is_valid, message = BotValidator.validate_execution(file_path, timeout=2.0)
        if is_valid:
            version.status = "READY"
            version.validation_error = None
            bot.status = "READY"
        else:
            version.status = "INVALID"
            version.validation_error = message
            bot.status = "INVALID"

        db.commit()
        db.refresh(version)
        db.refresh(bot)
        return version

    @staticmethod
    def list_user_bots(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả các bot của người chơi kèm thông tin phiên bản hiện tại"""
        bots = db.query(Bot).filter(Bot.user_id == user_id).order_by(Bot.created_at.desc()).all()
        result = []
        for b in bots:
            curr_ver = b.current_version
            ver_count = len(b.versions)
            result.append({
                "id": b.id,
                "user_id": b.user_id,
                "name": b.name,
                "description": b.description,
                "status": b.status,
                "current_version_id": b.current_version_id,
                "current_version_number": curr_ver.version_number if curr_ver else 1,
                "validation_error": curr_ver.validation_error if curr_ver else None,
                "total_versions": ver_count,
                "created_at": b.created_at,
                "updated_at": b.updated_at
            })
        return result

    @staticmethod
    def get_ready_bots(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Lấy danh sách các bot có trạng thái READY để người chơi chọn thi đấu"""
        bots = (
            db.query(Bot)
            .filter(Bot.user_id == user_id, Bot.status == "READY")
            .order_by(Bot.name.asc())
            .all()
        )
        result = []
        for b in bots:
            curr_ver = b.current_version
            result.append({
                "id": b.id,
                "user_id": b.user_id,
                "name": b.name,
                "description": b.description,
                "status": b.status,
                "current_version_id": b.current_version_id,
                "current_version_number": curr_ver.version_number if curr_ver else 1,
                "validation_error": None,
                "total_versions": len(b.versions),
                "created_at": b.created_at,
                "updated_at": b.updated_at
            })
        return result

    @staticmethod
    def get_bot_detail(db: Session, user_id: int, bot_id: int) -> Dict[str, Any]:
        """Lấy chi tiết bot cùng toàn bộ lịch sử các phiên bản đã nộp"""
        bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Không tìm thấy bot")

        curr_ver = bot.current_version
        versions_list = [
            {
                "id": v.id,
                "bot_id": v.bot_id,
                "version_number": v.version_number,
                "status": v.status,
                "validation_error": v.validation_error,
                "created_at": v.created_at
            }
            for v in bot.versions
        ]

        return {
            "id": bot.id,
            "user_id": bot.user_id,
            "name": bot.name,
            "description": bot.description,
            "status": bot.status,
            "current_version_id": bot.current_version_id,
            "current_version_number": curr_ver.version_number if curr_ver else 1,
            "validation_error": curr_ver.validation_error if curr_ver else None,
            "total_versions": len(bot.versions),
            "versions": versions_list,
            "created_at": bot.created_at,
            "updated_at": bot.updated_at
        }

    @staticmethod
    def revalidate_bot(db: Session, user_id: int, bot_id: int) -> Dict[str, Any]:
        """Chạy kiểm tra lại Sandbox cho phiên bản hiện tại của bot"""
        bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user_id).first()
        if not bot or not bot.current_version:
            raise HTTPException(status_code=404, detail="Không tìm thấy bot để kiểm tra lại")

        curr_ver = bot.current_version
        is_valid, message = BotValidator.validate_execution(curr_ver.file_path, timeout=2.0)
        
        if is_valid:
            curr_ver.status = "READY"
            curr_ver.validation_error = None
            bot.status = "READY"
        else:
            curr_ver.status = "INVALID"
            curr_ver.validation_error = message
            bot.status = "INVALID"

        db.commit()
        db.refresh(bot)
        return BotService.get_bot_detail(db, user_id, bot_id)

    @staticmethod
    def disable_bot(db: Session, user_id: int, bot_id: int) -> Dict[str, Any]:
        """Vô hiệu hóa bot (status = DISABLED)"""
        bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user_id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Không tìm thấy bot")

        bot.status = "DISABLED"
        if bot.current_version:
            bot.current_version.status = "DISABLED"
        db.commit()
        return {"message": "Đã vô hiệu hóa bot thành công!", "bot_id": bot.id, "status": bot.status}
