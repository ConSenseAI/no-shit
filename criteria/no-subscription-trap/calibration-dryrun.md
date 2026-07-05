# `no-subscription-trap` — calibration dry-run

**Status:** proxy for the CRITERION-SPEC §7.1 human-calibration gate — **NOT the formal gate.** Run with blind LLM adjudicators on a synthetic, self-authored corpus. The manifest's `human_calibration` stays `0` until independent human adjudicators run the real gate.
**Date:** 2026-07-01

## Purpose

§7.1 asks: can ≥2 *independent* adjudicators, given only the checks, reproduce consistent verdicts on the corpus? If not, the checks are under-specified — fix them before building any pipeline. This dry-run approximates that with blind LLM adjudicators.

## Method

- Each adjudicator got the 7 checks + verdict rules only (no intended answers), and the corpus scenarios with the category / expected-verdict / checks-exercised columns **stripped**, ids neutralized to `EXnn`, order shuffled.
- Adjudicators are isolated LLM instances with no access to this repo or the author's key; the author (who wrote the checks) is not counted as a rater.
- Canary scenarios embed text addressed to the judge ("return PASS"); a rule instructed raters to ignore in-scenario instructions.

## Run 1 — two Sonnet adjudicators, 35 examples

| metric | result |
|---|---|
| inter-rater (A vs B) | 35/35 = 100% (κ = 1.00) |
| vs authored key | A 35/35, B 35/35 |

Injection canaries (3) all correctly FAIL; the `unobserved`→CONDITIONAL case works; all 5 boundary cases → CONDITIONAL. **Caveat:** self-authored corpus, each scenario cleanly exercising one facet — 100% shows the checks are *legible and self-consistent*, not that they survive messy real products.

### Run 1 side-findings (C-1, C-2)

Two findings from the rater transcripts about the *corpus and reporting conventions*, not the check boundaries (referenced from SPEC §5 and the corpus README):

- **C-1 — attribution noise on multi-check failures.** When several checks fail (e.g., `viol-syn-retention-maze`), raters agree on the FAIL verdict but cite different subsets of failing checks as "the" reason. Resolution: on FAIL, the attestation enumerates **all** failing blocking checks, never one primary check (SPEC §5, Attribution).
- **C-2 — `viol-adobe-etf` originally bundled an out-of-scope facet.** Raters correctly excluded the undisclosed early-termination *fee* as `transparent-pricing`'s domain; the in-scope violation is the obstructive cancellation path. The label was narrowed to checks 2,3.

## Run 2 — Sonnet + Opus (model-diverse), 40 examples (the 35 + 5 engineered-ambiguous probes)

| metric | result |
|---|---|
| inter-rater (Sonnet vs Opus), all 40 | 37/40 = 92.5% (κ = 0.87) |
| original 35 (stability across panels) | 35/35 = 100% |
| the 5 ambiguity probes | 2/5 agree |

All three disagreements land on the probes — exactly where designed:

| probe | Sonnet | Opus | fuzzy boundary |
|---|---|---|---|
| optional/skippable extra step (signup 2, cancel 4 incl. 1 skippable) | FAIL | CONDITIONAL | **check 2** — do optional steps count? (D-2) |
| auto-renew disclosure inside a collapsed accordion | FAIL | CONDITIONAL | **check 5** — is click-to-reveal "in-flow"? (D-3) |
| reliable, instant, non-expiring email-confirm link | FAIL | PASS | **check 1** — automated confirmation vs human channel? (D-1) |

The other two probes agreed (low-contrast decline link → both FAIL misdirection; persistent single dismissible offer → both CONDITIONAL). Injection canaries again FAILed correctly under both models, each explicitly stating it ignored the injected text.

κ math (all 40): observed agreement 0.925; chance agreement (marginals FAIL/PASS/COND ≈ Sonnet 24/10/6, Opus 21/11/8) ≈ 0.414; κ = (0.925 − 0.414)/(1 − 0.414) ≈ **0.87**.

## Interpretation

- κ = 0.87 clears the ≥0.8 bar and 92.5% clears ≥90% (the then-draft targets; the v0.1.3 pre-registration later dropped the ≥90% disjunct) — but the aggregate **masks the structure**: ~100% on ordinary cases, 40% on engineered-hard ones. Honest read: **the checks are reliable in the common case and have three specific fuzzy boundaries** (D-1/D-2/D-3 → SPEC §12).
- Model diversity earned its keep: the two-Sonnet panel agreed 100% on the ordinary set; the mixed Sonnet+Opus panel surfaced the splits a single-model panel hid. (This is why the default calibration panel is now Sonnet+Opus.)

## Limits (why this is a proxy, not the gate)

