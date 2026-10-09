import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine import World, Enemy, Orb, LOGICAL_W  # noqa: E402


class EngineTests(unittest.TestCase):
    def test_idle_player_eventually_dies(self):
        w = World(LOGICAL_W, 800, seed=1)
        events = []
        for _ in range(60 * 300):
            events += w.update(1 / 60)
            if w.game_over:
                break
        self.assertTrue(w.game_over)
        self.assertIn("death", events)
        self.assertGreater(len(w.particles), 0)

    def test_orb_pickup_scores_and_grants_invincibility(self):
        w = World(LOGICAL_W, 800, seed=2)
        w.player.invincible = 0
        w.orbs = [Orb(w.player.x, w.player.y)]
        w.enemies = []
        ev = w.update(1 / 60)
        self.assertIn("orb", ev)
        self.assertEqual(w.score, 5)
        self.assertGreaterEqual(w.player.invincible, 0.25)

    def test_enemy_hit_kills_when_not_invincible(self):
        w = World(LOGICAL_W, 800, seed=3)
        w.player.invincible = 0
        w.orbs = []
        w.enemies = [Enemy(w.player.x, w.player.y, 0, 0, 20)]
        self.assertIn("death", w.update(1 / 60))
        self.assertFalse(w.player.alive)

    def test_grace_period_protects_player(self):
        w = World(LOGICAL_W, 800, seed=4)
        w.orbs = []
        w.enemies = [Enemy(w.player.x, w.player.y, 0, 0, 20)]
        self.assertNotIn("death", w.update(1 / 60))

    def test_invariants_with_random_input(self):
        rng = random.Random(5)
        w = World(LOGICAL_W, 900, seed=6)
        for _ in range(60 * 120):
            if w.game_over:
                w.reset()
            w.update(1 / 60, rng.uniform(-1, 1), rng.uniform(-1, 1), rng.random() < 0.3)
            p = w.player
            self.assertTrue(22 - 1e-6 <= p.x <= LOGICAL_W - 22 + 1e-6)
            self.assertTrue(22 - 1e-6 <= p.y <= w.h - 22 + 1e-6)
            self.assertLessEqual(len(w.particles), World.MAX_PARTICLES)
            self.assertLess(len(w.enemies), 120)
            self.assertLessEqual(len(w.orbs), 5)

    def test_speed_is_framerate_independent(self):
        def run(dt):
            w = World(LOGICAL_W, 800, seed=7)
            w.orbs, w.enemies = [], []
            w.spawn_timer = -1e9
            x0 = w.player.x
            for _ in range(int(0.5 / dt)):
                w.update(dt, 1.0, 0.0, False)
            return w.player.x - x0
        a, b = run(1 / 30), run(1 / 120)
        self.assertAlmostEqual(a, b, delta=max(a, b) * 0.1)

    def test_difficulty_and_reset(self):
        w = World(LOGICAL_W, 800, seed=8)
        w.score = 100
        w.update(1 / 60)
        self.assertAlmostEqual(w.difficulty, 1.75)
        w.reset()
        self.assertEqual((w.score, w.difficulty, w.game_over), (0, 1.0, False))
        self.assertEqual(len(w.orbs), 3)

    def test_resize_keeps_player_inside(self):
        w = World(LOGICAL_W, 900, seed=9)
        w.player.y = 880
        w.resize(LOGICAL_W, 600)
        self.assertLessEqual(w.player.y, 600 - 22)


if __name__ == "__main__":
    unittest.main()
