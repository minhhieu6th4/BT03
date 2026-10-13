import pytest
from judge.validator import BotValidator

def test_forbidden_import_subprocess():
    code = "import subprocess\nclass Bot:\n def get_move(self, s): return {}"
    is_valid, msg = BotValidator.validate(code)
    assert is_valid is False
    assert "subprocess" in msg.lower()

def test_forbidden_import_socket():
    code = "import socket\nclass Bot:\n def get_move(self, s): return {}"
    is_valid, msg = BotValidator.validate(code)
    assert is_valid is False
    assert "socket" in msg.lower()

def test_missing_get_move_method():
    code = "class Bot:\n pass"
    is_valid, msg = BotValidator.validate(code)
    assert is_valid is False
    assert "get_move" in msg
