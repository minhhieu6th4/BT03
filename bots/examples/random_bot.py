import random

class Bot:
    """
    RandomBot: Chọn ngẫu nhiên một nước đi hợp lệ.
    Tận dụng trực tiếp danh sách 'legal_moves' do hệ thống cung cấp sẵn.
    """
    def get_move(self, state_dict: dict) -> dict:
        legal_moves = state_dict.get("legal_moves")
        if legal_moves:
            return random.choice(legal_moves)

        board = state_dict["board"]
        size = len(board)
        
        # State_dict có chứa trường "team" là "RED" hoặc "BLUE"
        team_name = state_dict.get("team", "RED")
        team_vals = [1, 2, 3] if team_name == "RED" else [4, 5, 6]
        
        # Tìm tất cả quân cờ của mình
        my_pieces = []
        for r in range(size):
            for c in range(size):
                if board[r][c] in team_vals:
                    my_pieces.append((r, c))
                    
        valid_moves = []
        # 8 hướng di chuyển
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        # Lọc tất cả các bước đi hợp lệ
        for r, c in my_pieces:
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size:
                    # Ô đích không được chứa quân của cùng phe
                    target = board[nr][nc]
                    if target not in team_vals:
                        # Không được đi vào ô đích của chính phe mình
                        if team_name == "RED" and nr == 0 and nc == 0:
                            continue
                        if team_name == "BLUE" and nr == size - 1 and nc == size - 1:
                            continue
                        
                        valid_moves.append({
                            "from": [r, c],
                            "to": [nr, nc]
                        })
                        
        if not valid_moves:
            raise Exception("No valid moves available")
            
        # Chọn ngẫu nhiên 1 bước đi
        return random.choice(valid_moves)
