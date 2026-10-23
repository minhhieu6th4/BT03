import pytest
from judge.match_runner import DockerBotWrapper
from backend.config.settings import settings

def test_docker_bot_wrapper_init():
    # Kiểm tra khởi tạo wrapper trỏ đúng bot directory
    wrapper = DockerBotWrapper(bot_dir='bots/examples', team_name='RED')
    assert wrapper.team_name == 'RED'
    wrapper.close()


def test_production_refuses_host_subprocess_fallback(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr("judge.match_runner.is_docker_available", lambda: False)

    with pytest.raises(RuntimeError, match="host subprocess fallback is disabled"):
        DockerBotWrapper(bot_dir="bots/examples/random_bot.py", team_name="RED")
