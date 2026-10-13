# ⚔️ UET Algorithm Battle — Đấu Trường Thuật Toán AI

**UET Algorithm Battle** là nền tảng tổ chức thi đấu thuật toán trí tuệ nhân tạo (Bot vs Bot) dựa trên bộ môn cờ chiến thuật **Kéo - Búa - Bao (Rock - Paper - Scissors) trên bàn cờ 9x9**. Hệ thống cung cấp môi trường lập trình, kiểm duyệt bảo mật mã nguồn tự động (Static AST & Docker Sandbox), phòng thi đấu trực tuyến 1v1, bảng xếp hạng toàn server và hệ thống tổ chức giải đấu **Knockout (Loại trực tiếp)** hoàn chỉnh.

> 🌐 **Link truy cập trực tuyến (Khác mạng / Internet qua Cloudflare Tunnel)**:  
> 👉 **[https://blah-biology-fcc-ceo.trycloudflare.com/index.html](https://blah-biology-fcc-ceo.trycloudflare.com/index.html)**

---

## 🌟 Tính Năng Nổi Bật

### 1. ♟️ Game Engine Cờ Kéo - Búa - Bao 9x9
- **Bàn cờ 9x9**: Hai phe **Đỏ (RED)** và **Xanh (BLUE)** xuất phát đối xứng ở hai đầu chiến tuyến, mỗi bên gồm 9 quân cờ (3 Kéo ✂️, 3 Búa 🪨, 3 Bao 📄) bảo vệ căn cứ chính (`Base`).
- **Di chuyển 8 hướng**: Mỗi lượt, quân cờ di chuyển 1 ô theo 8 hướng (ngang, dọc, chéo).
- **Cơ chế giao tranh**: Khắc chế trực tiếp theo quy tắc **Búa thắng Kéo**, **Kéo thắng Bao**, **Bao thắng Búa**. Hai quân cùng loại giao chiến sẽ **cùng bị tiêu diệt** (Mutual Destruction).
- **Điều kiện phân định Thắng / Thua**:
  1. **Chiếm căn cứ địch**: Đưa bất kỳ quân cờ nào của mình vào ô căn cứ đối phương (`(0, 4)` hoặc `(8, 4)`).
  2. **Tiêu diệt toàn bộ quân cờ**: Đối phương bị tiêu diệt sạch **tất cả các quân cờ** trên bàn cờ.
  3. **Hết 200 lượt đi (Tie-breaker)**: Xét tổng số quân còn sống trên bàn cờ; nếu bằng nhau (hoặc trong giải đấu Knockout cần phân thắng bại), hệ thống xét tiếp khoảng cách Manhattan gần nhất tới căn cứ địch để quyết định người chiến thắng.

### 2. 🤖 Quản Lý Bot Python & Kiểm Duyệt Sandbox
- Người chơi nộp mã nguồn Bot (`.py`) trực tiếp trên giao diện web.
- **Tự động kiểm duyệt 2 lớp**:
  - **Lớp 1 (AST Static Validator)**: Phân tích cây cú pháp Python, đảm bảo tồn tại `class Bot` và phương thức `get_move()`, đồng thời chặn các thư viện bị cấm (`os`, `sys`, `subprocess`, `socket`, `shutil`, `http`,...).
  - **Lớp 2 (Sandbox Execution)**: Chạy thử nghiệm với trạng thái bàn cờ giả lập trong môi trường cô lập (Docker Sandbox hoặc Subprocess giới hạn thời gian 2.0s/nước đi) trước khi cấp trạng thái **`READY`**.
- Hỗ trợ lưu trữ lịch sử phiên bản (`BotVersion`) giúp người chơi dễ dàng nâng cấp thuật toán.

### 3. ⚔️ Chế Độ Thi Đấu Thường (PvP 1v1 Rooms)
- Tạo phòng đấu riêng hoặc tham gia phòng đang mở qua danh sách sảnh / mã phòng.
- Cơ chế duyệt người chơi vào phòng, chọn Bot `READY`, nhấn **Sẵn sàng** và bắt đầu trận đấu.
- Điểm số cộng trực tiếp vào **Bảng Xếp Hạng Toàn Server**:
  - **Thắng**: `+3 điểm` | **Hòa**: `+1 điểm` | **Thua**: `+0 điểm`.

### 4. 🏆 Hệ Thống Giải Đấu Knockout (Loại Trực Tiếp)
- **Tổ chức & Duyệt đăng ký**:
  - Người tổ chức tạo giải đấu (cấu hình số lượng tối thiểu $\ge 4$ và tối đa).
  - Người chơi gửi yêu cầu đăng ký kèm theo Bot có trạng thái `READY`.
  - Người tổ chức xét duyệt (`ACCEPTED` / `REJECTED`) với cơ chế khóa dữ liệu chống vượt quá giới hạn.
- **Thuật toán chia nhánh tổng quát ($N \ge 4$)**:
  - Hỗ trợ mọi số lượng người chơi hợp lệ (kể cả số lẻ hoặc không phải lũy thừa của 2 như 5, 6, 7, 9, 12...).
  - Tự động tính khung nhánh $2^k$ gần nhất và phân bổ ngẫu nhiên các suất miễn đấu (**`BYE`**) ở vòng đầu tiên để người chơi đặc cách tiến thẳng vào vòng trong.
- **Điểm danh 10 phút & Xử thua vắng mặt (`FORFEIT`)**:
  - Khi trận đấu mở (`READY`), hai tuyển thủ có **10 phút** để nhấn **"Tham gia trận đấu"**.
  - Khi cả 2 cùng tham gia, hệ thống tự động kích hoạt trận đấu. Nếu quá hạn 10 phút, người vắng mặt sẽ bị xử thua `FORFEIT`.
- **Bàn cờ trực quan (Interactive Battle Arena)**:
  - Khi trận đấu diễn ra, giao diện hiển thị bàn cờ 9x9 trực quan tái hiện từng nước đi của hai Bot (hỗ trợ tua bước, dừng/chạy, chỉnh tốc độ `0.5x` – `4x`).
  - **Bảo mật kịch tính**: Kết quả và danh tính người chiến thắng được ẩn hoàn toàn trong suốt quá trình quân cờ di chuyển và **chỉ công bố chính thức khi nước đi cuối cùng kết thúc**.

### 5. 🌐 Hỗ Trợ Đa Tab (Multi-Account) & Mạng LAN/Wi-Fi
- Sử dụng `sessionStorage` cho phép mở **nhiều tab trình duyệt với các tài khoản khác nhau trên cùng một máy tính** để tự kiểm thử và thi đấu.
- Tự động đồng bộ địa chỉ API theo IP mạng nội bộ (LAN/Wi-Fi), giúp nhiều máy tính khác nhau truy cập và thi đấu cùng lúc.

---

## 📁 Cấu Trúc Thư Mục Dự Án

```text
UET-Algorithm-Battle/
├── backend/                  # Backend FastAPI Server
│   ├── api/                  # Các RESTful API Endpoints (auth, bots, rooms, tournaments, matches, ranking...)
│   ├── config/               # Cấu hình hệ thống & biến môi trường (settings.py)
│   ├── database/             # Kết nối SQLAlchemy (MySQL & tự động fallback SQLite)
│   ├── models/               # Các bảng Database ORM (User, Bot, Room, Tournament, Match, PlayerStat...)
│   ├── schemas/              # Pydantic Schemas kiểm tra dữ liệu đầu vào/đầu ra
│   ├── services/             # Nghiệp vụ cốt lõi (Tournament Knockout, Room PvP, Bot Validator, Match Service)
│   └── main.py               # Điểm khởi chạy ứng dụng FastAPI
├── bots/                     # Hệ thống Bot AI
│   ├── bot_api.py            # API hỗ trợ lập trình viên viết Bot
│   ├── example_bot.py        # Bot mẫu chiến thuật cơ bản
│   ├── greedy_bot.py         # Bot mẫu chiến thuật tham lam (Greedy)
│   ├── random_bot.py         # Bot mẫu đi ngẫu nhiên
│   └── submissions/          # Thư mục lưu trữ mã nguồn Bot của người chơi nộp lên
├── configs/                  # Cấu hình JSON cho luật thi đấu và các vòng giải đấu
├── database/                 # File khởi tạo cấu trúc bảng SQL gốc (schema.sql)
├── docs/                     # Tài liệu thiết kế kiến trúc, luật chơi và hướng dẫn API Bot
├── frontend/                 # Giao diện người dùng (HTML5, CSS3, Vanilla JS)
│   ├── css/                  # Giao diện chuẩn hóa (style.css)
│   ├── js/                   # Logic điều hướng, xác thực đa tab và kết nối API
│   ├── index.html            # Trang chủ
│   ├── rules.html            # Trang luật chơi chi tiết 9x9
│   ├── submit.html           # Trang quản lý & nộp Bot Python
│   ├── rooms.html            # Sảnh phòng đấu thường 1v1
│   ├── room_detail.html      # Chi tiết phòng đấu & bàn cờ trực tiếp
│   ├── tournaments.html      # Danh sách & tạo giải đấu Knockout
│   ├── tournament_detail.html# Nhánh đấu Bracket, duyệt đơn & bàn cờ trực quan Knockout
│   └── ranking.html          # Bảng xếp hạng toàn server
├── game/                     # Core Game Engine cờ Kéo - Búa - Bao 9x9
│   ├── board.py              # Quản lý ma trận bàn cờ 9x9
│   ├── game_engine.py        # Luật di chuyển, giao chiến và kiểm tra điều kiện thắng/thua
│   ├── move.py               # Cấu trúc nước đi
│   └── rule_set.py           # Quản lý thông số luật chơi
├── judge/                    # Hệ thống chấm tự động & Docker Sandbox
│   ├── validator.py          # Kiểm tra mã nguồn tĩnh bằng AST
│   ├── sandbox.py            # Môi trường cô lập thực thi Bot
│   ├── match_runner.py       # Điều phối trận đấu giữa 2 Bot
│   └── Dockerfile            # Cấu hình Docker image cô lập cho Bot
├── tests/                    # Bộ 62 Unit & Integration Tests (Pytest)
├── tournament/               # Các thuật toán chia bảng, xếp hạt giống và quản lý luật giải đấu
├── docker-compose.yml        # Khởi tạo nhanh MySQL 8.0 bằng Docker
├── init_db.py                # Script tạo bảng Database thủ công
├── requirements.txt          # Danh sách thư viện Python cần thiết
├── run_all.bat               # Script khởi động nhanh trên Windows (Command Prompt)
└── run_all.ps1               # Script khởi động nhanh trên Windows (PowerShell + hiển thị IP LAN)
```

---

## 🛠️ Yêu Cầu Hệ Thống & Cài Đặt

### 1. Yêu cầu môi trường
- **Python**: Phiên bản `3.10` trở lên (khuyên dùng `3.11`).
- **Cơ sở dữ liệu**:
  - **Chế độ mặc định (Zero-Config)**: Nếu máy chưa bật MySQL, hệ thống **tự động chuyển sang dùng SQLite** (`uet_algorithm_battle.db`) ngay tại thư mục gốc mà không cần cài đặt gì thêm.
  - **Chế độ MySQL**: Hỗ trợ MySQL 8.0 qua XAMPP hoặc Docker (`docker-compose up -d`).
- **Trình duyệt**: Chrome, Edge, Firefox (hỗ trợ Live Server trên VS Code ở cổng `5500`).

### 2. Cài đặt thư viện Python
Mở terminal tại thư mục gốc của dự án và chạy lệnh:

```bash
pip install -r requirements.txt
```

---

## 🚀 Hướng Dẫn Khởi Chạy Nhanh

### Cách 1: Khởi chạy tự động trên Windows (Khuyên dùng)
1. Mở thư mục dự án trong **VS Code**, chuột phải vào [`frontend/index.html`](frontend/index.html) và chọn **"Open with Live Server"** (hoặc bấm nút **Go Live** ở góc dưới bên phải VS Code để chạy cổng `5500`).
2. Click đúp chuột vào file **`run_all.bat`** (hoặc chạy `./run_all.ps1` trong PowerShell).
   - Hệ thống sẽ tự động khởi động Backend FastAPI tại địa chỉ `http://0.0.0.0:5000` và mở trình duyệt web.

### Cách 2: Khởi chạy thủ công bằng dòng lệnh
1. **Khởi động Backend API (Cổng 5000)**:
   ```bash
   python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 5000
   ```
2. **Khởi động Frontend (Cổng 5500)**:
   - Dùng tiện ích **Live Server** trong VS Code hoặc chạy lệnh Python HTTP Server:
   ```bash
   python -m http.server 5500
   ```
3. **Các đường dẫn truy cập**:
   - 🌐 **Giao diện Web**: `http://127.0.0.1:5500/frontend/index.html`
   - ⚙️ **Backend API Root**: `http://127.0.0.1:5000/`
   - 📄 **Tài liệu Swagger UI**: `http://127.0.0.1:5000/docs`

### 🌍 Truy cập từ máy khác (Cùng Wi-Fi / Khác mạng)
- **Khác mạng Wi-Fi (Qua Internet — Cloudflare Tunnel)**:
  - Truy cập trực tiếp qua đường dẫn: **[https://blah-biology-fcc-ceo.trycloudflare.com/index.html](https://blah-biology-fcc-ceo.trycloudflare.com/index.html)**
- **Cùng mạng Wi-Fi / LAN**: Chạy `run_all.ps1` để xem địa chỉ IP LAN của máy chủ (ví dụ `http://192.168.1.15:5500/frontend/index.html`). Đảm bảo mở cổng `5000` và `5500` trên Windows Firewall nếu bị chặn.

---

## 🤖 Hướng Dẫn Viết Bot Python

Mỗi file `.py` nộp lên hệ thống cần định nghĩa lớp `Bot` cùng phương thức `get_move(self, board, player_id)`:

```python
import random

class Bot:
    def __init__(self):
        self.directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1)
        ]

    def get_move(self, board, player_id):
        """
        Tham số:
        - board: Ma trận 9x9. Mỗi ô là None hoặc dict {'player': 'RED'|'BLUE', 'type': 'ROCK'|'PAPER'|'SCISSORS'}
        - player_id: 'RED' (Căn cứ tại (8, 4)) hoặc 'BLUE' (Căn cứ tại (0, 4))

        Trả về:
        - Tuple ((from_row, from_col), (to_row, to_col))
        """
        own_base = (8, 4) if player_id == "RED" else (0, 4)
        valid_moves = []

        for r in range(9):
            for c in range(9):
                cell = board[r][c]
                if cell and cell.get("player") == player_id:
                    for dr, dc in self.directions:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < 9 and 0 <= nc < 9 and (nr, nc) != own_base:
                            target = board[nr][nc]
                            if target is None or target.get("player") != player_id:
                                valid_moves.append(((r, c), (nr, nc)))

        return random.choice(valid_moves) if valid_moves else None
```

> **Lưu ý bảo mật**: Không import các module thao tác hệ thống hoặc mạng (`os`, `sys`, `subprocess`, `socket`, `requests`, `urllib`, `pathlib`,...) và không dùng các hàm `eval()`, `exec()`, `open()`. Thời gian suy nghĩ tối đa cho mỗi lượt là **2000ms (2 giây)**.

---

## 🧪 Kiểm Thử Tự Động (Unit & Integration Tests)

Dự án đi kèm bộ **62 bài kiểm thử tự động** bao phủ toàn bộ Game Engine, Bot Validator, Sandbox, Phòng đấu PvP, Bảng xếp hạng và Giải đấu Knockout (bao gồm xử lý BYE, duyệt đơn, điểm danh và xử thua `FORFEIT`).

Chạy toàn bộ kiểm thử bằng lệnh:

```bash
python -m pytest
```

---

## 📚 Tài Liệu Tham Khảo Thêm

Xem thêm tài liệu chi tiết trong thư mục [`docs/`](docs/):
- [`docs/architecture.md`](docs/architecture.md) — Kiến trúc tổng thể hệ thống.
- [`docs/game-rules.md`](docs/game-rules.md) — Đặc tả luật cờ Kéo - Búa - Bao 9x9.
- [`docs/bot-api.md`](docs/bot-api.md) — Tài liệu API dành cho người lập trình Bot.
- [`docs/tournament-rules.md`](docs/tournament-rules.md) — Quy chế giải đấu.
