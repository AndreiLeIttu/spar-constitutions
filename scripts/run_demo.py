"""One-case end-to-end demo: offline generation, one paid rendering call, three paid answers."""
import argparse
import getpass
import json
import sys
from pathlib import Path
from generation.formal import Parameters, generate_formal
from generation.generate import load_instances
from scripts.build_dataset import build
from scripts.run_openrouter import complete
from evaluation.extraction import parse_answer
from evaluation.runner import score


def run(output, parameters, completion, context="auto", presentation="natural impersonal prose"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    objects = list(generate_formal(parameters))
    (output / "formal.jsonl").write_text("\n".join(json.dumps(x) for x in objects) + "\n", encoding="utf-8")
    (output / "formal.preview.json").write_text(json.dumps(objects, indent=2, ensure_ascii=False), encoding="utf-8")
    instances = load_instances(output / "formal.jsonl", 1)
    build(output / "dataset", instances, completion, context, presentation)
    record = json.loads((output / "dataset/private.jsonl").read_text(encoding="utf-8").splitlines()[0])
    candidate = record["generation"]["candidate"]
    report = ["# One-case policy benchmark demo", "", "## Context", candidate["context"],
              "", "## Predicate meanings", json.dumps(candidate["predicate_definitions"], indent=2, ensure_ascii=False),
              "", "## Action meanings", json.dumps(candidate["action_definitions"], indent=2, ensure_ascii=False),
              "", "## Governing policy"]
    for document in candidate["policy_documents"]:
        report.extend(["", document["title"], "", document["text"]])
    report.extend(["", "## Scenario", candidate["scenario"], "", "## Solver reference",
                   "```json", json.dumps(record["reference"], indent=2), "```", "",
                   "Generated grounding and prose are unverified. Scores measure agreement with the formal reference."])
    (output / "walkthrough.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    results = []
    with (output / "responses.jsonl").open("x", encoding="utf-8") as responses:
        for variant in record["renderings"]:
            answer = completion(variant["prompt"])
            responses.write(json.dumps({"id": record["id"], "level": variant["level"],
                                       "response": answer["text"],
                                       **{k: v for k, v in answer.items() if k != "text"}}) + "\n")
            responses.flush()
            result = {"id": record["id"], "level": variant["level"],
                      **score(record["reference"], parse_answer(answer["text"]))}
            results.append(result)
            (output / "scores.json").write_text(json.dumps({"completed": len(results), "expected": 3,
                "results": results}, indent=2), encoding="utf-8")
            print(f'{variant["level"]}: joint_correct={result["joint_correct"]}')
    report.extend(["", "## Model results", "| Presentation | Status | Action | Certificate | Joint |",
                   "| --- | --- | --- | --- | --- |"])
    for result in results:
        report.append("| " + " | ".join(str(result[k]) for k in
            ("level", "status_correct", "action_correct", "certificate_correct", "joint_correct")) + " |")
    report.extend(["", "This is one demonstration case, not an estimate of benchmark performance."])
    (output / "walkthrough.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="openai/gpt-6.1-sol")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--context", default="auto")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/runs/demo")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.model == "openrouter/auto":
        parser.error("Choose an explicit model")
    print(json.dumps({"model": args.model, "reasoning_effort": args.reasoning_effort,
        "formal_cases": 1, "paid_calls": 4, "max_tokens_per_call": 2048,
        "context": args.context, "output": args.output, "execute": args.execute}, indent=2))
    if not args.execute:
        return
    if Path(args.output).exists():
        parser.error("Output exists; choose a fresh --output directory")
    if not sys.stdin.isatty():
        parser.error("Run interactively in your own terminal; do not share or pipe the key")
    key = getpass.getpass("OpenRouter experiment key (hidden input): ").strip()
    if not key:
        parser.error("No key supplied")
    parameters = Parameters(seed=args.seed, count=1, rules=3, condition_depth=0,
                            requirement_depth=0, exception_rate=0)
    try:
        run(args.output, parameters, lambda prompt: complete(prompt, args.model, key, 2048, args.reasoning_effort), args.context)
    except (RuntimeError, ValueError, TypeError):
        print("Stopped: API or candidate-validation failure. Saved results remain; no automatic retry.", file=sys.stderr)
        raise SystemExit(1) from None
    print(f"Finished. Read {Path(args.output) / 'walkthrough.md'}")


if __name__ == "__main__":
    main()
