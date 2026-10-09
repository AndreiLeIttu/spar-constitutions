"""Strict JSON answers; invalid responses remain explicit format failures."""
import json


def parse_answer(text):
    try:
        value = json.loads(text) if isinstance(text, str) else text
        if not isinstance(value, dict) or set(value) != {"status", "action", "conflict_certificate"}:
            return None
        if value["status"] not in ("consistent", "priority_resolved", "unresolved_conflict", "insufficient_facts"):
            return None
        action = value["action"]
        if action is not None and (not isinstance(action, dict) or any(type(v) is not bool for v in action.values())):
            return None
        cert = value["conflict_certificate"]
        if not isinstance(cert, list) or any(not isinstance(x, str) for x in cert) or len(set(cert)) != len(cert):
            return None
        return value
    except (ValueError, TypeError):
        return None
