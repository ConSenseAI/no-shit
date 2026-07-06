# `no-dark-patterns` — calibration dry-run (2026-07-06)

**What this is:** an engineering dry-run of the CRITERION-SPEC §7.1 human-calibration gate, run with **blind LLM adjudicators** as a cheap proxy — *not* the formal gate (that requires independent human adjudicators; `human_calibration` stays `0`). Run against **v0.1.2** (post-review, post-0.6.0-migration); findings folded into **v0.1.3**.

## Method

- **Panel:** two isolated LLM instances, model-diverse per the sibling criterion's precedent — rater A (Sonnet), rater B (Opus). Each blind: instructed to read **SPEC.md §1–§5 only** (scope, checks, aggregation) and nothing else in the repo (no corpus, no §10–§12, no changelog, no calibration files).
- **Items:** 22 scenarios, id-stripped and paraphrased, shuffled across checks — 17 re-statements of the corpus's contested anchors (the §12 stress queue) plus **5 new engineered probes** for un-anchored edges: persistence-parity materiality (6-vs-12-month TTL), a *labeled* one-expand reject, rotating **non-equivalent** flash sales (the deliberately un-closed D-21 lane — the rules as written should yield PASS), a clearly-scoped sticker timer (check 1 "material decision" pass side), and a layout-shift charge control (check 7's inadvertent-activation shape).
- **Task:** per scenario — checks exercised, decision arm applied (quoted), verdict per §5, with **AMBIGUOUS** mandated over guessing when the written rules underdetermine, and rule-vs-instinct divergences logged separately.
- **Key:** authored expected outcomes fixed before launch.

## Results

| Metric | Result |
|---|---|
| Inter-rater verdict agreement | **22/22 (κ = 1.00)** |
| Rater A vs authored key | **22/22** |
| Rater B vs authored key | **22/22** |
| AMBIGUOUS (underdetermined) cases | **0** (both raters) |
| Check-attribution agreement | 21/22 (S20 — see P-1) |

All 22 items are engineered hard/boundary cases, so this result is effectively a 100% hard-subset score at dry-run scale. Highlights that were the run's actual questions:

- **Check 6 strictness held under blindness.** Both raters ruled the one-expand reject FAIL (S3) — including the *labeled* "Reject options…" variant (S21) — and both logged it as a rule-vs-instinct divergence, i.e., they applied the strict rule while personally reading it as caveat-grade. The exact §12-predicted pressure point, now with evidence that the *rule text* is unambiguous even where the *policy* is contestable.
- **Check 5's three-band lane placed cleanly** from all three sides (S14 ordinary-emphasis pass · S1 subordinated conditional · S8 ghost fail).
- **Rule-following beat vibes where designed:** rotating non-equivalent sales (S17) → PASS from both raters (each signal literally true, no equivalent relaunch — the D-21 lane stays open *by decision*, not by accident); 6-vs-12-month persistence asymmetry (S7) → FAIL from both, each noting the rule admits no magnitude tolerance.
- **Mode-join premise validated:** the behavioral-only fabrication evidence (S6) and code-only fabrication evidence (S13) each produced confident FAILs from single-mode facts — the §4.7 lattice's assumption that either mode can establish a fail alone.
- **The 0.1.1 shapes all decided literally:** consent wall (S11), withdrawal maze (S15), reject-resets (S19, with check 8 co-enumerated), type-carousel aggregate (S5), depiction shaming (S10), factual-consequence pass (S4), inadvertent-activation charge (S12), fake selected state (S20).

## Panel findings → v0.1.3

