from typing import List, Dict, Any, Optional
from .round_robin import generate_round_robin_schedule
from .ranking import RankingManager

class Group:
    """Quản lý một bảng đấu trong giai đoạn vòng bảng"""
    def __init__(self, group_id: str, name: str, teams: Optional[List[Dict[str, Any]]] = None):
        self.group_id = group_id
        self.name = name
        self.teams = teams or []
        self.matches = []

    def add_team(self, team: Dict[str, Any]):
        self.teams.append(team)

    def generate_matches(self) -> List[Dict[str, Any]]:
        pairings = generate_round_robin_schedule(self.teams)
        self.matches = []
        for i, (red, blue) in enumerate(pairings, 1):
            self.matches.append({
                "match_id": f"{self.group_id}_m{i:03d}",
                "group_id": self.group_id,
                "red_team": red,
                "blue_team": blue,
                "format": "BO1",
                "status": "SCHEDULED",
                "score": {"red": 0, "blue": 0},
                "winner": None
            })
        return self.matches

    def record_match_result(self, match_id: str, winner: str, red_score: int = 1, blue_score: int = 0):
        for m in self.matches:
            if m["match_id"] == match_id:
                m["status"] = "COMPLETED"
                m["winner"] = winner
                m["score"] = {"red": red_score, "blue": blue_score}
                break

    def get_standings(self) -> List[Dict[str, Any]]:
        return RankingManager.calculate_standings(self.teams, self.matches)
