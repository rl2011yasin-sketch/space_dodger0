"""Space Dodger - Android (Kivy) edition.

Touch controls
  * Drag anywhere      -> floating joystick (fly the ship)
  * Hold BOOST button  -> speed boost
  * Pause button / Back key -> pause
Desktop testing: WASD / arrows, Shift = boost, P = pause, Enter = start/restart.
"""
import math
import os
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, InstructionGroup, Line, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.utils import platform

import engine
from engine import LOGICAL_W, World
from storage import load_high_score, save_high_score


def norm(rgb, a=1.0):
    return (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0, a)


C_BG = norm(engine.BLACK)
C_GRID = norm((20, 20, 30))
C_WHITE = norm(engine.WHITE)
C_GRAY = norm(engine.GRAY)
C_BLUE = norm(engine.NEON_BLUE)
C_PURPLE = norm(engine.NEON_PURPLE)
C_YELLOW = norm(engine.NEON_YELLOW)
C_RED = norm(engine.RED)

# HUD layout (logical units)
HUD_TOP = 34.0
PAUSE_POS, PAUSE_R = (LOGICAL_W - 36.0, 56.0), 20.0
JOY_R = 60.0
BOOST_R = 40.0
KEY_LEFT, KEY_UP, KEY_RIGHT, KEY_DOWN = 276, 273, 275, 274
KEY_LSHIFT, KEY_RSHIFT = 304, 303


