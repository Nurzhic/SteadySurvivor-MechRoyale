#!/usr/bin/env python3
"""Deterministic unit smoke tests. This is not a match simulation."""
import copy
import gzip
import json
import math
import os
from example_bot import SurvivalBot, upgrade_choice

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.environ.get('MECHFIGHT_KIT', os.path.abspath(os.path.join(HERE, '..', 'mechfight-kit')))
with gzip.open(os.path.join(KIT, 'check', 'stream.jsonl.gz'), 'rt') as f:
    hello = json.loads(next(f))
    obs = json.loads(next(f))

def bot():
    b = SurvivalBot()
    assert b.ready(hello)['name'] == 'SteadySurvivor-v3'
    return b

assert upgrade_choice({'choices': [{'id': 'nanites'}, {'id': 'servos'}, {'id': 'gun_damage'}]}) == 1
assert upgrade_choice({'choices': [{'id': 'sensors'}, {'id': 'plating'}, {'id': 'armor'}]}) == 1

safe = copy.deepcopy(obs)
safe['t'] = 15.0
safe['tick'] = 300
safe['mechs'] = []
safe['projectiles'] = []
safe['crates'] = []
safe['cubes'] = []
safe['drops'] = []
safe['pickups'] = []
safe['events'] = []
safe['sounds'] = []
safe['zone'] = {'center': safe['self']['pos'][:2], 'radius': 350,
                'next_center': safe['self']['pos'][:2], 'next_radius': 250}
x = bot().act(safe)
assert math.hypot(*x['move']) < 1e-4, x

hit = copy.deepcopy(safe)
hit['events'] = [{'type': 'damaged', 'weapon': 'gun', 'bearing': 0.0, 'amount': 45}]
x = bot().act(hit)
assert x['move'][0] < -0.9, x
assert abs(x['aim'][0]) < 1e-4, x

# Do not try to take an object on another floor.
far_height = copy.deepcopy(safe)
far_height['pickups'] = [{'id': 8001, 'kind': 'laser', 'pos': [safe['self']['pos'][0],
                          safe['self']['pos'][1], safe['self']['pos'][2] + 20]}]
x = bot().act(far_height)
assert 'take' not in x, x

print('Strategy unit tests PASS (not a game simulation)')