- **P-1 — check 4 ↔ check 5 ownership line (from S20's attribution split).** Rater A enumerated check 4 on the fake-selected-state probe via the umbrella clause ("materially misstate its effect"); rater B matched the key (5,7) and explicitly reasoned "label accurate → not C4" on S12. Verdict unaffected (both FAIL), but the umbrella invited double-ownership of a fact 0.1.1 deliberately placed in check 5. Fix: check 4's boundary now states — check 4 owns what the control *says*; check 5 owns what the screen *shows* (rendered selection/progress state).
- **P-2 — check 1's "immediately" (from rater B's latent-rule note on S9).** The conditional arm read "equivalent offer relaunches *immediately* after expiry"; S9's relaunch follows a ~6-hour overnight gap. B decided it correctly via the governing serial-flash concept but named the word as a latent gap. Fix: "relaunches promptly or on a recurring cadence (an overnight gap does not break seriality)."
- **Resolved near-miss, no change:** rater B queried whether a "downgrade / canceling backup" prompt falls under the `no-subscription-trap` carve-out, and resolved it correctly from the fact-based boundary (a feature-downgrade offer prompt is not the subscription-cancellation flow). Recorded as evidence the 0.1.1/0.1.6 boundary restatement works under blindness.

## Watch-items for the formal §7.1 human gate (no rule changes now)

Deliberate-strict positions where both/either LLM rater logged instinct divergence — the places human adjudicators are most likely to balk, and therefore the places the pre-registered target's hard-subset floor will be earned or lost:

1. Check 6: one-expand reject = FAIL (both raters; policy contest, not text ambiguity — loosening stays free in the T-4 window if the human gate demands it).
2. Check 6: persistence parity with no de-minimis tolerance (S7's 6-vs-12-month FAIL felt immaterial to both raters; whether a materiality threshold belongs is explicitly a human-gate question — §12).
3. Check 8: the cross-type aggregate (≥4) failing a product whose every prompt type stays within its per-type limit (rater B: "mild discomfort," applied as written).
4. Check 5: the subordinated-link conditional band reading as harsh for a readable, in-flow link (rater A).

## Still un-probed / open after this run

- D-15: pass-side near-anchors for the "material" qualifiers (check 1 "material decision," check 4 "materially misstates") — S22 anchors one; author corpus rows at the next corpus round.
- D-21: rotating **non-equivalent** flash sales remain a deliberate pass (confirmed by both raters); candidate prevalence predicate if probes show it common in the wild.
- P-2's reworded seriality boundary (gap tolerance) — new wording, not yet re-probed.
- Probe-script-dependent lanes: tenure-gated fabrication, time-bomb enrollment, defeat-device composition (design doc, Architecture §7 territory).
- The formal §7.1 gate itself: ≥2 independent **human** adjudicators against a target **pre-registered before adjudication begins** (expected to mirror the sibling's: κ ≥ 0.8 aggregate AND ≥80% exact-verdict on boundary+adversarial pooled). This dry-run's 22/22 is evidence of operationalization quality, not a gate pass.

## Run 2 — cross-vendor panel (Claude + GPT-5), full 46-row corpus, formal blinded packets (2026-07-06)

**Method.** As the sibling's run 3: the formal adjudication kit (`../ADJUDICATION.md`), all 46 rows, id- and annotation-stripped, per-rater shuffled variants, §1–§5 excerpt only. First out-of-lineage rater (GPT-5, load-bearing); Claude is author-lineage, discounted.

**Results.** **46/46 inter-rater (κ = 1.00); hard subset (n=15) 15/15; both raters 46/46 against the key; zero underdetermined** — including the 24 rows run 1 never saw.

**Flags (no text changes).**

- **S05 `adv-syn-first-layer-asymmetry`** — rater-1 instinct wants a caveat for a labeled, in-place one-expand; the strict check-6 rule applied as written. The §12 watch-item now carries cross-lineage rule-over-instinct evidence; the strict-vs-caveat policy question still goes to the human gate.
- **S14 `bound-syn-variant-gated-consent`** — instinct wants fail; the `unobserved` arm's own exemplar governs. Applied cleanly.
- Silence semantics → mold T-12 (CRITERION-SPEC 0.6.1); see the sibling's run-3 record for the originating note.

**Evidence:** `calibration/panel-2026-07-06/`. Not the formal gate; `human_calibration` stays 0.
