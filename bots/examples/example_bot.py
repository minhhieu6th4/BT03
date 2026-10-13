import random

class Bot:
    """
    Bot mẫu tối thiểu (Example Bot):
    Nhận trạng thái trò chơi qua state_dict và trả về nước đi hợp lệ.
    """
    def get_move(self, state_dict: dict) -> dict:
        # Cách 1: Sử dụng danh sách legal_moves được hệ thống tính sẵn
        legal_moves = state_dict.get("legal_moves", [])
        if legal_moves:
            return random.choice(legal_moves)

        # Cách 2: Tự tính toán dựa trên ma trận bàn cờ board
        board = state_dict.get("board", [])
        size = len(board)
        team_name = state_dict.get("team", "RED")
        team_vals = [1, 2, 3] if team_name == "RED" else [4, 5, 6]

        my_pieces = []
        for r in range(size):
            for c in range(size):
                if board[r][c] in team_vals:
                    my_pieces.append((r, c))

        valid_moves = []
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]

        for r, c in my_pieces:
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size:
                    target_val = board[nr][nc]
                    if target_val not in team_vals:  # Không giẫm quân mình
                        if team_name == "RED" and nr == 0 and nc == 0:
                            continue
                        if team_name == "BLUE" and nr == size - 1 and nc == size - 1:
                            continue
                        valid_moves.append({"from": [r, c], "to": [nr, nc]})

        if not valid_moves:
            raise Exception("Không tìm thấy nước đi hợp lệ nào")

        return random.choice(valid_moves)
