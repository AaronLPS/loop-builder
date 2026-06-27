import os, sys, json, time, pathlib, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "distiller"))
import transcript_reader as tr  # noqa: E402


class LocateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        for k in (tr.TRANSCRIPT_FILE_ENV, tr.TRANSCRIPT_DIR_ENV):
            os.environ.pop(k, None)

    def tearDown(self):
        for k in (tr.TRANSCRIPT_FILE_ENV, tr.TRANSCRIPT_DIR_ENV):
            os.environ.pop(k, None)
        self.tmp.cleanup()

    def test_encode_replaces_slash_and_underscore(self):
        self.assertEqual(tr.encode_project_dir("/work/u/my_ws/loop-builder"),
                         "-work-u-my-ws-loop-builder")

    def test_file_env_takes_precedence(self):
        f = self.dir / "s.jsonl"
        f.write_text("{}\n", encoding="utf-8")
        os.environ[tr.TRANSCRIPT_FILE_ENV] = str(f)
        self.assertEqual(tr.locate(), f)

    def test_dir_env_picks_newest(self):
        old = self.dir / "old.jsonl"; old.write_text("{}\n", encoding="utf-8")
        new = self.dir / "new.jsonl"; new.write_text("{}\n", encoding="utf-8")
        os.utime(old, (1, 1)); os.utime(new, (time.time(), time.time()))
        os.environ[tr.TRANSCRIPT_DIR_ENV] = str(self.dir)
        self.assertEqual(tr.locate(), new)

    def test_returns_none_when_nothing_found(self):
        os.environ[tr.TRANSCRIPT_DIR_ENV] = str(self.dir)  # empty dir
        self.assertIsNone(tr.locate())


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.fix = pathlib.Path(__file__).resolve().parent / "fixtures" / "session.jsonl"

    def test_parse_yields_events_with_line_index(self):
        events = tr.parse(self.fix)
        self.assertEqual(events[0]["type"], "user")
        self.assertEqual(events[0]["text"], "triage my P1 issues")
        self.assertEqual(events[0]["i"], 0)

    def test_parse_extracts_tool_uses(self):
        events = tr.parse(self.fix)
        tools = [e for e in events if e["type"] == "tool_use"]
        self.assertEqual(tools[0]["tool"], "Bash")
        self.assertIn("gh issue list", tools[0]["text"])

    def test_parse_skips_unparseable_lines(self):
        events = tr.parse(self.fix)  # "not json at all" must not crash or appear
        self.assertFalse(any("not json" in e["text"] for e in events))


class CondenseTest(unittest.TestCase):
    def setUp(self):
        fix = pathlib.Path(__file__).resolve().parent / "fixtures" / "session.jsonl"
        self.c = tr.condense(tr.parse(fix))

    def test_discovery_captures_list_queries(self):
        hints = " ".join(r["hint"] for r in self.c["discovery"])
        self.assertIn("gh issue list", hints)

    def test_action_captures_mutations(self):
        hints = " ".join(r["hint"] for r in self.c["action"])
        self.assertIn("gh issue edit", hints)

    def test_verify_captures_test_runs(self):
        self.assertTrue(any("pytest" in r["hint"] for r in self.c["verify"]))

    def test_counts_match_bucket_lengths(self):
        for k in ("discovery", "action", "verify", "vcs"):
            self.assertEqual(self.c["counts"][k], len(self.c[k]))


if __name__ == "__main__":
    unittest.main()
