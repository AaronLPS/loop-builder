import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "scripts" / "feedback"))
import sanitize  # noqa: E402


class SanitizeTest(unittest.TestCase):
    def test_home_path_collapses_to_tilde_keeping_structure(self):
        # built from fragments so this design doc embeds no literal home path
        sample = "/home/" + "someuser" + "/proj/app.py"
        out, notes = sanitize.sanitize("see " + sample + " for details")
        self.assertIn("~/proj/app.py", out)
        self.assertNotIn("someuser", out)
        self.assertIn("local-path", notes)

    def test_macos_path_also_redacted(self):
        sample = "/Users/" + "someuser" + "/code/app.js"
        out, notes = sanitize.sanitize(sample)
        self.assertTrue(out.startswith("~/code/app.js"))
        self.assertIn("local-path", notes)

    def test_aws_key_redacted(self):
        # AKIAIOSFODNN7EXAMPLE is the documented AWS sample key (gitleaks allowlists it)
        out, notes = sanitize.sanitize("key=AKIAIOSFODNN7EXAMPLE")
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", out)
        self.assertIn("secret", notes)

    def test_email_redacted(self):
        out, notes = sanitize.sanitize("ping me at someone@example.com please")
        self.assertNotIn("someone@example.com", out)
        self.assertIn("email", notes)

    def test_clean_text_untouched(self):
        out, notes = sanitize.sanitize("the verifier returns the wrong exit code")
        self.assertEqual(out, "the verifier returns the wrong exit code")
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
