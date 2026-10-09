"""Balanced diagnostic families, with seeded benign irrelevant rules."""
import random
from policy.schema import Instance, Rule

FAMILIES = ("consistent", "opposition", "priority", "priority_reversed",
            "inactive", "exception", "higher_order", "higher_order_consistent", "unknown")


def generate(seed=7, count=18, distractors=0):
    if count < 1 or not 0 <= distractors <= 8:
        raise ValueError("Positive count and 0-8 distractors required")
    rng = random.Random(seed)
    for i in range(count):
        family = FAMILIES[i % len(FAMILIES)]
        facts = {"approved": True, "waiver": False}
        definitions = {"approved": "the archive transfer has recorded approval",
                       "waiver": "a transfer restriction waiver is recorded"}
        actions = {"send": "send the archive copy", "log": "record the transfer in the ledger"}
        rules = [Rule("r1", "approved", "send")]
        priorities = []
        if family in ("opposition", "priority", "priority_reversed", "inactive", "exception", "unknown"):
            rules.append(Rule("r2", "approved", {"not": "send"}))
        if family == "priority":
            priorities = [["r1", "r2"]]
        if family == "priority_reversed":
            priorities = [["r2", "r1"]]
        if family == "inactive":
            rules[1].condition = "waiver"
        if family == "exception":
            rules[1].exception = "waiver"
            facts["waiver"] = True
        if family == "unknown":
            facts["approved"] = None
        if family.startswith("higher_order"):
            rules.extend([Rule("r2", True, "log"),
                          Rule("r3", True, {"not": {"and": ["send", "log"]}})])
            if family == "higher_order_consistent":
                rules[2].condition = "waiver"
        for j in range(distractors):
            rules.append(Rule(f"d{j}", "waiver", rng.choice([True, "log"])))
        yield Instance(f"policy-{seed}-{i:04d}", facts, definitions, actions, rules, priorities,
                       {"seed": seed, "index": i, "family": family,
                        "distractors": distractors, "structure_group": family,
                        "generator_version": "0.1.0", "semantics_version": "0.1.0"}).validate()
