"""Fast deterministic strategy and map-navigation tests (no simulation)."""
import copy
import gzip
import json
import math
import os
from example_bot import SurvivalBot, MapNavigator

BASE = os.path.dirname(os.path.realpath(__file__))
DEFAULT_KIT = os.path.abspath(os.path.join(BASE, '..', 'mechfight-kit'))
KIT = os.environ.get('MECHFIGHT_KIT', DEFAULT_KIT)
with gzip.open(os.path.join(KIT, 'check', 'stream.jsonl.gz'), 'rt') as f:
    hello = json.loads(next(f))
    first = json.loads(next(f))
hello['map']['dir'] = os.path.join(KIT, 'arena')

def new_bot():
    b = SurvivalBot()
    assert b.ready(hello)['name'] == 'SteadySurvivor-v2'
    assert b.navigator.ok
    return b

# Upgrade catalog ID based, not text guesses.
b = new_bot()
a = copy.deepcopy(first)
a['offer'] = {'choices': [{'id': 'sensors'}, {'id': 'nanites'}, {'id': 'gun_damage'}]}
assert b.act(a)['pick'] == 1

# Outside future circle should actively head inside.
b = new_bot()
a = copy.deepcopy(first)
a['mechs'] = []
a['pickups'] = []
a['cubes'] = []
a['crates'] = []
a['projectiles'] = []
a['zone']['next_center'] = [-100, 0]
a['zone']['next_radius'] = 20
move = b.act(a)['move']
assert math.hypot(*move) > 0.5, move

# Take nearby weapon: horizontal radius and height both matter.
b = new_bot()
a = copy.deepcopy(first)
a['zone']['next_center'] = a['self']['pos'][:2]
a['zone']['next_radius'] = 380
a['mechs'] = []
a['projectiles'] = []
a['pickups'] = [{'id': 8001, 'kind': 'laser', 'pos':
                  [a['self']['pos'][0] + 2, a['self']['pos'][1], a['self']['pos'][2]]}]
assert b.act(a).get('take') == 8001

# The map avoids at least one route crossing a solid building.
nav = b.navigator
assert sum(nav.blocked) > 100
block = next((i,j) for j in range(10,nav.ny-10) for i in range(10,nav.nx-10)
             if not nav.free(i,j) and nav.free(i-2,j) and nav.free(i+2,j))
a = nav.to_world((block[0]-2,block[1]))
z = nav.to_world((block[0]+2,block[1]))
assert not nav.clear_segment(a,z)
for tick in range(100):
    nav.travel(a,z,tick)
    if nav.search is None:
        break
assert nav.search is None
print('Strategy and grid navigation checks PASS')
