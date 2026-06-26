import os, sys, io, json, pathlib, tempfile, contextlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "feedback"))
import cli  # noqa: E402


def run(argv, stdin=""):
    out = io.StringIO()
    if stdin:
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(stdin)
    with contextlib.redirect_stdout(out):
        code = cli.main(argv)
    if stdin:
        sys.stdin = old_stdin
    return code, out.getvalue()


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        os.environ["LOOP_BUILDER_FEEDBACK_FILE"] = self.tmp.name

    def tearDown(self):
        os.unlink(self.tmp.name)
        os.environ.pop("LOOP_BUILDER_FEEDBACK_FILE", None)

    def test_append_then_list_open(self):
        code, _ = run(["append", "--category", "bug", "--text", "boom"])
        self.assertEqual(code, 0)
        code, out = run(["list-open"])
        self.assertEqual(code, 0)
        items = json.loads(out)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["text"], "boom")

    def test_sanitize_subcommand(self):
        # path built from fragments; key is the documented AWS sample value
        sample = "/home/" + "someuser" + "/x"
        code, out = run(["sanitize"], stdin="path " + sample + " and key AKIAIOSFODNN7EXAMPLE")
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertNotIn("someuser", res["text"])
        self.assertIn("secret", res["notes"])

    def test_file_dry_run_does_not_create(self):
        code, out = run(["file", "--repo", "AaronLPS/loop-builder", "--title", "t",
                         "--labels", "bug", "--dry-run"], stdin="body")
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertIn(res["method"], ("gh", "url"))


if __name__ == "__main__":
    unittest.main()
