import json
import os
from game.game_state import GameState
from game.game_result import GameResult

class MatchLogger:
    """
    Lưu trữ lịch sử di chuyển (Move Log) và xuất ra file match.json
    để Frontend sử dụng cho mục đích hiển thị Replay.
    """
    def __init__(self, match_id: str, game_id: str, red_team: str, blue_team: str):
        self.match_id = match_id
        self.game_id = game_id
        self.red_team = red_team
        self.blue_team = blue_team
        self.initial_board = []
        self.moves = []

    def set_initial_board(self, state: GameState):
        self.initial_board = state.to_dict()["board"]

    def log_move(self, turn: int, team: str, move_dict: dict):
        self.moves.append({
            "turn": turn,
            "team": team,
            "from": move_dict["from"],
            "to": move_dict["to"]
        })

    def save(self, result: GameResult, output_dir: str, filename: str = None):
        data = {
            "match_id": self.match_id,
            "game_id": self.game_id,
            "red_team": self.red_team,
            "blue_team": self.blue_team,
            "initial_board": self.initial_board,
            "moves": self.moves,
            "total_turns": len(self.moves),
            "result": {
                "type": result.result_type.name if result else "UNKNOWN",
                "winner": result.winner.name if result and result.winner else None,
                "reason": result.reason if result else ""
            }
        }
        
        os.makedirs(output_dir, exist_ok=True)
        file_name = filename if filename else f"game_{self.game_id}.json"
        file_path = os.path.join(output_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return file_path

    @staticmethod
    def save_match_summary(match_dir: str, match_data: dict):
        """Lưu file match.json tổng kết toàn bộ cặp đấu"""
        os.makedirs(match_dir, exist_ok=True)
        summary_path = os.path.join(match_dir, "match.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(match_data, f, ensure_ascii=False, indent=2)
        return summary_path

