from typing import List, Tuple, Any

def generate_knockout_bracket(seeded_teams: list) -> list:
    """
    Tạo bracket cho vòng Knockout (Round of 32).
    Nguyên tắc: Seed 1 vs Seed 32, Seed 2 vs Seed 31...
    """
    if len(seeded_teams) != 32:
        raise ValueError("Vòng knockout đầu tiên yêu cầu chính xác 32 đội.")
    
    matches = []
    n = len(seeded_teams)
    for i in range(n // 2):
        match = (seeded_teams[i], seeded_teams[n - 1 - i])
        matches.append(match)
        
    return matches

class KnockoutStage:
    """Quản lý các vòng đấu loại trực tiếp từ Round of 32 đến Chung Kết"""
    STAGES = ["round_of_32", "round_of_16", "quarterfinal", "semifinal", "final"]

    @staticmethod
    def pair_next_round(winners: list) -> list:
        """Ghép cặp cho vòng kế tiếp từ danh sách các đội thắng"""
        matches = []
        n = len(winners)
        for i in range(0, n, 2):
            if i + 1 < n:
                matches.append((winners[i], winners[i+1]))
        return matches

    @staticmethod
    def get_match_format(stage: str) -> str:
        formats = {
            "round_of_32": "BO3",
            "round_of_16": "BO3",
            "quarterfinal": "BO5",
            "semifinal": "BO5",
            "final": "BO7"
        }
        return formats.get(stage, "BO3")
