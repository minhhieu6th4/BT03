import random

class Bot:
    """
    BOT 1: CHIẾN THẦN TẤN CÔNG (Aggressive Bot)
    Chiến lược:
    1. Ưu tiên cao nhất: Nước đi về đích để THẮNG NGAY LẬP TỨC!
       - Đỏ (RED) về đích tại ô (8, 8).
       - Xanh (BLUE) về đích tại ô (0, 0).
    2. Ưu tiên thứ hai: Ăn quân đối phương (Đá ăn Kéo, Kéo ăn Giấy, Giấy ăn Đá).
    3. Ưu tiên thứ ba: Tiến gần về phía ô đích của đối thủ.
    """

    def get_move(self, state_dict: dict) -> dict:
        legal_moves = state_dict.get("legal_moves", [])
        if not legal_moves:
            raise Exception("Không có nước đi hợp lệ nào!")

        board = state_dict.get("board", [])
        team_name = state_dict.get("team", "RED")
        size = len(board) if board else 9

        # Tọa độ đích đến để giành chiến thắng ngay lập tức
        goal_r, goal_c = (size - 1, size - 1) if team_name == "RED" else (0, 0)

        # Định nghĩa quy luật tương khắc (Thắng ăn Thua)
        # 1: Đỏ Đá, 2: Đỏ Giấy, 3: Đỏ Kéo
        # 4: Xanh Đá, 5: Xanh Giấy, 6: Xanh Kéo
        def is_winning_combat(my_val: int, enemy_val: int) -> bool:
            # Chuyển về loại: 1: Đá (Rock), 2: Giấy (Paper), 3: Kéo (Scissors)
            my_type = my_val if my_val <= 3 else my_val - 3
            enemy_type = enemy_val if enemy_val <= 3 else enemy_val - 3

            if my_type == 1 and enemy_type == 3:  # Đá đập Kéo
                return True
            if my_type == 3 and enemy_type == 2:  # Kéo cắt Giấy
                return True
            if my_type == 2 and enemy_type == 1:  # Giấy bọc Đá
                return True
            return False

        scored_moves = []

        for move in legal_moves:
            r1, c1 = move["from"]
            r2, c2 = move["to"]
            my_piece = board[r1][c1]
            target_cell = board[r2][c2]

            score = 0

            # 1. Nếu bước này đi thẳng vào đích của đối thủ -> THẮNG NGAY! (1000 điểm)
            if r2 == goal_r and c2 == goal_c:
                score += 1000

            # 2. Nếu ô đến có quân địch
            elif target_cell != 0:
                if is_winning_combat(my_piece, target_cell):
                    score += 500  # Ăn được quân đối phương
                else:
                    score -= 200  # Bị đối phương ăn hoặc hòa nhau chết cả hai

            # 3. Điểm tiến gần mục tiêu (khoảng cách Chebyshev giảm)
            dist_old = max(abs(r1 - goal_r), abs(c1 - goal_c))
            dist_new = max(abs(r2 - goal_r), abs(c2 - goal_c))
            distance_gain = dist_old - dist_new
            score += distance_gain * 10

            scored_moves.append((score, move))

        # Tìm điểm số cao nhất
        max_score = max(s[0] for s in scored_moves)
        best_moves = [s[1] for s in scored_moves if s[0] == max_score]

        return random.choice(best_moves)
