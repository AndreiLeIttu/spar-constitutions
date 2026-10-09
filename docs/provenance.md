# SciR reference and provenance

Repository: https://github.com/idiap/SciR

Pinned commit: `d6985141e3b9b6a02bf596034935fbd485ffadf3`.
The source is locally available in `references/scir`, ignored by the outer repository.
Recreate it with `./scripts/fetch_reference.ps1`; `references/scir.json` records the pin.
No SciR datasets or scientific solvers are needed for this prototype.

Inspected generation/abstract.py, generation/deduction/generate.py and transform.py,
evaluation/runner.py and extraction.py, repository README and license. The new track
uses the separation of generation, rendering, and evaluation as its skeleton. It does
not import or copy SciR implementations. SciR remains an independent GPL-3.0-only
reference with all upstream notices intact. No distribution license has been assigned
to the newly authored code yet. Revisit compatibility if upstream code is adapted
or the project is distributed.

SciR v2's induction tasks may admit several valid answers; our policy scorer likewise
accepts any admissible action assignment. SciR's LLM chunk obfuscation and inverse
reconstruction are future interfaces here, not completed functionality.

The two local handoff documents are excluded individually, rather than excluding
all Markdown. Project documentation is versionable. No other literature claims
from the handoffs were independently checked during this implementation.
