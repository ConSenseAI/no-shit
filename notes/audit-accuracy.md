# Audit Accuracy — Notes Before Building the Pipeline

**Status:** design note, 2026-07-06. Pre-pipeline. Captures what is known about maximizing true/false accuracy on claims about software, so the Stage 1 audit-engine design doesn't start naive. Nothing here changes the architecture today; it feeds *Architecture §2 (Audit Engine)* and *Threat Model & Validation* when pipeline design begins. A pointer lives in the design doc's Open Questions.

## The question

Every criterion check is a true/false-ish question about a piece of software, and the protocol's viability rests on answering those questions with a known, published error rate (assumption A1 — the keystone). The design question underneath: given unbounded model access and budget, what actually maximizes accuracy? As of mid-2026 the answer is settled enough to plan around.

## What the evidence says (mid-2026)

1. **No prompting or ensembling technique alone reaches very-high accuracy.** Majority voting and self-consistency plateau around 97–98% because model errors are *correlated*: the mistakes that survive a many-model vote are precisely the ones where every model shares the same wrong prior about how the code behaves. Multi-agent debate systems beat single models but top out around 72–88% on open-domain claims (DebateCV / FC-MAD / Tool-MAD lineage — markers for a future lit review; last checked 2026-07-06).
2. **Execution-grounding closes the gap.** Reduce the claim to an experiment run against the actual software; use models as orchestrators and interpreters, not as the oracle. Observed behavior gets checkable questions to ~99.9%+, bounded by harness bugs rather than model priors — the program doesn't care what the models expect it to do. Static code-reading sits around 90–95% on nontrivial questions.
3. **At very high accuracy, ambiguity dominates.** One error per thousand means ill-posed questions, not model mistakes, become the main error source. Interpretation must be pinned before anyone investigates.
4. **Debate must terminate in evidence, not rhetoric.** Judges are demonstrably persuadable by confidently argued falsehoods (the CW-POR failure mode). Verdicts should aggregate evidence chains — probe outputs, command receipts, file:line citations — never auditor prose.
5. **Escalation should be adaptive, not fixed-effort.** Unanimous and execution-verified → accept cheaply. Any split → escalate: more auditors, deeper investigation, and the key move — force the disagreeing sides to design an experiment whose outcome differs depending on which side is right, then run it.

Software is the one domain where the very-high bar is reachable at all, because the ground truth is executable. Anti-extraction properties are behavioral by nature — a structural advantage of this niche.

## The factorization (the most important single point)

**Audit error = observation error × adjudication error.**

- *Adjudication:* given established facts, do the criterion's decision arms produce the right verdict? The criterion-layer corpus dry-runs measure exactly this. Current evidence: blind, model-diverse raters mapping described facts → verdicts hit κ = 1.00 on no-lock-in (23/23) and no-dark-patterns (22/22). Strong early signal, small n.
- *Observation:* can the audit reliably establish those facts from the artifact — probe agents against a live product, or the code audit against a submission? **Unmeasured.** This is the half where execution-grounding does the work, and it is most of what the validation study is actually about.

Consequences:

- The validation study should measure the two factors separately before measuring them end-to-end. The public corpora already are the adjudication benchmark; observation validation needs product fixtures — live products with known ground truth, or synthetic products built to violate/satisfy specific checks (the synthetic-variant plan in Threat Model & Validation covers part of this).
- A check can fail validation two different ways, with two different remedies: facts unrecoverable → redesign the probe or prompt bundle; rules unadjudicable → redesign the decision arm. Kill-criteria reporting should distinguish them, or a fixable observation problem will kill a sound criterion — and vice versa.
- The corpus-leakage worry (Open Questions: keeping the corpus out of model training data) applies to the adjudication benchmark with full force — memorized corpora inflate exactly the factor we currently believe is solved.

## What the current design already gets right

Recorded so future-us doesn't re-derive it — the architecture is closer to the evidence than the pressure list below might suggest:

