import pytest
from judge.validator import BotValidator

def test_valid_code():
    code = """
class Bot:
    def get_move(self, state):
        return {"from": [0, 1], "to": [1, 1]}
"""
    is_valid, msg = BotValidator.validate(code)
    assert is_valid is True
    assert msg == "Valid"

def test_forbidden_module_os():
    code = """
import os
class Bot:
    def get_move(self, state): return {}
"""
    is_valid, msg = BotValidator.validate(code)
    assert is_valid is False
    assert "os" in msg.lower()

def test_missing_bot_class():
    code = "x = 10"
    is_valid, msg = BotValidator.validate(code)
    assert is_valid is False
    assert "bot" in msg.lower()

def test_syntax_error_code():
    code = "def get_move( invalid syntax"
    is_valid, msg = BotValidator.validate(code)
    assert is_valid is False
    assert "syntax" in msg.lower()
