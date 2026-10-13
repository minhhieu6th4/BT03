import pytest
from judge.match_runner import DockerBotWrapper

def test_docker_bot_wrapper_init():
    # Kiểm tra khởi tạo wrapper trỏ đúng bot directory
    wrapper = DockerBotWrapper(bot_dir='bots/examples', team_name='RED')
    assert wrapper.team_name == 'RED'
    wrapper.close()