- **Behavioral probe mode is execution-grounding by construction** (run the export, diff it against holdings; complete the deletion, re-query through another surface). The design doc already notes probe observations "sit much closer to ground truth than code judgment."
- **The criteria layer is the ambiguity triage, done once, publicly, versioned** — decision arms, boundary corpus rows, κ calibration gates, rule-vs-instinct divergence logs. Cheaper and stronger than per-audit triage, and it targets what becomes the dominant error source at high accuracy.
- **Unanimity-for-clean-pass is asymmetric skepticism in skeleton form** — any single model flagging blocks a clean pass, and forced decisions route to review at lower confidence instead of coercing a binary.
- **Four-state verdicts and `unobserved` check outcomes are the honest-residual valve** — refuse rather than absorb the error.
- **Cross-model disagreement as injection signal** and **challenge/revocation as the ecosystem-level adversarial layer** are both decorrelation plays the literature endorses.

## Design pressure — what the pipeline must get right

1. **Code mode is the weak flank; execution-ground it.** Reading submitted code is the ~90–95% regime. Where a check permits, the audit should *build and run* the submission — drive flows headlessly, execute the export path, observe emitted requests — and reading-only conclusions should cap confidence (pressure toward CONDITIONAL/INDETERMINATE rather than a confidently-read PASS). Two knock-ons: (a) this imports an **execution-sandbox requirement into the TEE design** — submitted code is hostile input (Threat Model §1–2), and running it inside the audit environment must not expose the pipeline's keys, judge context, or network egress; (b) it blurs the code/behavioral mode boundary — a code audit that executes the submission is a behavioral probe against a locally-instantiated product, and CRITERION-SPEC's mode system (`either` checks, per-mode audit artifacts) already gives that a place to live.
2. **Refinement rounds should trade in experiments, not prose.** The current consensus mechanism escalates disagreement into rounds where models "critically analyze each other's reasoning" — exactly the shape the persuasion-override results warn about: a confidently wrong (or injection-steered) judge can talk the pool into a false PASS. Keep the escalation skeleton; change the currency. A refinement round's output should be a *designed discriminating check* — an experiment or code-level observation whose outcome differs depending on which side is right — and the next round consumes its result. Judges aggregate receipts, not arguments. This also strengthens the injection story: instructions embedded in code can steer prose deliberation, but they cannot change what the program does when run.
3. **Skepticism budget goes disproportionately to provisional PASSes.** A false PASS at scale launders extraction — the kill criteria already price the asymmetry (~5% false-pass vs. ~10% false-flag tolerance) — while a false FAIL is vendor-recoverable through dispute and re-run. Adversarial-refutation effort (skeptic roles whose only job is to break the provisional answer) should be concentrated where the protocol-killing error lives.
4. **Per-check error compounds at the attestation level.** ~0.999 per check across a 7–8-check criterion is ~99.2–99.3% per attestation on blocking checks alone — and that assumes independence, which correlated model errors violate in the unfavorable direction. The kill thresholds are minimums that the reading-based regime can plausibly clear; the reason execution-grounding matters is *headroom* — the buyer-facing liability story ("measured error rates Z") strengthens with every factor below the threshold, and per-check targets must be set with verdict-level compounding in mind.
5. **The residual stays honest.** Checks that cannot be reduced to experiments (intent, taste) remain in the ~98–99% ensemble regime. Options, in order: redesign into executable form; accept INDETERMINATE-heavy behavior and say so in the criterion's validation record; kill the check. Overall attainable accuracy is a function of the executable fraction of the check set — worth tracking as a criterion-authoring metric from now on.

## Cheap moves available now (pre-pipeline)

- When authoring or revising criteria, prefer decision arms whose facts are establishable by execution or observation over arms that require reading intent, and note the executable fraction in the calibration record.
- Keep growing the adjudication benchmark — it is the half we can validate essentially for free — and keep dry-runs blind so author-key errors keep getting caught (the two errata in the no-lock-in round are the method working, not failing).
- When the validation study is designed, write the observation/adjudication split and the discriminating-experiment escalation into the methodology *before* the study runs, so the kill-criteria numbers decompose instead of arriving as one unexplainable aggregate.
