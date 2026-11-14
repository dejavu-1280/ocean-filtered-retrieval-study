"""Boundary and causal-isolation checks for tail batch changes."""
import unittest
import numpy as np
import run_pilot as base
import run_tail_pilot as tail


class TailChecks(unittest.TestCase):
    def test_shrink_only_after_nine(self):
        for method in ('fixed128_tail32', 'adaptive_tail32'):
            original = 'fixed_batch' if method.startswith('fixed') else 'adaptive'
            for hits in (0, 8, 9):
                observed = np.zeros(128, dtype=bool)
                observed[:hits] = True
                original_target = base.next_target(original, observed, .01, 10, 5000, 128)
                target = tail.next_target(method, observed, .01, 10, 5000, 128)
                self.assertEqual(target, min(original_target, 160) if hits == 9 else original_target)

    def test_tail_saves_96_when_tenth_in_small_next_batch(self):
        labels = np.zeros(300, dtype=bool)
        labels[:9], labels[159] = True, True
        a = tail.run_policy(labels, 'fixed128', .01, budget=300)
        b = tail.run_policy(labels, 'fixed128_tail32', .01, budget=300)
        self.assertEqual((a['checked'], b['checked'], b['calls']), (256, 160, 2))

    def test_no_early_abandonment_and_exact_budget_boundary(self):
        labels = np.zeros(257, dtype=bool)
        labels[:9], labels[-1] = True, True
        for method in tail.METHODS:
            self.assertEqual(tail.run_policy(labels, method, .04, budget=257)['full'], 1)
            self.assertEqual(tail.run_policy(labels, method, .04, budget=256)['full'], 0)

    def test_empty_dense_and_whole_corpus_shortage(self):
        for count in (0, 9, 257):
            labels = np.zeros(257, dtype=bool)
            labels[:count] = True
            for method in tail.METHODS:
                r = tail.run_policy(labels, method, count/257, budget=257)
                self.assertEqual(r['returned'], min(count, 10))
                self.assertLessEqual(r['checked'], 257)

    def test_random_paired_fullness_and_unchanged_baselines(self):
        rng = np.random.default_rng(20261114)
        for _ in range(100):
            labels = rng.random(900) < rng.uniform(.001, .15)
            p = float(labels.mean())
            for method in tail.METHODS:
                r = tail.run_policy(labels, method, p, budget=777)
                self.assertEqual(r['full'], int(labels[:777].sum() >= 10))
                self.assertEqual(r['returned'], min(10, int(labels[:r['checked']].sum())))
                self.assertLessEqual(r['checked'], 777)
            for method, old in [('fixed128', 'fixed_batch'), ('doubling', 'doubling'), ('adaptive_v01', 'adaptive')]:
                r = tail.run_policy(labels, method, p, budget=777)
                expected = base.run_policy(labels, old, p, budget=777)
                self.assertEqual({key: r[key] for key in expected}, expected)


if __name__ == '__main__':
    unittest.main()
