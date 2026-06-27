import os, sys, pathlib, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "distiller"))
import ledger  # noqa: E402


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ[ledger.LEDGER_FILE_ENV] = str(pathlib.Path(self.tmp.name) / "l.jsonl")

    def tearDown(self):
        os.environ.pop(ledger.LEDGER_FILE_ENV, None)
        self.tmp.cleanup()

    def test_new_candidate_starts_new_with_count_from_evidence(self):
        c = ledger.upsert("sigA", "triage", ["repo1"], ["fp1", "fp2"], ["discovery", "action"], 100)
        self.assertEqual(c["status"], "new")
        self.assertEqual(c["count"], 2)
        self.assertEqual(sorted(c["evidence"]), ["fp1", "fp2"])

    def test_upsert_same_signature_merges_evidence_and_count(self):
        ledger.upsert("sigA", "triage", ["repo1"], ["fp1"], ["action"], 100)
        c = ledger.upsert("sigA", "triage", ["repo2"], ["fp1", "fp3"], ["verify"], 200)
        self.assertEqual(c["count"], 2)                       # fp1 + fp3 distinct
        self.assertEqual(sorted(c["projects"]), ["repo1", "repo2"])
        self.assertEqual(c["last_seen"], 200)
        self.assertIn("verify", c["blocks"])
        self.assertEqual(len(ledger.read_all()), 1)           # still one candidate

    def test_dismissed_signature_does_not_resurrect(self):
        c = ledger.upsert("sigA", "triage", ["repo1"], ["fp1"], ["action"], 100)
        ledger.mark(c["id"], "dismissed")
        again = ledger.upsert("sigA", "triage", ["repo1"], ["fp9"], ["action"], 300)
        self.assertEqual(again["status"], "dismissed")        # not reactivated
        self.assertNotIn("fp9", again["evidence"])            # no new evidence added

    def test_mark_changes_status(self):
        c = ledger.upsert("sigA", "triage", ["repo1"], ["fp1"], ["action"], 100)
        self.assertEqual(ledger.mark(c["id"], "built")["status"], "built")

    def test_mark_raises_keyerror_on_unknown_id(self):
        with self.assertRaises(KeyError):
            ledger.mark("nonexistent-id", "built")
