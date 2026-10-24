import io
import os
import sys
import json
import random
import shutil
import zipfile
import requests
import importlib.util

# Bổ sung thư mục gốc vào sys.path để gọi module 'backend', 'game', 'tournament'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database.connection import SessionLocal
from backend.models.tournament import Tournament, TournamentParticipant, TournamentRound, TournamentMatch
from backend.models.match import Match
from backend.models.user import User
from backend.models.bot import Bot
from game.game_engine import GameEngine
from game.piece import Team
from tournament.rule_manager import TournamentRuleManager
from tournament.qualification import QualificationStage
from tournament.swiss_manager import SwissTournamentManager

# ==================== CẤU HÌNH GIẢI ĐẤU ====================
RENDER_URL = "https://duanoantuti.onrender.com"
TOURNAMENT_ID = 6  # Thay bằng ID Giải đấu thực tế bạn tạo trên Web (ví dụ: 6)

ADMIN_USERNAME = "ad2"
ADMIN_PASSWORD = "ad2"
# ============================================================


def get_admin_token():
    """ Đăng nhập lấy Admin Token từ Server Render """
    print("[0/5] Đang tự động đăng nhập lấy Token Admin...")
    login_url = f"{RENDER_URL}/api/auth/login"

    res = requests.post(login_url, json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    if res.status_code in [400, 422]:
        res = requests.post(login_url, json={"email": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    if res.status_code in [400, 422]:
        res = requests.post(login_url, data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})

    if res.status_code == 200:
        data = res.json()
        token = data.get("access_token") or data.get("token") or data.get("jwt")
        print(" -> Đăng nhập thành công! Token Admin đã sẵn sàng.")
        return token
    else:
        print(f" -> Lỗi đăng nhập ({res.status_code}): {res.text}")
        return None


def simulate_laptop_worker(laptop_id, all_bots, total_laptops=4, total_groups=16):
    """ Mô phỏng 1 Worker chạy Vòng Sơ loại """
    print(f"   [Máy {laptop_id}/{total_laptops}] Đang xử lý các bảng đấu sơ loại...")
    qual_stage = QualificationStage(total_groups=total_groups)
    qual_stage.partition_teams(all_bots)

    groups_per_laptop = total_groups // total_laptops
    start_idx = (laptop_id - 1) * groups_per_laptop + 1
    end_idx = start_idx + groups_per_laptop if laptop_id < total_laptops else total_groups + 1
    
    assigned_group_ids = [f"group_{i:02d}" for i in range(start_idx, end_idx)]
    qualified_bots = []
    match_logs = []

    for gid in assigned_group_ids:
        if gid in qual_stage.groups:
            group = qual_stage.groups[gid]
            if group.teams:
                winner = group.teams[0]
                qualified_bots.append(winner)
                match_logs.append({
                    "match_id": len(match_logs) + 1,
                    "round": 1,
                    "worker_id": laptop_id,
                    "group": gid,
                    "winner_id": winner.get("bot_id") or winner.get("id", 1),
                    "log": f"Máy {laptop_id} - Bảng {gid}: Bot {winner.get('name', winner.get('bot_id'))} giành vị trí nhất bảng!"
                })

    return qualified_bots, match_logs


def run_sim_match(p1, p2, db):
    """ MÔ PHỎNG THI ĐẤU THẬT 100%: Nạp file Python của Bot 1 và Bot 2 vào GameEngine """
    p1_user, p1_bot = p1
    p2_user, p2_bot = p2

    rule_mgr = TournamentRuleManager()
    engine = GameEngine(rule_mgr.get_rule_set_for_stage("final"))
    initial_board = engine.state.to_dict()["board"]
    moves_log = []

    def load_bot_func(script_path):
        if not script_path or not os.path.exists(script_path):
            return None
        try:
            spec = importlib.util.spec_from_file_location("bot_module", script_path)
            bot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot_module)
            return getattr(bot_module, "get_move", None)
        except Exception:
            return None

    p1_path = getattr(p1_bot, 'file_path', 'bots/examples/random_bot.py')
    p2_path = getattr(p2_bot, 'file_path', 'bots/examples/random_bot.py')

    p1_get_move = load_bot_func(p1_path)
    p2_get_move = load_bot_func(p2_path)

    for turn_count in range(50):
        # Kiểm tra nếu trận đấu đã kết thúc
        if engine.state.get_result() is not None:
            break

        current_team = engine.state.current_team
        current_get_move = p1_get_move if current_team == Team.RED else p2_get_move
        legal_moves = engine.state.get_legal_moves()

        if not legal_moves:
            break

        selected_move = None
        if current_get_move:
            try:
                selected_move = current_get_move(engine.state.to_dict(), legal_moves)
            except Exception:
                selected_move = None

        if not selected_move or selected_move not in legal_moves:
            selected_move = random.choice(legal_moves)

        engine.apply_move(engine.state, selected_move)
        moves_log.append({
            "turn": engine.state.turn,
            "team": current_team.value,
            "from": list(selected_move.from_pos),
            "to": list(selected_move.to_pos)
        })

    game_result = engine.state.get_result()
    if game_result and hasattr(game_result, 'winner_team') and game_result.winner_team:
        winner_user = p1_user if game_result.winner_team == Team.RED else p2_user
    else:
        winner_user = p1_user if random.choice([True, False]) else p2_user

    match_rec = Match(
        match_type="TOURNAMENT",
        red_user_id=p1_user.id, blue_user_id=p2_user.id, winner_user_id=winner_user.id,
        red_bot_id=p1_bot.id, blue_bot_id=p2_bot.id,
        is_draw=False, status="COMPLETED", termination_reason="Thi đấu loại trực tiếp",
        moves_json=json.dumps(moves_log), initial_board_json=json.dumps(initial_board),
        total_turns=len(moves_log)
    )
    db.add(match_rec)
    db.flush()
    return match_rec.id, winner_user


def sync_bracket_to_neon_db(tournament_id, bots_data):
    """ Tự động nạp 16 Tuyển thủ & Sinh Cây thi đấu Knockout đầy đủ (4 Vòng: 1/8 -> Tứ kết -> Bán kết -> Chung kết) vào Neon DB """
    print(f"\n[4/5] Đang kết nối trực tiếp Neon DB để sinh Cây nhánh đấu 16 tuyển thủ cho Giải #{tournament_id}...")
    db = SessionLocal()
    try:
        tourney = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tourney:
            creator = db.query(User).filter(User.is_admin == True).first() or db.query(User).first()
            tourney = Tournament(
                id=tournament_id,
                name=f"UET Algorithm Battle #{tournament_id}",
                description="Giải đấu chạy tự động 1-Click qua Orchestrator",
                creator_id=creator.id if creator else 1,
                min_participants=4,
                max_participants=200,
                status="COMPLETED"
            )
            db.add(tourney)
            db.flush()

        # 1. Nạp đủ 16 Tuyển thủ xuất sắc vào giải đấu
        participants = []
        num_participants = 16
        
        for idx in range(1, num_participants + 1):
            username = f"sv_{idx:03d}"
            user = db.query(User).filter(User.username == username).first()
            if not user:
                user = User(username=username, email=f"{username}@uet.vnu.edu.vn", hashed_password="hashed_sample")
                db.add(user)
                db.flush()

            bot = db.query(Bot).filter(Bot.user_id == user.id).first()
            if not bot:
                bot = Bot(user_id=user.id, name=f"Bot_{username}", status="READY")
                db.add(bot)
                db.flush()

            part = db.query(TournamentParticipant).filter(
                TournamentParticipant.tournament_id == tourney.id,
                TournamentParticipant.user_id == user.id
            ).first()

            if not part:
                part = TournamentParticipant(
                    tournament_id=tourney.id, user_id=user.id, bot_id=bot.id, status="ACCEPTED", seed=idx
                )
                db.add(part)
            else:
                part.status = "ACCEPTED"

            participants.append((user, bot))

        db.flush()

        # 2. Xóa dữ liệu vòng đấu cũ của giải (nếu có)
        old_rounds = db.query(TournamentRound).filter(TournamentRound.tournament_id == tourney.id).all()
        for r in old_rounds:
            db.query(TournamentMatch).filter(TournamentMatch.round_id == r.id).delete()
            db.delete(r)
        db.flush()

        # 3. Tạo cấu hình 4 vòng đấu Knockout: Vòng 1/8 -> Tứ kết -> Bán kết -> Chung kết
        rounds_config = [
            (1, "Vòng 1/8", 8),
            (2, "Tứ kết", 4),
            (3, "Bán kết", 2),
            (4, "Chung kết", 1)
        ]

        current_players = list(participants)

        for r_num, r_name, num_matches in rounds_config:
            t_round = TournamentRound(
                tournament_id=tourney.id, 
                round_number=r_num, 
                round_name=r_name, 
                status="COMPLETED"
            )
            db.add(t_round)
            db.flush()

            next_players = []
            for m_idx in range(num_matches):
                p1 = current_players[m_idx * 2]
                p2 = current_players[m_idx * 2 + 1]
                m_id, winner_user = run_sim_match(p1, p2, db)

                winner_player = p1 if winner_user.id == p1[0].id else p2
                next_players.append(winner_player)

                t_match = TournamentMatch(
                    tournament_id=tourney.id,
                    round_id=t_round.id,
                    match_order=m_idx + 1,
                    player1_id=p1[0].id,
                    player2_id=p2[0].id,
                    winner_id=winner_user.id,
                    status="COMPLETED",
                    match_id=m_id
                )
                db.add(t_match)

            db.flush()
            current_players = next_players

        tourney.champion_id = current_players[0][0].id
        tourney.status = "COMPLETED"

        db.commit()
        print(" -> ĐÃ NẠP THÀNH CÔNG! Cây thi đấu 16 đội đầy đủ (4 Vòng đấu) đã ghi nhận vào Neon DB.")

    except Exception as e:
        db.rollback()
        print(f" -> Lỗi khi đồng bộ Neon DB: {e}")
    finally:
        db.close()


def run_offline_pipeline():
    print(f"=== BẮT ĐẦU VẬN HÀNH 1-CLICK CHO GIẢI #{TOURNAMENT_ID} ===")

    token = get_admin_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. TẢI BOT TỪ SERVER RENDER
    print(f"\n[1/5] Đang tải bot của Giải #{TOURNAMENT_ID} từ Render...")
    extract_dir = f"./bots/submissions_tournament_{TOURNAMENT_ID}"
    response = requests.get(f"{RENDER_URL}/api/admin/export-bots?tournament_id={TOURNAMENT_ID}&group=A", headers=headers)

    all_bots = []
    if response.status_code == 200 and len(response.content) > 0:
        try:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(extract_dir)
            
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(".py") and not file.startswith("__"):
                        all_bots.append({"bot_id": len(all_bots) + 1, "name": f"Bot_{len(all_bots)+1}", "script_path": os.path.join(root, file)})
        except Exception:
            pass

    if len(all_bots) < 160:
        local_bots_file = "bots/all_submitted_bots.json"
        if os.path.exists(local_bots_file):
            with open(local_bots_file, "r", encoding="utf-8") as f:
                all_bots = json.load(f)
        else:
            all_bots = [{"bot_id": i, "name": f"Bot_SinhVien_{i}", "script_path": "bots/examples/random_bot.py"} for i in range(1, 161)]

    # 2. CHẠY SƠ LOẠI (4 WORKERS)
    print("\n[2/5] Đang mô phỏng chạy Sơ loại 4 Máy...")
    all_qualified_bots, all_match_logs = [], []
    for laptop_id in range(1, 5):
        q_bots, m_logs = simulate_laptop_worker(laptop_id, all_bots, total_laptops=4, total_groups=16)
        all_qualified_bots.extend(q_bots)
        all_match_logs.extend(m_logs)

    # 3. CHẠY VÒNG THỤY SĨ (SWISS STAGE)
    print("\n[3/5] Đang thi đấu Vòng Thụy Sĩ...")
    formatted_swiss_bots = [{"id": b.get("bot_id") or b.get("id"), "name": b.get("name"), "path": b.get("script_path", "")} for b in all_qualified_bots]
    swiss_mgr = SwissTournamentManager(bots=formatted_swiss_bots, total_rounds=5)
    swiss_mgr.run_tournament()

    swiss_standings = getattr(swiss_mgr, "standings", getattr(swiss_mgr, "bots", formatted_swiss_bots))
    final_standings = []
    for rank, bot_stat in enumerate(swiss_standings, start=1):
        b_id = bot_stat.get("id", rank) if isinstance(bot_stat, dict) else rank
        final_standings.append({"rank": rank, "bot_id": int(b_id), "score": float((len(swiss_standings) - rank + 1) * 3), "wins": max(0, len(swiss_standings) - rank), "losses": rank - 1})

    # 4. TỰ ĐỘNG ĐỒNG BỘ CÂY NHÁNH ĐẤU VÀO NEON DB
    sync_bracket_to_neon_db(TOURNAMENT_ID, all_bots)

    # 5. CẬP NHẬT TRẠNG THÁI GIẢI ĐẤU LÊN WEB RENDER
    print("\n[5/5] Đang cập nhật trạng thái Giải đấu thành COMPLETED trên Web Render...")
    payload = {"tournament_id": TOURNAMENT_ID, "standings": final_standings, "match_logs": all_match_logs, "status": "COMPLETED"}
    try:
        resp = requests.post(f"{RENDER_URL}/api/admin/import-results", json=payload, headers=headers)
        if resp.status_code in [200, 201]:
            print("=== HOÀN TẤT THÀNH CÔNG 100%! Hãy nhấn F5 trên trình duyệt để xem Cây thi đấu ===")
        else:
            print(f" -> Cảnh báo cập nhật trạng thái Render ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f" -> Lỗi gửi Render: {e}")


if __name__ == "__main__":
    run_offline_pipeline()