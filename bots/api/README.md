# UET Algorithm Battle - Bot API

## 1. Giao tiếp (Communication)
Trong môi trường giải đấu thật, Bot của sinh viên không được gọi trực tiếp bằng class Python thông thường, mà sẽ giao tiếp với hệ thống **Judge** thông qua `stdin`/`stdout`.
Tuy nhiên, để đơn giản hóa quá trình phát triển, sinh viên chỉ cần cung cấp file `student_bot.py` có chứa class `Bot` và hàm `get_move(self, state_dict)`.

## 2. Dữ liệu Đầu vào (Input)
Hàm `get_move` sẽ nhận được `state_dict` với định dạng JSON (Python dictionary) như sau:
```json
{
  "turn": 12,
  "team": "RED",
  "board": [
    [0, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    ... (mảng 2 chiều 9x9)
  ]
}
```
**Ý nghĩa các số trên Bàn cờ (Board):**
* `0`: Ô trống
* `1, 2, 3`: Lần lượt là ROCK, PAPER, SCISSORS của đội RED.
* `4, 5, 6`: Lần lượt là ROCK, PAPER, SCISSORS của đội BLUE.

## 3. Dữ liệu Đầu ra (Output)
Hàm `get_move` phải trả về một Dictionary chứa tọa độ nguồn `from` và tọa độ đích `to`. Cả 2 đều là array `[row, col]`.
```python
return {
    "from": [0, 1],
    "to": [1, 1]
}
```

## 4. Các giới hạn (Sandbox)
* Không được import thư viện hệ thống như `os`, `sys`, `subprocess`, `requests`.
* Code chạy quá thời gian (VD: 2 giây) sẽ bị xử thua.
* Code crash hoặc ném Exception sẽ bị xử thua.
