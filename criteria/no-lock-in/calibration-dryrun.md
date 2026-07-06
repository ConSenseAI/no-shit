# `no-lock-in` — calibration dry-run (2026-07-06)

**What this is:** an engineering dry-run of the CRITERION-SPEC §7.1 human-calibration gate, run with **blind LLM adjudicators** as a cheap proxy — *not* the formal gate (`human_calibration` stays `0`). Run against **v0.1.1** (post-review); findings folded into **v0.1.2**. Method identical to the `no-dark-patterns` dry-run.

## Method

- **Panel:** two isolated, model-diverse LLM raters — A (Sonnet), B (Opus) — each reading **SPEC.md §1–§5 only**, blind to the corpus, changelog, §6–§11, and each other.
- **Items:** 23 id-stripped scenarios covering **every 0.1.1 boundary**: the 30/90-day stated-completion bands, human-fulfillment-with-SLA, the downgrade hostage, per-type formats, item truncation, prerequisite transitivity, both confirmation-link twins, the debt and ID-strength lines, pre-selected retention, per-item-only export, the combined-flow interstitial targeting rule, terms-deactivation, passive-reset, the messaging lattice (recovery-window marketing, straggler band, 7-day default), lawful retention, pending-vs-elapsed delivery, the gated-path check-7 rule, and the extended data-deletion-control scope (the Alexa shape).
- **Task:** checks exercised → cascade arm quoted → verdict per §5; **AMBIGUOUS** mandated over guessing; rule-vs-instinct divergences logged separately.
- **Key:** authored before launch.

## Results

| Metric | Result |
|---|---|
| Inter-rater verdict agreement | **23/23 (κ = 1.00)** — identical distributions (4 PASS / 7 CONDITIONAL / 12 FAIL) |
| Rater A vs corrected key | **23/23** |
| Rater B vs corrected key | **23/23** |
| AMBIGUOUS (underdetermined) | **0** (both raters) |
| Check-attribution agreement | 22/23 (S11 — see P-2) |

**Author-key errata — the blind panel outperformed the key (recorded as the method working):** the key mis-keyed S22 (designed to probe check 7's gated-path rule, but the stated paywall also trips check 1 — both raters correctly ruled FAIL(1) with check 7's caveat fail enumerated; the key said CONDITIONAL); and under-enumerated S19 (checks 2/3's `unobserved` arms co-fire with check 1's — both raters enumerated all three).

Boundary behavior worth naming:
- **The combined-flow targeting rule held under blindness** (S12): both raters allocated the two subscription pitches to `no-subscription-trap` and counted only the data-retention interstitial here → CONDITIONAL, both logging the "feels like a gauntlet" instinct against it.
- **The extended check-6 scope read naturally** (S7): both raters applied the data-deletion-control scope to the Alexa-shaped scenario without prompting — rater B flagging the one real text gap (P-1).
- **Every 0.1.1 band placed correctly from both sides**: 45d vs 120d, pending vs elapsed, staff-with-SLA, debt vs payment-gate, ID-strength, straggler vs recurring, disclosed lawful retention.

## Panel findings → v0.1.2

- **P-1 — derivatives of covered data (rater B, S7).** Check 6's "covered data" did not literally say that derivative representations (transcripts of deleted recordings) count; B ruled FAIL on the anti-evasion reading and named the missing clause. Fix: the statement now says covered data **includes derivative representations of it** (transcripts, previews, indexes) — a transcode escape hatch would gut the guarantee.
- **P-2 — dual enumeration on the downgrade hostage (S11 attribution split).** A enumerated checks {1,3}; B routed to {1} via §3's "already check 1's fail" sentence. Check 3's fail arm literally fires (held data absent from the delivered artifact) and its `na` arm does not exempt the case, so per §5's enumerate-all rule the correct label is **{1,3}**. Fix: the §3 sentence now says "check 1's fail — and check 3's where the delivered artifact omits held data; enumerate both"; `viol-syn-downgrade-hostage` relabeled 1,3.

## Watch-items for the formal §7.1 human gate (no rule changes)

Rule-over-instinct divergences, concentrated exactly where the strict/lenient lines were drawn — the likely human-gate pressure points:
1. The combined-flow targeting rule (three consecutive interstitials landing at CONDITIONAL for this criterion reads counter-intuitive even when correct — S12, both raters).
2. The ID-upload-to-delete `conditional` (instinct says FAIL — S17, both raters).
3. The single-straggler tolerance (S14) and the 30–90-day automated band (S5) reading as soft on providers.
4. Staff-fulfilled export capped at CONDITIONAL (S1, rater A).

## Still open after this run

- P-1's derivatives wording and P-2's dual-enumeration rule are new text — not yet re-probed.
- The §11 queue's deliberately-unclosed items stand: export frequency caps, post-termination retrieval grace (candidate caveat check), documented-but-vacuous format docs, the messaging-facet split (D-28).
- The formal §7.1 gate: ≥2 independent **human** adjudicators against a pre-registered target (not yet registered for this criterion — register before adjudication; expected to mirror the siblings').

## Run 2 — cross-vendor panel (Claude + GPT-5), full 64-row corpus, formal blinded packets (2026-07-06)

**Method.** As the siblings': the formal adjudication kit (`../ADJUDICATION.md`), all 64 rows, id- and annotation-stripped, per-rater shuffled variants, §1–§5 excerpt only. First out-of-lineage rater (GPT-5, load-bearing); Claude is author-lineage, discounted.

**Results.** **64/64 inter-rater (κ = 1.00); hard subset (n=22) 22/22; both raters 64/64 against the key; zero underdetermined** — including P-1/P-2's 0.1.2 wording, previously un-re-probed.

**Flags → actions (0.1.5).**

- **S57 `bound-syn-single-offer`** — rater 1 raised exactly the watch-list's combined-flow targeting question (a subscription-pitch reading would route the offer to the sibling's check 3 and change what the flow counts). Resolved to the keyed CONDITIONAL; the row now states its pitch target ("keep your account") and the absence of any subscription pitch, making the targeting rule literally decidable from the row (0.1.5).
- Silence semantics → mold T-12 (CRITERION-SPEC 0.6.1); originating note in the `no-subscription-trap` run-3 record.

**Evidence:** `calibration/panel-2026-07-06/`. Not the formal gate; `human_calibration` stays 0.
