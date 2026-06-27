import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "distiller"))
import verify_scan as vs  # noqa: E402


def _cand(status="surfaced", count=3, blocks=("discovery", "action", "verify", "vcs"), sig="s"):
    return {"id": "x", "signature": sig, "status": status,
            "count": count, "blocks": list(blocks)}


class VerifyScanTest(unittest.TestCase):
    def test_passing_candidate_ok(self):
        ok, problems = vs.verify([_cand()])
        self.assertTrue(ok)
        self.assertEqual(problems, [])

    def test_too_few_recurrences_fails(self):
        ok, problems = vs.verify([_cand(count=2)])   # < DEFAULT_N (3)
        self.assertFalse(ok)
        self.assertTrue(any("recurrence" in p for p in problems))

    def test_too_few_blocks_fails(self):
        ok, problems = vs.verify([_cand(blocks=("discovery", "action"))])  # < DEFAULT_K (4)
        self.assertFalse(ok)
        self.assertTrue(any("block" in p for p in problems))

    def test_three_blocks_without_vcs_passes(self):
        ok, problems = vs.verify([_cand(blocks=("discovery", "action", "verify"))])
        self.assertTrue(ok)            # vcs optional: 3 core blocks clear K=3
        self.assertEqual(problems, [])

    def test_built_candidate_not_checked(self):
        ok, _ = vs.verify([_cand(status="built", count=1, blocks=())])
        self.assertTrue(ok)            # terminal 'built' skipped, like 'dismissed'

    def test_terminal_candidates_are_not_checked(self):
        ok, _ = vs.verify([_cand(status="dismissed", count=1, blocks=())])
        self.assertTrue(ok)                          # dismissed/built skipped

    def test_duplicate_active_signatures_flagged(self):
        ok, problems = vs.verify([_cand(sig="dup"), _cand(sig="dup")])
        self.assertFalse(ok)
        self.assertTrue(any("dup" in p.lower() or "duplicate" in p.lower() for p in problems))
