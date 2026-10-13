import os
from backend.database.connection import SessionLocal
from backend.models.match import Match
from backend.models.game import Game
from game.game_engine import GameEngine
from game.rule_set import RuleSet
from game.move import Move
from game.piece import Team
from game.game_result import GameResult, ResultType
from judge.result import MatchLogger
from judge.match_runner import DockerBotWrapper
from backend.config.settings import settings

class JudgeService:
    @staticmethod
    def run_match_background(match_id: int, red_team_id: int, blue_team_id: int):
        db = SessionLocal() # Mở kết nối riêng cho luồng background
        try:
            match = db.query(Match).filter(Match.id == match_id).first()
            if not match:
                return

            dir_a = os.path.join(settings.SUBMISSIONS_DIR, f"team_{red_team_id}")
            dir_b = os.path.join(settings.SUBMISSIONS_DIR, f"team_{blue_team_id}")
            
            # Khởi tạo 2 môi trường Sandbox
            bot_a = DockerBotWrapper(bot_dir=dir_a, team_name="RED")
            bot_b = DockerBotWrapper(bot_dir=dir_b, team_name="BLUE")
            
            engine = GameEngine(RuleSet.default())
            game_id_str = f"{red_team_id}_vs_{blue_team_id}_m{match_id}"
            logger = MatchLogger(match_id=str(match_id), game_id=game_id_str, red_team=f"Team {red_team_id}", blue_team=f"Team {blue_team_id}")
            logger.set_initial_board(engine.state)
            
            result = None
            try:
                while True:
                    winner = engine.check_winner(engine.state)
                    if winner:
                        result = winner
                        break
                        
                    current_bot = bot_a if engine.state.current_team == Team.RED else bot_b
                    try:
                        move_dict = current_bot.get_move(engine.state.to_dict())
                        move = Move.from_dict(move_dict)
                    except Exception as e:
                        losing_team = engine.state.current_team
                        winning_team = Team.BLUE if losing_team == Team.RED else Team.RED
                        result = GameResult(ResultType.WIN, winning_team, f"Crash: {str(e)}")
                        break

                    if not engine.is_valid_move(engine.state, move):
                        losing_team = engine.state.current_team
                        winning_team = Team.BLUE if losing_team == Team.RED else Team.RED
                        result = GameResult(ResultType.WIN, winning_team, "Invalid move")
                        break

                    logger.log_move(engine.state.turn, engine.state.current_team.name, move_dict)
                    engine.apply_move(engine.state, move)
            finally:
                bot_a.close()
                bot_b.close()
                
            MATCH_LOGS_DIR = settings.MATCH_LOGS_DIR
            os.makedirs(MATCH_LOGS_DIR, exist_ok=True)
            logger.save(result, output_dir=MATCH_LOGS_DIR)
            
            # Cập nhật kết quả vào MySQL
            match.status = "COMPLETED"
            if result.winner == Team.RED:
                match.winner_team_id = red_team_id
            elif result.winner == Team.BLUE:
                match.winner_team_id = blue_team_id
            
            # Tạo bản ghi Game
            log_file = os.path.join(MATCH_LOGS_DIR, f"game_{game_id_str}.json")
            game = Game(match_id=match_id, log_file_path=log_file, winner_team_id=match.winner_team_id)
            db.add(game)
            db.commit()

        finally:
            db.close()
