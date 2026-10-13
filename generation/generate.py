"""Prompt-driven scenario rendering of supplied formal cases."""
import hashlib
import json
import re
from pathlib import Path
from policy.schema import Instance
from policy.solver import solve
from generation.render import SEMANTICS, TASK, render

DEFAULT_PROMPT = Path(__file__).resolve().parents[1] / "prompts/policy/scenario.txt"


def load_instances(path, count):
    instances, seen = [], set()
    with Path(path).open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("representation", "propositional") != "propositional":
                raise ValueError("This solver and renderer only support propositional inputs")
            if "semantics" in data and data["semantics"] != "spar-mandatory-pairwise-defeat-v0.1.0":
                raise ValueError("Unsupported policy semantics")
            instance = Instance.from_dict(data.get("formal", data))
            if instance.id in seen:
                raise ValueError("Duplicate instance ID")
            seen.add(instance.id)
            instances.append(instance)
            if len(instances) == count:
                break
    if not instances:
        raise ValueError("No formal instances found")
    return instances


def scenario_prompt(instance, setting, presentation, prompt_path=DEFAULT_PROMPT):
    template = Path(prompt_path).read_text(encoding="utf-8")
    source = instance.to_dict()
    source.pop("metadata")
    values = {"{formal_object}": json.dumps(source, indent=2, sort_keys=True),
              "{setting}": setting, "{presentation}": presentation}
    for token in values:
        if token not in template:
            raise ValueError(f"Template missing {token}")
    prompt = re.sub(r"\{formal_object\}|\{setting\}|\{presentation\}", lambda m: values[m.group()], template)
    return prompt, hashlib.sha256(template.encode()).hexdigest()


def parse_scenario(text, instance):
    value = json.loads(text)
    if not isinstance(value, dict) or set(value) != {"context", "predicate_definitions", "policy_documents", "scenario", "action_definitions"}:
        raise ValueError("Invalid scenario response fields")
    if not isinstance(value["context"], str) or not value["context"].strip():
        raise ValueError("Chosen context required")
    if not isinstance(value["scenario"], str) or not value["scenario"].strip():
        raise ValueError("Nonempty scenario required")
    documents = value["policy_documents"]
    if not isinstance(documents, list) or not documents:
        raise ValueError("Policy documents required")
    for document in documents:
        if not isinstance(document, dict) or set(document) != {"title", "text"} or not all(
            isinstance(x, str) and x.strip() for x in document.values()
        ):
            raise ValueError("Policy documents need title and text")
    for field, expected in (("predicate_definitions", instance.facts), ("action_definitions", instance.actions)):
        mapping = value[field]
        if not isinstance(mapping, dict) or set(mapping) != set(expected) or not all(
            isinstance(x, str) and x.strip() for x in mapping.values()
        ):
            raise ValueError("Grounding must give a nonempty definition for every original ID, without new IDs")
        if len({x.strip().casefold() for x in mapping.values()}) != len(mapping):
            raise ValueError("Different symbols must have distinct definitions")
    if instance.metadata.get("grounding") and (
        value["predicate_definitions"] != instance.definitions or value["action_definitions"] != instance.actions
    ):
        raise ValueError("Previously grounded definitions are frozen")
    return value


def generate(instance, complete, setting, presentation, prompt_path=DEFAULT_PROMPT):
    reference = solve(instance)
    prompt, digest = scenario_prompt(instance, setting, presentation, prompt_path)
    response = complete(prompt)
    candidate = parse_scenario(response["text"], instance)
    grounded = Instance.from_dict(instance.to_dict() | {
        "definitions": candidate["predicate_definitions"], "actions": candidate["action_definitions"],
        "metadata": instance.metadata | {"grounding": {"context": candidate["context"], "status": "unverified"}}})
    if solve(grounded) != reference:
        raise ValueError("Grounding changed solver consequences")
    body = "Context: " + candidate["context"]
    body += "\nPredicate definitions:\n" + json.dumps(grounded.definitions, sort_keys=True)
    body += "\nActions:\n" + json.dumps(grounded.actions, sort_keys=True)
    for document in candidate["policy_documents"]:
        body += f'\nPolicy document: {document["title"]}\n{document["text"]}'
    body += "\nEstablished scenario:\n" + candidate["scenario"]
    variant = {"level": "scenario", "prompt": SEMANTICS + "\n\n" + body + "\n\n" + TASK,
               "validation": {"method": "llm_prompt", "status": "unverified",
                              "independent_reconstruction": "not_performed", "human_audit": "not_performed"}}
    return {"id": instance.id, "source_formal": instance.to_dict(), "formal": grounded.to_dict(), "reference": reference,
            "renderings": [render(grounded, "formal"), render(grounded, "clear"), variant],
            "generation": {"prompt": prompt, "prompt_sha256": digest, "setting": setting,
                           "presentation": presentation, "candidate": candidate,
                           "model_metadata": {k: v for k, v in response.items() if k != "text"}}}
