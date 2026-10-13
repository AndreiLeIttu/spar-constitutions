# User-run OpenRouter smoke test

## Generate scenarios from formal cases

The scenario generator now reads `prompts/policy/scenario.txt`. Supply formal
Instance objects as JSONL, or reuse historical private dataset records:

```powershell
python -m scripts.build_dataset --source data/examples/private.jsonl --model MODEL_ID --count 1
python -m scripts.build_dataset --source data/examples/private.jsonl --model MODEL_ID --count 1 --execute
```

The first command previews the filled prompt. The second makes one generation call
and writes `data/runs/generated-scenarios/`. Choose a new `--output` for later runs.
Change the prompt file, `--context`, or `--presentation` to alter how the case is
written. Context defaults to `auto`: one model call chooses the domain, assigns
concrete predicate/action meanings, and writes the policy and scenario. To request
a domain, use `--context "customer support"`. The old `--setting` option is an alias.
Rules, fact truth values, and priorities remain fixed; definitions are saved in
the grounded `formal` object and shared by all three presentations. The original
input is retained as `source_formal`. Inspect the chosen context and mappings with:

```powershell
$case = Get-Content data/runs/generated-scenarios/private.jsonl | ConvertFrom-Json
$case.generation.candidate | ConvertTo-Json -Depth 20
```

For re-running an old input with the new prompt, use a fresh output directory; old
saved scenarios are not rewritten. Solver answers are recomputed. Generated
prose is recorded as unverified, not automatically accepted as semantically faithful.

To evaluate those new prompts, pass
`--prompts data/runs/generated-scenarios/prompts.jsonl` to `scripts.run_openrouter`.
Then score against `data/runs/generated-scenarios/private.jsonl`. That one-case dataset
has exactly three paired prompts, so all three can be covered by the default smoke run.

## Evaluate saved prompts

Create a separate experiment key at https://openrouter.ai/settings/keys with a
small credit limit (for example $1), no periodic reset, and an expiry if available.
Do not use an account-management key. A token cap is not a dollar cap: model pricing,
input tokens and reasoning tokens also matter. Use the key's provider-side limit.

Choose an exact model ID from OpenRouter, replacing MODEL_ID below. In your own
PowerShell terminal, outside the agent's tool execution:

```powershell
python -m scripts.run_openrouter --model MODEL_ID
python -m scripts.run_openrouter --model MODEL_ID --execute
```

The first previews the plan without credentials or network calls. The second asks
for hidden key input, sends the first instance's three rendering prompts, and saves
responses and usage in ignored `data/runs/openrouter-smoke/responses.jsonl`.
The runner refuses to overwrite an existing output; choose another `--output` for
a new run. Default cap is three calls with 512 output tokens each. No retries occur
because timed-out calls may already be charged. Repeated invocations can spend more.
No authentication headers or raw error bodies are logged. Temperature zero is not
a determinism guarantee and provider routing may vary. No paid call has been run here.

```powershell
python -m evaluation.runner --dataset data/examples/private.jsonl --responses data/runs/openrouter-smoke/responses.jsonl --output data/runs/openrouter-smoke/scores.json
```

The scorer expects all 54 prompts. Inspect the three returned per-item results for
this smoke check: unattempted rows count as missing, so overall dataset accuracy is
not the selected subset's accuracy. This is a connectivity check, not a research pilot.

## Credential access

Git ignore prevents tracking; it does not prevent reading. An env file can still be
read with filesystem access, and inherited environment variables can be read by
commands. A secret store available to the same OS user may also be accessible.
Hidden terminal input avoids chat, repo, history and persistent key files, but the
request process sees the key. It is not isolation from sufficiently privileged
local processes. Review the runner before executing it with credentials.

For a real boundary, use a separate executor/account/service that holds the key,
deny the agent access to it, and enforce request quotas, allowed models and spending
limits there. A proxy whose code/configuration the agent can modify is not that
boundary. The local terminal approach reduces accidental exposure without claiming
the key is inaccessible to all local software.
