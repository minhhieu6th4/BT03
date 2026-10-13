import pytest
import os
from backend.utils.file_storage import FileStorageUtils
from judge.validator import BotValidator

def test_submission_validation_and_storage():
    valid_code = b"""
class Bot:
    def get_move(self, state):
        return {"from": [0, 1], "to": [1, 1]}
"""
    is_valid, msg = BotValidator.validate(valid_code.decode('utf-8'))
    assert is_valid is True
    
    # Lưu file qua storage utils
    saved_path = FileStorageUtils.save_code_file(valid_code, team_id=999, target_filename="student_bot.py")
    assert os.path.exists(saved_path)
    assert os.path.basename(saved_path) == "student_bot.py"
    
    # Dọn dẹp
    if os.path.exists(saved_path):
        os.remove(saved_path)
