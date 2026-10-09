# Prototype semantics v0.1.0

These are explicit, reversible implementation choices rather than finalized research
semantics. JSON examples are stored in `data/examples/private.jsonl`.

1. Facts are Boolean or null (unknown). Missing declared facts are invalid, not false.
   Conditions and exceptions use only facts; requirements use only actions. Expressions
   are atoms, true/false, `{"not": expr}`, `{"and": [expr, ...]}`, or `{"or": [...]}`.
2. Actions are independently performed/withheld Boolean propositions. All combinations
   are available; no alternative, partial action or complement is implied. There is
   no default obligation for an unconstrained action.
3. A rule applies iff its condition is true and its exception false. The exception
   disables that rule; it does not itself create permission or an obligation.
4. Overrides form a directed acyclic graph, interpreted transitively. Cycles and
   invalid IDs are rejected. There are no numeric priorities or implicit tie breakers.
5. An applicable higher rule defeats an applicable lower rule iff their requirements
   have no joint action model. All applicable rules participate in defeat, including
   rules themselves defeated. This explicit choice can defeat both lower rules in
   an alternating priority chain; it is not a claim of universal defeasible semantics.
   Higher-order incompatible subsets are not resolved by pairwise override edges
   unless an incompatible pair is present.
6. Surviving requirements are conjoined; all satisfying action assignments are gold.
   No assignments means `unresolved_conflict`. Otherwise, any defeat yields
   `priority_resolved`; no defeats yields `consistent`. Unknown facts always yield
   `insufficient_facts`, with exact known-fact completion results retained privately.
7. Conflict certificates enumerate every subset-minimal incompatible subset of
   surviving rules. The smallest cardinality is stored separately. A three-rule
   certificate is only emitted when no conflicting singleton or pair occurs inside it.

The trace stores active rules, defeat edges and surviving constraints. Surviving rules
need not all be necessary for an individual action decision: they are not claimed to
be a minimal explanation. Active pre-defeat opposition is available from the active
set, but potential conflict across possible facts is not yet a separate dataset label.

The solver is exhaustive, limited to 10 facts, 10 actions, and 12 rules. Runtime is
exponential, especially unknown completions and conflict-subset enumeration. Defaults
are deliberately tiny. It is an exact reference under these semantics, not a scalable
general policy engine. Tests hand-check decisive cases and conflict minimality.
