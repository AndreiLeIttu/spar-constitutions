import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from generation.formal import Parameters
from scripts.run_demo import run


class DemoTests(unittest.TestCase):
    def test_complete_demo_with_mock_calls_and_readable_previews(self):
        calls = []
        def completion(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                value = {"context": "Test office", "predicate_definitions": {f"p{i}": f"check {i} is complete" for i in range(1, 4)},
                         "action_definitions": {"a1": "issue the badge", "a2": "print the receipt"},
                         "policy_documents": [{"title": "Test", "text": "Mock policy"}], "scenario": "Mock scenario"}
            else:
                value = {"status": "consistent", "action": {"a1": False, "a2": False}, "conflict_certificate": []}
            return {"text": json.dumps(value), "model_requested": "mock"}
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as scratch, contextlib.redirect_stdout(io.StringIO()):
            output = Path(scratch) / "run"
            results = run(output, Parameters(count=1), completion)
            self.assertEqual(len(calls), 4)
            self.assertEqual(len(results), 3)
            preview = json.loads((output / "dataset/preview.json").read_text(encoding="utf-8"))
            private = json.loads((output / "dataset/private.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(preview, [private])
            self.assertIn("\n  {", (output / "formal.preview.json").read_text())
            self.assertIn("Mock scenario", (output / "walkthrough.md").read_text())
            self.assertTrue((output / "scores.json").exists())
