# SPAR policy reasoning benchmark

A small offline prototype inspired by SciR's generation → rendering → evaluation
pipeline.

## Running on Windows

For a one-case end-to-end paid demo, run `python -m scripts.run_demo --execute`
in your own terminal. Defaults are GPT-6.1 Sol, low reasoning, automatic context,
one scenario-generation call and three answer calls. The key is entered once without
echo. Outputs include readable `formal.preview.json`, `dataset/preview.json`, and
`walkthrough.md`, plus raw responses and scores under `data/runs/paid-demo`.
Without `--execute`, this command previews the plan and makes no calls.
Choose a fresh `--output` directory for repeat runs. A one-case result is a smoke
test; generated grounding and prose still need review before research conclusions.

Formal generation also writes a `.preview.json` companion beside its JSONL output.
Dataset generation automatically writes a formatted `preview.json` containing all
completed private records. These previews include hidden answers and are researcher
artifacts, not respondent inputs.

Python 3.11+ and Git suffice. There are no third-party runtime dependencies.
Run from the project root:

```powershell
python -m unittest discover -s tests -v
python -m generation.formal --representation propositional --count 5 --facts 3 --actions 2 --rules 4 --priority-edges 1 --output data/runs/formal.jsonl
python -m scripts.build_dataset --source data/runs/formal.jsonl --model MODEL_ID --count 1
```

The formal generator runs offline and writes new formal objects plus solver results.
The build_dataset command previews a scenario-generation prompt without calling a model. Replace
MODEL_ID with an OpenRouter model and add `--execute` in your own terminal to generate
one scenario. The key is entered without echo. Outputs go to a new directory under
`data/runs/generated-scenarios`; use `--output` to choose another directory.

The generator reads `prompts/policy/scenario.txt`. Edit that file to change its
instructions, or pass `--prompt PATH`. `--context` and `--presentation` fill its
placeholders. Input is JSONL containing formal `Instance` objects (or existing private
dataset records). The solver recomputes gold before each model-written scenario.
With `--context auto` (the default), the model chooses a concrete context and assigns
meanings to all predicate and action IDs in the same call that writes the scenario.
Use `--context "customer support"` to request a particular setting; `--setting` is
retained as an alias. No fixed context list applies. Definitions are frozen after
grounding and reused across formal, canonical clear, and scenario prompts.
Private records preserve the original `source_formal` and the grounded `formal`
object; `generation.candidate` contains the chosen context, mappings, and prose.
Code retains all facts, rules and priorities rather than asking the model to rewrite
them. Mapping validation and unchanged solver results do not prove that the prose
or concrete meanings introduce no hidden implications.
Generated prose remains explicitly **unverified**; JSON validation is not semantic
validation. No reconstruction or human audit is performed automatically.

`generation/formal.py` randomly samples Boolean formula trees, rule conditions,
exceptions, fact states and acyclic priorities, rather than cycling through handcrafted
cases. Choose `--condition-depth`, `--requirement-depth`, `--exception-rate`,
`--unknown-rate`, `--priority-edges` and `--seed` to control it. Formula depth bounds
AND/OR nesting, with literals at depth zero. Counts and priority edges are exact;
depths are maxima and rates are probabilities, not guaranteed frequencies. Outcomes
are measured by the solver, not preselected or balanced. Reusing a seed/configuration
reproduces formal objects; model-written prose need not be reproducible.

`--representation` currently supports **propositional** only. Objects use JSON as
serialization, with named Boolean requirements and explicit priority edges under
the recorded SPAR semantics; this is not plain classical implication or an implementation
of a standard defeasible calculus. A first-order backend would need domains, predicates,
quantifiers and a corresponding solver. It is not silently emulated by renaming atoms.
The initial definitions are abstract (`condition p1 holds`, `perform action a1`);
scenario generation now replaces them with concrete meanings and freezes those
meanings before creating text variants.

The nine handcrafted patterns have been removed from the generator. Existing
`data/examples/` files are retained as historical solver test fixtures and can supply
formal inputs for trying the new renderer. They are not a new independent benchmark.

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
full expected prompt set. Unknown/duplicate keys are rejected. An optional
[user-run OpenRouter smoke test](docs/openrouter.md) supports small direct-answer
experiments; model choice and paid execution remain user controlled. Do not describe the
gold solver self-check as evidence of model performance.



## Current limits and next milestone

Formal cases can be sampled offline or supplied as JSONL. The schema supports
conditional mandatory Boolean requirements, exceptions, pairwise explicit defeat,
higher-order conflicts, and unknown facts. It does not yet support permission
modalities, derived-fact inference chains, temporal rules, or real constitutions.

`generation/generate.py` reads the scenario prompt, calls a supplied model callback,
and records prompt/model provenance. `generation/render.py` supplies the deterministic
formal and clear baselines and shared task instructions. The legacy fragmented renderer
is available for old fixtures. `reconstruct.txt` and `perturb.txt` are still future
interfaces; they are not called by the generator. A round trip is evidence of fidelity,
not a guarantee.

Before a research pilot: add independently sampled structures and measured complexity
controls, configure direct/decomposition/formalization baselines, validate renderings,
and split by formal structure with all paired variants together. Safety-sensitive
execution tasks and shared failures require separate study; this prototype measures
benign hypothetical policy assessment only.
