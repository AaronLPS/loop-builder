import sys, pathlib, json, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts" / "feedback"))
import dedupe  # noqa: E402

ISSUES = [
    {"number": 1, "title": "verifier crashes on empty state file"},
    {"number": 2, "title": "scheduler ignores dynamic interval"},
    {"number": 3, "title": "typo in README install section"},
]


class DedupeTest(unittest.TestCase):
    def test_match_ranks_overlapping_issue_first(self):
        res = dedupe.match("verifier crash when state file empty", ISSUES)
        self.assertTrue(res)
        self.assertEqual(res[0]["number"], 1)

    def test_no_match_below_threshold(self):
        self.assertEqual(dedupe.match("billing dashboard colors", ISSUES), [])

    def test_fetch_uses_gh_when_available(self):
        def runner(cmd):
            self.assertEqual(cmd[0], "gh")
            return json.dumps([{"number": 5, "title": "from gh"}])

        out = dedupe.fetch_open_issues("AaronLPS/loop-builder", runner=runner)
        self.assertEqual(out, [{"number": 5, "title": "from gh"}])

    def test_fetch_falls_back_to_curl_and_drops_prs(self):
        def runner(cmd):
            if cmd[0] == "gh":
                raise RuntimeError("no gh")
            # REST shape; entries carrying a pull_request key are PRs, not issues
            return json.dumps([
                {"number": 9, "title": "real issue"},
                {"number": 10, "title": "a PR", "pull_request": {"url": "x"}},
            ])

        out = dedupe.fetch_open_issues("AaronLPS/loop-builder", runner=runner)
        self.assertEqual(out, [{"number": 9, "title": "real issue"}])

    def test_fetch_returns_empty_on_total_failure(self):
        def boom(cmd):
            raise RuntimeError("offline")

        self.assertEqual(dedupe.fetch_open_issues("AaronLPS/loop-builder", runner=boom), [])


if __name__ == "__main__":
    unittest.main()
