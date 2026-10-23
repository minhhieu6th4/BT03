from typing import List, Tuple, Set
from collections import deque
from game.game_engine import get_reserved_positions

SUPPORTED_MAP_SIZES = [4, 5, 6, 9, 15, 18]

def validate_custom_map(size: int, rocks: List[List[int]]) -> Tuple[bool, str]:
    """
    Xác thực tính hợp lệ của custom map:
    - Kích thước bàn cờ hỗ trợ: 4x4, 5x5, 6x6, 9x9, 15x15, 18x18.
    - Tọa độ đá phải nằm trong phạm vi bàn cờ (0 <= r < size, 0 <= c < size).
    - Không có tọa độ đá bị trùng lặp.
    - Không đặt đá lên ô căn cứ (Base) hoặc vị trí xuất phát bắt buộc của quân cờ.
    - Số lượng đá không vượt quá giới hạn cho phép ((size * size) // 3).
    - Map phải đảm bảo tính khả thi: tồn tại đường đi liên thông giữa 2 căn cứ (BFS).
    """
    if size not in SUPPORTED_MAP_SIZES:
        return False, f"Kích thước bàn cờ không hợp lệ: {size}x{size}. Hệ thống hỗ trợ: 4x4, 5x5, 6x6, 9x9, 15x15, 18x18."

    max_rocks = (size * size) // 3
    if len(rocks) > max_rocks:
        return False, f"Số lượng đá ({len(rocks)}) vượt quá giới hạn tối đa cho phép ({max_rocks} ô) của bàn cờ {size}x{size}."

    seen_rocks: Set[Tuple[int, int]] = set()
    reserved_pos = get_reserved_positions(size)

    for r_coord in rocks:
        if not isinstance(r_coord, (list, tuple)) or len(r_coord) != 2:
            return False, f"Định dạng tọa độ đá không hợp lệ: {r_coord}. Phải là [row, col]."
        r, c = r_coord[0], r_coord[1]
        if not (isinstance(r, int) and isinstance(c, int)):
            return False, f"Tọa độ đá phải là số nguyên: ({r}, {c})."
        if not (0 <= r < size and 0 <= c < size):
            return False, f"Tọa độ đá ({r}, {c}) nằm ngoài phạm vi bàn cờ {size}x{size}."
        if (r, c) in seen_rocks:
            return False, f"Trùng lặp tọa độ đá tại ({r}, {c})."
        seen_rocks.add((r, c))

        if (r, c) in reserved_pos:
            return False, f"Không được đặt đá lên vị trí xuất phát hoặc căn cứ tại ({r}, {c})."

    # Kiểm tra liên thông cơ bản: tồn tại đường đi giữa căn cứ Red (0, 0) và căn cứ Blue (size-1, size-1)
    start = (0, 0)
    target = (size - 1, size - 1)
    queue = deque([start])
    visited = {start}
    found = False

    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

    while queue:
        curr_r, curr_c = queue.popleft()
        if (curr_r, curr_c) == target:
            found = True
            break
        for dr, dc in directions:
            nr, nc = curr_r + dr, curr_c + dc
            if 0 <= nr < size and 0 <= nc < size:
                if (nr, nc) not in visited and (nr, nc) not in seen_rocks:
                    visited.add((nr, nc))
                    queue.append((nr, nc))

    if not found:
        return False, "Bàn cờ bị chia cắt hoàn toàn bởi đá cản, không tồn tại đường đi giữa 2 căn cứ!"

    return True, "Map hợp lệ"
