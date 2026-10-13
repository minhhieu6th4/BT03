from typing import List, Dict, Any
from .group import Group
from .seeding import select_top_32

class QualificationStage:
    """Quản lý toàn bộ vòng loại gồm 10 bảng đấu"""
    def __init__(self, total_groups: int = 10):
        self.total_groups = total_groups
        self.groups: Dict[str, Group] = {}
        for i in range(1, total_groups + 1):
            gid = f"group_{i:02d}"
            self.groups[gid] = Group(group_id=gid, name=f"Bảng {i}")

    def partition_teams(self, teams: List[Dict[str, Any]]):
        """Phân bổ các đội vào 10 bảng (mỗi bảng 10 đội)"""
        for i, team in enumerate(teams):
            group_idx = (i % self.total_groups) + 1
            gid = f"group_{group_idx:02d}"
            self.groups[gid].add_team(team)

        for group in self.groups.values():
            group.generate_matches()

    def get_all_standings(self) -> Dict[str, List[Dict[str, Any]]]:
        return {gid: g.get_standings() for gid, g in self.groups.items()}

    def get_top_32_advancing(self) -> List[Dict[str, Any]]:
        standings_dict = self.get_all_standings()
        return select_top_32(standings_dict)
