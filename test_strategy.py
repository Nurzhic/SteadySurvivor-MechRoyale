#!/usr/bin/env python3
"""Checks for v5's single new damage-response behavior; not a game simulation."""
import copy
import math
from example_bot import SurvivalBot


def observation(tick=20, events=None):
    return {
        'type':'obs','tick':tick,'t':tick/20.0, 'alive':16,
        'self':{'id':0,'pos':[0.0,0.0,0.0],'vel':[0.0,0.0,0.0],
                'aim':[0.0,0.0],'hp':900,'max_hp':1400,
                'grounded':True,'energy':90,'max_energy':100,
                'weapons':[{'kind':'gun','ammo':12,'reload':0,'cooldown':0,
                            'stats':{'range':230, 'speed':252}},None],
                'stats':{'muzzle_height':7}},
        'mechs':[],'cubes':[],'pickups':[],'crates':[],'drops':[],
        'projectiles':[], 'events':events or [],
        'zone':{'center':[0,0],'radius':560,
                'next_center':[0,0],'next_radius':380}
    }

def run():
    bot=SurvivalBot()
    bot.ready({'type':'hello','config':{}})
    quiet=bot.act(observation(tick=20))
    assert not quiet['boost'], quiet
    # East is the attacker's bearing. Move away and strafe, and face east.
    a=bot.act(observation(tick=22,events=[{
      'type':'damaged','amount':90,'weapon':'gun','bearing':0.0,'by':5,'rear':True}]))
    assert a['boost'], a
    assert a['move'][0] < -0.5, a
    assert abs(a['move'][1]) > 0.2, a
    assert abs(a['aim'][0]) < 0.01, a
    # Keep reacting briefly even if damage does not happen every action.
    b=bot.act(observation(tick=36))
    assert b['boost'] and b['move'][0] < 0, b
    # Expire after two seconds.
    c=bot.act(observation(tick=64))
    assert not c['boost'], c
    # Zone damage and absent bearing must not trigger false threats.
    bot=SurvivalBot()
    bot.ready({'type':'hello','config':{}})
    d=bot.act(observation(tick=22, events=[
         {'type':'damaged','amount':30,'weapon':'zone','bearing':None}]))
    assert not d['boost'], d
    print('Strategy tests PASS: attack bearing, sidestep, boost, rear armor, threat TTL, zone guard')

if __name__=='__main__':
    run()
