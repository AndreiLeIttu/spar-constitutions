import json
import tempfile
import unittest
from pathlib import Path
from generation.formal import Parameters, generate_formal
from generation.generate import load_instances, scenario_prompt
from policy.schema import Instance, atoms
from policy.solver import solve


class FormalTests(unittest.TestCase):
    def test_reproducible_sampling_and_different_seeds(self):
        a = list(generate_formal(Parameters(count=20)))
        self.assertEqual(a, list(generate_formal(Parameters(count=20))))
        self.assertNotEqual(a, list(generate_formal(Parameters(seed=8, count=20))))
        # Formal structures vary rather than cycling through preset families.
        self.assertGreater(len({json.dumps(r["formal"]["rules"], sort_keys=True) for r in a}), 10)

    def test_bounds_vocabulary_acyclicity_and_reference(self):
        for row in generate_formal(Parameters(count=30, facts=4, actions=3, rules=6, priority_edges=5)):
            instance = Instance.from_dict(row["formal"])
            self.assertEqual(len(instance.rules), 6)
            self.assertEqual(len(instance.overrides), 5)
            for rule in instance.rules:
                self.assertTrue(atoms(rule.condition) <= instance.facts.keys())
                self.assertTrue(atoms(rule.requirement) <= instance.actions.keys())
            self.assertEqual(row["reference"], solve(instance))

    def test_extreme_rates(self):
        row = next(generate_formal(Parameters(unknown_rate=1, exception_rate=0, priority_edges=0)))
        self.assertEqual(row["reference"]["status"], "insufficient_facts")
        self.assertTrue(all(v is None for v in row["formal"]["facts"].values()))
        self.assertTrue(all(r["exception"] is False for r in row["formal"]["rules"]))
        self.assertEqual(row["formal"]["overrides"], [])

    def test_unsupported_representation_and_invalid_parameters(self):
        for parameters in (Parameters(representation="first-order"), Parameters(facts=0),
                           Parameters(priority_edges=7), Parameters(exception_rate=2)):
            with self.assertRaises(ValueError):
                list(generate_formal(parameters))

    def test_output_loads_into_scenario_generation_without_gold_leak(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as scratch:
            path = Path(scratch) / "formal.jsonl"
            rows = list(generate_formal(Parameters(count=2)))
            path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
            instances = load_instances(path, 2)
            self.assertEqual(len(instances), 2)
            prompt, _ = scenario_prompt(instances[0], "fictional office", "prose")
            self.assertNotIn('"reference"', prompt)
            self.assertNotIn('"parameters"', prompt)
            rows[0]["representation"] = "first-order"
            path.write_text(json.dumps(rows[0]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_instances(path, 1)
