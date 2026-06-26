import sys, pathlib, urllib.parse, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "feedback"))
import file_issue  # noqa: E402

REPO = "AaronLPS/loop-builder"


class FileIssueTest(unittest.TestCase):
    def test_build_url_encodes_params(self):
        url = file_issue.build_url(REPO, "bug: x&y", "body with spaces", ["bug", "via-feedback-tool"])
        self.assertTrue(url.startswith(f"https://github.com/{REPO}/issues/new?"))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        self.assertEqual(q["title"], ["bug: x&y"])
        self.assertEqual(q["labels"], ["bug,via-feedback-tool"])

    def test_build_gh_command_shape(self):
        cmd = file_issue.build_gh_command(REPO, "t", "/tmp/body.md", ["bug"])
        self.assertEqual(cmd[:4], ["gh", "issue", "create", "--repo"])
        self.assertIn("--body-file", cmd)
        self.assertIn("--label", cmd)

    def test_create_dry_run_gh_path(self):
        out = file_issue.create(REPO, "t", "b", ["bug"], dry_run=True, gh_check=lambda: True)
        self.assertEqual(out["method"], "gh")
        self.assertIsNone(out["issue"])
        self.assertEqual(out["command"][:3], ["gh", "issue", "create"])

    def test_create_dry_run_url_path_when_no_gh(self):
        out = file_issue.create(REPO, "t", "b", ["bug"], dry_run=True, gh_check=lambda: False)
        self.assertEqual(out["method"], "url")
        self.assertIn("/issues/new?", out["url"])

    def test_url_path_truncates_oversized_body(self):
        big = "x" * 20000
        out = file_issue.create(REPO, "t", big, [], dry_run=True, gh_check=lambda: False)
        self.assertTrue(out["truncated"])
        self.assertLessEqual(len(out["url"]), file_issue.URL_LIMIT)

    def test_url_path_truncates_multibyte_oversized_body(self):
        # Test with multibyte characters (3 bytes each in UTF-8)
        big = "你" * 8000
        out = file_issue.create(REPO, "t", big, [], dry_run=True, gh_check=lambda: False)
        self.assertTrue(out["truncated"])
        self.assertLessEqual(len(out["url"]), file_issue.URL_LIMIT)


if __name__ == "__main__":
    unittest.main()
