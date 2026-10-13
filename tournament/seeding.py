def select_top_32(groups_standings: dict) -> list:
    """
    Lọc ra 32 đội xuất sắc nhất từ 10 bảng.
    groups_standings: dict dạng { "Group A": [đội 1, đội 2,...], "Group B": [...] }
    Mỗi đội là một dict chứa thông tin điểm (points), hiệu số,...
    
    Quy tắc:
    - Top 3 của 10 bảng = 30 đội.
    - 2 đội hạng 4 có thành tích tốt nhất.
    """
    qualified_teams = []
    fourth_place_teams = []
    
    for group_name, standings in groups_standings.items():
        # Giả định standings của mỗi bảng đã được sắp xếp giảm dần theo điểm
        top_3 = standings[:3]
        qualified_teams.extend(top_3)
        
        if len(standings) >= 4:
            fourth_place_teams.append(standings[3])
            
    # Lọc 2 đội hạng 4 xuất sắc nhất dựa trên điểm số
    fourth_place_teams.sort(key=lambda x: x.get("points", 0), reverse=True)
    qualified_teams.extend(fourth_place_teams[:2])
    
    # Sắp xếp lại toàn bộ 32 đội để tính Seed (1 -> 32)
    qualified_teams.sort(key=lambda x: x.get("points", 0), reverse=True)
    
    return qualified_teams
