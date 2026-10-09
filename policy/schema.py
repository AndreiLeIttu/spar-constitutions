"""Validated, JSON-native representation; null facts explicitly mean unknown."""
from dataclasses import dataclass, field, asdict

Expr = str | bool | dict


def atoms(expr: Expr) -> set[str]:
    if type(expr) is bool:
        return set()
    if isinstance(expr, str) and expr:
        return {expr}
    if not isinstance(expr, dict) or len(expr) != 1:
        raise ValueError(f"Invalid Boolean expression: {expr!r}")
    op, value = next(iter(expr.items()))
    if op == "not":
        return atoms(value)
    if op in ("and", "or") and isinstance(value, list) and value:
        return set().union(*(atoms(x) for x in value))
    raise ValueError(f"Invalid operator or operands: {expr!r}")


def evaluate(expr: Expr, state: dict[str, bool]) -> bool:
    if type(expr) is bool:
        return expr
    if isinstance(expr, str):
        return state[expr]
    op, value = next(iter(expr.items()))
    if op == "not":
        return not evaluate(value, state)
    values = [evaluate(x, state) for x in value]
    return all(values) if op == "and" else any(values)


@dataclass
class Rule:
    id: str
    condition: Expr
    requirement: Expr
    exception: Expr = False


@dataclass
class Instance:
    id: str
    facts: dict[str, bool | None]
    definitions: dict[str, str]
    actions: dict[str, str]
    rules: list[Rule]
    overrides: list[list[str]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def validate(self):
        ids = [r.id for r in self.rules]
        if not self.id or not ids or len(ids) != len(set(ids)):
            raise ValueError("Instance and unique rule IDs required")
        if not self.actions or len(self.actions) > 10 or len(self.rules) > 12:
            raise ValueError("Exact prototype supports 1-10 actions and 1-12 rules")
        if any(type(v) is not bool and v is not None for v in self.facts.values()):
            raise ValueError("Facts must be Boolean or null")
        if set(self.facts) != set(self.definitions):
            raise ValueError("Every fact needs exactly one definition")
        if set(self.facts) & set(self.actions):
            raise ValueError("Fact and action namespaces must be disjoint")
        if len(self.facts) > 10:
            raise ValueError("At most 10 facts supported")
        for r in self.rules:
            if not (atoms(r.condition) | atoms(r.exception)) <= self.facts.keys():
                raise ValueError("Conditions and exceptions reference declared facts")
            if not atoms(r.requirement) <= self.actions.keys():
                raise ValueError("Requirements reference declared actions")
        edges = {i: set() for i in ids}
        for pair in self.overrides:
            if len(pair) != 2 or any(x not in edges for x in pair):
                raise ValueError("Override must contain two known rule IDs")
            edges[pair[0]].add(pair[1])
        def visit(node, path):
            if node in path:
                raise ValueError("Priority cycles are unsupported")
            for child in edges[node]:
                visit(child, path | {node})
        for node in edges:
            visit(node, set())
        return self

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        data["rules"] = [Rule(**r) for r in data["rules"]]
        return cls(**data).validate()
