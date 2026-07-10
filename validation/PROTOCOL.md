# Validation Study — Protocol

**Version:** 0.1.6 · **Status:** draft — **not frozen; not yet a pre-registration**
**Serves:** design doc *Threat Model & Validation* (the study design and kill criteria) and *MVP — Stage 0* (deliverable 2); CRITERION-SPEC §7.2 (the candidate → active gate this study runs) and §7.3 (the record that travels with every attestation)
**Evidence base:** [`notes/audit-accuracy.md`](../notes/audit-accuracy.md) — what is known about maximizing true/false accuracy on claims about software, and why this protocol is shaped the way it is

This document operationalizes the validation study the design doc commits to. It becomes the **pre-registration** when frozen; until then it is a draft under open revision. The design doc states *what* the study must establish and the kill criteria; CRITERION-SPEC states the per-criterion gate mechanics; this document is the *how* — corpus construction, pools, procedure, metrics, decision rules, blinding, and reporting — in one place, versioned, so the study cannot drift into measuring something easier than the question.

---

## 1. Purpose and the gated decision

The study tests the protocol's keystone assumption (design doc, Assumptions A1): **multi-model LLM consensus can reliably judge anti-extraction criteria in real products.** Stage 1 — the pipeline, the TEE deployment, attestation issuance — proceeds only if the stated kill criteria are cleared. If they are not cleared after the permitted rubric iterations, the architecture changes (criterion narrowing, behavioral migration, human-in-the-loop) or the project stops, and **that result is published with the same prominence a pass would have been.** A negative result is a real contribution; an unpublished negative result is indistinguishable from marketing.

Project-level and criterion-level views are the same study: the Stage 0 → Stage 1 gate is CRITERION-SPEC §7.2 (candidate → active) run over the Stage 0 criterion set (`no-subscription-trap`, `no-dark-patterns`, `no-lock-in`). The project-kill condition is the design doc's: **no criterion clears its thresholds after two rubric iterations.** Per-criterion shippability is decided per (pool × mode) cell.

**Prerequisite, not part of this study:** each criterion passes its §7.1 calibration gate first (draft → candidate; recomposed at CRITERION-SPEC 0.7.0/T-13 into a full-corpus lineage-diverse **reliability** component — human or model adjudicators — plus a stratified **human-anchor** sample). All targets are pre-registered in the manifests (reliability: κ ≥ 0.8 aggregate AND ≥80% exact-verdict on boundary+adversarial pooled; anchor: ≥80% exact-verdict on the sample). The §7.1 results feed this study as the adjudication-error prior (§3).

## 2. Registration discipline

- **Freeze.** This protocol is frozen by a tagged commit **before any study execution** — before the sealed corpus is run against any pipeline configuration. Git history is the timestamp; the freeze commit hash appears in the study report.
- **Finalized at freeze, not before:** kill thresholds and miss budgets (pending the corpus-attainability audit, §4.3), sealed-corpus size and fold plan (§8), and model-pool membership (§5). The *structure* of every decision rule is fixed by this document now; only the named numeric parameters await the corpus audit.
- **After freeze:** amendments are versioned addenda, disclosed in the report. Metrics, thresholds, and decision rules MUST NOT change after any sealed-corpus result is known — a gate whose metric moves after unblinding is not a gate (the same stated-in-advance discipline as CRITERION-SPEC §7.1/§7.2).

## 3. Study questions — measured separately, reported decomposed

Audit error factors as **observation error × adjudication error** (`notes/audit-accuracy.md`). The study measures the factors separately before measuring them end-to-end, because they fail differently and are fixed differently:

