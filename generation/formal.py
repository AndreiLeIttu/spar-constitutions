"""Offline formal-object sampling; representation is distinct from JSON serialization."""
import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from policy.schema import Instance, Rule
from policy.solver import solve

REPRESENTATION = "propositional"
SEMANTICS = "spar-mandatory-pairwise-defeat-v0.1.0"


@dataclass(frozen=True)
class Parameters:
    representation: str = REPRESENTATION
    seed: int = 7
    count: int = 5
    facts: int = 3
    actions: int = 2
    rules: int = 4
    condition_depth: int = 1
    requirement_depth: int = 1
    exception_rate: float = 0.2
    priority_edges: int = 1
    unknown_rate: float = 0.0

    def validate(self):
        if self.representation != REPRESENTATION:
            raise ValueError("Only propositional representation is implemented; first-order requires a separate backend")
        if not 1 <= self.count <= 1000:
            raise ValueError("Count must be 1-1000")
        if not (1 <= self.facts <= 10 and 1 <= self.actions <= 10 and 1 <= self.rules <= 12):
            raise ValueError("Use 1-10 facts, 1-10 actions, and 1-12 rules")
        if not 0 <= self.condition_depth <= 3 or not 0 <= self.requirement_depth <= 3:
            raise ValueError("Formula depths must be 0-3")
        if not 0 <= self.exception_rate <= 1 or not 0 <= self.unknown_rate <= 1:
            raise ValueError("Rates must lie between 0 and 1")
        if not 0 <= self.priority_edges <= self.rules * (self.rules - 1) // 2:
            raise ValueError("Too many priority edges for an acyclic rule graph")
        return self


def expression(rng, names, depth):
    """Depth counts AND/OR nesting; leaves are positive or negative literals."""
    if depth == 0 or rng.random() < 0.5:
        atom = rng.choice(names)
        return atom if rng.random() < 0.5 else {"not": atom}
    return {rng.choice(["and", "or"]): [expression(rng, names, depth - 1),
                                         expression(rng, names, depth - 1)]}


def generate_formal(parameters):
    parameters.validate()
    rng = random.Random(parameters.seed)
    fact_names = [f"p{i + 1}" for i in range(parameters.facts)]
    action_names = [f"a{i + 1}" for i in range(parameters.actions)]
    for index in range(parameters.count):
        facts = {p: None if rng.random() < parameters.unknown_rate else rng.choice([True, False]) for p in fact_names}
        rules = [Rule(f"r{i + 1}",
                      True if rng.random() < 0.25 else expression(rng, fact_names, parameters.condition_depth),
                      expression(rng, action_names, parameters.requirement_depth),
                      expression(rng, fact_names, parameters.condition_depth)
                      if rng.random() < parameters.exception_rate else False)
                 for i in range(parameters.rules)]
        order = [r.id for r in rules]
        rng.shuffle(order)
        candidates = [[order[i], order[j]] for i in range(len(order)) for j in range(i + 1, len(order))]
        overrides = rng.sample(candidates, parameters.priority_edges)
        instance = Instance(f"prop-{parameters.seed}-{index:04d}", facts,
                            {p: f"condition {p} holds" for p in fact_names},
                            {a: f"perform action {a}" for a in action_names}, rules, overrides,
                            {"generator_version": "0.3.0", "representation": REPRESENTATION,
                             "semantics": SEMANTICS, "parameters": asdict(parameters), "index": index}).validate()
        yield {"representation": REPRESENTATION, "semantics": SEMANTICS,
               "formal": instance.to_dict(), "reference": solve(instance)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--representation", default=REPRESENTATION, choices=[REPRESENTATION])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--facts", type=int, default=3)
    parser.add_argument("--actions", type=int, default=2)
    parser.add_argument("--rules", type=int, default=4)
    parser.add_argument("--condition-depth", type=int, default=1)
    parser.add_argument("--requirement-depth", type=int, default=1)
    parser.add_argument("--exception-rate", type=float, default=0.2)
    parser.add_argument("--priority-edges", type=int, default=1)
    parser.add_argument("--unknown-rate", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=Path("data/runs/formal.jsonl"))
    args = parser.parse_args()
    values = vars(args).copy()
    output = values.pop("output")
    parameters = Parameters(**values)
    try:
        parameters.validate()
    except ValueError as error:
        parser.error(str(error))
    output.parent.mkdir(parents=True, exist_ok=True)
    statuses = {}
    preview = []
    with output.open("x", encoding="utf-8") as saved:
        for row in generate_formal(parameters):
            preview.append(row)
            saved.write(json.dumps(row) + "\n")
            status = row["reference"]["status"]
            statuses[status] = statuses.get(status, 0) + 1
    output.with_suffix(".preview.json").write_text(json.dumps(preview, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output), "count": parameters.count, "statuses": statuses}, indent=2))


if __name__ == "__main__":
    main()
