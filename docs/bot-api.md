# 🤖 HƯỚNG DẪN VIẾT VÀ NỘP BOT PYTHON — UET ALGORITHM BATTLE

Chào mừng bạn đến với Đấu trường Thuật toán **UET Algorithm Battle**! Tài liệu này cung cấp toàn bộ quy định kỹ thuật, hợp đồng dữ liệu JSON, bot mẫu và hướng dẫn từng bước để lập trình bot tham gia thi đấu.

---

## 1. Cấu trúc File Bot Tối Thiểu

File bot nộp lên hệ thống là một file mã nguồn Python thuần túy (`.py`), chứa **duy nhất** một class có tên là `Bot` và phương thức `get_move(self, state_dict: dict) -> dict`:

```python
import random

class Bot:
    def get_move(self, state_dict: dict) -> dict:
        # Nhận vào trạng thái trận đấu (state_dict)
        # Trả về nước đi hợp lệ
        legal_moves = state_dict.get("legal_moves", [])
        if legal_moves:
            return random.choice(legal_moves)
        raise Exception("Không có nước đi hợp lệ!")
```

> **Lưu ý bảo mật Sandbox:**
> - Nghiêm cấm import các thư viện hệ thống hoặc mạng: `os`, `sys`, `subprocess`, `socket`, `requests`, `urllib`, `builtins`, `eval`, `exec`, `shutil`...
> - Bạn được phép sử dụng các thư viện chuẩn an toàn như: `random`, `math`, `heapq`, `collections`, `itertools`, `copy`.

---

## 2. Hợp Đồng Dữ Liệu Đầu Vào (JSON Input)

Ở mỗi lượt thi đấu, hệ thống chuyển trạng thái trò chơi cho phương thức `get_move(state_dict)` với cấu trúc sau:

```json
{
  "turn": 1,
  "team": "RED",
  "player": "red",
  "board": [
    [0, 1, 1, 0, 0, 0, 0, 0, 0],
    [2, 3, 0, 0, 0, 0, 0, 0, 0],
    [2, 0, 3, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 6, 0, 5],
    [0, 0, 0, 0, 0, 0, 0, 6, 5],
    [0, 0, 0, 0, 0, 0, 4, 4, 0]
  ],
  "legal_moves": [
    {"from": [0, 1], "to": [0, 2]},
    {"from": [0, 1], "to": [1, 2]},
    {"from": [1, 0], "to": [2, 0]}
  ]
}
```

### Ý nghĩa các trường:
- `turn`: Số lượt hiện tại của trận đấu ($1 \le \text{turn} \le 200$).
- `team`: Phe điều khiển hiện tại (`"RED"` hoặc `"BLUE"`).
- `player`: Tên màu chữ thường (`"red"` hoặc `"blue"`).
- `board`: Mảng 2 chiều kích thước $9 \times 9$ đại diện cho bàn cờ:
  - `0`: Ô trống.
  - Quân Đỏ (**RED**): `1` = Búa (Rock), `2` = Bao (Paper), `3` = Kéo (Scissors).
  - Quân Xanh (**BLUE**): `4` = Búa (Rock), `5` = Bao (Paper), `6` = Kéo (Scissors).
- `legal_moves`: Danh sách tất cả các nước đi hợp lệ ở lượt hiện tại do Game Engine tính toán sẵn. Bạn có thể chọn ngay một nước đi từ danh sách này hoặc tự đánh giá chiến thuật.

---

## 3. Hợp Đồng Dữ Liệu Đầu Ra (JSON Output)

Phương thức `get_move` **bắt buộc** trả về một `dict` (hoặc JSON) chứa đúng 2 trường tọa độ `from` và `to`:

```json
{
  "from": [0, 1],
  "to": [1, 1]
}
```

### Quy định tọa độ:
- Định dạng: `[row, col]` trong đó $0 \le \text{row} < 9$ và $0 \le \text{col} < 9$.
- `[0, 0]` là góc trên cùng bên trái (căn cứ Đỏ). Quân Đỏ **không được** đi vào ô `[0, 0]`.
- `[8, 8]` là góc dưới cùng bên phải (căn cứ Xanh). Quân Xanh **không được** đi vào ô `[8, 8]`.
- Mỗi bước đi chỉ được di chuyển đúng 1 ô theo 8 hướng (ngang, dọc, chéo).
- Không được di chuyển vào ô có quân cùng phe.

