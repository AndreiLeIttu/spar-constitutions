"""Exhaustive action models and subset-minimal conflict certificates."""
from itertools import product, combinations
from policy.schema import Instance, evaluate


def assignments(names):
    names = sorted(names)
    return [dict(zip(names, values)) for values in product((False, True), repeat=len(names))]


def _solve_known(instance, facts):
    models = assignments(instance.actions)
    active = [r for r in instance.rules if evaluate(r.condition, facts)
              and not evaluate(r.exception, facts)]
    reach = {r.id: set() for r in instance.rules}
    for high, low in instance.overrides:
        reach[high].add(low)
    for _ in instance.rules:
        for high in reach:
            reach[high] |= set().union(*(reach[x] for x in list(reach[high]))) if reach[high] else set()
    defeats = []
    for high in active:
        for low in active:
            if low.id in reach[high.id] and not any(
                evaluate(high.requirement, m) and evaluate(low.requirement, m) for m in models
            ):
                defeats.append([high.id, low.id])
    defeated = {low for _, low in defeats}
    surviving = [r for r in active if r.id not in defeated]
    def satisfying(rules):
        return [m for m in models if all(evaluate(r.requirement, m) for r in rules)]
    admissible = satisfying(surviving)
    certificates = []
    if not admissible:
        for size in range(1, len(surviving) + 1):
            for subset in combinations(surviving, size):
                ids = {r.id for r in subset}
                if any(set(c) <= ids for c in certificates):
                    continue
                if not satisfying(subset):
                    certificates.append(sorted(ids))
    return {
        "status": "unresolved_conflict" if not admissible else
                  "priority_resolved" if defeats else "consistent",
        "admissible_actions": admissible,
        "active_rules": [r.id for r in active],
        "surviving_rules": [r.id for r in surviving],
        "defeats": defeats,
        "conflict_certificates": certificates,
        "smallest_conflict_size": min(map(len, certificates), default=None),
    }


def solve(instance: Instance) -> dict:
    instance.validate()
    unknown = [k for k, v in instance.facts.items() if v is None]
    if not unknown:
        return _solve_known(instance, instance.facts)
    completions = []
    for assignment in assignments(unknown):
        facts = instance.facts | assignment
        completions.append({"facts": facts, "result": _solve_known(instance, facts)})
    # Unknown applicability is reported even when action consequences happen to agree.
    return {"status": "insufficient_facts", "unknown_facts": sorted(unknown),
            "completions": completions}


def verify_certificate(instance, ids):
    result = solve(instance)
    return result["status"] != "insufficient_facts" and sorted(ids) in result["conflict_certificates"]
