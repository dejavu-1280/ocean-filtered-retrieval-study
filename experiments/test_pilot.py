"""Correctness checks for the experiment's budget and fairness claims."""
import unittest
import numpy as np
from scipy.stats import binom
from run_pilot import METHODS, ITERATIVE, run_policy, iid_target


class PolicyChecks(unittest.TestCase):
    def test_all_zero(self):
        labels = np.zeros(257, dtype=bool)
        for method in METHODS:
            r = run_policy(labels, method, 0, budget=257)
            self.assertEqual(r['full'], 0)
            self.assertEqual(r['returned'], 0)
            self.assertLessEqual(r['checked'], 257)

    def test_all_one(self):
        labels = np.ones(257, dtype=bool)
        for method in METHODS:
            r = run_policy(labels, method, 1, budget=257)
            self.assertEqual(r['full'], 1)
            self.assertEqual(r['returned'], 10)
            self.assertLessEqual(r['checked'], 257)

    def test_tenth_match_at_budget_included(self):
        labels = np.zeros(257, dtype=bool)
        labels[:9], labels[-1] = True, True
        for method in ITERATIVE:
            self.assertEqual(run_policy(labels, method, .04, budget=257)['full'], 1)
            self.assertEqual(run_policy(labels, method, .04, budget=256)['full'], 0)

    def test_global_insufficiency(self):
        labels = np.zeros(300, dtype=bool)
        labels[:9] = True
        for method in METHODS:
            r = run_policy(labels, method, .03, budget=300)
            self.assertEqual(r['full'], 0)
            self.assertEqual(r['returned'], 9)

    def test_binomial_threshold_is_minimal(self):
        n = iid_target(10, .01, 5000)
        self.assertEqual(n, 1568)
        self.assertGreaterEqual(binom.sf(9, n, .01), .95)
        self.assertLess(binom.sf(9, n-1, .01), .95)

    def test_paired_fullness_and_no_budget_overrun(self):
        rng = np.random.default_rng(123)
        for _ in range(100):
            labels = rng.random(1000) < rng.uniform(.001, .2)
            expected = int(labels[:777].sum() >= 10)
            for method in ITERATIVE:
                r = run_policy(labels, method, float(labels.mean()), budget=777)
                self.assertEqual(r['full'], expected)
                self.assertLessEqual(r['checked'], 777)
                self.assertEqual(r['returned'], min(10, int(labels[:r['checked']].sum())))

    def test_reject_short_sequence(self):
        with self.assertRaises(ValueError):
            run_policy(np.ones(3, dtype=bool), 'adaptive', 1, budget=4)


if __name__ == '__main__':
    unittest.main()
