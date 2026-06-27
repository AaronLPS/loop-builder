import os, sys, json, pathlib, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "distiller"))
import digest_store as ds  # noqa: E402

FIX = HERE / "fixtures" / "session.jsonl"          # Phase 1 fixture (gh + pytest)


class DigestStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = pathlib.Path(self.tmp.name) / "digests.jsonl"
        os.environ[ds.DIGESTS_FILE_ENV] = str(self.file)

    def tearDown(self):
        os.environ.pop(ds.DIGESTS_FILE_ENV, None)
        self.tmp.cleanup()

    def test_digest_builds_record_with_signature_and_blocks(self):
        d = ds.digest(FIX)
        self.assertIn("signature", d)
        self.assertIn("action", d["blocks"])
        self.assertIn(str(FIX), d["fingerprint"])             # fingerprint embeds the path
        self.assertEqual(d["project"], FIX.parent.name)       # project = parent dir name
        self.assertEqual(d["schema"], 1)

    def test_append_then_read_roundtrip(self):
        d = ds.digest(FIX); ds.append(d)
        got = ds.read_all()
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["signature"], d["signature"])

    def test_seen_fingerprints_is_the_watermark(self):
        d = ds.digest(FIX); ds.append(d)
        self.assertIn(d["fingerprint"], ds.seen_fingerprints())

    def test_digest_new_skips_already_seen(self):
        first = ds.digest_new([FIX])
        self.assertEqual(len(first), 1)
        second = ds.digest_new([FIX])          # same file, already digested
        self.assertEqual(second, [])
