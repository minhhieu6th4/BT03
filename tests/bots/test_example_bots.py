import pytest
from bots.examples.random_bot import Bot as RandomBot
from bots.examples.greedy_bot import Bot as GreedyBot
from bots.examples.example_bot import Bot as ExampleBot

def test_random_bot_get_move(game_engine):
    state_dict = game_engine.state.to_dict()
    bot = RandomBot()
    move_dict = bot.get_move(state_dict)
    assert "from" in move_dict
    assert "to" in move_dict
    assert len(move_dict["from"]) == 2
    assert len(move_dict["to"]) == 2

def test_greedy_bot_get_move(game_engine):
    state_dict = game_engine.state.to_dict()
    bot = GreedyBot()
    move_dict = bot.get_move(state_dict)
    assert "from" in move_dict
    assert "to" in move_dict

def test_example_bot_get_move(game_engine):
    state_dict = game_engine.state.to_dict()
    bot = ExampleBot()
    move_dict = bot.get_move(state_dict)
    assert "from" in move_dict
    assert "to" in move_dict
