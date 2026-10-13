import subprocess
import json
import os
import sys
import shutil
import threading
import queue

def is_docker_available() -> bool:
    """Kiểm tra Docker Desktop / Docker Engine có khả dụng không"""
    if not shutil.which("docker"):
        return False
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2
        )
        return res.returncode == 0
    except Exception:
        return False

class DockerBotWrapper:
    """
    Wrapper quản lý thực thi Bot an toàn.
    Ưu tiên chạy bên trong Docker Container (với --network none, memory 256m, cpus 1.0).
    Tự động fallback sang Isolated Subprocess với Thread Timeout nếu môi trường chưa cài Docker.
    """
    def __init__(self, bot_dir: str, team_name: str, time_limit: float = 2.0):
        self.team_name = team_name
        self.time_limit = time_limit
        
        # Hỗ trợ bot_dir là thư mục hoặc trực tiếp là file .py
        bot_path = os.path.abspath(bot_dir)
        if os.path.isfile(bot_path):
            self.bot_file = bot_path
            self.bot_dir = os.path.dirname(bot_path)
        else:
            self.bot_dir = bot_path
            candidate = os.path.join(self.bot_dir, "student_bot.py")
            if os.path.exists(candidate):
                self.bot_file = candidate
            else:
                py_files = [f for f in os.listdir(self.bot_dir) if f.endswith(".py")] if os.path.exists(self.bot_dir) else []
                self.bot_file = os.path.join(self.bot_dir, py_files[0]) if py_files else candidate

        self.runner_script = os.path.abspath(os.path.join(os.path.dirname(__file__), 'runner.py'))
        self.use_docker = False
        
        self.sandbox_image = "uet-algorithm-battle-sandbox"
        # Thử Docker nếu khả dụng
        if is_docker_available():
            for img_name in ["uet-algorithm-battle-sandbox", "uet-bot-sandbox"]:
                try:
                    img_check = subprocess.run(
                        ["docker", "images", "-q", img_name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        timeout=2
                    )
                    if img_check.returncode == 0 and img_check.stdout.strip():
                        self.use_docker = True
                        self.sandbox_image = img_name
                        break
                except Exception:
                    pass

        if self.use_docker:
            bot_filename = os.path.basename(self.bot_file) if hasattr(self, 'bot_file') and self.bot_file else "student_bot.py"
            # Khởi chạy trong Docker Sandbox được cô lập hoàn toàn
            cmd = [
                "docker", "run", "--rm", "-i",
                "--network", "none",
                "--memory", "256m",
                "--cpus", "1.0",
                "-e", f"BOT_FILE=/sandbox/{bot_filename}",
                "-e", "PYTHONPATH=/sandbox",
                "-v", f"{self.bot_dir}:/sandbox:ro",
                "-v", f"{self.runner_script}:/runner.py:ro",
                self.sandbox_image,
                "python", "/runner.py"
            ]
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
        else:
            # Chạy qua Isolated Subprocess
            env = os.environ.copy()
            env["PYTHONPATH"] = self.bot_dir
            env["PYTHONIOENCODING"] = "utf-8"
            if hasattr(self, 'bot_file') and os.path.exists(self.bot_file):
                env["BOT_FILE"] = self.bot_file

            python_bin = sys.executable or "python"
            self.process = subprocess.Popen(
                [python_bin, self.runner_script],
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

    def _readline_with_timeout(self, timeout: float) -> str:
        """Đọc 1 dòng từ stdout của process với cơ chế Thread timeout an toàn"""
        q = queue.Queue()
        def worker():
            try:
                line = self.process.stdout.readline()
                q.put((line, None))
            except Exception as e:
                q.put((None, e))

        reader_thread = threading.Thread(target=worker, daemon=True)
        reader_thread.start()
        reader_thread.join(timeout)

        if reader_thread.is_alive():
            self.close()
            raise TimeoutError(f"Bot ({self.team_name}) vượt quá giới hạn thời gian {timeout}s!")

        line, err = q.get_nowait()
        if err:
            raise err
        return line

    def get_move(self, state_dict: dict) -> dict:
        if self.process.poll() is not None:
            err = self.process.stderr.read() if self.process.stderr else ""
            raise Exception(f"Bot tiến trình đã dừng (Exit code: {self.process.returncode}). Lỗi: {err.strip()}")

        # Truyền state qua stdin
        self.process.stdin.write(json.dumps(state_dict) + "\n")
        self.process.stdin.flush()

        response_line = self._readline_with_timeout(self.time_limit)
        if not response_line:
            err = self.process.stderr.read() if self.process.stderr else ""
            raise Exception(f"Bot không trả về kết quả ra stdout. Lỗi: {err.strip()}")

        try:
            data = json.loads(response_line.strip())
        except Exception as e:
            raise Exception(f"Dữ liệu bot trả về không phải định dạng JSON hợp lệ: {response_line[:100]}")

        if "error" in data:
            raise Exception(f"Lỗi runtime trong mã bot: {data['error']}")

        if "move" not in data or not isinstance(data["move"], dict):
            raise Exception("JSON trả về thiếu trường 'move'!")

        move = data["move"]
        if "from" not in move or "to" not in move:
            raise Exception("Trường 'move' phải chứa tọa độ 'from' và 'to'!")

        return move

    def close(self):
        try:
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=1)
        except Exception:
            pass
