import os
import re
from backend.config.settings import settings

class FileStorageUtils:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Làm sạch tên file để tránh Path Traversal Attack.
        Chỉ cho phép giữ lại chữ cái, chữ số, dấu chấm, gạch ngang và gạch dưới.
        """
        filename = os.path.basename(filename) # Loại bỏ toàn bộ path nguy hiểm
        return re.sub(r'[^a-zA-Z0-9.\-_]', '', filename)

    @staticmethod
    def get_team_submission_dir(team_id: int) -> str:
        """
        Xác định và tạo thư mục an toàn để chứa file bài nộp của một đội thi.
        """
        team_dir = os.path.abspath(os.path.join(settings.SUBMISSIONS_DIR, f"team_{team_id}"))
        
        # Kiểm tra bảo mật cực kỳ quan trọng:
        # Đảm bảo thư mục vừa tạo chắc chắn phải nằm TRONG thư mục SUBMISSIONS_DIR
        # Đề phòng hacker nhập team_id = "../../../windows/system32"
        if not team_dir.startswith(os.path.abspath(settings.SUBMISSIONS_DIR)):
            raise ValueError("Phát hiện nguy cơ bảo mật (Path Traversal)")
            
        os.makedirs(team_dir, exist_ok=True)
        return team_dir

    @staticmethod
    def save_code_file(code_bytes: bytes, team_id: int, target_filename: str = "student_bot.py") -> str:
        """
        Lưu dữ liệu code thô xuống đĩa cứng an toàn.
        """
        team_dir = FileStorageUtils.get_team_submission_dir(team_id)
        safe_filename = FileStorageUtils.sanitize_filename(target_filename)
        file_path = os.path.join(team_dir, safe_filename)
        
        with open(file_path, "wb") as f:
            f.write(code_bytes)
                
        return file_path
