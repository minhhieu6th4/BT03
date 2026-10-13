import os
import sys

# Thêm thư mục ví dụ vào path để import được Bot
examples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples'))
sys.path.append(examples_dir)

def run_test():
    try:
        from greedy_bot import Bot
        bot = Bot()
    except Exception as e:
        print("❌ Lỗi khởi tạo Bot:", e)
        return
        
    print("✅ Khởi tạo Bot thành công.")
    
    # State giả lập cho test
    dummy_state = {
        "turn": 1,
        "team": "RED",
        "board": [[0] * 9 for _ in range(9)]
    }
    dummy_state["board"][0][1] = 1 # Đặt 1 quân RED ROCK
    
    print("\nTruyền vào State giả lập:")
    print(dummy_state)
    
    try:
        move = bot.get_move(dummy_state)
        print("\n✅ Bot trả về Move thành công:")
        print(move)
        
        if "from" in move and "to" in move:
            print("Cấu trúc JSON đầu ra hợp lệ!")
        else:
            print("❌ Thiếu 'from' hoặc 'to' trong kết quả.")
    except Exception as e:
        print("\n❌ Lỗi khi gọi get_move:", e)

if __name__ == "__main__":
    run_test()
