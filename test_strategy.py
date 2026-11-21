#!/usr/bin/env python3
"""Small unit tests of v6 next-circle timing; not a match simulator."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('bot_v6', Path(__file__).with_name('example_bot.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def obs(t, x=320.0, y=-280.0, radius=560.0, next_radius=380.0):
    return {
        'tick': int(t * 20), 't': t, 'type': 'obs',
        'self': {'id': 1, 'pos': [x, y, 0.0], 'vel': [0, 0, 0], 'hp': 1400,
                 'max_hp': 1400, 'energy': 100, 'max_energy': 100,
                 'grounded': True, 'aim': [0, 0], 'weapons': [{'kind':'gun', 'ammo':12, 'stats':{'speed':252, 'range':230}},None],
                 'stats': {'walk_speed':11.7,'muzzle_height':7}},
        'zone': {'center': [41.3,-72.8], 'radius': radius, 'next_center': [-23.72,2.21],
                 'next_radius': next_radius, 'shrink_start': 60, 'shrink_end':110, 'dps':20},
        'mechs': [], 'projectiles': [], 'cubes': [], 'pickups':[], 'crates':[], 'drops':[],
        'offer':None, 'events':[], 'sounds':[],
    }


def assert_points_to_next(v):
    # From [320,-280] the next circle is toward west/north.
    assert v['move'][0] < -0.6 and v['move'][1] > 0.5, v


b = module.SurvivalBot()
b.ready({'config': {}})
start = b.act(obs(0))
assert start['move'] == [0.0,0.0], start
assert start['tick'] == 0, start
late = module.SurvivalBot().act(obs(93))
assert_points_to_next(late)
outside = module.SurvivalBot().act(obs(10, x=800, y=0))
assert outside['move'][0] < -0.5, outside
# With an enemy close, enemy avoidance must still move the robot.
threatened = obs(0)
threatened['mechs'] = [{'kind':'mech','id':2,'pos':[340,-280,0], 'vel':[0,0,0], 'hp':1400, 'max_hp':1400}]
retreat = module.SurvivalBot().act(threatened)
assert retreat['move'][0] < -0.7, retreat
print('v6 strategy tests PASS (not a game simulation)')
