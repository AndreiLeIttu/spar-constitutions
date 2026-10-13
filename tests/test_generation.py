import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from generation.generate import load_instances, scenario_prompt, generate, parse_scenario
from scripts.build_dataset import main


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.instance = load_instances("data/examples/private.jsonl", 1)[0]
        self.candidate = {"policy_documents": [{"title": "Policy", "text": "r1: Approved transfers must be sent."}],
                          "scenario": "Approval is recorded.", "action_definitions": self.instance.actions,
                          "context": "Archive office", "predicate_definitions": self.instance.definitions}

    def test_template_is_read_and_gold_is_excluded(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as scratch:
            path = Path(scratch) / "prompt.txt"
            path.write_text('CUSTOM {formal_object} {setting} {presentation} {"literal": true}', encoding="utf-8")
            prompt, digest = scenario_prompt(self.instance, "office", "prose", path)
            self.assertTrue(prompt.startswith("CUSTOM"))
            self.assertIn('{"literal": true}', prompt)
            self.assertNotIn('"reference"', prompt)
            self.assertNotIn('"family"', prompt)
            self.assertEqual(len(digest), 64)

    def test_candidate_remains_unverified_and_solver_supplies_gold(self):
        row = generate(self.instance, lambda prompt: {"text": json.dumps(self.candidate)}, "office", "prose")
        self.assertEqual(row["reference"]["status"], "consistent")
        self.assertEqual(row["renderings"][-1]["validation"]["status"], "unverified")
        self.assertIn("Approval is recorded.", row["renderings"][-1]["prompt"])

    def test_changed_action_or_invalid_output_is_rejected(self):
        self.candidate["action_definitions"] = {"send": "redact instead"}
        with self.assertRaises(ValueError):
            parse_scenario(json.dumps(self.candidate), self.instance)
        with self.assertRaises(ValueError):
            parse_scenario('not JSON', self.instance)

    def test_concrete_grounding_is_shared_by_all_variants_and_structure_is_fixed(self):
        self.candidate["predicate_definitions"] = {"approved": "the borrower has an active membership",
                                                   "waiver": "a supervisor exemption has been recorded"}
        self.candidate["action_definitions"] = {"send": "issue the requested book", "log": "record the loan"}
        self.candidate["context"] = "Library lending"
        self.candidate["scenario"] = "The borrower has an active membership; no supervisor exemption is recorded."
        row = generate(self.instance, lambda prompt: {"text": json.dumps(self.candidate)}, "auto", "prose")
        for field in ("facts", "rules", "overrides", "id"):
            self.assertEqual(row["formal"][field], row["source_formal"][field])
        for variant in row["renderings"]:
            self.assertIn("issue the requested book", variant["prompt"])
            self.assertIn("the borrower has an active membership", variant["prompt"])
        self.assertEqual(row["formal"]["metadata"]["grounding"]["context"], "Library lending")
        from policy.schema import Instance
        grounded = Instance.from_dict(row["formal"])
        self.candidate["action_definitions"]["send"] = "send a parcel"
        with self.assertRaises(ValueError):
            parse_scenario(json.dumps(self.candidate), grounded)

    def test_bad_predicate_mapping_or_extra_formal_fields_rejected(self):
        self.candidate["predicate_definitions"] = {"approved": "membership is active"}
        with self.assertRaises(ValueError):
            parse_scenario(json.dumps(self.candidate), self.instance)
        self.candidate["predicate_definitions"] = self.instance.definitions
        self.candidate["facts"] = {"approved": False}
        with self.assertRaises(ValueError):
            parse_scenario(json.dumps(self.candidate), self.instance)

    def test_dry_run_does_not_read_key_or_call_model(self):
        import contextlib
        import io
        with patch("sys.argv", ["build", "--source", "data/examples/private.jsonl", "--model", "test/model"]), \
             patch("scripts.build_dataset.complete") as model, \
             patch("scripts.build_dataset.getpass.getpass") as key, \
             contextlib.redirect_stdout(io.StringIO()):
            main()
        model.assert_not_called()
        key.assert_not_called()
