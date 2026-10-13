import copy
import json
import tempfile
import unittest
from pathlib import Path
from generation.generate import load_instances
from generation.render import render
from policy.schema import Instance, Rule
from policy.solver import solve, verify_certificate
from policy.fidelity import compare
from scripts.build_dataset import build
from evaluation.runner import score
from evaluation.extraction import parse_answer


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        # Historical fixtures test semantics; production no longer generates these families.
        self.cases = {x.metadata["family"]: x for x in load_instances("data/examples/private.jsonl", 9)}

    def test_priority_reversal(self):
        for family, expected in [("priority", True), ("priority_reversed", False)]:
            result = solve(self.cases[family])
            self.assertEqual(result["status"], "priority_resolved")
            self.assertTrue(all(m["send"] == expected for m in result["admissible_actions"]))

    def test_higher_order_minimality(self):
        case = self.cases["higher_order"]
        result = solve(case)
        self.assertEqual(result["conflict_certificates"], [["r1", "r2", "r3"]])
        self.assertEqual(result["smallest_conflict_size"], 3)
        self.assertTrue(verify_certificate(case, ["r3", "r1", "r2"]))
        for dropped in range(3):
            pair = copy.deepcopy(case)
            pair.rules.pop(dropped)
            self.assertEqual(solve(pair)["status"], "consistent")
        self.assertEqual(solve(self.cases["higher_order_consistent"])["status"], "consistent")

    def test_exception_and_inactive(self):
        for family in ("exception", "inactive"):
            result = solve(self.cases[family])
            self.assertEqual(result["active_rules"], ["r1"])
            self.assertEqual(result["status"], "consistent")

    def test_unknown_is_not_false(self):
        result = solve(self.cases["unknown"])
        self.assertEqual(result["status"], "insufficient_facts")
        self.assertEqual({r["result"]["status"] for r in result["completions"]},
                         {"consistent", "unresolved_conflict"})

    def test_priority_chain_and_cycles(self):
        case = self.cases["priority"]
        case.rules.append(Rule("r3", True, "send"))
        case.overrides = [["r1", "r2"], ["r2", "r3"]]
        self.assertEqual(solve(case)["surviving_rules"], ["r1"])
        case.overrides.append(["r3", "r1"])
        with self.assertRaises(ValueError):
            solve(case)

    def test_compatible_rules_not_defeated(self):
        case = self.cases["priority"]
        case.rules[1].requirement = "log"
        result = solve(case)
        self.assertEqual(result["defeats"], [])
        self.assertEqual(result["admissible_actions"], [{"log": True, "send": True}])

    def test_negation_and_nested_conditions(self):
        case = self.cases["consistent"]
        case.rules[0].condition = {"and": ["approved", {"not": "waiver"}]}
        self.assertEqual(solve(case)["active_rules"], ["r1"])
        case.facts["waiver"] = True
        self.assertEqual(solve(case)["active_rules"], [])

    def test_validation_and_roundtrip(self):
        case = self.cases["consistent"]
        self.assertEqual(Instance.from_dict(case.to_dict()), case)
        case.rules[0].requirement = "undeclared"
        with self.assertRaises(ValueError):
            solve(case)

    def test_all_valid_actions_and_strict_output(self):
        ref = solve(self.cases["consistent"])
        self.assertEqual(len(ref["admissible_actions"]), 2)
        for action in ref["admissible_actions"]:
            answer = {"status": "consistent", "action": action, "conflict_certificate": []}
            self.assertTrue(score(ref, parse_answer(json.dumps(answer)))["joint_correct"])
        self.assertIsNone(parse_answer('{"status":"consistent"}'))
        self.assertFalse(score(ref, None)["joint_correct"])
        self.assertFalse(score(ref, {"status": "consistent", "action": {"send": True},
                                    "conflict_certificate": []})["action_correct"])

    def test_counterfactual_fidelity(self):
        original = self.cases["inactive"]
        recovered = copy.deepcopy(original)
        recovered.rules.pop()
        self.assertEqual(solve(original)["admissible_actions"], solve(recovered)["admissible_actions"])
        self.assertFalse(compare(original, recovered)["equivalent"])
        self.assertTrue(compare(original, original)["equivalent"])

    def test_reproducibility_and_answer_separation(self):
        # Keep test scratch files inside the writable project on Windows sandboxes.
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as a, tempfile.TemporaryDirectory(dir=Path.cwd()) as b:
            instance = self.cases["consistent"]
            def completion(prompt):
                return {"text": json.dumps({"policy_documents": [{"title": "Policy", "text": "r1: Approved transfers must be sent."}],
                    "scenario": "The transfer is approved.", "action_definitions": instance.actions,
                    "context": "Archive office", "predicate_definitions": instance.definitions}), "model_requested": "mock"}
            a, b = Path(a) / "dataset", Path(b) / "dataset"
            build(a, [instance], completion, "archive office", "clear")
            build(b, [instance], completion, "archive office", "clear")
            for filename in ("private.jsonl", "prompts.jsonl", "manifest.json"):
                self.assertEqual((Path(a) / filename).read_bytes(), (Path(b) / filename).read_bytes())
            public = [json.loads(x) for x in (Path(a) / "prompts.jsonl").read_text().splitlines()]
            self.assertEqual(len(public), 3)
            self.assertTrue(all(set(x) == {"id", "level", "prompt"} for x in public))
            self.assertTrue(all('"reference"' not in x["prompt"] and '"family"' not in x["prompt"] for x in public))
        with self.assertRaises(ValueError):
            render(self.cases["consistent"], "unverified_llm")


if __name__ == "__main__":
    unittest.main()
