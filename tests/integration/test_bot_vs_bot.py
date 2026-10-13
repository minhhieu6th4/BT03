import pytest
from game.game_engine import GameEngine
from game.rule_set import RuleSet
from game.move import Move
from game.piece import Team
from bots.examples.greedy_bot import Bot as GreedyBot
from bots.examples.random_bot import Bot as RandomBot

def test_full_bot_match_simulation():
    engine = GameEngine(RuleSet.default())
    bot_a = GreedyBot()
    bot_b = RandomBot()
    
    moves_played = 0
    winner = None
    for turn in range(1, 100):
        w = engine.check_winner(engine.state)
        if w:
            winner = w
            break
            
        current = engine.state.current_team
        bot = bot_a if current == Team.RED else bot_b
        
        move_dict = bot.get_move(engine.state.to_dict())
        move = Move.from_dict(move_dict)
        if not engine.is_valid_move(engine.state, move):
            break
            
        engine.apply_move(engine.state, move)
        moves_played += 1
        
    assert moves_played > 0
