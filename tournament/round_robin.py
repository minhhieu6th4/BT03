def generate_round_robin_schedule(teams: list):
    """
    Tạo lịch thi đấu vòng tròn (Round Robin) cho danh sách các đội trong một bảng.
    Trả về danh sách các cặp đấu (team_a, team_b).
    Mỗi đội sẽ gặp tất cả các đội còn lại đúng 1 lần (BO1).
    """
    teams_copy = list(teams)
    if len(teams_copy) % 2 != 0:
        teams_copy.append(None) # Thêm 'bye' nếu số lượng đội lẻ

    n = len(teams_copy)
    matches = []
    
    for round_idx in range(n - 1):
        for i in range(n // 2):
            team_a = teams_copy[i]
            team_b = teams_copy[n - 1 - i]
            
            if team_a is not None and team_b is not None:
                matches.append((team_a, team_b))
                
        # Thuật toán xoay vòng: Giữ nguyên đội đầu tiên, xoay tròn các đội còn lại
        teams_copy.insert(1, teams_copy.pop())
        
    return matches
