import sys
import os
import json
import traceback

def main():
    """
    Script này sẽ chạy BÊN TRONG Docker Container.
    Nhiệm vụ: Import student_bot, nhận JSON từ stdin, gọi get_move và trả ra stdout.
    """
    try:
        bot_file = os.environ.get("BOT_FILE")
        if bot_file and os.path.exists(bot_file):
            import importlib.util
            spec = importlib.util.spec_from_file_location("student_bot", bot_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            bot = mod.Bot()
        else:
            # Tìm kiếm file .py bất kỳ trong /sandbox hoặc thư mục hiện tại
            search_dirs = ["/sandbox", "."]
            found_py = None
            for d in search_dirs:
                if os.path.exists(d):
                    py_files = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".py") and f != "runner.py"]
                    if py_files:
                        found_py = py_files[0]
                        break

            if found_py:
                import importlib.util
                spec = importlib.util.spec_from_file_location("student_bot", found_py)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                bot = mod.Bot()
            else:
                from student_bot import Bot
                bot = Bot()
    except Exception as e:
        print(json.dumps({"error": f"Init failed: {str(e)}"}))
        sys.stdout.flush()
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        try:
            state = json.loads(line)
            move = bot.get_move(state)
            
            # Print kết quả ra stdout cho Host đọc
            print(json.dumps({"move": move}))
            sys.stdout.flush()
        except Exception:
            # Print lỗi ra stdout
            print(json.dumps({"error": traceback.format_exc()}))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