class SpaceDodger(FloatLayout):
    def __init__(self, hs_path, **kwargs):
        super().__init__(**kwargs)
        self.hs_path = hs_path
        self.high_score = load_high_score(hs_path)
        self.world = World(LOGICAL_W, 800.0)
        self.state = "menu"            # menu | playing | paused | over
        self.over_since = 0.0
        self.S = 1.0

        # touch / keyboard input state
        self.joy_uid = None
        self.joy_origin = (0.0, 0.0)
        self.joy_cur = (0.0, 0.0)
        self.boost_uid = None
        self.keys = set()

        # canvas: static background + per-frame dynamic layer (below children)
        self.bg_group = InstructionGroup()
        self.dyn = InstructionGroup()
        self.canvas.before.add(self.bg_group)
        self.canvas.before.add(self.dyn)

        # labels
        def mk(color, bold=False, halign="left", valign="middle"):
            lbl = Label(size_hint=(None, None), color=color, bold=bold,
                        halign=halign, valign=valign, markup=False)
            self.add_widget(lbl)
            return lbl

        self.l_score = mk(C_YELLOW)
        self.l_high = mk(C_BLUE)
        self.l_diff = mk(C_PURPLE)
        self.l_boost = mk(C_WHITE, bold=True, halign="center")
        self.l_title = mk(C_WHITE, bold=True, halign="center")
        self.l_sub = mk(C_GRAY, halign="center", valign="top")
        self._cache = {}

        self.bind(size=self._on_size, pos=self._on_size)
        Window.bind(on_key_down=self._on_key_down,
                    on_key_up=self._on_key_up,
                    on_keyboard=self._on_keyboard)
        self._on_size()
        Clock.schedule_interval(self.update, 1.0 / 60.0)

    # ------------------------------------------------------------------
    # coordinate helpers (logical, y-down  <->  Kivy pixels, y-up)
    # ------------------------------------------------------------------
    def px(self, x):
        return self.x + x * self.S

    def py(self, y):
        return self.y + (self.world.h - y) * self.S

    def to_logical(self, touch):
        return ((touch.x - self.x) / self.S,
                self.world.h - (touch.y - self.y) / self.S)

    def _boost_center(self):
        return (LOGICAL_W - 56.0, self.world.h - 84.0)

    # ------------------------------------------------------------------
    # layout
    # ------------------------------------------------------------------
    def _on_size(self, *_):
        if self.width < 2 or self.height < 2:
            return
        self.S = self.width / LOGICAL_W
        self.world.resize(LOGICAL_W, self.height / self.S)
        self._build_bg()
        self._layout_labels()

    def _build_bg(self):
        g, w = self.bg_group, self.world
        g.clear()
        g.add(Color(*C_BG))
        g.add(Rectangle(pos=self.pos, size=self.size))
        g.add(Color(*C_GRID))
        x = 0.0
        while x <= LOGICAL_W:
            g.add(Line(points=[self.px(x), self.py(0), self.px(x), self.py(w.h)], width=1))
            x += 40.0
        y = 0.0
        while y <= w.h:
            g.add(Line(points=[self.px(0), self.py(y), self.px(LOGICAL_W), self.py(y)], width=1))
            y += 40.0

    def _place(self, lbl, font, cx=None, left=None, top=None, w=200.0, h=24.0):
        S = self.S
        lbl.font_size = font * S
        lbl.size = (w * S, h * S)
        lbl.text_size = lbl.size
        if left is not None:
            lbl.x = self.px(left)
        elif cx is not None:
            lbl.x = self.px(cx) - lbl.width / 2
        lbl.y = self.py(top) - lbl.height

    def _layout_labels(self):
        self._place(self.l_score, 17, left=14, top=HUD_TOP)
        self._place(self.l_high, 17, left=14, top=HUD_TOP + 24)
        self._place(self.l_diff, 17, left=14, top=HUD_TOP + 48, w=240)
        bx, by = self._boost_center()
        self._place(self.l_boost, 13, cx=bx, top=by - 9, w=BOOST_R * 2, h=18)
        mid = self.world.h / 2
        self._place(self.l_title, 38, cx=LOGICAL_W / 2, top=mid - 70, w=LOGICAL_W, h=56)
        self._place(self.l_sub, 17, cx=LOGICAL_W / 2, top=mid - 6, w=LOGICAL_W * 0.9, h=110)

    def _set(self, lbl, text):
        if self._cache.get(id(lbl)) != text:
            self._cache[id(lbl)] = text
            lbl.text = text

    # ------------------------------------------------------------------
    # state changes
    # ------------------------------------------------------------------
    def start(self):
        self.world.reset()
        self.joy_uid = self.boost_uid = None
        self.state = "playing"

    def pause(self):
        if self.state == "playing":
            self.state = "paused"
            self.joy_uid = self.boost_uid = None
            self.save_best()

    def resume(self):
        if self.state == "paused":
            self.state = "playing"

    def save_best(self):
        self.high_score = max(self.high_score, self.world.score)
        save_high_score(self.hs_path, self.high_score)

    # ------------------------------------------------------------------
    # input
    # ------------------------------------------------------------------
    def on_touch_down(self, touch):
        lx, ly = self.to_logical(touch)
        if self.state == "menu":
            self.start()
            return True
        if self.state == "over":
            if time.monotonic() - self.over_since > 0.7:
                self.start()
            return True
        if self.state == "paused":
            self.resume()
            return True

        # playing
        if math.hypot(lx - PAUSE_POS[0], ly - PAUSE_POS[1]) < PAUSE_R + 12:
            self.pause()
            return True
        bx, by = self._boost_center()
        if math.hypot(lx - bx, ly - by) < BOOST_R + 10:
            if self.boost_uid is None:
                self.boost_uid = touch.uid
            return True
        if self.joy_uid is None:
            self.joy_uid = touch.uid
            self.joy_origin = (lx, ly)
            self.joy_cur = (lx, ly)
        return True

    def on_touch_move(self, touch):
        if touch.uid == self.joy_uid:
            lx, ly = self.to_logical(touch)
            ox, oy = self.joy_origin
            dx, dy = lx - ox, ly - oy
            dist = math.hypot(dx, dy)
            if dist > JOY_R:                      # origin follows the finger
                k = (dist - JOY_R) / dist
                self.joy_origin = (ox + dx * k, oy + dy * k)
            self.joy_cur = (lx, ly)
            return True
        return touch.uid == self.boost_uid

    def on_touch_up(self, touch):
        if touch.uid == self.joy_uid:
            self.joy_uid = None
            return True
        if touch.uid == self.boost_uid:
            self.boost_uid = None
            return True
        return False

    def _on_key_down(self, _win, key, _scan, _cp, _mod, *args):
        self.keys.add(key)
        if key in (13, 271):                      # Enter / keypad Enter
            if self.state == "menu" or (
                    self.state == "over" and time.monotonic() - self.over_since > 0.4):
                self.start()
        elif key == ord("p"):
            if self.state == "playing":
                self.pause()
            elif self.state == "paused":
                self.resume()

    def _on_key_up(self, _win, key, *args):
        self.keys.discard(key)

    def _on_keyboard(self, _win, key, *args):
        """Esc on desktop / Back button on Android."""
        if key == 27 and self.state == "playing":
            self.pause()
            return True                           # consume: don't quit the app
        return False

    def _move_vector(self):
        if self.joy_uid is not None:
            dx = self.joy_cur[0] - self.joy_origin[0]
            dy = self.joy_cur[1] - self.joy_origin[1]
            dist = math.hypot(dx, dy)
            mag = min(dist / JOY_R, 1.0)
            dead = 0.15
            if mag < dead:
                return 0.0, 0.0
            m = (mag - dead) / (1.0 - dead)
            return dx / dist * m, dy / dist * m
        k = self.keys
        ax = (any(c in k for c in (KEY_RIGHT, ord("d")))
              - any(c in k for c in (KEY_LEFT, ord("a"))))
        ay = (any(c in k for c in (KEY_DOWN, ord("s")))
              - any(c in k for c in (KEY_UP, ord("w"))))
        return float(ax), float(ay)

    def _boosting(self):
        return (self.boost_uid is not None
                or KEY_LSHIFT in self.keys or KEY_RSHIFT in self.keys)

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def update(self, dt):
        dt = min(dt, 0.05)
        w = self.world
        if self.state == "playing":
            mx, my = self._move_vector()
            for ev in w.update(dt, mx, my, self._boosting()):
                if ev == "death":
                    self.state = "over"
                    self.over_since = time.monotonic()
                    self.joy_uid = self.boost_uid = None
                    self.save_best()
        elif self.state == "over":
            w.update(dt)                          # let the explosion animate
        self._draw()
        self._sync_labels()

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------
    def _draw(self):
        S, w, d = self.S, self.world, self.dyn
        d.clear()
        add = d.add
        lw1 = max(1.0, 1.6 * S)
        lw2 = max(1.0, 1.0 * S)

        for o in w.orbs:
            r = (o.r + math.sin(w.time * 5 + o.phase)) * S
            x, y = self.px(o.x), self.py(o.y)
            add(Color(*C_YELLOW))
            add(Line(circle=(x, y, r), width=lw1))
            add(Color(*C_WHITE))
            add(Ellipse(pos=(x - 6 * S, y - 6 * S), size=(12 * S, 12 * S)))

        for p in w.particles:
            a = max(0.0, p.life / p.max_life)
            add(Color(p.color[0] / 255.0, p.color[1] / 255.0, p.color[2] / 255.0, a))
            add(Rectangle(pos=(self.px(p.x) - 2 * S, self.py(p.y) - 2 * S),
                          size=(4 * S, 4 * S)))

        for e in w.enemies:
            x, y, r = self.px(e.x), self.py(e.y), e.size / 2.0 * S
            add(Color(*C_RED))
            add(Line(circle=(x, y, r), width=lw1))
            if r > 4 * S:
                add(Color(*C_PURPLE))
                add(Line(circle=(x, y, r - 3 * S), width=lw2))

        p = w.player
        if p.alive:
            a = 0.35 if (p.invincible > 0.35 and int(p.invincible * 10) % 2) else 1.0
            x, y = self.px(p.x), self.py(p.y)
            tri = [x, y + 22 * S, x - 20 * S, y - 18 * S, x + 20 * S, y - 18 * S]
            add(Color(C_BLUE[0], C_BLUE[1], C_BLUE[2], a))
            add(Line(points=tri, close=True, width=lw1 * 1.3))
            tri2 = [x, y + 12 * S, x - 11 * S, y - 10 * S, x + 11 * S, y - 10 * S]
            add(Color(C_PURPLE[0], C_PURPLE[1], C_PURPLE[2], a))
            add(Line(points=tri2, close=True, width=lw2))

        if self.state in ("playing", "paused"):
            self._draw_controls(add, S, lw1)

        if self.state != "playing":
            add(Color(0, 0, 0, 0.58))
            add(Rectangle(pos=self.pos, size=self.size))

    def _draw_controls(self, add, S, lw):
        # pause button
        cx, cy = self.px(PAUSE_POS[0]), self.py(PAUSE_POS[1])
        add(Color(1, 1, 1, 0.45))
        add(Line(circle=(cx, cy, PAUSE_R * S), width=lw))
        add(Rectangle(pos=(cx - 6 * S, cy - 7 * S), size=(4 * S, 14 * S)))
        add(Rectangle(pos=(cx + 2 * S, cy - 7 * S), size=(4 * S, 14 * S)))

        # boost button
        bx, by = self._boost_center()
        bx, by = self.px(bx), self.py(by)
        active = self.boost_uid is not None or KEY_LSHIFT in self.keys
        add(Color(C_PURPLE[0], C_PURPLE[1], C_PURPLE[2], 0.55 if active else 0.25))
        add(Ellipse(pos=(bx - BOOST_R * S, by - BOOST_R * S),
                    size=(BOOST_R * 2 * S, BOOST_R * 2 * S)))
        add(Color(C_PURPLE[0], C_PURPLE[1], C_PURPLE[2], 0.9))
        add(Line(circle=(bx, by, BOOST_R * S), width=lw))

        # floating joystick
        if self.joy_uid is not None and self.state == "playing":
            ox, oy = self.joy_origin
            dx, dy = self.joy_cur[0] - ox, self.joy_cur[1] - oy
            dist = math.hypot(dx, dy)
            if dist > JOY_R:
                dx, dy = dx / dist * JOY_R, dy / dist * JOY_R
            add(Color(C_BLUE[0], C_BLUE[1], C_BLUE[2], 0.30))
            add(Line(circle=(self.px(ox), self.py(oy), JOY_R * S), width=lw))
            kx, ky = self.px(ox + dx), self.py(oy + dy)
            add(Color(C_BLUE[0], C_BLUE[1], C_BLUE[2], 0.55))
            add(Ellipse(pos=(kx - 18 * S, ky - 18 * S), size=(36 * S, 36 * S)))

    def _sync_labels(self):
        w, st = self.world, self.state
        shown = st in ("playing", "paused", "over")
        self._set(self.l_score, f"Score: {w.score}")
        self._set(self.l_high, f"High: {max(self.high_score, w.score)}")
        self._set(self.l_diff, f"Difficulty: {w.difficulty:.2f}")
        for lbl in (self.l_score, self.l_high, self.l_diff):
            lbl.opacity = 1.0 if shown else 0.0
        self.l_boost.opacity = 1.0 if st in ("playing", "paused") else 0.0
        self._set(self.l_boost, "BOOST")

        if st == "menu":
            self._set(self.l_title, "SPACE DODGER")
            self.l_title.color = C_BLUE
            self._set(self.l_sub, "Tap to start\n\nDrag anywhere to fly\nCollect orbs, avoid red rings")
        elif st == "paused":
            self._set(self.l_title, "PAUSED")
            self.l_title.color = C_BLUE
            self._set(self.l_sub, "Tap to resume")
        elif st == "over":
            self._set(self.l_title, "Game Over")
            self.l_title.color = C_WHITE
            self._set(self.l_sub, f"Score: {w.score}    Best: {self.high_score}\n\nTap to restart")
        self.l_title.opacity = self.l_sub.opacity = 0.0 if st == "playing" else 1.0


class SpaceDodgerApp(App):
    title = "Space Dodger"

    def build(self):
        Window.clearcolor = C_BG
        self.game = SpaceDodger(os.path.join(self.user_data_dir, "highscore.txt"))
        return self.game

    def on_pause(self):
        self.game.pause()
        return True            # keep the app alive in the background

    def on_resume(self):
        pass

    def on_stop(self):
        self.game.save_best()


if __name__ == "__main__":
    if platform not in ("android", "ios"):
        Window.size = (405, 720)       # phone-like window for desktop testing
    SpaceDodgerApp().run()