- **Q1 — Adjudication:** given established facts, do the criterion's decision arms produce the right verdict? Instrument: the **public corpora** (rows are the adjudication substrate, CRITERION-SPEC §6.4) under blind raters. The §7.1 calibration gates are the formal instrument (lineage-diverse reliability panels + human anchors, CRITERION-SPEC 0.7.0); engineering panels extend n cheaply. Prior evidence: same-lineage dry-runs at κ = 1.00 on `no-dark-patterns` (22/22) and `no-lock-in` (23/23), and an uncounted cross-vendor full-corpus panel (Claude + GPT-5) at 152/152 across all three criteria — the best current estimate of the adjudication-error prior.
- **Q2 — Observation:** can the audit establish those facts from the artifact — probe agents against a live product, the code audit against a submission? Instrument: **product fixtures with known ground truth** (§4). This is the unmeasured half and the study's main work. Behavioral-probe validation runs **inside this study** — the behavioral cells plus the defeat-device red-team lane *are* the probe-accuracy measurement (resolves §12.7); a sibling protocol would re-build the same fixtures and blinding for no added power, and the probe-engine capabilities the attainability audit enumerates (census, windows, rate sampling, dual-origin — `ATTAINABILITY.md` §4) are exactly what these cells exercise.
- **Q3 — End-to-end:** the §7.2 gate itself — per-criterion false-pass / false-flag per (pool × mode) cell on the **sealed** corpus, full pipeline, no shortcuts.

**Miss-classification rule (normative):** every end-to-end error is classified before the aggregate is reported: **observation failure** (the facts were wrong or unrecovered — remedy: probe/prompt-bundle redesign), **adjudication failure** (facts right, verdict wrong — remedy: decision-arm redesign), or **harness failure** (pipeline bug — remedy: fix and disclose). Kill-criteria numbers are published decomposed as well as aggregate, so a fixable observation problem cannot kill a sound criterion, and vice versa.

## 4. Corpus and fixtures

### 4.1 Adjudication benchmark and contamination checks

The public corpora (~150 labeled rows across the three criteria, versioned) are the Q1 benchmark and already exist. They are public by design — first published 2026-07-05 and crawlable since — so the working assumption is that pool-model training exposure is a *when*, not an *if*, and vendor-stated training cutoffs are treated as unverifiable metadata: **every pool model is checked.** Memorized rows inflate exactly the factor the dry-runs suggest is solved; the protocol below (resolves §12.6) bounds detectable exposure and removes its effect from Q1.

**Probe battery** — per pool model × criterion corpus, full corpus, **tools and browsing disabled** (the corpora sit on the public web; a probe that can retrieve is not measuring recall). Run at freeze against the pinned pools; re-run for any pool amendment (§2):

1. **Verbatim continuation.** Each scenario is split at its midpoint and the model prompted to continue the prefix. Fires on a contiguous verbatim match ≥ 20 tokens or ROUGE-L ≥ 0.6 against the held-out suffix — the rows' fictional product names and specific values make suffixes high-entropy, so competence cannot reconstruct them.
2. **Membership quiz** (DCQ-style — Golchin & Surdeanu, TACL 2025 — adapted). The true row text is presented among three sealed **same-facts paraphrases**; the model picks which appeared in the published corpus. All options carry identical deciding facts, so knowledge of the underlying enforcement case cannot answer — only surface-form memory can — which makes the probe valid on enforcement-anchored rows, where "knows the FTC case" is expected and is not contamination. Fires on above-chance selection over the corpus (one-sided binomial against 25%, p < 0.05).
3. **Metadata recall.** Given a scenario's text and corpus context, the model is asked for the row's `example_id`, expected verdict, and failing checks. Corroborating signal only — IDs are semi-descriptive and partially guessable from content — scored as an exact multi-field match.

**What is deliberately not a signal: verdict accuracy without the rules.** The rows were written to be decidable (T-9), so a capable model scores well uncontaminated. Label leakage is measured only by the **paraphrase differential**: the model adjudicates original and paraphrased rows under the real rules, and a significant original-minus-paraphrase exact-verdict gap (one-sided paired test, p < 0.05, stratified sample ≥ 30 rows) fires at corpus level.

