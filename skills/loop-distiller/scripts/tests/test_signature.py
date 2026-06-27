import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "distiller"))
import signature as sig  # noqa: E402


def _cond(discovery=(), action=(), verify=(), vcs=()):
    b = {"discovery": list(discovery), "action": list(action),
         "verify": list(verify), "vcs": list(vcs)}
    b["counts"] = {k: len(v) for k, v in b.items()}
    return b


def _ref(tool, hint):
    return {"i": 0, "tool": tool, "hint": hint}


class SignatureTest(unittest.TestCase):
    def test_same_workflow_surface_variation_same_signature(self):
        a = _cond(discovery=[_ref("Bash", "gh issue list --label P1")],
                  action=[_ref("Bash", "gh issue edit 41 --add-assignee me")],
                  verify=[_ref("Bash", "pytest -q")])
        b = _cond(discovery=[_ref("Bash", "gh issue list --label bug --limit 50")],
                  action=[_ref("Bash", "gh issue edit 99 --add-assignee you")],
                  verify=[_ref("Bash", "pytest tests/ -x")])
        self.assertEqual(sig.signature(a), sig.signature(b))   # high recall: args/order ignored

    def test_different_tools_different_signature(self):
        a = _cond(action=[_ref("Bash", "gh issue edit 1")])
        b = _cond(action=[_ref("Edit", "/work/x.py")])
        self.assertNotEqual(sig.signature(a), sig.signature(b))

    def test_signature_ignores_empty_blocks(self):
        a = _cond(action=[_ref("Bash", "gh x")])
        self.assertNotIn("discovery", sig.signature(a))

    def test_group_and_drop_singletons(self):
        digests = [{"signature": "s1"}, {"signature": "s1"}, {"signature": "s2"}]
        groups = sig.group_by_signature(digests)
        self.assertEqual(len(groups["s1"]), 2)
        kept = sig.drop_singletons(groups)
        self.assertIn("s1", kept)        # family of 2 survives
        self.assertNotIn("s2", kept)     # singleton dropped (bar < threshold N)
