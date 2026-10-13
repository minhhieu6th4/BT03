import os
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from backend.models.submission import Submission
from backend.config.settings import settings
from judge.validator import BotValidator

class SubmissionService:
    @staticmethod
    async def create_submission(db: Session, team_id: int, file: UploadFile):
        if not file.filename.endswith('.py'):
            raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .py")
            
        code_content = await file.read()
        code_str = code_content.decode('utf-8')
        
        # Kiểm tra tính hợp lệ bằng AST (BotValidator cũ)
        is_valid, msg = BotValidator.validate(code_str)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Code không hợp lệ: {msg}")
            
        # Lưu file vật lý cực kỳ an toàn thông qua thư mục Utils
        from backend.utils.file_storage import FileStorageUtils
        file_path = FileStorageUtils.save_code_file(code_content, team_id, "student_bot.py")
        
        # Lưu bản ghi vào MySQL
        submission = Submission(team_id=team_id, file_path=file_path, status="VALID")
        db.add(submission)
        db.commit()
        db.refresh(submission)
        
        return submission