**Decision rule.** Row-level: probe 1 fires, or probe 3 matches exactly → the row is *exposed* for that model. Corpus-level: probe 2 fires, or the paraphrase differential fires, or > 5% of rows are row-level exposed → the corpus is *exposed* for that model. Consequences: exposure is reported per model × criterion regardless of magnitude (§11); for exposed rows and corpora, that model's Q1 numbers are computed on the paraphrase variants as primary, with original-row numbers reported as secondary. The triggers are deliberately conservative — the remediation is cheap, so a false flag costs little and a false clear costs the benchmark — and the numeric fire thresholds are finalized together with the pool pins at freeze (§12.3).

**Paraphrase-set discipline.** A full held-back paraphrase set is built at freeze: every row re-surfaced with every deciding fact and the expected verdict preserved, verified by someone other than its author (a paraphrase that shifts a deciding fact is a benchmark bug, fixed before use); the generating model is disclosed and excluded from the pools. The set stays sealed until the report publishes it — publication burns it, and any later re-check regenerates fresh variants.

**Limitation, stated in advance:** a clean battery does not prove absence — models can be shaped by training exposure without extractable recall. The battery bounds *detectable* memorization; the paraphrase differential catches the non-extractable remainder where it matters (labels); residual undetected exposure is a stated Q1 caveat, not a silent assumption.

### 4.2 Observation fixtures and the sealed corpus

Fixture classes, per the design doc's selection-bias handling (stated there before it bites, imported here as normative steps):

1. **Documented-real:** products with documented extractive behavior (FTC dark-pattern actions, CPPA enforcement targets, UIGuard/DarkBench-documented examples) and documented-clean controls, drawn from open-source and client-side software where ground truth is inspectable.
2. **Synthetic variants:** extraction patterns from documented closed-source cases re-implemented into otherwise-clean open codebases — labeled as synthetic in the record, **scored separately** in the report so the external-validity caveat travels with the results, and **provenance-blinded to the judges** (§9).
3. **Client-side middle:** proprietary products with decompilable or observably-documented behavior.
4. **Behavioral fixtures:** live or locally-instantiable products the probe engine can exercise (export, deletion, cancellation flows) with known ground truth — including **defeat-device fixtures** built to detect auditors and behave (the Volkswagen attack), which anchor the behavioral red-team lane.

Rows are product-level with **per-criterion labels** (a product violating `no-subscription-trap` may be clean for `no-lock-in`); one fixture therefore serves multiple cells. Every criterion's **injection canaries** are carried into the sealed set — a canary that passes blocks that rubric/pool version outright (design doc, Threat Model §1).

