import os
import json
from typing import Optional, Dict, Any
from game.rule_set import RuleSet

class TournamentRuleManager:
    """Quản lý và áp dụng luật thi đấu theo từng giai đoạn của giải đấu"""
    def __init__(self, configs_dir: Optional[str] = None):
        self.configs_dir = configs_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', 'configs')
        )
        self.configs: Dict[str, Dict[str, Any]] = {}
        self._load_configs()

    def _load_configs(self):
        if not os.path.exists(self.configs_dir):
            return
        for file in os.listdir(self.configs_dir):
            if file.endswith('.json'):
                key = file.replace('.json', '')
                with open(os.path.join(self.configs_dir, file), 'r', encoding='utf-8') as f:
                    try:
                        self.configs[key] = json.load(f)
                    except Exception:
                        pass

    def get_stage_config(self, stage: str) -> Dict[str, Any]:
        alias = {
            "round_of_32": "top32",
            "round_of_16": "top16",
            "quarterfinal": "quarterfinal",
            "semifinal": "semifinal",
            "final": "final",
            "qualification": "qualification"
        }
        key = alias.get(stage, stage)
        return self.configs.get(key, {})

    def get_rule_set_for_stage(self, stage: str) -> RuleSet:
        comp_rules = self.configs.get("competition", {}).get("game_rules", {})
        board_size = comp_rules.get("board_width", 9)
        max_turns = comp_rules.get("max_turns_per_game", 200)
        time_limit_ms = comp_rules.get("time_limit_per_move_ms", 2000)
        
        return RuleSet({
            "board_size": board_size,
            "max_turns": max_turns,
            "move_time_limit": time_limit_ms / 1000.0
        })