### Luật tương khắc khi giẫm lên quân địch (Combat):
- 🪨 Búa thắng ✂️ Kéo.
- ✂️ Kéo thắng 📄 Bao.
- 📄 Bao thắng 🪨 Búa.
- Nếu cùng loại quân: **Cả 2 quân cùng bị tiêu diệt**.

### Điều kiện thắng:
1. Chiếm được căn cứ đối phương (Đỏ đi vào `[8, 8]` hoặc Xanh đi vào `[0, 0]`).
2. Tiêu diệt toàn bộ quân thuộc một loại của đối phương (ví dụ đối phương hết sạch quân Kéo).

---

## 4. Giới Hạn Tài Nguyên & Môi Trường Sandbox

Mỗi bot chạy trong môi trường **Docker Sandbox** (hoặc tiến trình cô lập an toàn) với các giới hạn:
- **Thời gian xử lý mỗi nước đi (`Timeout`):** Tối đa **2.0 giây**.
- **Bộ nhớ RAM:** Tối đa **256 MB**.
- **CPU:** Tối đa **1.0 Core**.
- **Mạng (`Network`):** Hoàn toàn bị ngắt kết nối (`--network none`).
- Nếu bot bị quá thời gian (Timeout), sinh exception runtime hoặc trả về nước đi sai luật, bot sẽ bị **xử thua kỹ thuật ngay lập tức**.

---

## 5. Các Bot Mẫu Có Sẵn

Dự án cung cấp 3 bot mẫu tại thư mục `bots/examples/` (bạn cũng có thể tải về trực tiếp từ trang **🤖 Bot Của Tôi** trên web):

1. **`random_bot.py`**: Chọn ngẫu nhiên một nước đi trong `legal_moves`. Phù hợp cho người mới bắt đầu.
2. **`greedy_bot.py`**: Đánh giá khoảng cách và ưu tiên tiến về căn cứ đối phương.
3. **`example_bot.py`**: Sử dụng hướng đối tượng (OOP) thông qua các lớp hỗ trợ trong thư mục `bots/api/`.

---

## 6. Hướng Dẫn Test Bot Tại Máy Cá Nhân

Trước khi nộp lên hệ thống, bạn có thể kiểm tra bot của mình bằng một đoạn code Python đơn giản:

```python
from bots.examples.random_bot import Bot

bot = Bot()
mock_state = {
    "turn": 1,
    "team": "RED",
    "player": "red",
    "board": [[0]*9 for _ in range(9)],
    "legal_moves": [{"from": [0, 1], "to": [1, 1]}]
}

move = bot.get_move(mock_state)
print("Nước đi của bot:", move)
assert "from" in move and "to" in move
print("Bot hoạt động hoàn hảo!")
```

---

## 7. Quy Trình Nộp và Thi Đấu Trên Giao Diện Web

1. **Đăng ký / Đăng nhập** tài khoản tại API `http://127.0.0.1:5500/docs` hoặc giao diện Web.
2. Truy cập mục **🤖 Bot Của Tôi** trên thanh menu điều hướng.
3. Điền **Tên Bot**, chọn file `.py` và nhấn nút **"Nộp Bot Ngay"**.
4. Hệ thống sẽ tự động kiểm tra cú pháp và chạy thử 1 lượt trong Sandbox:
   - Nếu đạt chuẩn: Trạng thái hiển thị `READY` (màu xanh).
   - Nếu có lỗi: Trạng thái hiển thị `INVALID` kèm giải thích chi tiết.
5. Khi có phiên bản mới cải tiến chiến thuật, bạn nhấn nút **"Cập Nhật Bản Mới"** cho bot đó để tăng số phiên bản (v1 $\rightarrow$ v2 $\rightarrow$ v3) mà không làm mất lịch sử phiên bản cũ.
6. Vào mục **⚔️ Thi Đấu Thường** $\rightarrow$ Tạo phòng hoặc Vào phòng của bạn bè.
7. Chọn Bot của bạn từ danh sách $\rightarrow$ Bấm **"Sẵn Sàng"**.
8. Khi cả hai bên đã sẵn sàng, chủ phòng nhấn **"Bắt Đầu Trận Đấu"** để quan sát hai bot tự động giao đấu trực tiếp trên bàn cờ 9x9!
