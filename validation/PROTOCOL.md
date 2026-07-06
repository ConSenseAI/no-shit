# Validation Study — Protocol

**Version:** 0.1.0 · **Status:** draft — **not frozen; not yet a pre-registration**
**Serves:** design doc *Threat Model & Validation* (the study design and kill criteria) and *MVP — Stage 0* (deliverable 2); CRITERION-SPEC §7.2 (the candidate → active gate this study runs) and §7.3 (the record that travels with every attestation)
**Evidence base:** [`notes/audit-accuracy.md`](../notes/audit-accuracy.md) — what is known about maximizing true/false accuracy on claims about software, and why this protocol is shaped the way it is

This document operationalizes the validation study the design doc commits to. It becomes the **pre-registration** when frozen; until then it is a draft under open revision. The design doc states *what* the study must establish and the kill criteria; CRITERION-SPEC states the per-criterion gate mechanics; this document is the *how* — corpus construction, pools, procedure, metrics, decision rules, blinding, and reporting — in one place, versioned, so the study cannot drift into measuring something easier than the question.

---

## 1. Purpose and the gated decision

The study tests the protocol's keystone assumption (design doc, Assumptions A1): **multi-model LLM consensus can reliably judge anti-extraction criteria in real products.** Stage 1 — the pipeline, the TEE deployment, attestation issuance — proceeds only if the stated kill criteria are cleared. If they are not cleared after the permitted rubric iterations, the architecture changes (criterion narrowing, behavioral migration, human-in-the-loop) or the project stops, and **that result is published with the same prominence a pass would have been.** A negative result is a real contribution; an unpublished negative result is indistinguishable from marketing.

Project-level and criterion-level views are the same study: the Stage 0 → Stage 1 gate is CRITERION-SPEC §7.2 (candidate → active) run over the Stage 0 criterion set (`no-subscription-trap`, `no-dark-patterns`, `no-lock-in`). The project-kill condition is the design doc's: **no criterion clears its thresholds after two rubric iterations.** Per-criterion shippability is decided per (pool × mode) cell.

**Prerequisite, not part of this study:** each criterion passes its §7.1 human-calibration gate first (draft → candidate). All three targets are pre-registered in the manifests (κ ≥ 0.8 aggregate AND ≥80% exact-verdict on boundary+adversarial pooled). The §7.1 results feed this study as the adjudication-error prior (§3).

## 2. Registration discipline

- **Freeze.** This protocol is frozen by a tagged commit **before any study execution** — before the sealed corpus is run against any pipeline configuration. Git history is the timestamp; the freeze commit hash appears in the study report.
- **Finalized at freeze, not before:** kill thresholds and miss budgets (pending the corpus-attainability audit, §4.3), sealed-corpus size and fold plan (§8), and model-pool membership (§5). The *structure* of every decision rule is fixed by this document now; only the named numeric parameters await the corpus audit.
- **After freeze:** amendments are versioned addenda, disclosed in the report. Metrics, thresholds, and decision rules MUST NOT change after any sealed-corpus result is known — a gate whose metric moves after unblinding is not a gate (the same stated-in-advance discipline as CRITERION-SPEC §7.1/§7.2).

## 3. Study questions — measured separately, reported decomposed

Audit error factors as **observation error × adjudication error** (`notes/audit-accuracy.md`). The study measures the factors separately before measuring them end-to-end, because they fail differently and are fixed differently:

- **Q1 — Adjudication:** given established facts, do the criterion's decision arms produce the right verdict? Instrument: the **public corpora** (rows are the adjudication substrate, CRITERION-SPEC §6.4) under blind raters. The §7.1 human gates are the formal instrument; blind model-diverse LLM panels extend n cheaply. Prior evidence: dry-runs at κ = 1.00 on `no-dark-patterns` (22/22) and `no-lock-in` (23/23) — strong signal, small n.
- **Q2 — Observation:** can the audit establish those facts from the artifact — probe agents against a live product, the code audit against a submission? Instrument: **product fixtures with known ground truth** (§4). This is the unmeasured half and the study's main work.
- **Q3 — End-to-end:** the §7.2 gate itself — per-criterion false-pass / false-flag per (pool × mode) cell on the **sealed** corpus, full pipeline, no shortcuts.

**Miss-classification rule (normative):** every end-to-end error is classified before the aggregate is reported: **observation failure** (the facts were wrong or unrecovered — remedy: probe/prompt-bundle redesign), **adjudication failure** (facts right, verdict wrong — remedy: decision-arm redesign), or **harness failure** (pipeline bug — remedy: fix and disclose). Kill-criteria numbers are published decomposed as well as aggregate, so a fixable observation problem cannot kill a sound criterion, and vice versa.

## 4. Corpus and fixtures

### 4.1 Adjudication benchmark

The public corpora (~150 labeled rows across the three criteria, versioned) are the Q1 benchmark and already exist. Additions before the study: **contamination checks** — the corpora are public by design, so pool models may have trained on them; the study probes for memorization (models asked to reproduce or identify corpus rows) and reports exposure. Where contamination is found, Q1 confirmation uses held-back paraphrase variants of the affected rows. The corpus-leakage worry applies to this benchmark with full force: memorized rows inflate exactly the factor the dry-runs suggest is solved.

