from sqlalchemy.orm import Session
from backend.models.ranking import Ranking
from backend.models.team import Team

class RankingService:
    @staticmethod
    def get_leaderboard(db: Session):
        rankings = db.query(Ranking, Team.name).join(Team, Ranking.team_id == Team.id).order_by(Ranking.score.desc()).all()
        result = []
        for r in rankings:
            result.append({
                "id": r.Ranking.id,
                "team_id": r.Ranking.team_id,
                "score": r.Ranking.score,
                "wins": r.Ranking.wins,
                "losses": r.Ranking.losses,
                "team_name": r.name
            })
        return result
