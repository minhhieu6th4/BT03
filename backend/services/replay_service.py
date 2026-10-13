import os
import json
from typing import Optional, Dict, Any, List
from backend.config.settings import settings

class ReplayService:
    @staticmethod
    def get_replay_data(game_id: str) -> Optional[Dict[str, Any]]:
        """
        Tìm kiếm file replay của game_id.
        Hỗ trợ cả file game_<id>.json và tìm đệ quy trong các thư mục vòng đấu:
        qualification, round_of_32, final, v.v.
        """
        # 1. Kiểm tra trực tiếp tại root của match_logs
        direct_candidates = [
            os.path.join(settings.MATCH_LOGS_DIR, f"game_{game_id}.json"),
            os.path.join(settings.MATCH_LOGS_DIR, f"{game_id}.json"),
            os.path.join(settings.MATCH_LOGS_DIR, game_id)
        ]
        for candidate in direct_candidates:
            if os.path.exists(candidate) and os.path.isfile(candidate):
                with open(candidate, 'r', encoding='utf-8') as f:
                    return json.load(f)

        # 2. Tìm kiếm đệ quy trong toàn bộ cây thư mục match_logs
        target_names = [f"game_{game_id}.json", f"{game_id}.json"]
        for root, _, files in os.walk(settings.MATCH_LOGS_DIR):
            for file in files:
                if file in target_names:
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)

        return None

    @staticmethod
    def get_replay_by_path(relative_path: str) -> Optional[Dict[str, Any]]:
        """
        Đọc replay theo relative path (VD: 'qualification/group_01/match_0001/game_01.json')
        """
        safe_path = os.path.normpath(relative_path).lstrip(r'\/')
        full_path = os.path.join(settings.MATCH_LOGS_DIR, safe_path)
        
        # Phòng chống Path Traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(settings.MATCH_LOGS_DIR)):
            return None
            
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    @staticmethod
    def get_tournament_tree() -> List[Dict[str, Any]]:
        """
        Quét thư mục match_logs để trích xuất cây phân cấp giải đấu:
        Stage -> Group -> Match -> Games.
        """
        tree = []
        if not os.path.exists(settings.MATCH_LOGS_DIR):
            return tree

        for stage in sorted(os.listdir(settings.MATCH_LOGS_DIR)):
            stage_path = os.path.join(settings.MATCH_LOGS_DIR, stage)
            if not os.path.isdir(stage_path):
                continue

            stage_info = {"stage": stage, "groups": [], "matches": []}
            
            # Kiểm tra xem có group hay match trực tiếp
            for item in sorted(os.listdir(stage_path)):
                item_path = os.path.join(stage_path, item)
                if not os.path.isdir(item_path):
                    continue

                if item.startswith("group_"):
                    group_info = {"group": item, "matches": []}
                    for match_name in sorted(os.listdir(item_path)):
                        m_path = os.path.join(item_path, match_name)
                        if os.path.isdir(m_path):
                            match_meta = ReplayService._read_match_meta(m_path, f"{stage}/{item}/{match_name}")
                            group_info["matches"].append(match_meta)
                    stage_info["groups"].append(group_info)
                elif item.startswith("match_"):
                    match_meta = ReplayService._read_match_meta(item_path, f"{stage}/{item}")
                    stage_info["matches"].append(match_meta)

            tree.append(stage_info)
        return tree

    @staticmethod
    def _read_match_meta(match_dir: str, rel_path: str) -> Dict[str, Any]:
        match_json_path = os.path.join(match_dir, "match.json")
        games = []
        for file in sorted(os.listdir(match_dir)):
            if file.startswith("game_") and file.endswith(".json"):
                games.append({
                    "game_id": file.replace(".json", ""),
                    "file_path": f"{rel_path}/{file}"
                })

        meta = {
            "match_id": os.path.basename(match_dir),
            "path": rel_path,
            "games": games
        }
        if os.path.exists(match_json_path):
            try:
                with open(match_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    meta.update({
                        "red_team": data.get("red_team"),
                        "blue_team": data.get("blue_team"),
                        "score": data.get("score"),
                        "winner": data.get("winner"),
                        "winner_team": data.get("winner_team"),
                        "format": data.get("format"),
                        "status": data.get("status")
                    })
            except Exception:
                pass
        return meta

