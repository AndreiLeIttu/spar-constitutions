import argparse
import json
from pathlib import Path
from generation.policy.generate import generate
from generation.policy.transform import render
from policy.solver import solve


def build(output, seed, count, distractors):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "private.jsonl").open("w", encoding="utf-8") as private, \
         (output / "prompts.jsonl").open("w", encoding="utf-8") as public:
        for instance in generate(seed, count, distractors):
            variants = [render(instance, level) for level in ("formal", "clear", "fragmented")]
            private.write(json.dumps({"id": instance.id, "formal": instance.to_dict(),
                                      "reference": solve(instance), "renderings": variants}) + "\n")
            for variant in variants:
                public.write(json.dumps({"id": instance.id, "level": variant["level"],
                                         "prompt": variant["prompt"]}) + "\n")
    (output / "manifest.json").write_text(json.dumps({"schema_version": "0.1.0", "seed": seed,
        "count": count, "distractors": distractors, "levels": ["formal", "clear", "fragmented"],
        "split_warning": "Diagnostic fixture only. Group structure_group and all renderings together before splitting."}, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/examples")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--count", type=int, default=18)
    parser.add_argument("--distractors", type=int, default=0)
    args = parser.parse_args()
    build(args.output, args.seed, args.count, args.distractors)


if __name__ == "__main__":
    main()
