import os
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.models.room import Room, RoomJoinRequest
from backend.models.user import User
from backend.models.match import Match
from backend.models.bot import Bot, BotVersion
from backend.schemas.room import RoomResponse, RoomJoinRequestResponse
from backend.services.player_service import PlayerService

class RoomService:
    @staticmethod
    def _to_response(db: Session, room: Room, caller_id: Optional[int] = None) -> RoomResponse:
        current_count = 1 if room.player1_id else 0
        if room.player2_id:
            current_count += 1

        req_responses = []
        # Chỉ chủ phòng hoặc chính người gửi mới thấy danh sách requests
        if caller_id and (caller_id == room.owner_id):
            requests = (
                db.query(RoomJoinRequest)
                .filter(RoomJoinRequest.room_id == room.id)
                .order_by(RoomJoinRequest.created_at.desc())
                .all()
            )
            for r in requests:
                req_responses.append(
                    RoomJoinRequestResponse(
                        id=r.id,
                        room_id=r.room_id,
                        user_id=r.user_id,
                        username=r.user.username if r.user else f"User {r.user_id}",
                        status=r.status,
                        created_at=r.created_at
                    )
                )

        p1_bot_name = room.player1_bot.name if room.player1_bot else None
        p1_bot_ver = (
            room.player1_bot_version.version_number
            if room.player1_bot_version
            else (room.player1_bot.current_version.version_number if (room.player1_bot and room.player1_bot.current_version) else None)
        )
        p2_bot_name = room.player2_bot.name if room.player2_bot else None
        p2_bot_ver = (
            room.player2_bot_version.version_number
            if room.player2_bot_version
            else (room.player2_bot.current_version.version_number if (room.player2_bot and room.player2_bot.current_version) else None)
        )

        my_role = "SPECTATOR"
        my_join_status = None
        if caller_id:
            if caller_id == room.owner_id or caller_id == room.player1_id:
                my_role = "PLAYER1"
            elif caller_id == room.player2_id:
                my_role = "PLAYER2"
                my_join_status = "ACCEPTED"
            else:
                user_req = (
                    db.query(RoomJoinRequest)
                    .filter(RoomJoinRequest.room_id == room.id, RoomJoinRequest.user_id == caller_id)
                    .order_by(RoomJoinRequest.created_at.desc())
                    .first()
                )
                if user_req:
                    my_join_status = user_req.status
                    if user_req.status == "PENDING":
                        my_role = "PENDING_GUEST"

        return RoomResponse(
            id=room.id,
            room_code=room.room_code,
            name=room.name,
            owner_id=room.owner_id,
            owner_name=room.owner.username if room.owner else "Unknown",
            player1_id=room.player1_id,
            player1_name=room.player1.username if room.player1 else None,
            player2_id=room.player2_id,
            player2_name=room.player2.username if room.player2 else None,
            player1_ready=room.player1_ready,
            player2_ready=room.player2_ready,
            player1_bot_id=room.player1_bot_id,
            player1_bot_name=p1_bot_name,
            player1_bot_version=p1_bot_ver,
            player2_bot_id=room.player2_bot_id,
            player2_bot_name=p2_bot_name,
            player2_bot_version=p2_bot_ver,
            status=room.status,
            current_player_count=current_count,
            capacity=2,
            current_match_id=room.current_match_id,
            created_at=room.created_at,
            join_requests=req_responses,
            my_role=my_role,
            my_join_status=my_join_status
        )

    @staticmethod
    def create_room(db: Session, owner: User, name: str = "Phòng thách đấu") -> Room:
        """Tạo phòng thi đấu thường mới, người tạo trở thành chủ phòng (Player 1)"""
        code = uuid.uuid4().hex[:6].upper()
        # Đảm bảo mã phòng duy nhất
        while db.query(Room).filter(Room.room_code == code).first():
            code = uuid.uuid4().hex[:6].upper()

        new_room = Room(
            room_code=code,
            name=name or f"Phòng của {owner.username}",
            owner_id=owner.id,
            player1_id=owner.id,
            player2_id=None,
            player1_ready=False,
            player2_ready=False,
            status="WAITING"
        )
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        return new_room

    @staticmethod
    def list_open_rooms(db: Session) -> List[RoomResponse]:
        """Danh sách các phòng đang mở (WAITING) và còn chỗ trống (1/2 người)"""
        rooms = (
            db.query(Room)
            .filter(Room.status == "WAITING", Room.player2_id == None)
            .order_by(Room.created_at.desc())
            .all()
        )
        return [RoomService._to_response(db, r) for r in rooms]

    @staticmethod
    def get_room_by_id_or_code(db: Session, identifier: str) -> Room:
        """Tìm phòng theo ID hoặc mã phòng room_code"""
        query = db.query(Room)
        if identifier.isdigit():
            room = query.filter(Room.id == int(identifier)).first()
            if room:
                return room
        room = query.filter(Room.room_code == identifier.strip().upper()).first()
        if not room:
            raise HTTPException(status_code=404, detail="Không tìm thấy phòng với ID hoặc mã đã nhập")
        return room

    @staticmethod
    def get_room_response(db: Session, identifier: str, caller_id: Optional[int] = None) -> RoomResponse:
        """Lấy thông tin phòng kèm vai trò của người gọi dưới dạng RoomResponse"""
        room = RoomService.get_room_by_id_or_code(db, str(identifier))
        return RoomService._to_response(db, room, caller_id)

    @staticmethod
    def request_join_room(db: Session, identifier: str, user: User) -> RoomJoinRequestResponse:
        """Gửi yêu cầu tham gia phòng"""
        room = RoomService.get_room_by_id_or_code(db, identifier)

        if room.owner_id == user.id:
            raise HTTPException(status_code=400, detail="Bạn là chủ phòng, không cần gửi yêu cầu tham gia")

        if room.player2_id is not None or room.status not in ["WAITING", "READY"]:
            raise HTTPException(status_code=400, detail="Phòng đã đủ 2 người chơi hoặc không còn nhận người")

        # Kiểm tra yêu cầu đang chờ
        existing = (
            db.query(RoomJoinRequest)
            .filter(
                RoomJoinRequest.room_id == room.id,
                RoomJoinRequest.user_id == user.id,
                RoomJoinRequest.status == "PENDING"
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Bạn đã có một yêu cầu đang chờ duyệt cho phòng này")

        req = RoomJoinRequest(room_id=room.id, user_id=user.id, status="PENDING")
        db.add(req)
        db.commit()
        db.refresh(req)

        return RoomJoinRequestResponse(
            id=req.id,
            room_id=req.room_id,
            user_id=req.user_id,
            username=user.username,
            status=req.status,
            created_at=req.created_at
        )

    @staticmethod
    def respond_to_request(
        db: Session,
        room_id: int,
        request_id: int,
        owner: User,
        action: str
    ) -> RoomResponse:
        """
        Chủ phòng duyệt yêu cầu tham gia:
        - action = 'ACCEPT' hoặc 'REJECT'
        - Bảo vệ concurrency: Kiểm tra slot trống bên trong transaction, tránh 2 người cùng vào phòng.
        """
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại")

        if room.owner_id != owner.id:
            raise HTTPException(status_code=403, detail="Chỉ chủ phòng mới có quyền duyệt yêu cầu")

        req = db.query(RoomJoinRequest).filter(RoomJoinRequest.id == request_id, RoomJoinRequest.room_id == room.id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Yêu cầu tham gia không tồn tại")

        if req.status != "PENDING":
            raise HTTPException(status_code=400, detail="Yêu cầu này đã được xử lý trước đó")

        action_upper = action.strip().upper()
        if action_upper == "REJECT":
            req.status = "REJECTED"
            db.commit()
            return RoomService._to_response(db, room, owner.id)

        elif action_upper == "ACCEPT":
            # Concurrency check: Đảm bảo phòng chưa có player2
            if room.player2_id is not None:
                req.status = "REJECTED"
                db.commit()
                raise HTTPException(status_code=400, detail="Phòng đã đủ 2 người chơi! Không thể chấp nhận thêm")

            room.player2_id = req.user_id
            room.player2_ready = False
            req.status = "ACCEPTED"

            # Tự động từ chối các yêu cầu đang chờ còn lại để giữ tính nhất quán
            other_pending = (
                db.query(RoomJoinRequest)
                .filter(RoomJoinRequest.room_id == room.id, RoomJoinRequest.id != req.id, RoomJoinRequest.status == "PENDING")
                .all()
            )
            for r in other_pending:
                r.status = "REJECTED"

            db.commit()
            db.refresh(room)
            return RoomService._to_response(db, room, owner.id)
        else:
            raise HTTPException(status_code=400, detail="Hành động không hợp lệ (chỉ chấp nhận ACCEPT hoặc REJECT)")

    @staticmethod
    def select_bot(db: Session, room_id: int, user: User, bot_id: int) -> RoomResponse:
        """Người chơi chọn Bot (phải ở trạng thái READY) để thi đấu trong phòng"""
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại")

        if user.id != room.player1_id and user.id != room.player2_id:
            raise HTTPException(status_code=403, detail="Bạn không phải thành viên của phòng này")

        bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user.id).first()
        if not bot:
            raise HTTPException(status_code=404, detail="Không tìm thấy bot hoặc bạn không sở hữu bot này")

        if bot.status != "READY" or not bot.current_version:
            raise HTTPException(status_code=400, detail="Chỉ có thể chọn Bot đã vượt qua kiểm tra và ở trạng thái READY!")

        if user.id == room.player1_id:
            room.player1_bot_id = bot.id
            room.player1_bot_version_id = bot.current_version_id
            room.player1_ready = False
        else:
            room.player2_bot_id = bot.id
            room.player2_bot_version_id = bot.current_version_id
            room.player2_ready = False

        if room.status == "READY":
            room.status = "WAITING"

        db.commit()
        db.refresh(room)
        return RoomService._to_response(db, room, user.id)

    @staticmethod
    def set_ready_status(db: Session, room_id: int, user: User, is_ready: bool) -> RoomResponse:
        """Người chơi bật/tắt trạng thái Sẵn sàng"""
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại")

        if user.id == room.player1_id:
            if is_ready:
                if not room.player1_bot_id:
                    raise HTTPException(status_code=400, detail="Vui lòng chọn Bot của bạn trước khi Sẵn Sàng!")
                if not room.player1_bot or room.player1_bot.status != "READY":
                    raise HTTPException(status_code=400, detail="Bot đã chọn chưa đạt trạng thái READY!")
            room.player1_ready = is_ready
        elif user.id == room.player2_id:
            if is_ready:
                if not room.player2_bot_id:
                    raise HTTPException(status_code=400, detail="Vui lòng chọn Bot của bạn trước khi Sẵn Sàng!")
                if not room.player2_bot or room.player2_bot.status != "READY":
                    raise HTTPException(status_code=400, detail="Bot đã chọn chưa đạt trạng thái READY!")
            room.player2_ready = is_ready
        else:
            raise HTTPException(status_code=403, detail="Bạn không phải thành viên của phòng này")

        # Cập nhật trạng thái phòng: READY khi cả 2 cùng ready
        if room.player1_id and room.player2_id and room.player1_ready and room.player2_ready:
            room.status = "READY"
        else:
            if room.status == "READY":
                room.status = "WAITING"

        db.commit()
        db.refresh(room)
        return RoomService._to_response(db, room, user.id)

    @staticmethod
    def _execute_bot_match(db: Session, match_id: int):
        """Thực thi vòng lặp trận đấu tự động giữa 2 Bot trong Sandbox"""
        import json
        from game.game_engine import GameEngine
        from game.rule_set import RuleSet
        from game.move import Move
        from game.piece import Team
        from game.game_result import ResultType
        from judge.match_runner import DockerBotWrapper

        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return

        red_ver = db.query(BotVersion).filter(BotVersion.id == match.red_bot_version_id).first() if match.red_bot_version_id else None
        blue_ver = db.query(BotVersion).filter(BotVersion.id == match.blue_bot_version_id).first() if match.blue_bot_version_id else None

        red_file = red_ver.file_path if red_ver and os.path.exists(red_ver.file_path) else "bots/examples/random_bot.py"
        blue_file = blue_ver.file_path if blue_ver and os.path.exists(blue_ver.file_path) else "bots/examples/random_bot.py"

        engine = GameEngine(RuleSet.default())
        initial_board = engine.state.to_dict()["board"]
        moves_log = []
        winner_user_id = None
        is_draw = False
        termination_reason = "Trận đấu kết thúc bình thường"

        wrapper_red = None
        wrapper_blue = None

        try:
            wrapper_red = DockerBotWrapper(bot_dir=red_file, team_name="RED", time_limit=2.0)
            wrapper_blue = DockerBotWrapper(bot_dir=blue_file, team_name="BLUE", time_limit=2.0)

            while True:
                winner_res = engine.check_winner(engine.state)
                if winner_res:
                    if winner_res.result_type == ResultType.DRAW:
                        is_draw = True
                        winner_user_id = None
                        termination_reason = winner_res.reason
                    else:
                        is_draw = False
                        winner_user_id = match.red_user_id if winner_res.winner == Team.RED else match.blue_user_id
                        termination_reason = winner_res.reason
                    break

                curr_team = engine.state.current_team
                curr_wrapper = wrapper_red if curr_team == Team.RED else wrapper_blue
                state_dict = engine.state.to_dict()

                try:
                    move_dict = curr_wrapper.get_move(state_dict)
                    move = Move.from_dict(move_dict)
                except Exception as e:
                    if curr_team == Team.RED:
                        winner_user_id = match.blue_user_id
                        termination_reason = f"Bot Đỏ bị xử thua kỹ thuật: {str(e)[:120]}"
                    else:
                        winner_user_id = match.red_user_id
                        termination_reason = f"Bot Xanh bị xử thua kỹ thuật: {str(e)[:120]}"
                    is_draw = False
                    break

                if not engine.is_valid_move(engine.state, move):
                    if curr_team == Team.RED:
                        winner_user_id = match.blue_user_id
                        termination_reason = f"Bot Đỏ đi nước cờ không hợp lệ: {move_dict}"
                    else:
                        winner_user_id = match.red_user_id
                        termination_reason = f"Bot Xanh đi nước cờ không hợp lệ: {move_dict}"
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

        finally:
            if wrapper_red:
                wrapper_red.close()
            if wrapper_blue:
                wrapper_blue.close()

        # Lưu kết quả trận đấu
        match.status = "COMPLETED"
        match.winner_user_id = winner_user_id
        match.is_draw = is_draw
        match.termination_reason = termination_reason
        match.moves_json = json.dumps(moves_log)
        match.initial_board_json = json.dumps(initial_board)
        match.total_turns = len(moves_log)

        # Cập nhật điểm số bảng xếp hạng server một cách idempotent
        PlayerService.record_match_result(db, match, winner_user_id=winner_user_id, is_draw=is_draw)

        room = db.query(Room).filter(Room.id == match.room_id).first()
        if room:
            room.status = "FINISHED"
            room.player1_ready = False
            room.player2_ready = False

        db.commit()

    @staticmethod
    def start_room_match(db: Session, room_id: int, owner: User) -> Match:
        """Chủ phòng bắt đầu trận đấu khi cả 2 người chơi đã sẵn sàng cùng Bot"""
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại")

        if room.owner_id != owner.id:
            raise HTTPException(status_code=403, detail="Chỉ chủ phòng mới có thể bắt đầu trận đấu")

        if not room.player1_id or not room.player2_id:
            raise HTTPException(status_code=400, detail="Cần đủ 2 người chơi để bắt đầu trận")

        if not room.player1_ready or not room.player2_ready:
            raise HTTPException(status_code=400, detail="Cả hai người chơi phải cùng Sẵn sàng trước khi bắt đầu")

        if not room.player1_bot_id or not room.player2_bot_id:
            raise HTTPException(status_code=400, detail="Cả hai người chơi phải cùng chọn một Bot hợp lệ!")

        # Tạo trận đấu mới kiểu REGULAR
        match = Match(
            match_type="REGULAR",
            room_id=room.id,
            red_user_id=room.player1_id,
            blue_user_id=room.player2_id,
            red_bot_id=room.player1_bot_id,
            blue_bot_id=room.player2_bot_id,
            red_bot_version_id=room.player1_bot_version_id,
            blue_bot_version_id=room.player2_bot_version_id,
            status="PLAYING",
            points_awarded=False
        )
        db.add(match)
        db.flush()

        room.status = "PLAYING"
        room.current_match_id = match.id
        db.commit()
        db.refresh(match)

        # Chạy trận đấu tự động giữa 2 Bot qua GameEngine Sandbox
        RoomService._execute_bot_match(db, match.id)
        db.refresh(match)
        return match

    @staticmethod
    def get_room_match_state(db: Session, room_id: int) -> dict:
        """Lấy toàn bộ trạng thái trận đấu, hai bot, kết quả và danh sách nước đi của phòng"""
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại")

        match = None
        if room.current_match_id:
            match = db.query(Match).filter(Match.id == room.current_match_id).first()

        if not match:
            return {
                "room_id": room.id,
                "room_status": room.status,
                "has_match": False
            }

        import json
        initial_board = json.loads(match.initial_board_json) if match.initial_board_json else []
        moves = json.loads(match.moves_json) if match.moves_json else []

        return {
            "room_id": room.id,
            "room_status": room.status,
            "has_match": True,
            "match_id": match.id,
            "status": match.status,
            "red_user_id": match.red_user_id,
            "red_username": match.red_user.username if match.red_user else "Player 1",
            "red_bot_id": match.red_bot_id,
            "red_bot_name": match.red_bot.name if match.red_bot else "Bot Red",
            "red_bot_version": match.red_bot_version.version_number if match.red_bot_version else 1,
            "blue_user_id": match.blue_user_id,
            "blue_username": match.blue_user.username if match.blue_user else "Player 2",
            "blue_bot_id": match.blue_bot_id,
            "blue_bot_name": match.blue_bot.name if match.blue_bot else "Bot Blue",
            "blue_bot_version": match.blue_bot_version.version_number if match.blue_bot_version else 1,
            "winner_user_id": match.winner_user_id,
            "is_draw": match.is_draw,
            "termination_reason": match.termination_reason,
            "total_turns": match.total_turns,
            "initial_board": initial_board,
            "moves": moves
        }

    @staticmethod
    def finish_room_match(
        db: Session,
        room_id: int,
        winner_user_id: Optional[int] = None,
        is_draw: bool = False
    ) -> Match:
        """
        Kết thúc trận đấu trong phòng, cập nhật điểm và rank server một cách idempotent
        """
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room or not room.current_match_id:
            raise HTTPException(status_code=404, detail="Không tìm thấy trận đấu đang diễn ra trong phòng")

        match = db.query(Match).filter(Match.id == room.current_match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Trận đấu không tồn tại")

        # Áp dụng điểm số idempotent
        PlayerService.record_match_result(db, match, winner_user_id=winner_user_id, is_draw=is_draw)

        room.status = "FINISHED"
        room.player1_ready = False
        room.player2_ready = False
        db.commit()
        db.refresh(match)
        return match

    @staticmethod
    def cancel_room(db: Session, room_id: int, user: User) -> Room:
        """
        Hủy phòng đấu:
        - Chỉ chủ phòng mới có quyền hủy.
        - Chỉ cho phép hủy khi phòng chưa bước vào trận đấu (WAITING hoặc READY).
        - Đổi trạng thái phòng sang CANCELLED và tự động từ chối các yêu cầu đang chờ.
        """
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại")

        if room.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Chỉ chủ phòng mới có quyền hủy phòng")

        if room.status == "PLAYING":
            raise HTTPException(status_code=400, detail="Trận đấu đang diễn ra, không thể hủy phòng!")

        if room.status in ["FINISHED", "CANCELLED"]:
            raise HTTPException(status_code=400, detail="Phòng này đã kết thúc hoặc đã bị hủy trước đó")

        room.status = "CANCELLED"
        room.player1_ready = False
        room.player2_ready = False

        # Tự động từ chối tất cả yêu cầu tham gia đang chờ
        pending_requests = (
            db.query(RoomJoinRequest)
            .filter(RoomJoinRequest.room_id == room.id, RoomJoinRequest.status == "PENDING")
            .all()
        )
        for req in pending_requests:
            req.status = "REJECTED"

        db.commit()
        db.refresh(room)
        return room
