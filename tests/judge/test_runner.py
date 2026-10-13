import pytest
import os

def test_runner_file_exists():
    runner_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'judge', 'runner.py'))
    assert os.path.exists(runner_path)
