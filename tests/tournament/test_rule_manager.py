import pytest
from configs import *
import os
import json

def test_stage_configs_exist():
    configs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'configs'))
    assert os.path.exists(os.path.join(configs_dir, 'competition.json'))
    assert os.path.exists(os.path.join(configs_dir, 'qualification.json'))
    assert os.path.exists(os.path.join(configs_dir, 'final.json'))
