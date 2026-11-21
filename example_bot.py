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
        'nanites': 108, 'armor': 100, 'plating': 96, 'servos': 93,
        'jets': 90, 'reactor': 82, 'capacitor': 78, 'gun_rate': 70,
        'gun_damage': 68, 'gun_mag': 65, 'laser_damage': 72,
        'laser_charge': 72, 'gun_velocity': 64, 'gyros': 45,
        'sensors': 40, 'mortar_reload': 65, 'mortar_velocity': 50,
        'lightning_efficiency': 61, 'lightning_range': 48,
    }
    choices = offer.get('choices', [])
    if not choices:
        return None
    def score(item):
        words = (str(item.get('id', '')) + ' ' + str(item.get('name', '')) + ' ' + str(item.get('desc', ''))).lower()
        return max((rank for word, rank in scores.items() if word in words), default=15)
    return max(range(len(choices)), key=lambda i: score(choices[i]))


# Place after imports and helpers, before SurvivalBot.
import heapq


class MapNavigator:
    """Small deterministic grid navigator for ground-level campus buildings.

    Bridges are deliberately not treated as solid footprint obstacles: most
    bridges can be crossed under or on top. This remains an approximation.
    """
    def __init__(self, map_dir):
        self.ok = False
        self.cell = 7.0
        self.path = []
        self.target_cell = None
        self.next_replan = 0
        self.search = None
        self.index = 0
        if not map_dir:
            return
        try:
            with open(os.path.join(map_dir, 'v2', 'world.json'), 'r') as f:
                world = json.load(f)
        except (OSError, ValueError):
            return
        bounds = world['bounds']
        self.minx, self.miny = float(bounds['minX']), float(bounds['minY'])
        self.nx = int((float(bounds['maxX']) - self.minx) / self.cell) + 1
        self.ny = int((float(bounds['maxY']) - self.miny) / self.cell) + 1
        self.blocked = bytearray(self.nx * self.ny)
        for prism in world.get('prisms', []):
            if prism.get('kind') not in ('building', 'stadium'):
                continue
            ring = prism.get('ring') or []
            if len(ring) < 6:
                continue
            xs = ring[::2]
            ys = ring[1::2]
            x0 = max(0, int((min(xs) - 3.5 - self.minx) / self.cell))
            x1 = min(self.nx - 1, int((max(xs) + 3.5 - self.minx) / self.cell) + 1)
            y0 = max(0, int((min(ys) - 3.5 - self.miny) / self.cell))
            y1 = min(self.ny - 1, int((max(ys) + 3.5 - self.miny) / self.cell) + 1)
            holes = prism.get('holes') or []
            for j in range(y0, y1 + 1):
                y = self.miny + self.cell * j
                for i in range(x0, x1 + 1):
                    x = self.minx + self.cell * i
                    # Inflation by ~3 m to allow clearance for the mech's radius.
                    samples = ((x,y), (x+2.5,y), (x-2.5,y),
                               (x,y+2.5), (x,y-2.5))
                    if any(self.point_in_polygon(sx, sy, ring) and
                           not any(self.point_in_polygon(sx,sy,h) for h in holes)
                           for sx, sy in samples):
                        self.blocked[j*self.nx + i] = 1
        self.ok = True

    @staticmethod
    def point_in_polygon(x, y, ring):
        inside = False
        # Flat polygon xy pairs; crossing test.
        k = len(ring) - 2
        for n in range(0, len(ring), 2):
            ax, ay = ring[k], ring[k+1]
            bx, by = ring[n], ring[n+1]
            if (ay > y) != (by > y):
                intersect_x = (bx - ax) * (y - ay) / (by - ay) + ax
                if x < intersect_x:
                    inside = not inside
            k = n
        return inside

    def to_cell(self, pt):
        return (max(0, min(self.nx-1, round((pt[0]-self.minx)/self.cell))),
                max(0, min(self.ny-1, round((pt[1]-self.miny)/self.cell))))

    def to_world(self, cell):
        return (self.minx + self.cell*cell[0], self.miny+self.cell*cell[1])

    def free(self, i, j):
        return 0 <= i < self.nx and 0 <= j < self.ny and not self.blocked[j*self.nx+i]

    def nearest_free(self, ij):
        x, y = ij
        if self.free(x,y):
            return ij
        for r in range(1, 8):
            points = [(x+dx, y+dy) for dx in range(-r, r+1)
                      for dy in range(-r,r+1) if max(abs(dx),abs(dy)) == r]
            candidates = [p for p in points if self.free(*p)]
            if candidates:
                return min(candidates, key=lambda p: (p[0]-x)**2+(p[1]-y)**2)
        return ij

    def clear_segment(self, a, b):
        # A coarse LOS through the footprint grid. Stuck handler handles
        # collision cases where the grid approximation is too permissive.
        length = dist(a,b)
        count = max(1, int(length / (self.cell*.46)))
        for k in range(1, count+1):
            f = k/count
            x,y = a[0]*(1-f)+b[0]*f, a[1]*(1-f)+b[1]*f
            ci,cj = self.to_cell((x,y))
            if not self.free(ci,cj):
                return False
        return True

    def build_path(self, start, goal):
        start = self.nearest_free(start)
        goal = self.nearest_free(goal)
        if not self.free(*start) or not self.free(*goal):
            return []
        if start == goal:
            return [goal]
        dirs = ((1,0,1),(-1,0,1),(0,1,1),(0,-1,1),
                (1,1,1.4142),(-1,1,1.4142),(1,-1,1.4142),(-1,-1,1.4142))
        openq = [(0.0, 0.0, start)]
        best = {start:0.0}
        prev = {}
        visits=0
        while openq and visits < 6000:
            _, cost, cur = heapq.heappop(openq)
            if cost != best.get(cur):
                continue
            visits+=1
            # Time-slice A* so that a long map search never blocks a 50 ms tick.
            if visits % 380 == 0:
                yield None
            if cur == goal:
                out = [cur]
                while cur != start:
                    cur = prev[cur]
                    out.append(cur)
                out.reverse()
                return out
            x,y=cur
            for dx,dy,w in dirs:
                nx,ny=x+dx,y+dy
                if not self.free(nx,ny):
                    continue
                if dx and dy and (not self.free(x+dx,y) or not self.free(x,y+dy)):
                    continue
                nxt=(nx,ny)
                nc=cost+w
                if nc < best.get(nxt,1e30):
                    best[nxt]=nc
                    prev[nxt]=cur
                    heuristic=math.hypot(nx-goal[0],ny-goal[1])
                    heapq.heappush(openq,(nc+heuristic,nc,nxt))
        return []

    def travel(self, current, goal, tick, force=False):
        if not self.ok or dist(current,goal)<8:
            return goal
        # For destinations in immediate line of sight, don't search.
        if self.clear_segment(current, goal):
            self.path=[]
            self.search=None
            self.target_cell=None
            return goal
        target_cell=self.to_cell(goal)
        if (target_cell != self.target_cell or
                (self.search is None and tick >= self.next_replan) or
                (force and self.search is None and tick >= self.next_replan - 15)):
            self.search=self.build_path(self.to_cell(current), target_cell)
            self.target_cell=target_cell
            self.path=[]
            self.index=0
            self.next_replan=tick+38
        if self.search is not None:
            try:
                next(self.search)
            except StopIteration as done:
                self.path=done.value or []
                self.search=None
        if not self.path:
            # While planning, move toward goal; a stalled unit can jet over an edge.
            return goal
        # Look ahead on the path, avoiding tiny cell-to-cell turns.
        closest = min(range(len(self.path)),key=lambda i: dist(current,self.to_world(self.path[i])))
        self.index=max(self.index,closest)
        best=self.index
        for i in range(self.index+1,min(len(self.path),self.index+12)):
            p=self.to_world(self.path[i])
            if self.clear_segment(current,p):
                best=i
            else:
                break
        self.index=best
        return self.to_world(self.path[best])