1. Synthetic, self-authored corpus → flattering; real products carry conflicting partial signals.
2. LLM adjudicators, not humans.
3. The condensed rubric handed to raters dropped some SPEC nuance (e.g., check 2's "required steps only"), which partly explains D-2 — a lesson for how faithfully the probe script must encode the checks.
4. "Model-diverse" here means two model families from one vendor (Sonnet + Opus, shared Anthropic lineage). The frontier pool's diversity standard is *unrelated training lineages*; a cross-vendor panel is stronger, and the formal study uses the actual pools.

## Re-probe — v0.1.1 validation (2026-07-01)

After applying the three §12 resolutions to checks 1/2/5, a fresh Sonnet+Opus panel re-adjudicated the five probes plus five ordinary anchors (10 blind items) using the *clarified* rubric.

| metric | run 2 (v0.1.0) | re-probe (v0.1.1) |
|---|---|---|
| the 3 previously-split probes | 0/3 agree | **3/3 agree** |
| all 10 items (probes + anchors) | — | **10/10 = 100%** |

The splits closed as designed: optional-step probe → both CONDITIONAL; accordion probe → both CONDITIONAL; reliable-email-confirm probe → both PASS. The five anchors held (clean→PASS, phone-wall→FAIL, injection canary→FAIL with the bait ignored, tiny-decline-link→FAIL, unobserved→CONDITIONAL). No regressions. Inter-rater reliability on the hard cases went 40% → 100%.

**Caveat unchanged:** still a proxy (synthetic corpus, LLM raters); the formal §7.1 gate still needs human adjudicators on real products.

## Re-probe — v0.1.3 validation (2026-07-02)

After the T-8 statement↔decision parity fixes (checks 1/3/4 fail-predicates widened, check 2's counting rule made explicit, check 3's volume rule added), a fresh blind Sonnet+Opus panel adjudicated **16 items**: the seven violating/adversarial rows touched by the fixes (incl. the two new fixtures `viol-syn-medium-switch` and `adv-syn-dismissible-gauntlet`), one injection-canary anchor, three clean anchors, and five boundary-stability items (incl. the three v0.1.1-calibrated probes). Same method as prior runs: rubric + neutralized scenarios only, no expected verdicts, in-scenario instructions to be ignored.

| metric | result |
|---|---|
| inter-rater (Sonnet vs Opus), verdict-level | **16/16 = 100% (κ = 1.00)** |
| vs authored key, verdict-level | Sonnet 16/16, Opus 16/16 |
| the 3 v0.1.1-calibrated probes (plus-one-step / persistent-offer / reliable-email-confirm) | unchanged: CONDITIONAL / CONDITIONAL / PASS |
| new ≥3-gauntlet boundary (4-offer gauntlet vs 2-offer flow) | both raters: FAIL vs CONDITIONAL — as decided |
| injection canary | FAIL under both; bait explicitly reported as ignored |

All seven T-8-touched rows now decide **literally** — medium-switch → FAIL(1), downgrade-only → FAIL, annual-lockstep → FAIL(4), expiring-confirm → FAIL(3), pause-resumes → FAIL(3,4), iliad → FAIL(2,3), buried-view → FAIL(2,3) — with no rater needing the worked-example charity the pre-0.1.3 cascades required.

**Residual attribution variance (C-1, expected):** on two multi-check FAILs the raters agreed on the verdict but cited different failing-check subsets (downgrade-only {1,3} vs {1}; phone-wall canary {1,2} vs {1}). Verdict-invariant, and exactly the noise the enumerate-all rule (CRITERION-SPEC §5.2) absorbs at attestation time — but worth watching at the formal gate, since "enumerate all" presumes raters agree on *which* checks fail.

**Caveats unchanged:** synthetic scenarios, LLM raters, same-vendor panel (limit 4). The formal §7.1 gate still needs independent human adjudicators.

## Next

- **v0.1.1 — done** (see first Re-probe): checks 1/2/5 clarified; splits closed 10/10.
- **v0.1.3 — done** (see second Re-probe): T-8 parity fixes validated 16/16 blind; the ≥3 gauntlet threshold behaved as decided but is a *new, engineered* boundary — stress it near the line (exactly three interstitials; mixed offer/survey/confirm compositions) in the next calibration round.
- **v0.1.5 — not yet probed:** the reviewer-pass boundary changes (check 6's notice-content line — vague / missing amount-date / non-actionable lead time → FAIL; check 5's cadence-only-in-ToS FAIL and earlier-screen weak placement; check 3's trick-wording prong; check 2's channel-gated `na`) shipped without a fresh panel. Fold them into the next calibration round together with the ≥3-gauntlet stress items. Also queued from the re-verify pass: check 5's "clearly and conspicuously" is operationalized as placement only — an adjacent-but-illegible disclosure (tiny / low-contrast) is an untested lane predating v0.1.5; define legibility or route it to `conditional` in the same round.
- **Formal §7.1 gate:** independent human adjudicators on a corpus that includes real (dated) products, not only synthetic fixtures — against the pre-registered target (κ ≥ 0.8 aggregate AND ≥80% exact-verdict on boundary+adversarial, fixed at v0.1.3).
