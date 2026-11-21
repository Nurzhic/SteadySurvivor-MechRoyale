#!/usr/bin/env python3
"""Deterministic action checks; this is NOT a match simulator."""
from example_bot import SurvivalBot

def obs(special='laser', charge=0.2, ammo=10, aim=(0.0, -0.0997), d=25):
    w0={"kind":"gun","ammo":ammo,"reload":0,"cooldown":0.0,
        "stats":{"range":230,"speed":252}}
    w1={"kind":special,"cooldown":0.0,"charge":charge,
        "stats":{"range":280 if special=="laser" else 45 if special=="lightning" else 235,
                 "charge":0.75,"speed":72,"gravity":22}}
    return {
      "type":"obs","tick":20,"t":1.0,"alive":16,
      "self":{"id":0,"pos":[0,0,0],"vel":[0,0,0],"aim":list(aim),
              "hp":1400,"max_hp":1400,"energy":100,"max_energy":100,
              "grounded":True,"weapons":[w0,w1],"stats":{"muzzle_height":7}},
      "mechs":[{"kind":"mech","id":1,"pos":[d,0,0],"vel":[0,0,0],
                "hp":1000,"max_hp":1400}],
      "pickups":[],"cubes":[],"crates":[],"drops":[],"projectiles":[],
      "zone":{"center":[0,0],"radius":560,"next_center":[0,0],"next_radius":380}}
def act(o):
    bot=SurvivalBot()
    bot.ready({"type":"hello","config":{},"seed":1})
    return bot.act(o)
def main():
    a=act(obs(special="laser",charge=0.2))
    assert a["fire"]==[True,True], f"both gun and charging laser must fire: {a}"
    a=act(obs(special="laser",charge=0.75))
    assert a["fire"]==[True,False], f"gun must continue while laser releases: {a}"
    a=act(obs(special="lightning"))
    assert a["fire"]==[True,True], f"gun and lightning must fire together: {a}"
    a=act(obs(special="mortar"))
    assert a["fire"]==[False,True], f"do not waste gun at ballistic arc: {a}"
    a=act(obs(special="laser",ammo=0))
    assert a["fire"][0] is False, f"empty gun must not fire: {a}"
    a=act(obs(special="laser",aim=(2.5,0)))
    assert a["fire"][0] is False, f"gun should wait to align: {a}"
    print("Strategy tests PASS: dual-fire laser, lightning, safe mortar separation, ammo and aim guards")
if __name__ == "__main__":
    main()
