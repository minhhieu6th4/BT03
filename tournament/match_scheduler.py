from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

class MatchScheduler:
    """Lập lịch thời gian thi đấu cho các trận đấu trong giải"""
    def __init__(self, start_time: Optional[datetime] = None):
        self.start_time = start_time or datetime(2026, 10, 12, 8, 0, 0, tzinfo=timezone.utc)

    def schedule_matches(self, matches: List[Dict[str, Any]], interval_minutes: int = 15) -> List[Dict[str, Any]]:
        current_time = self.start_time
        scheduled = []
        for match in matches:
            m_copy = dict(match)
            m_copy["scheduled_time"] = current_time.isoformat()
            current_time += timedelta(minutes=interval_minutes)
            scheduled.append(m_copy)
        return scheduled
