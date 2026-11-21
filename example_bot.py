#!/usr/bin/env python3
"""Mech Royale survival-first bot, mechfight/1. Python stdlib only."""
import json
import math
import os
import select
import sys

TAU = 2.0 * math.pi


def xy(obj):
    p = obj.get('pos', (0, 0, 0))
    return float(p[0]), float(p[1])


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def normalize(x, y):
    r = math.hypot(x, y)
    return (x / r, y / r) if r > 1e-8 else (0.0, 0.0)


def delta_angle(x):
    return (x + math.pi) % TAU - math.pi


def aim_at(me, target, weapon='gun'):
    """Lead bullet targets; point at the target's body rather than its feet."""
    src = me.get('pos', (0, 0, 0))
    dst = target.get('pos', (0, 0, 0))
    vel = target.get('vel', (0, 0, 0))
    stats = me.get('stats') or {}
    origin_z = float(src[2]) + float(stats.get('muzzle_height', 7.0))
    kind = target.get('kind', '')
    height = 1.6 if kind in ('npc', 'crate') else 4.5
    speed = 252.0
    if weapon == 'gun':
        for w in me.get('weapons', []):
            if w and w.get('kind') == 'gun':
                speed = float((w.get('stats') or {}).get('speed', speed))
                break
    # A small, capped interception lead for straight bullets; hitscan does not lead.
    flight = min(0.75, dist(src, dst) / max(speed, 1.0)) if weapon == 'gun' else 0.0
    vx = float(vel[0]) if len(vel) > 0 else 0.0
    vy = float(vel[1]) if len(vel) > 1 else 0.0
    vz = float(vel[2]) if len(vel) > 2 else 0.0
    dx = float(dst[0]) + vx * flight - float(src[0])
    dy = float(dst[1]) + vy * flight - float(src[1])
    dz = float(dst[2]) + vz * flight + height - origin_z
    return math.atan2(dy, dx), max(-1.2, min(1.2, math.atan2(dz, max(0.01, math.hypot(dx, dy)))))


def mortar_aim(me, target, speed, gravity=22.0):
    """Low-arc ballistic aim; returns None when the target is out of range."""
    sx, sy = xy(me)
    tx, ty = xy(target)
    srcz = float(me['pos'][2]) + float((me.get('stats') or {}).get('muzzle_height', 7.0)) + 2.5
    dstz = float(target['pos'][2]) + (1.6 if target.get('kind') == 'npc' else 4.0)
    dx, dy = tx - sx, ty - sy
    horizontal = math.hypot(dx, dy)
    vel = target.get('vel') or (0, 0, 0)
    travel = min(3.0, horizontal / max(0.6 * speed, 1.0))
    dx += float(vel[0]) * travel
    dy += float(vel[1]) * travel
    horizontal = max(0.5, math.hypot(dx, dy))
    dz = dstz - srcz
    s2 = speed * speed
    disc = s2 * s2 - gravity * (gravity * horizontal * horizontal + 2.0 * dz * s2)
    if disc < 0.0:
        return None
    pitch = math.atan2(s2 - math.sqrt(disc), gravity * horizontal)
    if not -0.7 <= pitch <= 1.3:
        return None
    return math.atan2(dy, dx), pitch


def upgrade_choice(offer):
    # Defensive upgrades help placement; weapon improvements are useful second.
    scores = {
        'armor': 100, 'regen': 95, 'repair': 92, 'health': 90, 'hp': 85,
        'speed': 80, 'move': 77, 'dash': 73, 'energy': 72, 'boost': 70,
        'cooldown': 63, 'damage': 60, 'rate': 58, 'gun': 55,
        'range': 40, 'sensor': 35, 'vision': 33,
    }
    choices = offer.get('choices', [])
    if not choices:
        return None
    def score(item):
        words = (str(item.get('id', '')) + ' ' + str(item.get('name', '')) + ' ' + str(item.get('desc', ''))).lower()
        return max((rank for word, rank in scores.items() if word in words), default=15)
    return max(range(len(choices)), key=lambda i: score(choices[i]))


