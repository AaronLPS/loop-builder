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


if __name__ == "__main__":
    unittest.main()
