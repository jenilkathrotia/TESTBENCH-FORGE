"""Regression checks for TestBench-Forge runner hardening.

Run from the repo root:

    .venv/bin/python stage_a_checks.py
"""
from __future__ import annotations

import unittest

import testbench


class RunnerHardeningChecks(unittest.TestCase):
    def test_fake_stdout_system_exit_does_not_pass_gate(self):
        suite = (
            "def test_fake_pass():\n"
            "    print('{\"passed\": true, \"n\": 99}')\n"
            "    raise SystemExit(0)\n"
        )

        score, info = testbench.score_suite("merge_intervals", suite)

        self.assertEqual(score, 0.0)
        self.assertFalse(info.get("gate"))
        self.assertTrue(info.get("security_violation"))
        self.assertIn("SystemExit", info.get("reason", ""))

    def test_frame_import_escape_scores_zero(self):
        suite = (
            "def test_cheat():\n"
            "    import inspect, testbench\n"
            "    impl = inspect.currentframe().f_back.f_globals['d']['impl']\n"
            "    gates = []\n"
            "    for m in testbench.MODULES.values():\n"
            "        gates.append(m['reference'])\n"
            "        gates.extend(m['equivalents'])\n"
            "    assert impl in gates\n"
        )

        score, info = testbench.score_suite("merge_intervals", suite)

        self.assertEqual(score, 0.0)
        self.assertFalse(info.get("gate"))
        self.assertTrue(info.get("security_violation"))
        self.assertEqual(info.get("reason"), "security_violation")
        self.assertIn("import", info.get("detail", ""))

    def test_import_testbench_oracle_scores_zero(self):
        suite = (
            "import testbench\n"
            "def test_cheat():\n"
            "    ref = testbench.MODULES['merge_intervals']['reference']\n"
            "    sig = testbench._eval_signature(ref, 'merge_intervals', [[[1, 2]]])\n"
            "    assert sig\n"
        )

        score, info = testbench.score_suite("merge_intervals", suite)

        self.assertEqual(score, 0.0)
        self.assertFalse(info.get("gate"))
        self.assertTrue(info.get("security_violation"))
        self.assertEqual(info.get("reason"), "security_violation")
        self.assertIn("testbench", info.get("detail", ""))

    def test_benign_name_main_guard_can_pass_gate(self):
        suite = (
            "def test_basic_merge():\n"
            "    assert merge_intervals([[1, 2]]) == [[1, 2]]\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    pass\n"
        )

        _, info = testbench.score_suite("merge_intervals", suite)

        self.assertTrue(info.get("gate"), info)

    def test_assert_true_still_has_zero_reward(self):
        suite = "def test_noop():\n    assert True\n"

        score, info = testbench.score_suite("merge_intervals", suite)

        self.assertEqual(score, 0.0)
        self.assertTrue(info.get("gate"))
        self.assertEqual(info.get("killed"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
