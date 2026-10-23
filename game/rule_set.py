class RuleSet:
    def __init__(self, config=None, **kwargs):
        cfg = {}
        if isinstance(config, dict):
            cfg.update(config)
        cfg.update(kwargs)
        self.board_size = cfg.get("board_size", 9)
        self.max_turns = cfg.get("max_turns", 200)
        self.move_time_limit = cfg.get("move_time_limit", 2)
        self.special_cells = cfg.get("special_cells", False)
        self.fog_of_war = cfg.get("fog_of_war", False)
        self.display_delay = cfg.get("display_delay", 3)
        self.rocks = [tuple(r) for r in cfg.get("rocks", [])]

    @classmethod
    def default(cls):
        return cls({
            "board_size": 9,
            "max_turns": 200,
            "move_time_limit": 2,
            "special_cells": False,
            "fog_of_war": False,
            "display_delay": 3,
            "rocks": []
        })
