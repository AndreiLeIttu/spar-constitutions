"""Offline scoring of saved responses; never invokes a provider or exposes gold prompts."""
import argparse
import json
from evaluation.extraction import parse_answer


def score(reference, answer):
    if answer is None:
        return {"invalid_format": True, "status_correct": False, "action_correct": False,
                "certificate_correct": False, "joint_correct": False}
    status_ok = answer["status"] == reference["status"]
    action_ok = answer["action"] in reference.get("admissible_actions", []) if reference.get("admissible_actions") else answer["action"] is None
    certs = reference.get("conflict_certificates", [])
    cert_ok = sorted(answer["conflict_certificate"]) in certs if certs else answer["conflict_certificate"] == []
    return {"invalid_format": False, "status_correct": status_ok, "action_correct": action_ok,
            "certificate_correct": cert_ok, "joint_correct": status_ok and action_ok and cert_ok}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--responses", required=True, help="JSONL: id, level, response (JSON object or string)")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.dataset, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    gold = {(row["id"], variant["level"]): row["reference"] for row in rows for variant in row["renderings"]}
    predictions = {}
    with open(args.responses, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            key = (row["id"], row["level"])
            if key not in gold or key in predictions:
                raise ValueError(f"Unknown or duplicate response key {key}")
            predictions[key] = parse_answer(row.get("response"))
    results = [{"id": key[0], "level": key[1], "missing_response": key not in predictions,
                **score(ref, predictions.get(key))} for key, ref in gold.items()]
    summary = {"total": len(results), "received": len(predictions)}
    for metric in ("invalid_format", "status_correct", "action_correct", "certificate_correct", "joint_correct"):
        summary[metric] = sum(r[metric] for r in results) / len(results) if results else None
    by_level = {}
    for level in sorted({r["level"] for r in results}):
        group = [r for r in results if r["level"] == level]
        by_level[level] = {"count": len(group), "joint_accuracy": sum(r["joint_correct"] for r in group) / len(group)}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "by_level": by_level, "results": results}, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
