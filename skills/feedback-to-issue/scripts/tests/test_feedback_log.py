import os, sys, pathlib, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "feedback"))
import feedback_log  # noqa: E402


class FeedbackLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        self.tmp.close()
        os.environ["LOOP_BUILDER_FEEDBACK_FILE"] = self.tmp.name

    def tearDown(self):
        os.unlink(self.tmp.name)
        os.environ.pop("LOOP_BUILDER_FEEDBACK_FILE", None)

    def test_append_then_read(self):
        e = feedback_log.append("bug", "verifier crashed", context={"action": "scaffold"})
        self.assertEqual(e["category"], "bug")
        self.assertEqual(e["status"], "open")
        self.assertTrue(e["id"])
        all_entries = feedback_log.read_all()
        self.assertEqual(len(all_entries), 1)
        self.assertEqual(all_entries[0]["text"], "verifier crashed")

    def test_invalid_category_rejected(self):
        with self.assertRaises(ValueError):
            feedback_log.append("nonsense", "x")

    def test_mark_filed_only_targets_given_ids(self):
        a = feedback_log.append("bug", "a")
        b = feedback_log.append("idea", "b")
        n = feedback_log.mark_filed([a["id"]], 42)
        self.assertEqual(n, 1)
        by_id = {e["id"]: e for e in feedback_log.read_all()}
        self.assertEqual(by_id[a["id"]]["status"], "filed")
        self.assertEqual(by_id[a["id"]]["issue"], 42)
        self.assertEqual(by_id[b["id"]]["status"], "open")
        self.assertEqual(feedback_log.list_open(), [e for e in feedback_log.read_all() if e["id"] == b["id"]])


if __name__ == "__main__":
    unittest.main()
