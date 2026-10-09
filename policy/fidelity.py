"""Bounded semantic comparison for recovered formalizations, independent of original facts."""
from policy.schema import Instance
from policy.solver import assignments, solve


def compare(original: Instance, recovered: Instance):
    original.validate()
    recovered.validate()
    if original.actions != recovered.actions or original.definitions != recovered.definitions:
        return {"equivalent": False, "reason": "Action/predicate vocabularies or definitions differ; alignment required"}
    checked = 0
    for facts in assignments(original.facts):
        left = Instance.from_dict(original.to_dict() | {"facts": facts})
        right = Instance.from_dict(recovered.to_dict() | {"facts": facts})
        a, b = solve(left), solve(right)
        checked += 1
        if (a["status"], a["admissible_actions"]) != (b["status"], b["admissible_actions"]):
            return {"equivalent": False, "checked": checked, "counterexample": facts,
                    "original": a, "recovered": b}
    return {"equivalent": True, "checked": checked,
            "scope": "Status and action models for every Boolean fact assignment in declared vocabulary"}
