"""Generate model-written scenarios from formal JSONL and an editable prompt file."""
import argparse
import getpass
import json
import sys
from pathlib import Path
from generation.generate import DEFAULT_PROMPT, load_instances, scenario_prompt, generate
from scripts.run_openrouter import complete


def build(output, instances, completion, setting, presentation, prompt_path=DEFAULT_PROMPT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(json.dumps({"schema_version": "0.3.0",
        "requested_count": len(instances), "setting": setting, "presentation": presentation,
        "prompt_sha256": scenario_prompt(instances[0], setting, presentation, prompt_path)[1],
        "levels": ["formal", "clear", "scenario"], "scenario_validation": "unverified"}, indent=2), encoding="utf-8")
    preview = []
    with (output / "private.jsonl").open("w", encoding="utf-8") as private, \
         (output / "prompts.jsonl").open("w", encoding="utf-8") as public:
        for instance in instances:
            row = generate(instance, completion, setting, presentation, prompt_path)
            preview.append(row)
            (output / "preview.json").write_text(json.dumps(preview, indent=2, ensure_ascii=False), encoding="utf-8")
            private.write(json.dumps(row) + "\n")
            private.flush()
            for variant in row["renderings"]:
                public.write(json.dumps({"id": row["id"], "level": variant["level"], "prompt": variant["prompt"]}) + "\n")
            public.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Formal Instance JSONL or existing private.jsonl")
    parser.add_argument("--model", required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--context", "--setting", dest="setting", default="auto",
                        help="auto lets the model choose; otherwise request a context (--setting remains an alias)")
    parser.add_argument("--presentation", default="clear impersonal prose")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--output", default="data/runs/generated-scenarios")
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.count <= 12 or not 1 <= args.max_tokens <= 4096 or args.model == "openrouter/auto":
        parser.error("Use an explicit model, 1-12 cases and 1-4096 output tokens")
    instances = load_instances(args.source, args.count)
    prompts = [scenario_prompt(i, args.setting, args.presentation, args.prompt)[0] for i in instances]
    print(json.dumps({"model": args.model, "calls": len(prompts), "execute": args.execute,
                      "reasoning_effort": args.reasoning_effort,
                      "generation_prompts": prompts}, indent=2))
    if not args.execute:
        return
    if Path(args.output).exists():
        parser.error("Output exists; choose a new --output")
    if not sys.stdin.isatty():
        parser.error("Run in your own interactive terminal")
    key = getpass.getpass("OpenRouter experiment key (hidden input): ").strip()
    if not key:
        parser.error("No key supplied")
    try:
        build(args.output, instances, lambda prompt: complete(prompt, args.model, key, args.max_tokens, args.reasoning_effort),
              args.setting, args.presentation, args.prompt)
    except (RuntimeError, ValueError, TypeError):
        print("Generation stopped: API or candidate-validation failure. Earlier rows retained; no retry.", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
