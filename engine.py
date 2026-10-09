"""Space Dodger - pure game logic (no Kivy / Pygame dependency).

All coordinates are "logical" units with the origin at the top-left and the
y axis pointing down (same convention as the original Pygame version).
The world is LOGICAL_W units wide; its height adapts to the phone's aspect
ratio.  The rendering layer (main.py) scales everything to real pixels.
"""
import math
import random

LOGICAL_W = 450.0

# The original game was tuned for an 800x600 window.  The phone world is
# narrower, so per-frame speeds are scaled down a bit to keep it fair.
WORLD_K = 0.75

# Palette (same values as the original settings.py)
BLACK = (10, 10, 14)
WHITE = (240, 240, 240)
GRAY = (100, 100, 120)
NEON_BLUE = (80, 200, 255)
NEON_PURPLE = (190, 130, 255)
NEON_YELLOW = (255, 220, 90)
RED = (255, 80, 90)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Player:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.alive = True
        self.invincible = 0.0


class Enemy:
    def __init__(self, x, y, vx, vy, size):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy          # logical units per 1/60 s
        self.size = size
        self.hit_r = size * 0.45


class Orb:
    R = 10.0

    def __init__(self, x, y, phase=0.0):
        self.x, self.y = x, y
        self.r = self.R
        self.phase = phase


class Particle:
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color


class World:
    PLAYER_SPEED = 4.0
    BOOST = 1.8
    MAX_SPEED = 8.0
    PLAYER_MARGIN = 22.0
    PLAYER_HIT_R = 15.0
    PICKUP_R = 24.0
    ORB_TOP = 90.0        # keep orbs away from the HUD ...
    ORB_BOTTOM = 160.0    # ... and from the thumb controls
    MAX_PARTICLES = 400

    def __init__(self, w, h, seed=None):
        self.rng = random.Random(seed)
        self.w, self.h = float(w), float(h)
        self.player = None
        self.reset()

    # ------------------------------------------------------------------
    def resize(self, w, h):
        self.w, self.h = float(w), float(h)
        if self.player:
            m = self.PLAYER_MARGIN
            self.player.x = clamp(self.player.x, m, self.w - m)
            self.player.y = clamp(self.player.y, m, self.h - m)

    def reset(self):
        self.score = 0
        self.difficulty = 1.0
        self.spawn_timer = 0.0
        self.orb_timer = 0.0
        self.time = 0.0
        self.game_over = False
        self.enemies, self.orbs, self.particles = [], [], []
        self.player = Player(self.w / 2, self.h / 2)
        self.player.invincible = 2.0       # short grace period
        for _ in range(3):
            self.orbs.append(self._new_orb())

    # ------------------------------------------------------------------
    def _new_orb(self):
        lo, hi = self.ORB_TOP, self.h - self.ORB_BOTTOM
        if hi <= lo:
            lo, hi = 40.0, max(41.0, self.h - 40.0)
        return Orb(self.rng.uniform(40, self.w - 40),
                   self.rng.uniform(lo, hi),
                   self.rng.uniform(0, 6.28))

    def _new_enemy(self):
        r = self.rng
        size = r.randint(14, 28)
        sp = r.uniform(2, 4) * self.difficulty * WORLD_K
        side = r.choice(("top", "bottom", "left", "right"))
        if side == "top":
            return Enemy(r.uniform(0, self.w), -size, 0, sp, size)
        if side == "bottom":
            return Enemy(r.uniform(0, self.w), self.h + size, 0, -sp, size)
        if side == "left":
            return Enemy(-size, r.uniform(0, self.h), sp, 0, size)
        return Enemy(self.w + size, r.uniform(0, self.h), -sp, 0, size)

    def _burst(self, x, y, color, n):
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, math.tau)
            s = r.uniform(1, 4) * WORLD_K
            self.particles.append(
                Particle(x, y, math.cos(a) * s, math.sin(a) * s,
                         r.uniform(0.4, 0.9), color))
        extra = len(self.particles) - self.MAX_PARTICLES
        if extra > 0:
            del self.particles[:extra]

    # ------------------------------------------------------------------
    def _update_particles(self, dt):
        f = dt * 60.0
        alive = []
        for p in self.particles:
            p.x += p.vx * f
            p.y += p.vy * f
            p.life -= dt
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def update(self, dt, move_x=0.0, move_y=0.0, boost=False):
        """Advance the simulation.  Returns a list of event names
        ("orb", "death") that happened during this step."""
        events = []
        self.time += dt
        self._update_particles(dt)
        if self.game_over:
            return events

        f = dt * 60.0
        self.difficulty = 1.0 + (self.score // 20) * 0.15

        # --- spawning (same curves as the original) --------------------
        self.spawn_timer += dt
        interval = clamp(0.8 - self.score / 200.0, 0.25, 0.8)
        if self.spawn_timer >= interval:
            self.spawn_timer = 0.0
            self.enemies.append(self._new_enemy())

        self.orb_timer += dt
        if self.orb_timer >= 3.0 and len(self.orbs) < 5:
            self.orb_timer = 0.0
            self.orbs.append(self._new_orb())

        # --- player ----------------------------------------------------
        p = self.player
        ax, ay = move_x, move_y
        mag = math.hypot(ax, ay)
        if mag > 1.0:
            ax, ay = ax / mag, ay / mag
        accel = self.PLAYER_SPEED * (self.BOOST if boost else 1.0)
        p.vx += ax * accel * f * 0.12
        p.vy += ay * accel * f * 0.12
        damp = 0.92 ** f
        p.vx *= damp
        p.vy *= damp
        spd = math.hypot(p.vx, p.vy)
        if spd > self.MAX_SPEED:
            p.vx *= self.MAX_SPEED / spd
            p.vy *= self.MAX_SPEED / spd
        m = self.PLAYER_MARGIN
        p.x = clamp(p.x + p.vx * f * WORLD_K, m, self.w - m)
        p.y = clamp(p.y + p.vy * f * WORLD_K, m, self.h - m)
        if p.invincible > 0:
            p.invincible -= dt

        # --- enemies ---------------------------------------------------
        kept = []
        for e in self.enemies:
            e.x += e.vx * f
            e.y += e.vy * f
            if -60 <= e.x <= self.w + 60 and -60 <= e.y <= self.h + 60:
                kept.append(e)
        self.enemies = kept

        # --- player vs enemy -------------------------------------------
        if p.invincible <= 0:
            for e in self.enemies:
                if math.hypot(e.x - p.x, e.y - p.y) < self.PLAYER_HIT_R + e.hit_r:
                    self._burst(p.x, p.y, RED, 40)
                    p.alive = False
                    self.game_over = True
                    events.append("death")
                    return events

        # --- player vs orb ---------------------------------------------
        remaining = []
        for o in self.orbs:
            if math.hypot(o.x - p.x, o.y - p.y) < self.PICKUP_R + o.r:
                self.score += 5
                self._burst(o.x, o.y, NEON_YELLOW, 16)
                p.invincible = max(p.invincible, 0.3)
                events.append("orb")
            else:
                remaining.append(o)
        self.orbs = remaining
        return events
