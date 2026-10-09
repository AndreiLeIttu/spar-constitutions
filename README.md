# SPAR policy reasoning benchmark

A small offline prototype inspired by SciR's generation → rendering → evaluation
pipeline. `research-context.md` was used as the current research direction; both
handoff documents remain local and are ignored by Git.

## Run on Windows

Python 3.11+ and Git suffice. There are no runtime dependencies or API calls.
Run from the project root:

```powershell
python -m unittest discover -s tests -v
python -m scripts.build_dataset --seed 7 --count 18 --output data/examples
```

This creates 18 formal instances and 54 prompts across formal, clear, and fragmented
presentations. The nine families repeat twice: these are diagnostic fixtures, not
an independent research evaluation set. `--distractors 2` adds rules separately
from the rendering choice, but may change applicability/outcomes; gold is always
recomputed. These controls are a starting point, not a validated difficulty scale.

Only send `prompts.jsonl` to respondents. `private.jsonl` contains formal sources,
hidden reference results, traces, certificates, rendering validation and provenance.
The private record is useful for researchers, not a model input. IDs join the files.
Each action is a Boolean decision; several combinations may be admissible.

Saved responses use one JSONL row per instance and rendering:

```json
{"id":"policy-7-0000","level":"clear","response":{"status":"consistent","action":{"send":true,"log":false},"conflict_certificate":[]}}
```

```powershell
python -m evaluation.runner --dataset data/examples/private.jsonl --responses responses.jsonl --output scores.json
```

Scoring checks status, action admissibility, and certificate separately, with joint
accuracy and invalid-format rate. Missing responses count as failures against the
full expected prompt set. Unknown/duplicate keys are rejected. Model/provider adapters
and paid evaluations are intentionally pending configuration. Do not describe the
gold solver self-check as evidence of model performance.

## Architecture for someone new to SciR

SciR has three scientific tracks. Each creates a formal problem, translates it
into text, optionally obfuscates its chunks with an LLM and inverse reconstruction,
then evaluates model answers. Its scientific solvers are track-specific. Here the
same stages serve a new policy task; SciR is a reference checkout, not a runtime dependency.

```text
generation/policy/generate.py → formal Instance
                                  ↓
policy/solver.py              → hidden answer + rule trace + conflict certificates
                                  ↓
generation/policy/transform.py → formal / clear / fragmented prompts
                                  ↓
external respondent          → saved response JSONL
                                  ↓
evaluation/runner.py         → strict parsing + separate scores
```

| SciR component | This setup | Purpose |
| --- | --- | --- |
| `generation/<track>/generate.py` | `generation/policy/generate.py` | Seeded formal instances |
| Track-specific solvers | `policy/solver.py` | Exact finite action enumeration |
| `generation/<track>/transform.py` | `generation/policy/transform.py` | Text variants from the same source |
| `generation/api.py` | Pending provider adapter | Future LLM generation/perturbation |
| `prompts/obfuscation_styles/` | `prompts/policy/` | Future perturbation/reconstruction prompts |
| `evaluation/extraction.py`, runner | Same directory pattern | Parse and score saved responses |

`policy/schema.py` defines and validates the JSON representation. `policy/fidelity.py`
compares a recovered formalization with gold over **every Boolean fact assignment**
in the declared vocabulary and returns a counterexample on disagreement. It requires
aligned action/predicate definitions and checks status and admissible actions, not
structural recovery or prose meaning. Original scenario fact extraction must also
be assessed separately. No formalizer is connected yet.

See [the semantics specification](docs/semantics.md) for the prototype's explicit
choices and [reference provenance](docs/provenance.md) for the pinned SciR checkout.

## Current limits and next milestone

The generator is a small set of patterns, not broad parametric sampling. It supports
conditional mandatory Boolean requirements, exceptions, pairwise explicit defeat,
higher-order conflicts, and unknown facts. It does not yet support permission
modalities, derived-fact inference chains, temporal rules, or real constitutions.

Clear and fragmented text uses deterministic templates, with explicit parentheses
and negation. Fragmentation changes order and document grouping; it is not yet
natural paraphrase/roleplay. Validation records say `by_construction`, with independent
reconstruction and human audits `not_performed`. Future LLM output must remain
unverified until reviewed; a round trip is evidence, not a guarantee.

Before a research pilot: add independently sampled structures and measured complexity
controls, configure direct/decomposition/formalization baselines, validate renderings,
and split by formal structure with all paired variants together. Safety-sensitive
execution tasks and shared failures require separate study; this prototype measures
benign hypothetical policy assessment only.