**Sealed-corpus discipline:** sized per CRITERION-SPEC §7.2 — at least `3/ε` on the measured side per threshold: **≥60 violating-labeled and ≥30 clean-labeled per criterion** per measured cell (the sealed corpus MAY be shared across a criterion's cells). Never published before the study; the sealed manifest's hash is committed publicly at freeze and the corpus is revealed with the report. The design doc's ~50/~50 sketch is superseded by these sizing floors.

**The build plan for these classes** — the shared fixture platform (virtual clock, messaging capture, state seeding, support personas), host-bench assignments, six build lanes, QA gates, manifest schema, and sequencing to freeze — is drafted at [`FIXTURES.md`](FIXTURES.md) (§12.4); its numeric parameters (budget, QA thresholds, the §12.9 observation parameters) are fixed at freeze.

### 4.3 Corpus-attainability audit (before thresholds are finalized)

The intersection "documented-extractive AND code-inspectable" may be far thinner than the floors require — documented extraction and inspectable ground truth are anti-correlated by construction. So, per the design doc: attainability is audited **first**, the real-world slice is reported (not papered over), synthetic variants fill the shortfall with the caveat attached, and if a credible code-auditable extractive corpus cannot be assembled at all, that finding is published and the protocol's weight shifts to the behavioral tier. Kill thresholds and miss budgets are finalized only after this audit — a pass on an unrepresentative corpus would be worse than a fail.

**The audit is drafted at [`ATTAINABILITY.md`](ATTAINABILITY.md):** demand analysis from the cell matrix, a full observation/fixture classification of all 152 public-corpus rows, findings O-1…O-10 (probe-engine and fixture-platform requirements), and the dated supply survey. Its finding O-10 sharpens this section's worry: the public corpus is 100% attainable *as owned fixtures*; the anti-correlation lands on the **live** side (backend-truth facts unobservable, multi-week windows, rate sampling), which is what the synthetic share ends up pricing.

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

- **Ground-truth labelers ≠ pipeline operators.** Fixture labels are assigned by people who do not run the pipeline; label disputes are resolved before the study — a disputed fixture is dropped or re-labeled, never re-argued after a miss.
- **Every label carries its basis, date, and scope** (resolves §12.5, on the attainability audit's supply classes — `ATTAINABILITY.md` §5–§6). Four bases, in descending ground-truth strength:
  1. **Enforcement-exhibit** — the fixture re-implements a flow documented in a public enforcement record; the label claims fidelity-to-exhibit at the record's date, not live truth. Adjudicated/fined cases outrank commitments-without-admission.
  2. **Construction** — implanted variants and unmodified-baseline hosts, labeled from the build spec and verified against it by someone other than the builder (a builder never solely labels their own implant).
  3. **Execution-verified** — the labeler executed the flow first-party and recorded the evidence (export delivered and diffed, deletion confirmed post-window), with the census/window discipline attached (`no-lock-in` cleans; platform-mandate cancels, scoped to the mandated flow).
  4. **Inspection** — documented manual inspection where no stronger basis exists (`no-dark-patterns` cleans on live products): **two independent labelers minimum**, disagreement resolved before sealing.

  Label records — basis, evidence, dates, labeler roles — are published with the sealed corpus after the study.
- **§7.1 adjudicators MAY serve as study labelers** (resolves §12.8). The calibration gates run on the *public* corpora and labeling runs on the *sealed* corpus — disjoint row sets by construction, which is what the independence concern actually requires. Two constraints: nobody labels and later adjudicates the same fixture (this binds any post-iteration re-gate that touches sealed rows), and the overlap is disclosed in the §7.1 and §9 records. Rationale: the T-13 recomposition made anchor humans the scarce class; reusing their calibration for labeling is efficient once same-row contamination is excluded.
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
4. Fixture build plan and budget — synthetic-variant engineering and defeat-device fixtures are the expected long pole. **Plan drafted (0.1.4) at [`FIXTURES.md`](FIXTURES.md):** six lanes over a four-service platform; the E4 defeat lane confirmed as the long pole. Remaining for freeze: the dollar budget and QA-gate numerics.
5. ~~Ground-truth labeling protocol~~ — **resolved (0.1.3, §9):** four label bases (enforcement-exhibit, construction, execution-verified, inspection) each carrying basis/date/scope; builder-independence; two-labeler minimum for inspection-basis; pre-study dispute resolution; label records published post-study.
6. ~~Contamination-check method and threshold for the public corpora~~ — **resolved (0.1.5, §4.1):** tool-less probe battery per pool model (verbatim continuation; same-facts membership quiz; metadata recall as corroboration) plus the paraphrase differential for label leakage; two-tier row/corpus decision rule with conservative triggers; exposed rows re-measured on the sealed paraphrase set; exposure reported per model × criterion. Numeric fire thresholds finalize with the pool pins at freeze.
7. ~~Behavioral-probe validation placement~~ — **resolved (0.1.3, §3 Q2):** runs inside this study as the behavioral cells + the defeat-device red-team lane; no sibling protocol.
8. ~~§7.1 adjudicators as study labelers~~ — **resolved (0.1.3, §9):** permitted across disjoint row sets (public corpora vs. sealed corpus); same-fixture label-then-adjudicate forbidden; overlap disclosed.
9. Observation-procedure parameters surfaced by the attainability audit (`ATTAINABILITY.md` §4): per-rate-fact **trial counts** and decision rules (O-4); pre-registered **observation-window lengths** for every longitudinal fact, per cell (O-1); the **surface-census definition** that scopes absence claims (O-2); **vision-capable judging** as a pool-membership constraint where depiction facts are in scope (O-7, binds §12.3). **Proposals drafted** at [`FIXTURES.md`](FIXTURES.md) §7, and **expanded to row grain (0.1.6)** at [`OBSERVATION-PARAMS.md`](OBSERVATION-PARAMS.md): a 17-class window registry over all 152 public rows, the census definition with per-criterion keyword lists, per-rate-fact trial rules with the detection-vs-certification asymmetry worked, and the `ui*` vision-rows enumeration binding §12.3. Pinned at freeze.

## 13. Changelog

- **0.1.6** (2026-07-10) — §12.9's proposals expanded to row grain at [`OBSERVATION-PARAMS.md`](OBSERVATION-PARAMS.md) 0.1.0 (17-class window registry with fixture clock scripts and pre-registered live windows; surface-census definition with the absence-vs-burial split and per-criterion keyword lists; rate-fact trial rules incl. the clean-certification n ≥ 23 proposal; vision-rows enumeration). The item remains open until freeze pins the numerics. No methodology changes.

- **0.1.5** (2026-07-09) — resolves §12.6: §4.1 becomes the contamination-check protocol — every-pool-model scoping (vendor cutoffs treated as unverifiable), tool-less probe battery (verbatim continuation; membership quiz adapted from the Data Contamination Quiz with same-facts paraphrase options so case knowledge cannot answer; metadata recall as corroboration), the paraphrase differential as the only valid label-leakage signal (the rows are decidable by competence, so raw verdict accuracy proves nothing), a two-tier row/corpus decision rule with deliberately conservative triggers (the remediation is cheap), and the sealed fact-preserving paraphrase set (independently verified, generator disclosed and pool-excluded, burned by publication).

- **0.1.4** (2026-07-09) — §12.4's plan half drafted at [`FIXTURES.md`](FIXTURES.md) 0.1.0 (four-service fixture platform, host-bench assignments, six build lanes, pre-registered QA gates including SusBench-style indistinguishability, F0–F3 sequencing, budget shape); §12.9's parameters get drafted proposals there (its §7). §4.2 links the plan. Both items remain open until freeze pins the budget and numerics. No methodology changes.

- **0.1.3** (2026-07-09) — resolves three §12 open parameters on the attainability audit's material: §12.5 → the §9 labeling protocol (four label bases with basis/date/scope, builder-independence, two-labeler inspection minimum, pre-study dispute resolution, post-study label-record publication); §12.7 → probe validation runs in-study as the behavioral cells + red-team lane (§3 Q2); §12.8 → adjudicator/labeler overlap permitted across disjoint row sets with same-fixture exclusion and disclosure (§9). Remaining open: §12 items 1–4, 6, 9.

- **0.1.2** (2026-07-08) — §4.3 links the drafted corpus-attainability audit (`ATTAINABILITY.md`); §12 gains item 9 (observation-procedure parameters the audit surfaced: rate-fact trial counts, pre-registered window lengths, surface-census definition, vision-capable pool constraint) and an item-8 note syncing the adjudicator/labeler trade-off to the T-13 recomposition. No methodology changes.

- **0.1.1** (2026-07-06) — §1 prerequisite synced to the §7.1 calibration-gate recomposition (CRITERION-SPEC 0.7.0, T-13): reliability component (full corpus, lineage-diverse, human or model) plus human-anchor sample; targets restated. No methodology changes.

- **0.1.0** (2026-07-06) — initial draft. Encodes the design doc's study design, selection-bias handling, and kill criteria; CRITERION-SPEC §7.2 gate mechanics (per-(pool × mode) cells, 3/ε sizing, sealed-corpus discipline); and the `notes/audit-accuracy.md` methodology requirements registered in advance: the observation × adjudication decomposition with per-miss classification, execution-grounding preference with reading-only confidence caps, evidence-terminated (discriminating-check) escalation, skepticism asymmetry toward provisional PASSes, sealed-set fold plan for the two-iteration allowance, and point-estimate gates with published exact CIs. Not frozen; open parameters listed in §12.
