class RuleSet:
    def __init__(self, config: dict):
        self.board_size = config.get("board_size", 9)
        self.max_turns = config.get("max_turns", 200)
        self.move_time_limit = config.get("move_time_limit", 2)
        self.special_cells = config.get("special_cells", False)
        self.fog_of_war = config.get("fog_of_war", False)
        self.display_delay = config.get("display_delay", 3)

    @classmethod
    def default(cls):
        return cls({
            "board_size": 9,
            "max_turns": 200,
            "move_time_limit": 2,
            "special_cells": False,
            "fog_of_war": False,
            "display_delay": 3
        })