class SurvivalBot:
    def __init__(self):
        self.prev_xy = None
        self.stuck = 0
        self.escape_until = -1
        self.escape_side = 1
        self.config = {}
        self.navigator = None
        self.scan_offset = 0.0
        self.last_threat_tick = -10000
        self.last_threat_yaw = 0.0
        self.goal_id = None
        self.goal_until = 0
        self.retreat_goal = None
        self.retreat_refresh = 0
        self.retreat_enemy_id = None

    def ready(self, hello):
        self.config = hello.get('config', {}) or {}
        self.scan_offset = (float(hello.get('seed', 1)) % 997) / 997.0 * TAU
        self.navigator = MapNavigator((hello.get('map') or {}).get('dir'))
        return {'type': 'ready', 'name': 'SteadySurvivor-v2'}

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
        move_x, move_y = 0.0, 0.0
        strategic_goal = None
        if outside:
            strategic_goal = (float(zone_xy[0]), float(zone_xy[1]))
        elif next_edge > 0:
            strategic_goal = (float(next_xy[0]), float(next_xy[1]))
        else:
            # Stay well inside the *next* zone, but avoid camping in its busy center.
            safe_offset = min(55.0, max(5.0, nrad * 0.26))
            u0, v0 = normalize(pos[0]-float(next_xy[0]), pos[1]-float(next_xy[1]))
            strategic_goal = (float(next_xy[0])+u0*safe_offset,
                              float(next_xy[1])+v0*safe_offset)


        enemies = [m for m in obs.get('mechs', []) if m.get('kind') == 'mech' and m.get('pos')]
        npcs = [m for m in obs.get('mechs', []) if m.get('kind') == 'npc' and m.get('pos')]
        enemies.sort(key=lambda m: dist(pos, xy(m)))
        nearest = enemies[0] if enemies else None
        closest_d = dist(pos, xy(nearest)) if nearest else 1e9
        for evt in obs.get('events', []):
            if evt.get('type') == 'damaged' and evt.get('bearing') is not None:
                self.last_threat_yaw = float(evt['bearing'])
                self.last_threat_tick = tick


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

        # Navigation priority: emergency safe zone > escape pursuers > loot > quiet position.
        if goal is not None and closest_d > 70 and zone_urgency < 2.5:
            nav_goal = xy(goal)
            nav_weight = 1.85
        else:
            nav_goal = strategic_goal
            nav_weight = 1.25 if zone_urgency < 2.5 else 3.0
        # Retreat from a hostile mech, but keep our escape point inside the zone.
        if nearest is not None and closest_d < 110 and zone_urgency < 3.5:
            enpos=xy(nearest)
            ex,ey=normalize(pos[0]-enpos[0],pos[1]-enpos[1])
            if ex or ey:
                if (self.retreat_goal is None or tick>=self.retreat_refresh or
                        self.retreat_enemy_id != nearest.get('id')):
                    candidate=(pos[0]+ex*68,pos[1]+ey*68)
                    safe_r=max(8, nrad-13)
                    if dist(candidate,next_xy)>safe_r:
                        ux,uy=normalize(candidate[0]-next_xy[0],candidate[1]-next_xy[1])
                        candidate=(next_xy[0]+safe_r*ux,next_xy[1]+safe_r*uy)
                    self.retreat_goal=candidate
                    self.retreat_refresh=tick+25
                    self.retreat_enemy_id=nearest.get('id')
                if dist(self.retreat_goal, enpos) > closest_d+7:
                    nav_goal=self.retreat_goal
                    nav_weight=2.5
        # Recently struck by an unseen enemy: use bearing to escape rather than idle.
        elif nearest is None and tick-self.last_threat_tick < 25 and zone_urgency<2.5:
            heading=self.last_threat_yaw+math.pi
            nav_goal=(pos[0]+math.cos(heading)*48,
                      pos[1]+math.sin(heading)*48)
            nav_weight=1.8
        if nav_goal is not None:
            next_pt=(self.navigator.travel(pos,nav_goal,tick, self.stuck>12)
                     if self.navigator else nav_goal)
            ux,uy=normalize(next_pt[0]-pos[0],next_pt[1]-pos[1])
            if dist(pos, nav_goal)>7.0:
                move_x += ux*nav_weight
                move_y += uy*nav_weight

        # Dynamic short-range separation from visible opponents.
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
        elif nearest is None and tick-self.last_threat_tick<30:
            aim = [self.last_threat_yaw, -0.05]
        elif not nearest:
            # Full 360-degree scan. v1 only swept back/forth through 180 degrees.
            yaw = (t*0.92 + self.scan_offset + math.pi) % TAU - math.pi
            aim = [yaw, -0.05]

        action = {
            'tick': tick,
            'move': [round(mx, 5), round(my, 5)],
            'aim': [round(aim[0], 5), round(aim[1], 5)],
            'fire': fire,
            'boost': bool(me.get('grounded', True) and energy > max_energy * 0.38 and
                          (outside or next_edge > 70 or closest_d < 95 or
                           (tick-self.last_threat_tick < 15 and health_ratio < 0.65)) and
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
        if pickup and dist(pos, xy(pickup)) <= 3.7 and abs(float(me['pos'][2])-float(pickup['pos'][2])) <= 3.5:
            if any(w is None for w in me.get('weapons',[])):
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
