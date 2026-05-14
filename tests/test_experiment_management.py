from __future__ import annotations

import unittest

from auto_rl.experiment_management import confidence_score, median_absolute_deviation


class ExperimentManagementTests(unittest.TestCase):
    def test_mad_returns_zero_for_short_history(self) -> None:
        self.assertEqual(median_absolute_deviation([1.0, 2.0]), 0.0)

    def test_confidence_score_uses_noise_floor(self) -> None:
        self.assertAlmostEqual(median_absolute_deviation([1.0, 1.2, 1.1, 4.0]), 0.1)
        self.assertAlmostEqual(confidence_score(0.5, 0.1), 5.0)
        self.assertGreater(confidence_score(0.5, 0.0), 1.0)
        self.assertEqual(confidence_score(0.0, 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