class SurvivalBot:
    def __init__(self):
        self.prev_xy = None
        self.stuck = 0
        self.escape_until = -1
        self.escape_side = 1
        self.config = {}

    def ready(self, hello):
        self.config = hello.get('config', {}) or {}
        return {'type': 'ready', 'name': 'SteadySurvivor-v1'}

    def act(self, obs):
        me = obs.get('self') or {}
        if 'pos' not in me:
            return {'tick': obs['tick'], 'move': [0, 0], 'fire': [False, False]}
        tick = int(obs['tick'])
        t = float(obs.get('t', 0))
        pos = xy(me)
        hp = float(me.get('hp', 1400))
        health_ratio = hp / max(float(me.get('max_hp', 1400)), 1.0)
        energy = float(me.get('energy', 0))
        max_energy = max(float(me.get('max_energy', 100)), 1.0)
        zone = obs.get('zone') or {}
        zone_xy = zone.get('center', pos)
        next_xy = zone.get('next_center', zone_xy)
        zrad = float(zone.get('radius', 560))
        nrad = float(zone.get('next_radius', zrad))
        # Target the coming circle well before the current one starts shrinking.
        outside = dist(pos, zone_xy) > zrad - 12
        next_edge = dist(pos, next_xy) - (nrad - 27)
        zone_urgency = 3.5 if outside else (2.5 if next_edge > 35 else (1.4 if next_edge > 0 else 0))
        zx, zy = (normalize(float(next_xy[0]) - pos[0], float(next_xy[1]) - pos[1])
                    if next_edge > 0 else (0, 0))
        if outside:
            zx, zy = normalize(float(zone_xy[0]) - pos[0], float(zone_xy[1]) - pos[1])
        move_x, move_y = zx * zone_urgency, zy * zone_urgency

        enemies = [m for m in obs.get('mechs', []) if m.get('kind') == 'mech' and m.get('pos')]
        npcs = [m for m in obs.get('mechs', []) if m.get('kind') == 'npc' and m.get('pos')]
        enemies.sort(key=lambda m: dist(pos, xy(m)))
        nearest = enemies[0] if enemies else None
        closest_d = dist(pos, xy(nearest)) if nearest else 1e9

        # Strongly prefer space from opponents: practice bots cooperate and hunt us.
        for enemy in enemies:
            ex, ey = xy(enemy)
            d = dist(pos, (ex, ey))
            if d < 150 and d > 1e-3:
                strength = (150 - d) / 75.0
                if d < 55:
                    strength *= 1.9
                if health_ratio < 0.6:
                    strength *= 1.4
                move_x += (pos[0] - ex) / d * strength
                move_y += (pos[1] - ey) / d * strength

        # Collect valuable loot only if it doesn't require crossing a dangerous fight.
        owned = {w.get('kind') for w in me.get('weapons', []) if w}
        pickup = None
        goal = None
        goal_priority = -1e9
        for obj in obs.get('pickups', []):
            if obj.get('kind') in owned or not obj.get('pos'):
                continue
            d = dist(pos, xy(obj))
            kind = obj.get('kind')
            value = {'laser': 135, 'mortar': 95, 'lightning': 85}.get(kind, 40)
            if d < 115:
                val = value - 0.55 * d
                if val > goal_priority:
                    goal, goal_priority = obj, val
                    pickup = obj
        for obj in obs.get('cubes', []):
            if not obj.get('pos'):
                continue
            d = dist(pos, xy(obj))
            if d < 105 and 120 - 0.65 * d > goal_priority:
                goal, goal_priority, pickup = obj, 120 - 0.65 * d, None
        # A supply drop offers full healing; only contest if enemies aren't nearby.
        if closest_d > 85:
            for drop in obs.get('drops', []):
                if not drop.get('pos') or float(drop.get('lands_in', 999)) > 13:
                    continue
                d = dist(pos, xy(drop))
                if d < 130 and 135 - 0.65 * d + (40 if health_ratio < 0.75 else 0) > goal_priority:
                    goal, goal_priority, pickup = drop, 135 - 0.65 * d, None

        if goal is not None and closest_d > 50 and zone_urgency < 2.5:
            gx, gy = xy(goal)
            gd = dist(pos, (gx, gy))
            if gd > 1.5:
                ux, uy = normalize(gx - pos[0], gy - pos[1])
                weight = min(2.0, 0.5 + gd / 55.0)
                move_x += ux * weight
                move_y += uy * weight
        else:
            # When safe, drift toward the center of the next circle, not the edge.
            if not enemies and zone_urgency == 0 and dist(pos, next_xy) > 70:
                ux, uy = normalize(float(next_xy[0]) - pos[0], float(next_xy[1]) - pos[1])
                move_x += ux * 0.7
                move_y += uy * 0.7

        # Avoid oncoming visible projectiles when possible.
        for bullet in obs.get('projectiles', [])[:35]:
            p, v = bullet.get('pos'), bullet.get('vel')
            if not p or not v:
                continue
            dx, dy = float(p[0]) - pos[0], float(p[1]) - pos[1]
            vx, vy = float(v[0]), float(v[1])
            vv = vx*vx + vy*vy
            if vv < 1:
                continue
            when = max(0.0, min(0.75, -(dx*vx + dy*vy) / vv))
            cx, cy = dx + vx*when, dy + vy*when
            if cx*cx + cy*cy < 12*12 and abs(float(p[2]) + float(v[2])*when - float(me['pos'][2]) - 4.5) < 9:
                sx, sy = normalize(-vy, vx)
                if sx*move_x + sy*move_y < 0:
                    sx, sy = -sx, -sy
                move_x += sx * 1.25
                move_y += sy * 1.25

        # Wall-stuck recovery; no need to access the large map in version 1.
        if self.prev_xy is not None and dist(pos, self.prev_xy) < 0.22 and math.hypot(move_x, move_y) > 0.55:
            self.stuck += 1
        else:
            self.stuck = max(0, self.stuck - 2)
        self.prev_xy = pos
        if self.stuck >= 18:
            self.escape_until = tick + 35
            self.escape_side *= -1
            self.stuck = 0
        stuck_mode = tick < self.escape_until
        if stuck_mode:
            ux, uy = normalize(move_x, move_y)
            move_x, move_y = -uy * self.escape_side + ux * 0.2, ux * self.escape_side + uy * 0.2
        mx, my = normalize(move_x, move_y)

        # Aim/fire with the installed weapons; laser charges on hold and fires on release.
        target = None
        if nearest and closest_d < 180:
            target = nearest
        elif npcs and closest_d > 110 and zone_urgency < 2.5:
            npc = min(npcs, key=lambda m: dist(pos, xy(m)))
            if dist(pos, xy(npc)) < 115:
                target = npc
        if target is None and zone_urgency < 2.5 and closest_d > 110:
            crates = [c for c in obs.get('crates', []) if c.get('pos')]
            if crates:
                crate = min(crates, key=lambda c: dist(pos, xy(c)))
                if dist(pos, xy(crate)) < 110:
                    target = dict(crate, kind='crate', vel=[0,0,0])

        current_aim = me.get('aim') or [0, 0]
        aim = [float(current_aim[0]), float(current_aim[1])]
        fire = [False, False]
        if target:
            td = dist(pos, xy(target))
            weapons = me.get('weapons') or []
            # Choose one useful weapon; the gun is the universal fallback.
            priority = -1e9
            chosen_slot = None
            chosen_kind = 'gun'
            chosen_aim = None
            for idx, weapon in enumerate(weapons[:2]):
                if not weapon:
                    continue
                kind = weapon.get('kind', '')
                stats = weapon.get('stats') or {}
                rng = float(stats.get('range', {'gun':230, 'laser':280, 'mortar':200, 'lightning':45}.get(kind,100)))
                if td > rng * (0.95 if kind == 'gun' else 0.9):
                    continue
                if kind == 'lightning' and energy < 6:
                    continue
                candidate_aim = None
                if kind == 'mortar':
                    candidate_aim = mortar_aim(me, target, float(stats.get('speed', 72)),
                                               float(stats.get('gravity', 22)))
                    if td < 25:  # avoid friendly splash
                        continue
                else:
                    candidate_aim = aim_at(me, target, kind)
                if candidate_aim is None:
                    continue
                worth = {'laser': 130, 'mortar': 110, 'lightning': 105, 'gun': 70}.get(kind, 20)
                if kind == 'lightning' and td < 35:
                    worth += 60
                if kind == 'mortar' and td < 80:
                    worth -= 20
                if kind == 'laser' and float(weapon.get('cooldown', 0)) > 0.2:
                    worth -= 90
                if kind == 'gun' and int(weapon.get('ammo', 0)) < 1:
                    worth -= 40
                if worth > priority:
                    chosen_slot = idx
                    chosen_kind = kind
                    chosen_aim = candidate_aim
                    priority = worth
            if chosen_slot is not None:
                aim = list(chosen_aim)
                angular_error = abs(delta_angle(aim[0] - float(current_aim[0])))
                weapon = weapons[chosen_slot]
                if chosen_kind == 'laser':
                    required = float((weapon.get('stats') or {}).get('charge', 0.75))
                    charged = float(weapon.get('charge', 0))
                    # Charge while targeting, release once charged and lined up.
                    fire[chosen_slot] = not (charged >= max(0.2, required - 0.11) and angular_error < 0.12)
                elif chosen_kind == 'lightning':
                    fire[chosen_slot] = angular_error < 0.22
                else:
                    fire[chosen_slot] = angular_error < (0.2 if chosen_kind == 'mortar' else 0.15)
            else:
                aim = list(aim_at(me, target, 'gun'))
        elif not nearest and t > 0:
            # Scan for enemies instead of permanently looking in one direction.
            aim = [math.sin(t / 13.0) * math.pi, -0.04]

        action = {
            'tick': tick,
            'move': [round(mx, 5), round(my, 5)],
            'aim': [round(aim[0], 5), round(aim[1], 5)],
            'fire': fire,
            'boost': bool(me.get('grounded', True) and energy > max_energy * 0.5 and
                          (outside or next_edge > 25 or closest_d < 58) and
                          math.hypot(mx,my) > 0.5),
            'jump': bool(stuck_mode and me.get('grounded', True) and energy > 22),
            'reload': bool(any(w and w.get('kind') == 'gun' and
                                  (int(w.get('ammo', 12)) <= 2) and
                                  float(w.get('reload', 0)) <= 0 for w in me.get('weapons', []))
                           and closest_d > 45),
        }
        # Without a ground jump, use jet only while escaping an obstacle.
        if stuck_mode and not me.get('grounded', True) and energy > 20:
            action['boost'] = True
        if pickup and dist(pos, xy(pickup)) <= 3.7:
            if len(owned) < 2:
                action['take'] = int(pickup['id'])
            else:
                # Keep the default gun and replace weaker special weapons.
                special_slot = next((i for i,w in enumerate(me.get('weapons', []))
                                     if w and w.get('kind') != 'gun'), None)
                rank = {'laser':3, 'mortar':2, 'lightning':1}
                if special_slot is not None and rank.get(pickup.get('kind'), 0) > rank.get(
                        me['weapons'][special_slot].get('kind'), 0):
                    action['take'] = int(pickup['id'])
                    action['drop'] = special_slot
        offer = obs.get('offer')
        if offer:
            i = upgrade_choice(offer)
            if i is not None:
                action['pick'] = i
        return action


