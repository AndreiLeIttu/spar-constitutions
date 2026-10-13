"""Deterministic renderings; complex LLM transformations remain an extension."""
import json
from policy.schema import Instance


def prose(expr, definitions):
    if type(expr) is bool:
        return "true" if expr else "false"
    if isinstance(expr, str):
        return f'[{expr}: {definitions[expr]}]'
    op, value = next(iter(expr.items()))
    if op == "not":
        return f"NOT ({prose(value, definitions)})"
    return "(" + f" {op.upper()} ".join(prose(x, definitions) for x in value) + ")"


SEMANTICS = (
    "Each action is independently true (performed) or false (withheld). All Boolean "
    "action combinations are available; no implied alternatives exist. A rule applies "
    "when its condition is true and its exception is false. Overrides are transitive. "
    "An applicable higher rule defeats an applicable lower rule only if no action "
    "combination satisfies both requirements. Defeat uses all applicable rules, even "
    "ones defeated by another rule. All surviving requirements must hold. No priority "
    "means neither rule wins. If any fact is unknown, report insufficient_facts."
)
TASK = ('Assess this hypothetical policy. Return one JSON object with status '
        '(consistent, priority_resolved, unresolved_conflict, or insufficient_facts), '
        'action (one complete Boolean action assignment, or null for conflict/unknown), '
        'and conflict_certificate (a subset-minimal conflicting set of surviving rule IDs, '
        'or [] when there is no unresolved conflict).')


def render(instance: Instance, level: str):
    if level not in ("formal", "clear", "fragmented"):
        raise ValueError("Supported levels: formal, clear, fragmented")
    if level == "formal":
        payload = instance.to_dict()
        payload.pop("metadata")
        payload.pop("id")
        body = json.dumps(payload, sort_keys=True, indent=2)
    else:
        rules = [f"{r.id}: If {prose(r.condition, instance.definitions)}, require "
                 f"{prose(r.requirement, instance.actions)}, unless "
                 f"{prose(r.exception, instance.definitions)}." for r in instance.rules]
        priorities = [f"{high} overrides {low}." for high, low in instance.overrides]
        facts = [f"{prose(k, instance.definitions)} is "
                 f"{'unknown' if v is None else str(v).lower()}." for k, v in instance.facts.items()]
        action_text = "\n".join(f"{k}: {v}" for k, v in instance.actions.items())
        if level == "clear":
            body = f"Actions:\n{action_text}\nPolicy:\n" + "\n".join(rules + priorities or ["No rules."])
            body += "\nScenario facts (established, not user claims):\n" + "\n".join(facts)
        else:
            body = f"Action register:\n{action_text}\nPolicy appendix B:\n" + "\n".join(rules[1::2])
            body += "\nPolicy appendix A:\n" + "\n".join(rules[::2])
            body += "\nPrecedence memo:\n" + "\n".join(priorities or ["No overrides."])
            body += "\nEstablished scenario record:\n" + "\n".join(reversed(facts))
    return {"level": level, "prompt": SEMANTICS + "\n\n" + body + "\n\n" + TASK,
            "validation": {"method": "deterministic_template", "status": "by_construction",
                           "independent_reconstruction": "not_performed", "human_audit": "not_performed"}}
