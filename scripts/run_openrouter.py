"""User-run OpenRouter smoke test; credentials never loaded from files or env."""
import argparse
import getpass
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def complete(prompt, model, key, max_tokens=2048, reasoning_effort=None):
    """One generation call; no retries or authentication metadata in returned results."""
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    settings = {"max_tokens": max_tokens}
    # Sol's current catalog does not list temperature among supported parameters.
    if model not in ("openai/gpt-6.1-sol", "openai/gpt-6.1-sol-pro"):
        body["temperature"] = 0
        settings["temperature"] = 0
    if reasoning_effort is not None:
        body["reasoning"] = {"effort": reasoning_effort}
        settings["reasoning_effort"] = reasoning_effort
    request = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("No text response")
        return {"text": content, "model_requested": model, "model_returned": payload.get("model"),
                "generation_id": payload.get("id"), "usage": payload.get("usage"),
                "finish_reason": payload["choices"][0].get("finish_reason"),
                "settings": settings}
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}; error body omitted") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError):
        raise RuntimeError("Network or response error; raw error omitted") from None


def select_prompts(path, limit):
    selected = []
    seen = set()
    with Path(path).open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if set(row) != {"id", "level", "prompt"} or not all(isinstance(v, str) for v in row.values()):
                raise ValueError("Use public prompts.jsonl, containing only id, level, prompt")
            key = (row["id"], row["level"])
            if key in seen:
                raise ValueError("Duplicate prompt key")
            seen.add(key)
            selected.append(row)
            if len(selected) == limit:
                break
    if not selected:
        raise ValueError("No prompts selected")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Exact OpenRouter model ID")
    parser.add_argument("--prompts", default="data/examples/prompts.jsonl")
    parser.add_argument("--output", default="data/runs/openrouter-smoke/responses.jsonl")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    parser.add_argument("--execute", action="store_true", help="Make paid calls; default is dry run")
    args = parser.parse_args()
    if not 1 <= args.limit <= 12 or not 1 <= args.max_tokens <= 2048:
        parser.error("Smoke runner allows 1-12 calls and 1-2048 output tokens per call")
    if args.model == "openrouter/auto":
        parser.error("Choose an explicit model")
    rows = select_prompts(args.prompts, args.limit)
    print(json.dumps({"model": args.model, "calls": len(rows), "max_tokens": args.max_tokens,
                      "reasoning_effort": args.reasoning_effort,
                      "items": [{"id": r["id"], "level": r["level"]} for r in rows],
                      "execute": args.execute}, indent=2))
    if not args.execute:
        return
    if not sys.stdin.isatty():
        parser.error("Run interactively in your own terminal; do not pipe credentials")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as saved:
        key = getpass.getpass("OpenRouter experiment key (hidden input): ").strip()
        if not key:
            parser.error("No key supplied")
        for row in rows:
            try:
                response = complete(row["prompt"], args.model, key, args.max_tokens, args.reasoning_effort)
                result = {"id": row["id"], "level": row["level"],
                          "response": response.pop("text"), **response}
                saved.write(json.dumps(result) + "\n")
                saved.flush()
                print(f'Saved {row["id"]} / {row["level"]}')
            except RuntimeError as error:
                print(f"Stopped: {error}. No retry.", file=sys.stderr)
                raise SystemExit(1) from None



if __name__ == "__main__":
    main()
