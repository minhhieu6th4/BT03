import os
import json
import math
import random
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.models.tournament import Tournament, TournamentParticipant, TournamentRound, TournamentMatch, TournamentMap
from backend.models.user import User
from backend.models.bot import Bot, BotVersion
from backend.models.match import Match
from backend.schemas.tournament import (
    TournamentResponse, TournamentDetailResponse, TournamentParticipantResponse,
    TournamentRoundResponse, TournamentMatchResponse,
    TournamentMapCreate, TournamentMapUpdate, TournamentMapResponse,
    TournamentScheduleCreate,
    MatchConfigUpdateRequest, SetupOverviewMatch, SetupOverviewResponse
)


class TournamentService:
    @staticmethod
    def _to_response(db: Session, t: Tournament) -> TournamentResponse:
        p_count = db.query(TournamentParticipant).filter(TournamentParticipant.tournament_id == t.id).count()
        accepted_count = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == t.id,
            TournamentParticipant.status == "ACCEPTED"
        ).count()
        pending_count = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == t.id,
            TournamentParticipant.status == "PENDING"
        ).count()

        return TournamentResponse(
            id=t.id,
            name=t.name,
            description=t.description or "",
            creator_id=t.creator_id,
            creator_name=t.creator.username if t.creator else None,
            min_participants=getattr(t, "min_participants", 4) or 4,
            max_participants=getattr(t, "max_participants", 32) or 32,
            max_concurrent_matches=getattr(t, "max_concurrent_matches", 4) or 4,
            status=t.status,
            participant_count=accepted_count if t.status not in ["REGISTRATION", "REGISTRATION_OPEN"] else p_count,
            accepted_count=accepted_count,
            pending_count=pending_count,
            champion_id=t.champion_id,
            champion_name=t.champion.username if t.champion else None,
            setup_started_at=getattr(t, "setup_started_at", None),
            published_at=getattr(t, "published_at", None),
            created_at=t.created_at
        )

    @staticmethod
    def create_tournament(
        db: Session,
        creator: User,
        name: str,
        description: str = "",
        min_participants: int = 4,
        max_participants: int = 32
    ) -> Tournament:
        """Tạo giải đấu loại trực tiếp mới"""
        if min_participants < 4:
            raise HTTPException(status_code=400, detail="Số lượng người tham gia tối thiểu phải từ 4 trở lên")
        if max_participants < min_participants:
            raise HTTPException(status_code=400, detail="Số lượng tối đa phải lớn hơn hoặc bằng số tối thiểu")

        t = Tournament(
            name=name,
            description=description,
            creator_id=creator.id,
            min_participants=min_participants,
            max_participants=max_participants,
            status="REGISTRATION_OPEN"
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return t

    @staticmethod
    def list_tournaments(db: Session) -> List[TournamentResponse]:
        tournaments = db.query(Tournament).order_by(Tournament.created_at.desc()).all()
        return [TournamentService._to_response(db, t) for t in tournaments]

    @staticmethod
    def get_tournament_detail(db: Session, tournament_id: int, current_user: Optional[User] = None) -> TournamentDetailResponse:
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")

        # Kích hoạt Scheduler Tick kiểm tra lịch trình, thời hạn 10 phút và hàng đợi chạy bot
        TournamentService.run_scheduler_tick(db, tournament_id)

        participants_db = (
            db.query(TournamentParticipant)
            .filter(TournamentParticipant.tournament_id == t.id)
            .order_by(TournamentParticipant.seed.asc(), TournamentParticipant.registered_at.asc())
            .all()
        )
        participants = [
            TournamentParticipantResponse(
                id=p.id,
                user_id=p.user_id,
                username=p.user.username if p.user else f"User {p.user_id}",
                bot_id=p.bot_id,
                bot_name=p.bot.name if p.bot else None,
                status=p.status,
                seed=p.seed,
                registered_at=p.registered_at,
                reviewed_at=p.reviewed_at
            )
            for p in participants_db
        ]

        rounds_db = (
            db.query(TournamentRound)
            .filter(TournamentRound.tournament_id == t.id)
            .order_by(TournamentRound.round_number.asc())
            .all()
        )
        rounds = []
        now = datetime.utcnow()
        is_host_or_admin = current_user and (current_user.id == t.creator_id or getattr(current_user, "is_admin", False))

        # Giai đoạn SETTING_UP: Chỉ Host/Admin mới có quyền xem nhánh đấu chưa công bố!
        if t.status != "SETTING_UP" or is_host_or_admin:
            for r in rounds_db:
                matches_db = (
                    db.query(TournamentMatch)
                    .filter(TournamentMatch.round_id == r.id)
                    .order_by(TournamentMatch.match_order.asc())
                    .all()
                )
                matches = []
                round_cur_wave = r.current_wave or 1
                total_waves_in_r = max((mat.wave_number or 1) for mat in matches_db) if matches_db else 1

                for m in matches_db:
                    seconds_remaining = None
                    if m.status == "READY" and m.participation_deadline:
                        rem = int((m.participation_deadline - now).total_seconds())
                        seconds_remaining = max(0, rem)

                    match_map = m.map or r.map
                    match_rocks = []
                    if match_map:
                        try:
                            match_rocks = json.loads(match_map.rocks_json or "[]")
                        except Exception:
                            match_rocks = []

                    matches.append(
                        TournamentMatchResponse(
                            id=m.id,
                            round_id=m.round_id,
                            match_order=m.match_order,
                            wave_number=m.wave_number or 1,
                            current_wave=round_cur_wave,
                            total_waves=total_waves_in_r,
                            player1_id=m.player1_id,
                            player1_name=m.player1.username if m.player1 else None,
                            player1_bot_id=m.player1_bot_id,
                            player1_bot_name=m.player1_bot.name if m.player1_bot else None,
                            player1_joined_at=m.player1_joined_at,
                            player2_id=m.player2_id,
                            player2_name=m.player2.username if m.player2 else None,
                            player2_bot_id=m.player2_bot_id,
                            player2_bot_name=m.player2_bot.name if m.player2_bot else None,
                            player2_joined_at=m.player2_joined_at,
                            winner_id=m.winner_id,
                            winner_name=m.winner.username if m.winner else None,
                            is_bye=m.is_bye,
                            status=m.status,
                            map_id=m.map_id or r.map_id,
                            map_name=match_map.name if match_map else "Bản đồ mặc định (9×9)",
                            map_size=match_map.size if match_map else 9,
                            map_reveal_at=None,
                            is_map_revealed=True,
                            rocks=match_rocks,
                            scheduled_at=m.scheduled_at,
                            check_in_opens_at=m.check_in_opens_at,
                            started_at=m.started_at,
                            completed_at=m.completed_at,
                            ready_at=m.ready_at,
                            participation_deadline=m.participation_deadline,
                            seconds_remaining=seconds_remaining,
                            result_reason=m.result_reason,
                            match_id=m.match_id,
                            is_configured=True
                        )
                    )

                map_obj = r.map
                rocks_disclosed = []
                if map_obj:
                    try:
                        rocks_disclosed = json.loads(map_obj.rocks_json or "[]")
                    except Exception:
                        rocks_disclosed = []

                rounds.append(
                    TournamentRoundResponse(
                        id=r.id,
                        round_number=r.round_number,
                        round_name=r.round_name,
                        status=r.status,
                        current_wave=round_cur_wave,
                        total_waves=total_waves_in_r,
                        map_id=r.map_id,
                        map_name=map_obj.name if map_obj else None,
                        map_size=map_obj.size if map_obj else 9,
                        map_announced_at=r.map_announced_at,
                        is_map_announced=True,
                        rocks=rocks_disclosed,
                        matches=matches
                    )
                )

        # Lấy danh sách map của giải đấu
        maps_db = db.query(TournamentMap).filter(TournamentMap.tournament_id == t.id).order_by(TournamentMap.id.asc()).all()
        maps_response = []
        for m_item in maps_db:
            try:
                r_list = json.loads(m_item.rocks_json or "[]")
            except Exception:
                r_list = []

            maps_response.append(
                TournamentMapResponse(
                    id=m_item.id,
                    tournament_id=m_item.tournament_id,
                    name=m_item.name,
                    size=m_item.size,
                    rocks=r_list,
                    version=m_item.version,
                    is_valid=m_item.is_valid,
                    creator_id=m_item.creator_id,
                    created_at=m_item.created_at,
                    updated_at=m_item.updated_at
                )
            )

        return TournamentDetailResponse(
            tournament=TournamentService._to_response(db, t),
            participants=participants,
            rounds=rounds,
            maps=maps_response
        )


    @staticmethod
    def register_participant(db: Session, tournament_id: int, user: User, bot_id: Optional[int] = None, auto_accept: bool = False):
        """Đăng ký tham gia giải đấu (mặc định trạng thái PENDING chờ người tổ chức duyệt)"""
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.status not in ["REGISTRATION", "REGISTRATION_OPEN"]:
            raise HTTPException(status_code=400, detail="Giải đấu đã đóng đăng ký")

        # Kiểm tra Bot hợp lệ nếu có chỉ định
        if bot_id:
            bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user.id).first()
            if not bot:
                raise HTTPException(status_code=404, detail="Không tìm thấy Bot của bạn")
            if bot.status not in ["READY", "UPLOADED", "VALIDATING"]:
                raise HTTPException(status_code=400, detail="Bot phải ở trạng thái READY hoặc hợp lệ để tham gia")

        existing = (
            db.query(TournamentParticipant)
            .filter(TournamentParticipant.tournament_id == t.id, TournamentParticipant.user_id == user.id)
            .first()
        )
        if existing:
            if existing.status == "ACCEPTED":
                raise HTTPException(status_code=400, detail="Bạn đã được chấp nhận vào giải đấu này rồi")
            elif existing.status == "PENDING":
                raise HTTPException(status_code=400, detail="Bạn đã gửi yêu cầu tham gia, đang chờ người tổ chức duyệt")
            else:
                # Nếu trước đó từng bị REJECTED hoặc CANCELLED thì cho phép gửi lại
                existing.status = "ACCEPTED" if auto_accept else "PENDING"
                existing.bot_id = bot_id
                existing.registered_at = datetime.utcnow()
                db.commit()
                return {"message": "Đã gửi lại yêu cầu tham gia giải đấu", "seed": existing.seed, "status": existing.status}

        # Nếu auto_accept=True (tự động chấp nhận), kiểm tra giới hạn max_participants
        if auto_accept:
            accepted_count = db.query(TournamentParticipant).filter(
                TournamentParticipant.tournament_id == t.id,
                TournamentParticipant.status == "ACCEPTED"
            ).count()
            if accepted_count >= (t.max_participants or 32):
                raise HTTPException(status_code=400, detail="Giải đấu đã đạt số lượng tuyển thủ tối đa")

        current_count = db.query(TournamentParticipant).filter(TournamentParticipant.tournament_id == t.id).count()
        participant = TournamentParticipant(
            tournament_id=t.id,
            user_id=user.id,
            bot_id=bot_id,
            status="ACCEPTED" if auto_accept else "PENDING",
            seed=current_count + 1
        )
        db.add(participant)
        db.commit()
        db.refresh(participant)
        return {"message": "Đăng ký thành công", "seed": participant.seed, "status": participant.status}

    @staticmethod
    def respond_registration(db: Session, tournament_id: int, participant_id: int, user: User, action: str):
        """Người tổ chức duyệt hoặc từ chối yêu cầu đăng ký của tuyển thủ"""
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")

        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải hoặc Admin mới có quyền duyệt yêu cầu")

        if t.status not in ["REGISTRATION", "REGISTRATION_OPEN"]:
            raise HTTPException(status_code=400, detail="Giải đấu đã bắt đầu hoặc đã kết thúc, không thể duyệt thêm")

        p = db.query(TournamentParticipant).filter(
            TournamentParticipant.tournament_id == t.id,
            TournamentParticipant.id == participant_id
        ).first()
        if not p:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu đăng ký")

        action_norm = action.upper()
        if action_norm in ["ACCEPTED", "APPROVE", "ACCEPT"]:
            if p.status == "ACCEPTED":
                return {"message": "Tuyển thủ đã được chấp nhận từ trước", "status": p.status}

            # Transaction-safe limit checking
            accepted_count = db.query(TournamentParticipant).filter(
                TournamentParticipant.tournament_id == t.id,
                TournamentParticipant.status == "ACCEPTED"
            ).count()
            if accepted_count >= (t.max_participants or 32):
                raise HTTPException(status_code=400, detail="Giải đấu đã đạt số lượng tuyển thủ tối đa")

            p.status = "ACCEPTED"
            p.reviewed_at = datetime.utcnow()
            p.reviewed_by_id = user.id
            db.commit()
            return {"message": "Đã chấp nhận tuyển thủ vào danh sách thi đấu chính thức", "status": "ACCEPTED"}

        elif action_norm in ["REJECTED", "REJECT"]:
            p.status = "REJECTED"
            p.reviewed_at = datetime.utcnow()
            p.reviewed_by_id = user.id
            db.commit()
            return {"message": "Đã từ chối yêu cầu tham gia", "status": "REJECTED"}
        else:
            raise HTTPException(status_code=400, detail="Hành động không hợp lệ (chỉ hỗ trợ ACCEPTED hoặc REJECTED)")

    @staticmethod
    def unregister_participant(db: Session, tournament_id: int, user: User):
        """Tuyển thủ hủy yêu cầu tham gia giải khi giải chưa bắt đầu"""
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.status not in ["REGISTRATION", "REGISTRATION_OPEN"]:
            raise HTTPException(status_code=400, detail="Giải đấu đang diễn ra hoặc đã kết thúc, không thể hủy đăng ký")

        participant = (
            db.query(TournamentParticipant)
            .filter(TournamentParticipant.tournament_id == t.id, TournamentParticipant.user_id == user.id)
            .first()
        )
        if not participant:
            raise HTTPException(status_code=400, detail="Bạn chưa đăng ký giải đấu này")

        participant.status = "CANCELLED"
        db.commit()
        return {"message": "Hủy đăng ký thành công", "status": "CANCELLED"}

    @staticmethod
    def list_registration_requests(db: Session, tournament_id: int, user: User) -> List[TournamentParticipantResponse]:
        """Danh sách yêu cầu đăng ký dành cho người tổ chức xem và duyệt"""
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")

        participants_db = (
            db.query(TournamentParticipant)
            .filter(TournamentParticipant.tournament_id == t.id)
            .order_by(TournamentParticipant.registered_at.desc())
            .all()
        )
        return [
            TournamentParticipantResponse(
                id=p.id,
                user_id=p.user_id,
                username=p.user.username if p.user else f"User {p.user_id}",
                bot_id=p.bot_id,
                bot_name=p.bot.name if p.bot else None,
                status=p.status,
                seed=p.seed,
                registered_at=p.registered_at,
                reviewed_at=p.reviewed_at
            )
            for p in participants_db
        ]

    @staticmethod
    def start_tournament(db: Session, tournament_id: int, user: User, auto_publish: bool = False) -> TournamentDetailResponse:
        """
        Khởi động giai đoạn thiết lập giải đấu Knockout:
        - Kiểm tra người có quyền tổ chức (Chủ giải hoặc Admin).
        - Kiểm tra tối thiểu min_participants (>= 4).
        - Xáo trộn ngẫu nhiên danh sách người chơi và tính toán nhánh đấu Knockout.
        - Chuyển trạng thái sang SETTING_UP (giải đấu riêng tư, thí sinh chưa thấy nhánh đấu).
        - Nếu auto_publish=True (hoặc chế độ publish): kích hoạt IN_PROGRESS và thời hạn 10 phút.
        """
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")

        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tạo giải hoặc Admin mới có quyền bắt đầu giải đấu")

        if t.status not in ["REGISTRATION", "REGISTRATION_OPEN"]:
            raise HTTPException(status_code=400, detail="Giải đấu đã bắt đầu hoặc đã kết thúc")

        # 1. Lấy danh sách tuyển thủ đã ACCEPTED
        accepted_participants = (
            db.query(TournamentParticipant)
            .filter(TournamentParticipant.tournament_id == t.id, TournamentParticipant.status == "ACCEPTED")
            .order_by(TournamentParticipant.seed.asc())
            .all()
        )
        # Fallback hỗ trợ backward-compat: nếu chưa có ai ACCEPTED mà có PENDING >= min_participants
        if not accepted_participants:
            pending = (
                db.query(TournamentParticipant)
                .filter(TournamentParticipant.tournament_id == t.id, TournamentParticipant.status == "PENDING")
                .order_by(TournamentParticipant.seed.asc())
                .all()
            )
            min_req = getattr(t, "min_participants", 4) or 4
            if len(pending) >= min_req:
                for p in pending:
                    p.status = "ACCEPTED"
                db.flush()
                accepted_participants = pending

        n = len(accepted_participants)
        min_p = getattr(t, "min_participants", 4) or 4
        if n < min_p:
            raise HTTPException(
                status_code=400,
                detail=f"Số lượng người chơi được chấp nhận hiện tại là {n}. Giải đấu yêu cầu tối thiểu {min_p} người chơi để bắt đầu!"
            )

        # 2. Xáo trộn ngẫu nhiên danh sách người chơi
        random.shuffle(accepted_participants)
        for idx, p in enumerate(accepted_participants):
            p.seed = idx + 1
        db.flush()

        # 3. Tính toán kích thước nhánh Knockout và số suất đặc cách BYE
        k = math.ceil(math.log2(n))
        bracket_size = 2 ** k
        num_byes = bracket_size - n
        total_rounds = k

        bye_participants = accepted_participants[:num_byes]
        non_bye_participants = accepted_participants[num_byes:]

        # 4. Tạo các vòng thi đấu
        created_rounds = []
        for r_num in range(1, total_rounds + 1):
            matches_in_round = 2 ** (total_rounds - r_num)
            if matches_in_round == 1:
                r_name = "Chung kết"
            elif matches_in_round == 2:
                r_name = "Bán kết"
            elif matches_in_round == 4:
                r_name = "Tứ kết"
            else:
                r_name = f"Vòng {r_num}"

            round_obj = TournamentRound(
                tournament_id=t.id,
                round_number=r_num,
                round_name=r_name,
                status="IN_PROGRESS" if (r_num == 1 and auto_publish) else "PENDING"
            )
            db.add(round_obj)
            db.flush()
            created_rounds.append(round_obj)

        round_1 = created_rounds[0]
        round_1_matches = []
        now = datetime.utcnow()
        check_in_opens_3m = now + timedelta(minutes=3)
        deadline_10m = check_in_opens_3m + timedelta(minutes=10)
        current_match_order = 0

        # Cặp BYE ở vòng 1: Tuyển thủ được đặc cách vào thẳng vòng 2
        for bp in bye_participants:
            m = TournamentMatch(
                tournament_id=t.id,
                round_id=round_1.id,
                match_order=current_match_order,
                wave_number=1,
                player1_id=bp.user_id,
                player1_bot_id=bp.bot_id,
                player2_id=None,
                player2_bot_id=None,
                winner_id=bp.user_id,
                is_bye=True,
                status="COMPLETED",
                result_reason="BYE"
            )
            db.add(m)
            db.flush()
            round_1_matches.append(m)
            current_match_order += 1

        # Cặp thi đấu thật ở vòng 1: Mỗi wave tối đa 10 trận đấu song song
        real_idx = 0
        for i in range(0, len(non_bye_participants), 2):
            p1 = non_bye_participants[i]
            p2 = non_bye_participants[i+1] if (i+1) < len(non_bye_participants) else None
            is_bye_match = (p2 is None)
            wave_num = 1 if is_bye_match else ((real_idx // 10) + 1)
            if not is_bye_match:
                real_idx += 1

            is_ready_now = (auto_publish and not is_bye_match and wave_num == 1)

            m = TournamentMatch(
                tournament_id=t.id,
                round_id=round_1.id,
                match_order=current_match_order,
                wave_number=wave_num,
                player1_id=p1.user_id,
                player1_bot_id=p1.bot_id,
                player2_id=p2.user_id if p2 else None,
                player2_bot_id=p2.bot_id if p2 else None,
                winner_id=p1.user_id if is_bye_match else None,
                is_bye=is_bye_match,
                status="COMPLETED" if is_bye_match else ("READY" if is_ready_now else "WAITING"),
                ready_at=now if is_ready_now else None,
                check_in_opens_at=check_in_opens_3m if is_ready_now else None,
                participation_deadline=deadline_10m if is_ready_now else None,
                result_reason="BYE" if is_bye_match else None
            )
            db.add(m)
            db.flush()
            round_1_matches.append(m)
            current_match_order += 1

        # Tạo placeholder matches cho các vòng sau (Round 2 đến Chung kết)
        all_rounds_matches = {1: round_1_matches}
        for r_num in range(2, total_rounds + 1):
            cur_round = created_rounds[r_num - 1]
            matches_count = 2 ** (total_rounds - r_num)
            cur_matches = []
            for m_ord in range(matches_count):
                m = TournamentMatch(
                    tournament_id=t.id,
                    round_id=cur_round.id,
                    match_order=m_ord,
                    wave_number=(m_ord // 10) + 1,
                    player1_id=None,
                    player2_id=None,
                    winner_id=None,
                    is_bye=False,
                    status="WAITING"
                )
                db.add(m)
                db.flush()
                cur_matches.append(m)
            all_rounds_matches[r_num] = cur_matches

        # Đẩy ngay những người thắng suất đặc cách BYE từ Vòng 1 lên Vòng 2!
        for m in round_1_matches:
            if m.is_bye and m.winner_id:
                TournamentService._propagate_winner_to_next_round(
                    db, m, 1, total_rounds, all_rounds_matches
                )

        t.status = "IN_PROGRESS" if auto_publish else "SETTING_UP"
        t.setup_started_at = now
        if auto_publish:
            t.published_at = now
        db.commit()
        return TournamentService.get_tournament_detail(db, t.id, current_user=user)

    @staticmethod
    def _propagate_winner_to_next_round(
        db: Session,
        completed_match: TournamentMatch,
        current_round_num: int,
        total_rounds: int,
        all_rounds_matches: dict
    ):
        """Đẩy người thắng vào trận tương ứng ở vòng tiếp theo"""
        if current_round_num >= total_rounds:
            return  # Trận Chung kết

        next_round_num = current_round_num + 1
        next_match_order = completed_match.match_order // 2
        slot_is_player1 = (completed_match.match_order % 2 == 0)

        next_matches = all_rounds_matches.get(next_round_num, [])
        if next_match_order < len(next_matches):
            target_match = next_matches[next_match_order]
            winner_bot_id = completed_match.player1_bot_id if completed_match.winner_id == completed_match.player1_id else completed_match.player2_bot_id
            if slot_is_player1:
                target_match.player1_id = completed_match.winner_id
                target_match.player1_bot_id = winner_bot_id
            else:
                target_match.player2_id = completed_match.winner_id
                target_match.player2_bot_id = winner_bot_id
            db.flush()

    @staticmethod
    def check_tournament_deadlines(db: Session, tournament_id: int):
        """Kiểm tra thời hạn chuẩn bị của các trận READY: xử thua nếu vắng mặt hoặc tự động bắt đầu trận đấu"""
        now = datetime.utcnow()
        ready_matches = (
            db.query(TournamentMatch)
            .filter(
                TournamentMatch.tournament_id == tournament_id,
                TournamentMatch.status == "READY",
                TournamentMatch.participation_deadline != None,
                TournamentMatch.participation_deadline < now
            )
            .all()
        )
        for m in ready_matches:
            TournamentService._handle_deadline_expired(db, m)

    @staticmethod
    def _handle_deadline_expired(db: Session, m: TournamentMatch):
        """Xử lý trận đấu hết hạn tham gia: xử thua (FORFEIT) nếu vắng mặt hoặc khởi chạy trận đấu nếu cả hai đã sẵn sàng"""
        if m.status != "READY":
            return

        p1_joined = (m.player1_joined_at is not None)
        p2_joined = (m.player2_joined_at is not None)

        if p1_joined and not p2_joined:
            # Tuyển thủ 2 vắng mặt -> Tuyển thủ 1 thắng do đối thủ vắng mặt
            m.winner_id = m.player1_id
            m.status = "FORFEIT"
            m.result_reason = "NO_SHOW"
            hist_match = Match(
                match_type="TOURNAMENT",
                red_user_id=m.player1_id,
                blue_user_id=m.player2_id,
                winner_user_id=m.winner_id,
                red_bot_id=m.player1_bot_id,
                blue_bot_id=m.player2_bot_id,
                is_draw=False,
                points_awarded=False,
                status="COMPLETED",
                termination_reason=m.result_reason
            )
            db.add(hist_match)
            db.flush()
            m.match_id = hist_match.id
            TournamentService._on_match_concluded(db, m)
            db.commit()
        elif p2_joined and not p1_joined:
            # Tuyển thủ 1 vắng mặt -> Tuyển thủ 2 thắng do đối thủ vắng mặt
            m.winner_id = m.player2_id
            m.status = "FORFEIT"
            m.result_reason = "NO_SHOW"
            hist_match = Match(
                match_type="TOURNAMENT",
                red_user_id=m.player1_id,
                blue_user_id=m.player2_id,
                winner_user_id=m.winner_id,
                red_bot_id=m.player1_bot_id,
                blue_bot_id=m.player2_bot_id,
                is_draw=False,
                points_awarded=False,
                status="COMPLETED",
                termination_reason=m.result_reason
            )
            db.add(hist_match)
            db.flush()
            m.match_id = hist_match.id
            TournamentService._on_match_concluded(db, m)
            db.commit()
        elif not p1_joined and not p2_joined:
            # Cả hai đều không tham gia trong thời hạn -> Cả hai bị loại (DOUBLE_NO_SHOW)
            m.winner_id = None
            m.status = "FORFEIT"
            m.result_reason = "DOUBLE_NO_SHOW"
            hist_match = Match(
                match_type="TOURNAMENT",
                red_user_id=m.player1_id,
                blue_user_id=m.player2_id,
                winner_user_id=m.winner_id,
                red_bot_id=m.player1_bot_id,
                blue_bot_id=m.player2_bot_id,
                is_draw=False,
                points_awarded=False,
                status="COMPLETED",
                termination_reason=m.result_reason
            )
            db.add(hist_match)
            db.flush()
            m.match_id = hist_match.id
            TournamentService._on_match_concluded(db, m)
            db.commit()
        else:
            # Cả hai người chơi đều đã xác nhận/chọn bot -> Tự động bắt đầu trận đấu!
            now = datetime.utcnow()
            m.status = "PLAYING"
            m.started_at = now
            db.commit()
            TournamentService._execute_tournament_match(db, m)

    @staticmethod
    def join_match(db: Session, tournament_id: int, match_id: int, user: User):
        """
        Tuyển thủ bấm Tham Gia / Xác nhận trong thời hạn 3 phút chuẩn bị:
        - Điểm danh ghi nhận playerX_joined_at
        - Nếu cả 2 cùng điểm danh trước thời hạn: khởi động trận đấu tự động giữa 2 Bot!
        """
        TournamentService.check_tournament_deadlines(db, tournament_id)

        m = db.query(TournamentMatch).filter(
            TournamentMatch.tournament_id == tournament_id,
            TournamentMatch.id == match_id
        ).first()
        if not m:
            raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu")

        if m.status in ["COMPLETED", "FORFEIT"]:
            raise HTTPException(status_code=400, detail="Trận đấu này đã kết thúc")

        if m.status != "READY":
            raise HTTPException(status_code=400, detail=f"Trận đấu hiện đang ở trạng thái {m.status}, chưa mở để tham gia")

        now = datetime.utcnow()
        if m.check_in_opens_at and now < m.check_in_opens_at:
            remaining_secs = int((m.check_in_opens_at - now).total_seconds())
            raise HTTPException(
                status_code=400,
                detail=f"Chưa đến giờ điểm danh! Người chơi bắt buộc phải chờ hết 3 phút xem map (còn {remaining_secs} giây)."
            )

        if m.participation_deadline and now > m.participation_deadline:
            TournamentService._handle_deadline_expired(db, m)
            raise HTTPException(status_code=400, detail="Đã hết thời hạn 10 phút điểm danh thi đấu. Trận đấu đã bị xử phạt vắng mặt.")

        if user.id == m.player1_id:
            m.player1_joined_at = now
        elif user.id == m.player2_id:
            m.player2_joined_at = now
        else:
            raise HTTPException(status_code=403, detail="Bạn không phải tuyển thủ của trận đấu này")

        db.commit()
        db.refresh(m)

        # Nếu cả 2 người chơi cùng điểm danh thành công
        if m.player1_joined_at and m.player2_joined_at:
            m.status = "PLAYING"
            m.started_at = now
            db.commit()
            TournamentService._execute_tournament_match(db, m)

        return TournamentService.get_match_detail(db, tournament_id, match_id)

    @staticmethod
    def _execute_tournament_match(db: Session, m: TournamentMatch):
        """Khởi chạy trận đấu thực tế giữa 2 Bot trong Sandbox"""
        from game.game_engine import GameEngine
        from game.rule_set import RuleSet
        from game.move import Move
        from game.piece import Team
        from game.game_result import ResultType
        from judge.match_runner import DockerBotWrapper

        red_file = None
        blue_file = None
        if m.player1_bot_id:
            b1 = db.query(Bot).filter(Bot.id == m.player1_bot_id).first()
            if b1 and b1.current_version and b1.current_version.file_path and os.path.exists(b1.current_version.file_path):
                red_file = b1.current_version.file_path
        if m.player2_bot_id:
            b2 = db.query(Bot).filter(Bot.id == m.player2_bot_id).first()
            if b2 and b2.current_version and b2.current_version.file_path and os.path.exists(b2.current_version.file_path):
                blue_file = b2.current_version.file_path

        if not red_file or not os.path.exists(red_file):
            red_file = "bots/examples/random_bot.py" if os.path.exists("bots/examples/random_bot.py") else None
        if not blue_file or not os.path.exists(blue_file):
            blue_file = "bots/examples/random_bot.py" if os.path.exists("bots/examples/random_bot.py") else None

        # Tải cấu hình Map tùy chỉnh (nếu có gán cho trận hoặc vòng đấu)
        map_obj = m.map
        if not map_obj and m.round_id:
            r = db.query(TournamentRound).filter(TournamentRound.id == m.round_id).first()
            if r and r.map_id:
                map_obj = db.query(TournamentMap).filter(TournamentMap.id == r.map_id).first()
                if map_obj:
                    m.map_id = map_obj.id

        if map_obj:
            try:
                rocks = json.loads(map_obj.rocks_json or "[]")
            except Exception:
                rocks = []
            rule_set = RuleSet({"board_size": map_obj.size, "rocks": rocks})
        else:
            rule_set = RuleSet.default()

        if not m.started_at:
            m.started_at = datetime.utcnow()

        engine = GameEngine(rule_set)
        initial_board = engine.state.to_dict()["board"]
        moves_log = []
        winner_user_id = None
        is_draw = False
        termination_reason = "Trận đấu loại trực tiếp kết thúc thành công"

        wrapper_red = None
        wrapper_blue = None


        try:
            if red_file and blue_file:
                try:
                    wrapper_red = DockerBotWrapper(bot_dir=red_file, team_name="RED", time_limit=2.0)
                    wrapper_blue = DockerBotWrapper(bot_dir=blue_file, team_name="BLUE", time_limit=2.0)
                except Exception:
                    wrapper_red = None
                    wrapper_blue = None

            if wrapper_red and wrapper_blue:
                while True:
                    winner_res = engine.check_winner(engine.state)
                    if winner_res:
                        if winner_res.result_type == ResultType.DRAW:
                            is_draw = True
                            winner_user_id = None
                            termination_reason = winner_res.reason
                        else:
                            is_draw = False
                            winner_user_id = m.player1_id if winner_res.winner == Team.RED else m.player2_id
                            termination_reason = winner_res.reason
                        break

                    curr_team = engine.state.current_team
                    curr_wrapper = wrapper_red if curr_team == Team.RED else wrapper_blue
                    state_dict = engine.state.to_dict()

                    try:
                        move_dict = curr_wrapper.get_move(state_dict)
                        move = Move.from_dict(move_dict)
                    except Exception as e:
                        winner_user_id = m.player2_id if curr_team == Team.RED else m.player1_id
                        termination_reason = f"Bot {'Đỏ' if curr_team == Team.RED else 'Xanh'} lỗi kỹ thuật: {str(e)[:100]}"
                        is_draw = False
                        break

                    if not engine.is_valid_move(engine.state, move):
                        winner_user_id = m.player2_id if curr_team == Team.RED else m.player1_id
                        termination_reason = f"Bot {'Đỏ' if curr_team == Team.RED else 'Xanh'} phạm quy: {move_dict}"
                        is_draw = False
                        break

                    from_pos = list(move.from_pos)
                    to_pos = list(move.to_pos)
                    engine.apply_move(engine.state, move)
                    moves_log.append({
                        "turn": engine.state.turn,
                        "team": curr_team.value,
                        "player": curr_team.value.lower(),
                        "from": from_pos,
                        "to": to_pos,
                        "board_after": engine.state.to_dict()["board"]
                    })
            else:
                # Fallback mô phỏng hợp lệ trên GameEngine
                for _ in range(40):
                    winner_res = engine.check_winner(engine.state)
                    if winner_res:
                        if winner_res.result_type != ResultType.DRAW:
                            winner_user_id = m.player1_id if winner_res.winner == Team.RED else m.player2_id
                            termination_reason = winner_res.reason
                            break
                    curr_team = engine.state.current_team
                    valid_moves = []
                    for r in range(engine.state.board.rows):
                        for c in range(engine.state.board.cols):
                            p = engine.state.board.get_piece((r, c))
                            if p and p.team == curr_team:
                                for dr in [-1, 0, 1]:
                                    for dc in [-1, 0, 1]:
                                        if dr == 0 and dc == 0:
                                            continue
                                        mv = Move((r, c), (r + dr, c + dc))
                                        if engine.is_valid_move(engine.state, mv):
                                            valid_moves.append(mv)
                    if not valid_moves:
                        winner_user_id = m.player2_id if curr_team == Team.RED else m.player1_id
                        termination_reason = "Hết nước đi hợp lệ"
                        break
                    mv = random.choice(valid_moves)
                    engine.apply_move(engine.state, mv)
                    moves_log.append({
                        "turn": engine.state.turn,
                        "team": curr_team.value,
                        "player": curr_team.value.lower(),
                        "from": list(mv.from_pos),
                        "to": list(mv.to_pos),
                        "board_after": engine.state.to_dict()["board"]
                    })
                if not winner_user_id:
                    winner_user_id = random.choice([m.player1_id, m.player2_id])
                    termination_reason = "Phân định thắng cuộc sau số lượt tối đa"

        finally:
            if wrapper_red:
                wrapper_red.close()
            if wrapper_blue:
                wrapper_blue.close()

        # Trong Knockout không có hòa: giải quyết hòa bằng tiebreaker
        if is_draw or not winner_user_id:
            winner_user_id = random.choice([m.player1_id, m.player2_id])
            termination_reason += " (Phân định thắng lợi hiệp phụ)"

        m.winner_id = winner_user_id
        m.status = "COMPLETED"
        m.result_reason = termination_reason

        match_record = Match(
            match_type="TOURNAMENT",
            red_user_id=m.player1_id,
            blue_user_id=m.player2_id,
            winner_user_id=winner_user_id,
            red_bot_id=m.player1_bot_id,
            blue_bot_id=m.player2_bot_id,
            is_draw=False,
            points_awarded=False,
            status="COMPLETED",
            termination_reason=termination_reason,
            moves_json=json.dumps(moves_log),
            initial_board_json=json.dumps(initial_board),
            total_turns=len(moves_log)
        )
        db.add(match_record)
        db.flush()
        m.match_id = match_record.id

        TournamentService._on_match_concluded(db, m)
        db.commit()

    @staticmethod
    def play_match(
        db: Session,
        tournament_id: int,
        tournament_match_id: int,
        winner_id: Optional[int] = None
    ) -> TournamentDetailResponse:
        """
        Thi đấu / Mô phỏng trận đấu thủ công (dành cho người tổ chức hoặc test case)
        """
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t or t.status != "IN_PROGRESS":
            raise HTTPException(status_code=400, detail="Giải đấu không trong trạng thái đang diễn ra")

        tm = db.query(TournamentMatch).filter(TournamentMatch.id == tournament_match_id).first()
        if not tm or tm.tournament_id != t.id:
            raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu trong giải")

        if tm.status in ["COMPLETED", "FORFEIT"]:
            raise HTTPException(status_code=400, detail="Trận đấu này đã kết thúc trước đó")

        if not tm.player1_id or not tm.player2_id:
            raise HTTPException(status_code=400, detail="Trận đấu chưa đủ 2 người chơi (đang chờ kết quả vòng trước)")

        if winner_id:
            if winner_id not in [tm.player1_id, tm.player2_id]:
                raise HTTPException(status_code=400, detail="Winner phải là một trong hai người chơi của trận đấu")
            actual_winner = winner_id
        else:
            actual_winner = random.choice([tm.player1_id, tm.player2_id])

        tm.winner_id = actual_winner
        tm.status = "COMPLETED"
        tm.result_reason = "NORMAL"

        regular_match = Match(
            match_type="TOURNAMENT",
            red_user_id=tm.player1_id,
            blue_user_id=tm.player2_id,
            winner_user_id=actual_winner,
            is_draw=False,
            points_awarded=False,
            status="COMPLETED"
        )
        db.add(regular_match)
        db.flush()
        tm.match_id = regular_match.id

        TournamentService._on_match_concluded(db, tm)
        db.commit()
        return TournamentService.get_tournament_detail(db, t.id)

    @staticmethod
    def _on_match_concluded(db: Session, m: TournamentMatch):
        """Xử lý sau khi một trận đấu hoàn tất (thắng bình thường hoặc xử thua vắng mặt)"""
        t = db.query(Tournament).filter(Tournament.id == m.tournament_id).first()
        cur_round = db.query(TournamentRound).filter(TournamentRound.id == m.round_id).first()
        all_rounds = (
            db.query(TournamentRound)
            .filter(TournamentRound.tournament_id == t.id)
            .order_by(TournamentRound.round_number.asc())
            .all()
        )
        total_rounds = len(all_rounds)

        if cur_round.round_number < total_rounds:
            next_round = all_rounds[cur_round.round_number]
            next_match_order = m.match_order // 2
            next_match = (
                db.query(TournamentMatch)
                .filter(TournamentMatch.round_id == next_round.id, TournamentMatch.match_order == next_match_order)
                .first()
            )
            if next_match:
                winner_bot_id = m.player1_bot_id if m.winner_id == m.player1_id else m.player2_bot_id
                if m.match_order % 2 == 0:
                    next_match.player1_id = m.winner_id
                    next_match.player1_bot_id = winner_bot_id
                else:
                    next_match.player2_id = m.winner_id
                    next_match.player2_bot_id = winner_bot_id
                db.flush()

            # Kiểm tra xem wave hiện tại đã xong hết các trận chưa
            now = datetime.utcnow()
            cur_wave = cur_round.current_wave or 1
            unfinished_in_wave = (
                db.query(TournamentMatch)
                .filter(
                    TournamentMatch.round_id == cur_round.id,
                    TournamentMatch.wave_number == cur_wave,
                    TournamentMatch.status.in_(["READY", "WAITING", "PLAYING"])
                )
                .count()
            )

            if unfinished_in_wave == 0:
                # Wave hiện tại đã xong! Kiểm tra xem còn wave kế tiếp trong vòng không
                next_wave_num = cur_wave + 1
                next_wave_matches = (
                    db.query(TournamentMatch)
                    .filter(
                        TournamentMatch.round_id == cur_round.id,
                        TournamentMatch.wave_number == next_wave_num
                    )
                    .all()
                )
                if next_wave_matches:
                    cur_round.current_wave = next_wave_num
                    for nwm in next_wave_matches:
                        if nwm.player1_id and nwm.player2_id:
                            nwm.status = "READY"
                            nwm.ready_at = now
                            nwm.check_in_opens_at = now + timedelta(minutes=3)
                            nwm.participation_deadline = nwm.check_in_opens_at + timedelta(minutes=10)
                    db.flush()
                else:
                    # Toàn bộ wave trong vòng này đã xong!
                    remaining_matches = (
                        db.query(TournamentMatch)
                        .filter(TournamentMatch.round_id == cur_round.id, TournamentMatch.status.in_(["READY", "WAITING", "PLAYING"]))
                        .count()
                    )
                    if remaining_matches == 0:
                        cur_round.status = "COMPLETED"
                        next_round.status = "IN_PROGRESS"
                        next_round.current_wave = 1

                        # Kích hoạt các trận ở vòng tiếp theo (Wave 1 tối đa 10 trận)
                        next_matches = db.query(TournamentMatch).filter(TournamentMatch.round_id == next_round.id).order_by(TournamentMatch.match_order.asc()).all()
                        real_idx = 0
                        for nm in next_matches:
                            if nm.player1_id and nm.player2_id:
                                nm.wave_number = (real_idx // 10) + 1
                                real_idx += 1
                                if nm.wave_number == 1:
                                    nm.status = "READY"
                                    nm.ready_at = now
                                    nm.check_in_opens_at = now + timedelta(minutes=3)
                                    nm.participation_deadline = nm.check_in_opens_at + timedelta(minutes=10)
                                else:
                                    nm.status = "WAITING"
                            elif nm.player1_id and not nm.player2_id:
                                # BYE do đối thủ vắng mặt -> tự động thắng
                                nm.is_bye = True
                                nm.winner_id = nm.player1_id
                                nm.status = "COMPLETED"
                                nm.result_reason = "BYE"
                                TournamentService._on_match_concluded(db, nm)
                            elif nm.player2_id and not nm.player1_id:
                                nm.is_bye = True
                                nm.winner_id = nm.player2_id
                                nm.status = "COMPLETED"
                                nm.result_reason = "BYE"
                                TournamentService._on_match_concluded(db, nm)
                            elif not nm.player1_id and not nm.player2_id:
                                nm.status = "FORFEIT"
                                nm.result_reason = "DOUBLE_NO_SHOW"
                                TournamentService._on_match_concluded(db, nm)
        else:
            # ĐÂY LÀ TRẬN CHUNG KẾT!
            cur_round.status = "COMPLETED"
            t.status = "COMPLETED"
            t.champion_id = m.winner_id

    @staticmethod
    def get_match_detail(db: Session, tournament_id: int, match_id: int) -> TournamentMatchResponse:
        """Chi tiết một trận đấu kèm thời gian đếm ngược 10 phút"""
        TournamentService.check_tournament_deadlines(db, tournament_id)
        m = db.query(TournamentMatch).filter(
            TournamentMatch.tournament_id == tournament_id,
            TournamentMatch.id == match_id
        ).first()
        if not m:
            raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu")

        seconds_remaining = None
        if m.status == "READY" and m.participation_deadline:
            rem = int((m.participation_deadline - datetime.utcnow()).total_seconds())
            seconds_remaining = max(0, rem)

        match_map = m.map or (m.round.map if m.round else None)
        match_rocks = []
        if match_map:
            try:
                match_rocks = json.loads(match_map.rocks_json or "[]")
            except Exception:
                match_rocks = []

        round_cur_wave = m.round.current_wave if m.round else 1
        all_r_matches = db.query(TournamentMatch).filter(TournamentMatch.round_id == m.round_id).all() if m.round_id else []
        total_w = max((mat.wave_number or 1) for mat in all_r_matches) if all_r_matches else 1

        return TournamentMatchResponse(
            id=m.id,
            round_id=m.round_id,
            match_order=m.match_order,
            wave_number=m.wave_number or 1,
            current_wave=round_cur_wave,
            total_waves=total_w,
            player1_id=m.player1_id,
            player1_name=m.player1.username if m.player1 else None,
            player1_bot_id=m.player1_bot_id,
            player1_bot_name=m.player1_bot.name if m.player1_bot else None,
            player1_joined_at=m.player1_joined_at,
            player2_id=m.player2_id,
            player2_name=m.player2.username if m.player2 else None,
            player2_bot_id=m.player2_bot_id,
            player2_bot_name=m.player2_bot.name if m.player2_bot else None,
            player2_joined_at=m.player2_joined_at,
            winner_id=m.winner_id,
            winner_name=m.winner.username if m.winner else None,
            is_bye=m.is_bye,
            status=m.status,
            map_id=m.map_id or (m.round.map_id if m.round else None),
            map_name=match_map.name if match_map else "Bản đồ mặc định (9×9)",
            map_size=match_map.size if match_map else 9,
            map_reveal_at=None,
            is_map_revealed=True,
            rocks=match_rocks,
            scheduled_at=m.scheduled_at,
            check_in_opens_at=m.check_in_opens_at,
            started_at=m.started_at,
            completed_at=m.completed_at,
            ready_at=m.ready_at,
            participation_deadline=m.participation_deadline,
            seconds_remaining=seconds_remaining,
            result_reason=m.result_reason,
            match_id=m.match_id,
            is_configured=True
        )

    @staticmethod
    def validate_map_candidate(size: int, rocks: List[List[int]]) -> dict:
        from game.map_validator import validate_custom_map
        is_valid, msg = validate_custom_map(size, rocks)
        return {"valid": is_valid, "message": msg, "size": size, "rock_count": len(rocks)}

    @staticmethod
    def create_map(db: Session, tournament_id: int, user: User, data: TournamentMapCreate) -> TournamentMapResponse:
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải hoặc Admin mới có quyền tạo map")

        from game.map_validator import validate_custom_map
        is_valid, msg = validate_custom_map(data.size, data.rocks)
        if not is_valid:
            raise HTTPException(status_code=400, detail=msg)

        m = TournamentMap(
            tournament_id=t.id,
            name=data.name.strip(),
            size=data.size,
            rocks_json=json.dumps(data.rocks),
            creator_id=user.id,
            version=1,
            is_valid=True
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        return TournamentMapResponse(
            id=m.id,
            tournament_id=m.tournament_id,
            name=m.name,
            size=m.size,
            rocks=data.rocks,
            version=m.version,
            is_valid=m.is_valid,
            creator_id=m.creator_id,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    @staticmethod
    def update_map(db: Session, tournament_id: int, map_id: int, user: User, data: TournamentMapUpdate) -> TournamentMapResponse:
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải hoặc Admin mới có quyền sửa map")

        m = db.query(TournamentMap).filter(TournamentMap.id == map_id, TournamentMap.tournament_id == t.id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Không tìm thấy map")

        # Kiểm tra xem map đã được sử dụng bởi trận đấu đã hoặc đang diễn ra chưa
        in_use = db.query(TournamentMatch).filter(
            TournamentMatch.map_id == m.id,
            TournamentMatch.status.in_(["PLAYING", "COMPLETED"])
        ).count()
        if in_use > 0:
            raise HTTPException(status_code=400, detail="Map đang hoặc đã được sử dụng bởi trận đấu, không được sửa trực tiếp. Vui lòng tạo phiên bản map mới!")

        if data.rocks is not None:
            from game.map_validator import validate_custom_map
            is_valid, msg = validate_custom_map(m.size, data.rocks)
            if not is_valid:
                raise HTTPException(status_code=400, detail=msg)
            m.rocks_json = json.dumps(data.rocks)
            m.version += 1

        if data.name is not None and data.name.strip():
            m.name = data.name.strip()

        db.commit()
        db.refresh(m)
        try:
            r_list = json.loads(m.rocks_json or "[]")
        except Exception:
            r_list = []
        return TournamentMapResponse(
            id=m.id,
            tournament_id=m.tournament_id,
            name=m.name,
            size=m.size,
            rocks=r_list,
            version=m.version,
            is_valid=m.is_valid,
            creator_id=m.creator_id,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    @staticmethod
    def delete_map(db: Session, tournament_id: int, map_id: int, user: User):
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải mới có quyền xóa map")

        m = db.query(TournamentMap).filter(TournamentMap.id == map_id, TournamentMap.tournament_id == t.id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Không tìm thấy map")

        rounds_assigned = db.query(TournamentRound).filter(TournamentRound.map_id == m.id).count()
        if rounds_assigned > 0:
            raise HTTPException(status_code=400, detail="Map đang được gán cho vòng đấu, vui lòng gỡ map trước khi xóa")

        db.delete(m)
        db.commit()
        return {"message": "Đã xóa map thành công"}

    @staticmethod
    def list_maps(db: Session, tournament_id: int) -> List[TournamentMapResponse]:
        maps_db = db.query(TournamentMap).filter(TournamentMap.tournament_id == tournament_id).order_by(TournamentMap.id.asc()).all()
        res = []
        for m in maps_db:
            try:
                r_list = json.loads(m.rocks_json or "[]")
            except Exception:
                r_list = []
            res.append(
                TournamentMapResponse(
                    id=m.id,
                    tournament_id=m.tournament_id,
                    name=m.name,
                    size=m.size,
                    rocks=r_list,
                    version=m.version,
                    is_valid=m.is_valid,
                    creator_id=m.creator_id,
                    created_at=m.created_at,
                    updated_at=m.updated_at
                )
            )
        return res

    @staticmethod
    def get_map(db: Session, tournament_id: int, map_id: int, user: Optional[User] = None) -> TournamentMapResponse:
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")

        m = db.query(TournamentMap).filter(TournamentMap.id == map_id, TournamentMap.tournament_id == t.id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Không tìm thấy map")

        try:
            r_list = json.loads(m.rocks_json or "[]")
        except Exception:
            r_list = []

        return TournamentMapResponse(
            id=m.id,
            tournament_id=m.tournament_id,
            name=m.name,
            size=m.size,
            rocks=r_list,
            version=m.version,
            is_valid=m.is_valid,
            creator_id=m.creator_id,
            created_at=m.created_at,
            updated_at=m.updated_at
        )

    @staticmethod
    def assign_round_map(
        db: Session,
        tournament_id: int,
        round_id: int,
        user: User,
        map_id: int,
        map_announced_at: Optional[datetime] = None
    ):
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải mới có quyền gán map")

        round_obj = db.query(TournamentRound).filter(TournamentRound.id == round_id, TournamentRound.tournament_id == t.id).first()
        if not round_obj:
            raise HTTPException(status_code=404, detail="Không tìm thấy vòng đấu")

        if round_obj.status == "COMPLETED":
            raise HTTPException(status_code=400, detail="Vòng đấu đã hoàn tất, không được thay đổi map")

        playing_count = db.query(TournamentMatch).filter(
            TournamentMatch.round_id == round_obj.id,
            TournamentMatch.status == "PLAYING"
        ).count()
        if playing_count > 0:
            raise HTTPException(status_code=400, detail="Vòng đấu đang có trận đang thi đấu, không thể thay đổi map lúc này!")

        map_obj = db.query(TournamentMap).filter(TournamentMap.id == map_id, TournamentMap.tournament_id == t.id).first()
        if not map_obj:
            raise HTTPException(status_code=404, detail="Không tìm thấy map trong giải đấu")

        round_obj.map_id = map_obj.id
        round_obj.map_announced_at = map_announced_at

        # Cập nhật map_id cho các trận chưa hoàn tất trong vòng
        matches = db.query(TournamentMatch).filter(
            TournamentMatch.round_id == round_obj.id,
            TournamentMatch.status.notin_(["COMPLETED", "FORFEIT"])
        ).all()
        for m in matches:
            m.map_id = map_obj.id

        db.commit()
        return {
            "message": f"Đã gán map '{map_obj.name}' ({map_obj.size}x{map_obj.size}) cho {round_obj.round_name}",
            "round_id": round_obj.id,
            "map_id": map_obj.id,
            "map_announced_at": map_announced_at
        }

    @staticmethod
    def create_tournament_schedule(
        db: Session,
        tournament_id: int,
        user: User,
        data: TournamentScheduleCreate
    ):
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải mới có quyền lên lịch thi đấu")

        if data.max_concurrent_matches < 1:
            raise HTTPException(status_code=400, detail="Số trận chạy đồng thời tối đa phải từ 1 trở lên")
        if data.batch_size < 1:
            raise HTTPException(status_code=400, detail="Số trận mỗi đợt phải từ 1 trở lên")

        t.max_concurrent_matches = data.max_concurrent_matches

        r1 = db.query(TournamentRound).filter(TournamentRound.tournament_id == t.id, TournamentRound.round_number == 1).first()
        if not r1:
            raise HTTPException(status_code=400, detail="Giải đấu chưa khởi động các vòng thi đấu")

        real_matches = (
            db.query(TournamentMatch)
            .filter(TournamentMatch.round_id == r1.id, TournamentMatch.is_bye == False)
            .order_by(TournamentMatch.match_order.asc())
            .all()
        )

        base_time = data.first_batch_time or datetime.utcnow()
        check_in_advance = timedelta(minutes=data.check_in_advance_minutes)
        interval = timedelta(minutes=data.interval_minutes)
        now = datetime.utcnow()

        for idx, m in enumerate(real_matches):
            batch_num = idx // data.batch_size
            scheduled_start = base_time + (batch_num * interval)
            check_in_opens = scheduled_start - check_in_advance
            deadline = scheduled_start + timedelta(minutes=10)

            m.scheduled_at = scheduled_start
            m.check_in_opens_at = check_in_opens
            m.participation_deadline = deadline

            if now >= check_in_opens:
                m.status = "READY"
                m.ready_at = now
            else:
                m.status = "WAITING"

        db.commit()
        return {
            "message": f"Đã lên lịch thành công cho {len(real_matches)} trận đấu chia làm {math.ceil(len(real_matches) / data.batch_size)} đợt",
            "batch_count": math.ceil(len(real_matches) / data.batch_size),
            "max_concurrent_matches": t.max_concurrent_matches
        }

    @staticmethod
    def get_tournament_schedule(db: Session, tournament_id: int):
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")

        TournamentService.run_scheduler_tick(db, tournament_id)

        all_matches = (
            db.query(TournamentMatch)
            .filter(TournamentMatch.tournament_id == t.id)
            .order_by(TournamentMatch.scheduled_at.asc(), TournamentMatch.match_order.asc())
            .all()
        )
        running_count = sum(1 for m in all_matches if m.status == "PLAYING")
        waiting_count = sum(1 for m in all_matches if m.status == "WAITING")
        ready_count = sum(1 for m in all_matches if m.status == "READY")
        completed_count = sum(1 for m in all_matches if m.status in ["COMPLETED", "FORFEIT"])

        batches = {}
        unscheduled = []
        for m in all_matches:
            match_data = {
                "match_id": m.id,
                "round_id": m.round_id,
                "match_order": m.match_order,
                "player1_name": m.player1.username if m.player1 else "Chờ xác định",
                "player2_name": m.player2.username if m.player2 else "Chờ xác định",
                "status": m.status,
                "is_bye": m.is_bye,
                "check_in_opens_at": m.check_in_opens_at.isoformat() if m.check_in_opens_at else None,
                "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
                "started_at": m.started_at.isoformat() if m.started_at else None,
                "completed_at": m.completed_at.isoformat() if m.completed_at else None,
                "participation_deadline": m.participation_deadline.isoformat() if m.participation_deadline else None
            }
            if m.scheduled_at:
                time_key = m.scheduled_at.isoformat()
                if time_key not in batches:
                    batches[time_key] = []
                batches[time_key].append(match_data)
            else:
                unscheduled.append(match_data)

        return {
            "tournament_id": t.id,
            "max_concurrent_matches": getattr(t, "max_concurrent_matches", 4) or 4,
            "stats": {
                "running": running_count,
                "waiting": waiting_count,
                "ready": ready_count,
                "completed": completed_count
            },
            "batches": batches,
            "unscheduled": unscheduled
        }

    @staticmethod
    def configure_match(
        db: Session,
        tournament_id: int,
        match_id: int,
        user: User,
        data: MatchConfigUpdateRequest
    ) -> TournamentMatchResponse:
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải hoặc Admin mới có quyền cấu hình trận đấu")

        m = db.query(TournamentMatch).filter(
            TournamentMatch.id == match_id,
            TournamentMatch.tournament_id == t.id
        ).first()
        if not m:
            raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu trong giải này")

        if m.status in ["PLAYING", "COMPLETED", "FORFEIT"]:
            raise HTTPException(status_code=400, detail="Trận đấu đã hoặc đang diễn ra, không thể thay đổi cấu hình!")

        if data.map_id is not None:
            if data.map_id == 0:
                m.map_id = None
            else:
                map_obj = db.query(TournamentMap).filter(
                    TournamentMap.id == data.map_id,
                    TournamentMap.tournament_id == t.id
                ).first()
                if not map_obj:
                    raise HTTPException(status_code=404, detail="Không tìm thấy map trong giải đấu")
                if not map_obj.is_valid:
                    raise HTTPException(status_code=400, detail="Map được chọn chưa hợp lệ")
                m.map_id = map_obj.id
        else:
            m.map_id = None

        if data.scheduled_at is not None:
            m.scheduled_at = data.scheduled_at

        db.commit()
        db.refresh(m)

        return TournamentService.get_match_detail(db, tournament_id, match_id)

    @staticmethod
    def get_setup_overview(db: Session, tournament_id: int, user: User) -> SetupOverviewResponse:
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải hoặc Admin mới có quyền xem tổng quan thiết lập")

        rounds = (
            db.query(TournamentRound)
            .filter(TournamentRound.tournament_id == t.id)
            .order_by(TournamentRound.round_number.asc())
            .all()
        )

        match_items: List[SetupOverviewMatch] = []

        for r in rounds:
            matches = (
                db.query(TournamentMatch)
                .filter(TournamentMatch.round_id == r.id)
                .order_by(TournamentMatch.match_order.asc())
                .all()
            )
            for m in matches:
                m_map = m.map or r.map
                rock_cnt = 0
                if m_map and m_map.rocks_json:
                    try:
                        rock_cnt = len(json.loads(m_map.rocks_json))
                    except Exception:
                        rock_cnt = 0

                match_items.append(
                    SetupOverviewMatch(
                        match_id=m.id,
                        round_id=r.id,
                        round_number=r.round_number,
                        round_name=r.round_name,
                        match_order=m.match_order,
                        wave_number=m.wave_number or 1,
                        player1_id=m.player1_id,
                        player1_name=m.player1.username if m.player1 else "Chờ xác định",
                        player2_id=m.player2_id,
                        player2_name=m.player2.username if m.player2 else "Chờ xác định",
                        is_bye=m.is_bye,
                        map_id=m.map_id or (r.map_id if r.map_id else None),
                        map_name=m_map.name if m_map else "Bản đồ mặc định (9×9)",
                        map_size=m_map.size if m_map else 9,
                        rock_count=rock_cnt,
                        scheduled_at=m.scheduled_at,
                        map_reveal_at=None,
                        status=m.status,
                        is_configured=True,
                        validation_errors=[]
                    )
                )

        total_matches = len(match_items)
        can_publish = (total_matches > 0)

        return SetupOverviewResponse(
            tournament_id=t.id,
            status=t.status,
            can_publish=can_publish,
            total_matches=total_matches,
            configured_matches=total_matches,
            matches=match_items,
            errors=[]
        )

    @staticmethod
    def publish_tournament(db: Session, tournament_id: int, user: User) -> TournamentDetailResponse:
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")
        if t.creator_id != user.id and not getattr(user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Chỉ người tổ chức giải hoặc Admin mới có quyền công bố giải đấu")

        if t.status not in ["SETTING_UP", "REGISTRATION_OPEN", "REGISTRATION"]:
            raise HTTPException(status_code=400, detail=f"Không thể công bố giải đấu ở trạng thái {t.status}")

        r1 = db.query(TournamentRound).filter(
            TournamentRound.tournament_id == t.id,
            TournamentRound.round_number == 1
        ).first()
        if not r1:
            raise HTTPException(status_code=400, detail="Giải đấu chưa được tạo nhánh đấu")

        r1_matches = db.query(TournamentMatch).filter(
            TournamentMatch.round_id == r1.id,
            TournamentMatch.is_bye == False
        ).order_by(TournamentMatch.match_order.asc()).all()

        now = datetime.utcnow()
        t.status = "IN_PROGRESS"
        t.published_at = now
        r1.status = "IN_PROGRESS"
        r1.current_wave = 1

        for m in r1_matches:
            if m.wave_number == 1 and m.player1_id and m.player2_id:
                m.status = "READY"
                m.ready_at = now
                m.check_in_opens_at = now + timedelta(minutes=3)
                m.participation_deadline = m.check_in_opens_at + timedelta(minutes=10)
            elif m.wave_number > 1:
                m.status = "WAITING"

        db.commit()
        return TournamentService.get_tournament_detail(db, t.id, current_user=user)

    @staticmethod
    def select_match_bot(db: Session, tournament_id: int, match_id: int, user: User, bot_id: int) -> TournamentMatchResponse:
        """Tuyển thủ xem map và chọn bot trong thời gian chuẩn bị 3 phút"""
        TournamentService.check_tournament_deadlines(db, tournament_id)
        m = db.query(TournamentMatch).filter(
            TournamentMatch.tournament_id == tournament_id,
            TournamentMatch.id == match_id
        ).first()
        if not m:
            raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu")

        if m.status in ["COMPLETED", "FORFEIT"]:
            raise HTTPException(status_code=400, detail="Trận đấu này đã kết thúc")

        if m.status != "READY":
            raise HTTPException(status_code=400, detail=f"Trận đấu hiện đang ở trạng thái {m.status}, chưa mở để chọn bot")

        bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user.id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Không tìm thấy Bot hoặc Bot không thuộc sở hữu của bạn")
        if not bot.current_version_id:
            raise HTTPException(status_code=400, detail="Bot chưa có phiên bản mã nguồn nào hợp lệ")

        if user.id == m.player1_id:
            m.player1_bot_id = bot.id
        elif user.id == m.player2_id:
            m.player2_bot_id = bot.id
        else:
            raise HTTPException(status_code=403, detail="Bạn không phải tuyển thủ của trận đấu này")

        db.commit()
        db.refresh(m)
        return TournamentService.get_match_detail(db, tournament_id, match_id)

    @staticmethod
    def start_match_now(db: Session, tournament_id: int, match_id: int, user: User) -> TournamentMatchResponse:
        """Bắt đầu trận đấu ngay sau khi đã hết 3 phút xem map bắt buộc"""
        t = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Không tìm thấy giải đấu")

        m = db.query(TournamentMatch).filter(
            TournamentMatch.tournament_id == tournament_id,
            TournamentMatch.id == match_id
        ).first()
        if not m:
            raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu")

        if m.status in ["COMPLETED", "FORFEIT"]:
            raise HTTPException(status_code=400, detail="Trận đấu đã kết thúc")

        is_host_or_admin = (user.id == t.creator_id or getattr(user, "is_admin", False))
        is_player = (user.id in [m.player1_id, m.player2_id])
        if not is_host_or_admin and not is_player:
            raise HTTPException(status_code=403, detail="Bạn không có quyền bắt đầu trận đấu này")

        now = datetime.utcnow()
        if m.check_in_opens_at and now < m.check_in_opens_at:
            remaining_view_secs = int((m.check_in_opens_at - now).total_seconds())
            raise HTTPException(
                status_code=400,
                detail=f"Người chơi bắt buộc phải chờ 3 phút để xem map! Không được đấu ngay trong thời gian này (còn {remaining_view_secs} giây)."
            )

        m.status = "PLAYING"
        m.started_at = now
        db.commit()
        TournamentService._execute_tournament_match(db, m)
        return TournamentService.get_match_detail(db, tournament_id, match_id)

    @staticmethod
    def run_scheduler_tick(db: Session, tournament_id: Optional[int] = None):
        """
        Bộ điều phối lập lịch và kiểm tra hạn chót:
        1. Quét các trận READY: nếu hết 3 phút chuẩn bị (participation_deadline <= now) -> tự động khởi chạy và hoàn tất trận đấu!
        """
        now = datetime.utcnow()
        query = db.query(Tournament)
        if tournament_id:
            query = query.filter(Tournament.id == tournament_id)
        tournaments = query.filter(Tournament.status.in_(["IN_PROGRESS", "PUBLISHED"])).all()

        for t in tournaments:
            TournamentService.check_tournament_deadlines(db, t.id)

