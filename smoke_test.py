"""Synthetic I/O protocol smoke test; NOT an official conformance check."""
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
bot = subprocess.Popen(['python3','-u',str(ROOT/'example_bot.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)

def exchange(data):
    before = time.perf_counter()
    bot.stdin.write(json.dumps(data)+'\n')
    bot.stdin.flush()
    out = bot.stdout.readline()
    ms = (time.perf_counter()-before)*1000
    if not out:
        raise RuntimeError('Bot stopped replying')
    return json.loads(out), ms

hello, ms = exchange({'type':'hello', 'protocol':'mechfight/1', 'slot':0, 'seed':123,'config':{}})
assert hello['type']=='ready', hello
latencies=[]
for tick in range(300):
    obs = {'type':'obs', 'tick':tick*2,'t':tick*0.1,'alive':14,
        'self':{'id':0, 'pos':[tick*0.15,0,0], 'vel':[1.5,0,0], 'aim':[0,0],
                'hp':1400-(tick%7)*20, 'max_hp':1400, 'energy':65, 'max_energy':100,
                'grounded':True, 'cubes':3, 'weapons':[
                   {'kind':'gun','cooldown':0,'ammo':10,'reload':0,'stats':{'range':230,'speed':252}},
                   {'kind':'laser','charge':(tick%13)*0.1,'cooldown':0,'stats':{'range':280,'charge':0.75}}],
                'stats':{'muzzle_height':7}},
        'mechs': [{'id':1,'kind':'mech','pos':[70,20 + tick*0.1,0], 'vel':[0,0.5,0], 'hp':750,'weapons':['gun']}] if tick % 4 else [],
        'crates':[{'id':1001,'pos':[30,18,0],'hp':300}],
        'projectiles':[{'pos':[10,0,5],'vel':[-20,0,0]}] if tick%3==0 else [],
        'cubes':[{'id':5020, 'pos':[25,12,0]}],
        'pickups':[{'id':8040,'kind':'mortar','pos':[20,15,0]}],
        'zone':{'center':[0,0], 'radius':560, 'next_center':[100,0], 'next_radius':380, 'shrink_start':60, 'shrink_end':110, 'dps':20},
        'offer':{'choices':[{'id':'armor','name':'Armor'}, {'id':'gun_rate','name':'Faster gun'}, {'id':'sensors','name':'Sensors'}]} if tick%40==0 else None}
    action, ms = exchange(obs)
    latencies.append(ms)
    assert action['tick']==tick*2,(tick, action)
    assert len(action['move'])==2 and sum(v*v for v in action['move']) <= 1.001,action
    assert len(action['aim'])==2 and len(action['fire'])==2,action
    assert action['fire'][0] in [True,False],action
    if tick % 40==0: assert action['pick']==0,action
bot.stdin.write('{"type":"end","place":7,"kills":0}\n')
bot.stdin.flush()
bot.stdin.close()
bot.wait(timeout=5)
assert bot.returncode==0,bot.stderr.read()
print(f'Synthetic protocol smoke test PASS, 300 obs, median {sorted(latencies)[150]:.2f} ms, max {max(latencies):.2f} ms (includes IPC), exit {bot.returncode}')
