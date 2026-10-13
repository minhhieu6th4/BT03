import ast
import os
from game.game_engine import GameEngine
from game.rule_set import RuleSet
from game.move import Move
from judge.match_runner import DockerBotWrapper

class BotValidator:
    FORBIDDEN_IMPORTS = {
        'os', 'sys', 'subprocess', 'requests', 'socket', 'urllib',
        'builtins', 'eval', 'exec', 'shutil', 'importlib', 'pty',
        'platform', 'ctypes', 'multiprocessing'
    }

    @classmethod
    def validate(cls, code: str) -> tuple[bool, str]:
        """
        Kiểm tra mã nguồn tĩnh của sinh viên bằng AST:
        - Cú pháp Python
        - Các thư viện bị cấm
        - Sự tồn tại của class Bot và phương thức get_move
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Lỗi cú pháp Python (Syntax Error): {str(e)}"

        has_class = False
        has_get_move = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split('.')[0]
                    if root_pkg in cls.FORBIDDEN_IMPORTS:
                        return False, f"Forbidden import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split('.')[0]
                    if root_pkg in cls.FORBIDDEN_IMPORTS:
                        return False, f"Forbidden import: {node.module}"
            elif isinstance(node, ast.ClassDef) and node.name == 'Bot':
                has_class = True
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == 'get_move':
                        has_get_move = True

        if not has_class:
            return False, "Missing class 'Bot'"
        if not has_get_move:
            return False, "Missing method 'get_move' in class 'Bot'"

        return True, "Valid"

    @classmethod
    def validate_file(cls, file_path: str) -> tuple[bool, str]:
        """Kiểm tra mã nguồn từ đường dẫn file"""
        if not os.path.exists(file_path):
            return False, f"File không tồn tại: {file_path}"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            return cls.validate(code)
        except Exception as e:
            return False, f"Không thể đọc file: {str(e)}"

    @classmethod
    def validate_execution(cls, file_path: str, timeout: float = 2.0) -> tuple[bool, str]:
        """
        Chạy thử bot trong môi trường sandbox với dữ liệu bàn cờ mẫu:
        - Khởi tạo process qua DockerBotWrapper
        - Gửi state bàn cờ ban đầu của quân Đỏ
        - Nhận nước đi và kiểm tra tính hợp lệ theo luật GameEngine
        """
        # Bước 1: Static AST Check trước
        valid, msg = cls.validate_file(file_path)
        if not valid:
            return False, msg

        # Bước 2: Chạy thực tế trong Sandbox
        engine = GameEngine(RuleSet.default())
        initial_state = engine.state.to_dict()

        wrapper = None
        try:
            wrapper = DockerBotWrapper(bot_dir=file_path, team_name="RED", time_limit=timeout)
            move_dict = wrapper.get_move(initial_state)

            if not isinstance(move_dict, dict) or "from" not in move_dict or "to" not in move_dict:
                return False, f"Nước đi trả về không đúng định dạng: {move_dict}"

            move = Move.from_dict(move_dict)
            if not engine.is_valid_move(engine.state, move):
                return False, f"Nước đi của bot không hợp lệ theo luật cờ: {move.to_dict()}"

            return True, "Bot hợp lệ và sẵn sàng thi đấu!"
        except TimeoutError as te:
            return False, f"Bot timeout: {str(te)}"
        except Exception as e:
            return False, f"Lỗi thực thi bot trong Sandbox: {str(e)}"
        finally:
            if wrapper:
                wrapper.close()
