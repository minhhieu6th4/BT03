from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from fastapi import HTTPException

from backend.models.user import User
from backend.models.player_stat import PlayerStat
from backend.models.match import Match
from backend.schemas.player_stat import PlayerStatResponse, ServerLeaderboardEntry

class PlayerService:
    @staticmethod
    def get_or_create_stats(db: Session, user_id: int) -> PlayerStat:
        """Lấy hoặc tạo mới bản ghi thống kê người chơi"""
        stat = db.query(PlayerStat).filter(PlayerStat.user_id == user_id).first()
        if not stat:
            stat = PlayerStat(user_id=user_id, total_matches=0, wins=0, draws=0, losses=0, total_points=0)
            db.add(stat)
            db.commit()
            db.refresh(stat)
        return stat

    @staticmethod
    def get_server_rank(db: Session, user_id: int) -> int:
        """
        Tính thứ hạng trên toàn server:
        Sắp xếp theo: total_points DESC, wins DESC, user_id ASC
        """
        all_stats = (
            db.query(PlayerStat)
            .order_by(desc(PlayerStat.total_points), desc(PlayerStat.wins), PlayerStat.user_id.asc())
            .all()
        )
        for index, s in enumerate(all_stats, start=1):
            if s.user_id == user_id:
                return index
        return len(all_stats) + 1

    @staticmethod
    def get_player_profile(db: Session, user: User) -> PlayerStatResponse:
        """Lấy hồ sơ cá nhân với đầy đủ thống kê, điểm số và rank server"""
        stat = PlayerService.get_or_create_stats(db, user.id)
        rank = PlayerService.get_server_rank(db, user.id)
        win_rate = round((stat.wins / stat.total_matches * 100), 1) if stat.total_matches > 0 else 0.0

        return PlayerStatResponse(
            user_id=user.id,
            username=user.username,
            total_matches=stat.total_matches,
            wins=stat.wins,
            draws=stat.draws,
            losses=stat.losses,
            total_points=stat.total_points,
            server_rank=rank,
            win_rate=win_rate
        )

    @staticmethod
    def record_match_result(
        db: Session,
        match: Match,
        winner_user_id: Optional[int] = None,
        is_draw: bool = False
    ):
        """
        Ghi nhận kết quả trận đấu thường và cộng điểm IDEMPOTENT (chống cộng lặp):
        - Thắng: +3 điểm (Thua: 0 điểm)
        - Hòa: +1 điểm mỗi bên
        - total_points = wins * 3 + draws
        - Chỉ cộng nếu match.points_awarded == False
        - Chỉ áp dụng cho chế độ đấu thường (match_type == 'REGULAR')
        """
        if match.points_awarded:
            return  # Đã cộng điểm rồi, không cộng lần 2

        if match.match_type != "REGULAR":
            return  # Trận đấu giải thống kê riêng

        red_user_id = match.red_user_id
        blue_user_id = match.blue_user_id

        if not red_user_id or not blue_user_id:
            return  # Không đủ 2 người chơi hợp lệ

        red_stat = PlayerService.get_or_create_stats(db, red_user_id)
        blue_stat = PlayerService.get_or_create_stats(db, blue_user_id)

        if is_draw:
            match.is_draw = True
            match.winner_user_id = None
            red_stat.draws += 1
            blue_stat.draws += 1
        else:
            match.is_draw = False
            match.winner_user_id = winner_user_id
            if winner_user_id == red_user_id:
                red_stat.wins += 1
                blue_stat.losses += 1
            elif winner_user_id == blue_user_id:
                blue_stat.wins += 1
                red_stat.losses += 1

        red_stat.recalculate()
        blue_stat.recalculate()

        match.points_awarded = True
        match.status = "COMPLETED"
        db.commit()

    @staticmethod
    def get_server_leaderboard(db: Session, limit: int = 100) -> List[ServerLeaderboardEntry]:
        """
        Bảng xếp hạng toàn server:
        - Sắp xếp theo: total_points DESC, wins DESC, user_id ASC
        - Hiển thị: rank, user_id, username, total_matches, wins, draws, losses, total_points, win_rate
        """
        # Đảm bảo mọi user đều có bản ghi trong player_stats
        users = db.query(User).all()
        for u in users:
            PlayerService.get_or_create_stats(db, u.id)

        stats = (
            db.query(PlayerStat, User.username)
            .join(User, PlayerStat.user_id == User.id)
            .order_by(desc(PlayerStat.total_points), desc(PlayerStat.wins), PlayerStat.user_id.asc())
            .limit(limit)
            .all()
        )

        leaderboard = []
        for rank, (st, uname) in enumerate(stats, start=1):
            wr = round((st.wins / st.total_matches * 100), 1) if st.total_matches > 0 else 0.0
            leaderboard.append(
                ServerLeaderboardEntry(
                    rank=rank,
                    user_id=st.user_id,
                    username=uname,
                    total_matches=st.total_matches,
                    wins=st.wins,
                    draws=st.draws,
                    losses=st.losses,
                    total_points=st.total_points,
                    win_rate=wr
                )
            )
        return leaderboard
