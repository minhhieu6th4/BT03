import pytest
from game.rule_set import RuleSet

def test_default_rule_set():
    rules = RuleSet.default()
    assert rules.board_size == 9
    assert rules.move_time_limit == 2
    assert rules.max_turns == 200

def test_custom_rule_set():
    rules = RuleSet({
        "board_size": 11,
        "move_time_limit": 3,
        "max_turns": 300
    })
    assert rules.board_size == 11
    assert rules.move_time_limit == 3
    assert rules.max_turns == 300
