import unittest
import numpy as np
import run_early_pilot as early
import run_tail_pilot as previous


class EarlyChecks(unittest.TestCase):
    def test_shrink_at_eight_and_stay_small_at_nine(self):
        self.assertEqual([early.next_step(n) for n in (0, 7, 8, 9)], [128, 128, 32, 32])
        labels = np.zeros(300, dtype=bool)
        labels[:8], labels[140:142] = True, True
        a = early.run_policy(labels, 'fixed128_tail8', .01, budget=300)
        b = early.run_policy(labels, 'fixed128_tail32', .01, budget=300)
        self.assertEqual((a['checked'], b['checked']), (160, 256))

    def test_boundary_dense_empty_insufficient(self):
        for count in (0, 9, 257):
            labels = np.zeros(257, dtype=bool)
            labels[:count] = True
            self.assertEqual(early.run_policy(labels, 'fixed128_tail8', count/257, budget=257)['returned'], min(count, 10))
        labels = np.zeros(257, dtype=bool)
        labels[:9], labels[-1] = True, True
        for budget in (256, 257):
            self.assertEqual(early.run_policy(labels, 'fixed128_tail8', .04, budget=budget)['full'], int(budget == 257))

    def test_random_paired_and_baselines_unchanged(self):
        rng = np.random.default_rng(8089)
        for _ in range(100):
            labels = rng.random(1000) < rng.uniform(.001, .15)
            p = float(labels.mean())
            for method in early.METHODS:
                r = early.run_policy(labels, method, p, budget=777)
                self.assertEqual(r['full'], int(labels[:777].sum() >= 10))
                self.assertLessEqual(r['checked'], 777)
                if method != 'fixed128_tail8':
                    self.assertEqual(r, previous.run_policy(labels, method, p, budget=777))


if __name__ == '__main__':
    unittest.main()