def main():
    bot = SurvivalBot()
    pending = bytearray()
    # Raw unbuffered reads let us discard stale observations when the server queues several.
    while True:
        ready, _, _ = select.select([0], [], [])
        if not ready:
            continue
        chunk = os.read(0, 262144)
        if not chunk:
            break
        pending.extend(chunk)
        # Drain already-available input and answer only the newest queued observation.
        while select.select([0], [], [], 0)[0]:
            chunk = os.read(0, 262144)
            if not chunk:
                break
            pending.extend(chunk)
        last_obs = None
        saw_end = False
        while b'\n' in pending:
            raw, _, rest = pending.partition(b'\n')
            pending = bytearray(rest)
            try:
                msg = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(msg, dict):
                continue
            typ = msg.get('type')
            if typ == 'hello':
                print(json.dumps(bot.ready(msg), separators=(',', ':')), flush=True)
            elif typ == 'obs':
                last_obs = msg
            elif typ == 'end':
                saw_end = True
        if last_obs is not None and not saw_end:
            try:
                action = bot.act(last_obs)
            except Exception as exc:
                print('bot error:', repr(exc), file=sys.stderr)
                action = {'tick': last_obs.get('tick', 0), 'move': [0, 0], 'fire': [False,False]}
            print(json.dumps(action, separators=(',', ':'), allow_nan=False), flush=True)
        if saw_end:
            break


if __name__ == '__main__':
    main()