### 4.2 Observation fixtures and the sealed corpus

Fixture classes, per the design doc's selection-bias handling (stated there before it bites, imported here as normative steps):

1. **Documented-real:** products with documented extractive behavior (FTC dark-pattern actions, CPPA enforcement targets, UIGuard/DarkBench-documented examples) and documented-clean controls, drawn from open-source and client-side software where ground truth is inspectable.
2. **Synthetic variants:** extraction patterns from documented closed-source cases re-implemented into otherwise-clean open codebases — labeled as synthetic in the record, **scored separately** in the report so the external-validity caveat travels with the results, and **provenance-blinded to the judges** (§9).
3. **Client-side middle:** proprietary products with decompilable or observably-documented behavior.
4. **Behavioral fixtures:** live or locally-instantiable products the probe engine can exercise (export, deletion, cancellation flows) with known ground truth — including **defeat-device fixtures** built to detect auditors and behave (the Volkswagen attack), which anchor the behavioral red-team lane.

Rows are product-level with **per-criterion labels** (a product violating `no-subscription-trap` may be clean for `no-lock-in`); one fixture therefore serves multiple cells. Every criterion's **injection canaries** are carried into the sealed set — a canary that passes blocks that rubric/pool version outright (design doc, Threat Model §1).

**Sealed-corpus discipline:** sized per CRITERION-SPEC §7.2 — at least `3/ε` on the measured side per threshold: **≥60 violating-labeled and ≥30 clean-labeled per criterion** per measured cell (the sealed corpus MAY be shared across a criterion's cells). Never published before the study; the sealed manifest's hash is committed publicly at freeze and the corpus is revealed with the report. The design doc's ~50/~50 sketch is superseded by these sizing floors.

### 4.3 Corpus-attainability audit (before thresholds are finalized)

The intersection "documented-extractive AND code-inspectable" may be far thinner than the floors require — documented extraction and inspectable ground truth are anti-correlated by construction. So, per the design doc: attainability is audited **first**, the real-world slice is reported (not papered over), synthetic variants fill the shortfall with the caveat attached, and if a credible code-auditable extractive corpus cannot be assembled at all, that finding is published and the protocol's weight shifts to the behavioral tier. Kill thresholds and miss budgets are finalized only after this audit — a pass on an unrepresentative corpus would be worse than a fail.

## 5. Model pools and cells

Both confidentiality tiers run against the same sealed corpus (design doc, Code confidentiality): the **frontier pool** (3–5 frontier models via external APIs) and the **enclave-contained pool** (open-weight models from unrelated training lineages). Pool membership is fixed at freeze and recorded in the frozen protocol; "diversity" for the enclave pool means unrelated training lineages, not API vendors. The study converts the tiers' quality gap from an assumption into a number.

Expected cell matrix for the Stage 0 set (final declaration lives in each criterion's manifest):

| Criterion | Mode(s) | Frontier pool | Enclave pool |
|---|---|---|---|
| `no-subscription-trap` | behavioral | measured | n/a (no submitted code) |
| `no-lock-in` | behavioral | measured | n/a (no submitted code) |
| `no-dark-patterns` | code + behavioral | measured × 2 | measured × 2 (code-audit keystone) |

Six measured cells. `no-dark-patterns` is where the two-pool comparison and the code-mode question land first.

## 6. Procedure under test

The unit under test is the reference pipeline exactly as it will ship — same prompt bundles, probe scripts, consensus mechanism, and confidence thresholds, versioned. Normative properties (from Architecture §2 as refined by `notes/audit-accuracy.md`):

- **Untrusted-data quoting:** all submitted code, content, page output, and probe observations reach judges as quoted untrusted data, never as instructions (CRITERION-SPEC §9).
- **Execution-grounding preference:** where a check's deciding facts are establishable by running the artifact — probes against live products, or building and exercising a submission — the pipeline MUST prefer execution-established facts over read-inferred ones; conclusions supported only by reading cap confidence (pressure toward CONDITIONAL/INDETERMINATE rather than a confidently-read PASS).
- **Evidence-terminated escalation:** unanimity with execution-verified evidence → accept. Any split → refinement rounds whose **output is a designed discriminating check** — an experiment or code-level observation whose outcome differs depending on which side is right — and whose result the next round consumes. Judges aggregate evidence chains (probe outputs, command receipts, file:line citations), never auditor prose. Forced decisions at max rounds are marked lower-confidence and routed to review.
- **Skepticism asymmetry:** adversarial-refutation effort concentrates on provisional PASSes — the protocol-killing error — matching the kill thresholds' 5%/10% asymmetry.

## 7. Metrics and decision rules

Per (criterion × pool × mode) cell, on the sealed corpus: **false-pass rate**, **false-flag rate**, **INDETERMINATE rate**, **inter-model agreement**, **consensus-failure (forced-decision) frequency**, and **measured token/$ cost per audit**. Alongside, the §3 decomposition: each miss classified observation / adjudication / harness.

**Kill criteria** (design doc, verbatim; numeric finalization at freeze per §4.3):

- False-pass rate above **~5%** per criterion → that criterion is not shippable. A wrong PASS at scale launders extraction; it is worse than no protocol.
- False-flag rate above **~10%** per criterion → also not shippable. Honest creators will not pay for coin-flip audits.
- No criterion clears after **two rubric iterations** → the architecture changes or the project stops.

**Statistics, stated in advance:** gates are evaluated on **point estimates** (as the design doc's thresholds read), with **exact Clopper–Pearson intervals published alongside every rate** and the one-sided 95% upper bound reported as the headline uncertainty. The honesty this buys, illustrated at the sizing floor: with n = 60 violating, zero misses gives a point estimate of 0% with a one-sided 95% upper bound of ~4.9% — the floor is exactly where a perfect run first *resolves* the 5% gate; even one miss (point 1.7%) pushes the upper bound to ~7.9%. A point-estimate pass near the threshold is weak evidence and the report will say so; n above the floor buys headroom, which is the real target (`notes/audit-accuracy.md` §design-pressure: per-check error compounds across a 7–8-check criterion).

## 8. Rubric iterations and sealed-set burn

Two rubric iterations are permitted per the kill criteria. An **iteration** is a versioned change to a criterion, its audit artifact, or the pipeline configuration made in response to sealed-corpus results. Each sealed-corpus run *burns* the rows it exposes to the team: results on re-used rows are no longer clean evidence. Handling: at freeze the sealed corpus is **partitioned into iteration folds** (run 1 on fold A; a post-iteration run on fold A + fresh fold B; final numbers cite the freshest fold per cell), with fold sizes meeting the §4.2 floors per run where attainable — else the shortfall and the re-use are disclosed per cell. Material criterion changes during iteration re-trigger the mold's gates (a §7.1 re-gate for changed decision arms; re-validation attaches per artifact, CRITERION-SPEC §9).

## 9. Blinding and roles

- **Ground-truth labelers ≠ pipeline operators.** Fixture labels are assigned from documentation/enforcement records and manual inspection by people who do not run the pipeline; label disputes are resolved before the study, not after a miss.
- **Judges see no labels and no provenance.** Synthetic-vs-real is hidden from the pipeline (it is a report-time stratification), as is expected verdict. Id-stripping follows the corpus dry-run discipline.
- **Corrected-key discipline:** where blind raters outperform an authored key, the key is corrected and the erratum recorded — the dry-runs already produced two such errata; that is the method working.

## 10. Costs

Measured token/$ per audit, per cell, replaces the design doc's $5–30 inference estimate — which is plausibly 10–100× low for real codebases. If measured costs break the fee model, the report says so before pricing does (feeds Economics).

## 11. Reporting and publication

Published regardless of outcome: the frozen protocol and freeze hash; per-cell tables (all §7 metrics, decomposed misses, CIs); consensus-failure and forced-decision frequencies; canary results; synthetic-vs-real stratification; the corpus-attainability audit; raw per-fixture verdicts (sealed corpus revealed post-study); cost tables; all errata; deviations from this protocol. The report is the citable Schelling-point artifact — corpus + methodology + measured error rates is what a regulator's staff, journalist, or standards body reaches for — and the natural joint publication with the dark-patterns research community. Measured rates then travel with every attestation (CRITERION-SPEC §7.3).

## 12. Open parameters (resolve before freeze)

1. Final kill thresholds, miss budgets, and n per cell — after the §4.3 attainability audit.
2. Sealed-corpus fold plan and per-fold sizes (§8).
3. Pool membership lists, with model/version pins (§5).
4. Fixture build plan and budget — synthetic-variant engineering and defeat-device fixtures are the expected long pole.
5. Ground-truth labeling protocol: who labels, independence requirements, dispute resolution (§9).
6. Contamination-check method and threshold for the public corpora (§4.1).
7. Behavioral-probe validation detail: the design doc validates probe accuracy "separately and more cheaply" — decide whether that runs as a section of this study (current lean: yes, as the behavioral cells + the defeat-device red-team lane) or as a sibling protocol.
8. Whether §7.1 human-gate adjudicators may also serve as study labelers (independence trade-off vs. calibrated-rater scarcity).

## 13. Changelog

- **0.1.0** (2026-07-06) — initial draft. Encodes the design doc's study design, selection-bias handling, and kill criteria; CRITERION-SPEC §7.2 gate mechanics (per-(pool × mode) cells, 3/ε sizing, sealed-corpus discipline); and the `notes/audit-accuracy.md` methodology requirements registered in advance: the observation × adjudication decomposition with per-miss classification, execution-grounding preference with reading-only confidence caps, evidence-terminated (discriminating-check) escalation, skepticism asymmetry toward provisional PASSes, sealed-set fold plan for the two-iteration allowance, and point-estimate gates with published exact CIs. Not frozen; open parameters listed in §12.
