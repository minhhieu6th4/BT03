import random

class Bot:
    """
    BOT 2: CHIẾN THUẬT PHÒNG THỦ & PHẢN CÔNG (Tactical Bot)
    Chiến lược:
    1. Ưu tiên 1: Chạm đích chiến thắng tuyệt đối nếu có cơ hội (Turn Win).
    2. Ưu tiên 2: Phản công ăn quân địch khi có lợi thế tương khắc.
    3. Ưu tiên 3: Né tránh hiểm nguy (tránh đi vào ô bị quân địch xung quanh đe dọa ăn thịt).
    4. Ưu tiên 4: Dồn sức cho quân tiên phong ở gần đích nhất tiến lên.
    """

    def get_move(self, state_dict: dict) -> dict:
        legal_moves = state_dict.get("legal_moves", [])
        if not legal_moves:
            raise Exception("Hết nước đi hợp lệ!")

        board = state_dict.get("board", [])
        team_name = state_dict.get("team", "RED")
        size = len(board) if board else 9

        # Căn cứ đối thủ
        goal_r, goal_c = (size - 1, size - 1) if team_name == "RED" else (0, 0)
        enemy_vals = [4, 5, 6] if team_name == "RED" else [1, 2, 3]

        def get_piece_type(val: int) -> int:
            """Trả về 1: Đá, 2: Giấy, 3: Kéo"""
            return val if val <= 3 else val - 3

        def beats(t1: int, t2: int) -> bool:
            """Kiểm tra loại t1 có thắng loại t2 không"""
            return (t1 == 1 and t2 == 3) or (t1 == 3 and t2 == 2) or (t1 == 2 and t2 == 1)

        def is_cell_threatened(r: int, c: int, my_piece_val: int) -> bool:
            """Kiểm tra ô (r, c) có nguy cơ bị quân địch xung quanh ăn ở lượt sau không"""
            my_type = get_piece_type(my_piece_val)
            directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size:
                    cell_val = board[nr][nc]
                    if cell_val in enemy_vals:
                        enemy_type = get_piece_type(cell_val)
                        if beats(enemy_type, my_type):
                            return True
            return False

        scored_moves = []

        for move in legal_moves:
            r1, c1 = move["from"]
            r2, c2 = move["to"]
            my_piece = board[r1][c1]
            my_type = get_piece_type(my_piece)
            target_piece = board[r2][c2]

            score = 100

            # 1. Thắng ngay lập tức
            if r2 == goal_r and c2 == goal_c:
                score += 5000
                scored_moves.append((score, move))
                continue

            # 2. Combat ăn quân
            if target_piece in enemy_vals:
                enemy_type = get_piece_type(target_piece)
                if beats(my_type, enemy_type):
                    score += 600  # Ăn quân thành công
                elif my_type == enemy_type:
                    score += 50   # Đổi quân ngang giá
                else:
                    score -= 800  # Tự sát (bị ăn)

            # 3. Đánh giá độ an toàn sau khi bước tới ô đích
            if is_cell_threatened(r2, c2, my_piece):
                score -= 300  # Tránh đi vào ô nguy hiểm

            # 4. Ưu tiên đưa quân đã ở gần đích tiến thêm 1 bước
            dist_old = max(abs(r1 - goal_r), abs(c1 - goal_c))
            dist_new = max(abs(r2 - goal_r), abs(c2 - goal_c))
            if dist_new < dist_old:
                score += 150 - (dist_new * 10)  # Càng gần đích điểm càng cao

            scored_moves.append((score, move))

        # Chọn nước đi có điểm chiến thuật cao nhất
        max_score = max(s[0] for s in scored_moves)
        best_moves = [s[1] for s in scored_moves if s[0] == max_score]

        return random.choice(best_moves)
