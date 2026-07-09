# Corpus-Attainability Audit

**Version:** 0.1.0 · **Status:** draft
**Serves:** [`PROTOCOL.md`](PROTOCOL.md) §4.3 (the audit that precedes threshold finalization), §12.1 (kill thresholds / miss budgets / n per cell), §12.4 (fixture build plan and budget)
**Audited against:** `no-subscription-trap` 0.1.10 · `no-dark-patterns` 0.1.8 · `no-lock-in` 0.1.6 · CRITERION-SPEC 0.7.0
**Supply survey as of:** 2026-07-08 (external-world facts in §5 are dated estimates, not standing truth)

PROTOCOL §4.3's worry, verbatim: *the intersection "documented-extractive AND code-inspectable" may be far thinner than the floors require — documented extraction and inspectable ground truth are anti-correlated by construction.* This audit measures that worry from both ends before any threshold is finalized: **demand** (what the sealed corpus must contain, in what form, derived from the cell matrix and the public corpora) and **supply** (what the real world actually offers with defensible ground truth). It finalizes nothing — per PROTOCOL §2, numeric parameters are fixed at freeze; this document is the evidence they are fixed *on*.

---

## 1. What "attainable" means here

A fixture is attainable for a cell when both halves hold:

1. **Ground truth is defensible** — the label rests on public enforcement records, construction (we built it), or inspection by independent labelers (PROTOCOL §9), not on the team's read of a live product it doesn't control.
2. **The observation procedure can reach the deciding facts** — the probe script (or code audit, for `no-dark-patterns`' code mode) can actually obtain the facts the label depends on, within a bounded window, per each SPEC's §9 binding.

These fail independently. An FTC-documented cancellation maze has unimpeachable ground truth and is usually **unobservable live** (remediated under order). A live product's export flow is observable today and has **no defensible label** until someone inspects and labels it. The audit's job is to say where both hold at once, and at what cost.

## 2. Demand — what the sealed corpus must contain

From PROTOCOL §4.2/§5 and CRITERION-SPEC §7.2:

| Criterion | Measured cells | Sealed floor (shareable across the criterion's cells) | Required fixture form |
|---|---|---|---|
| `no-subscription-trap` | behavioral × frontier | ≥60 violating + ≥30 clean | probe-exercisable: live or locally-instantiable signup/trial/cancel flows |
| `no-lock-in` | behavioral × frontier | ≥60 violating + ≥30 clean | probe-exercisable: accounts with seeded content; export/deletion flows; messaging capture |
| `no-dark-patterns` | (code + behavioral) × (frontier + enclave) — 4 cells | ≥60 violating + ≥30 clean | **dual-form**: source-available (code cells) AND runnable (behavioral cells); single-mode rows only where mode-evasion is the point |
| + each criterion | — | sealed injection-canary subset | bait embedded in page text / markup / comments / export artifacts |

Three structural consequences:

- **Products, not rows.** Sealed rows are product-level with per-criterion labels; one fixture product serves multiple cells. The floors therefore price out to *violation-instances*, not products: ≥180 violating labels across the three criteria, hostable on fewer products if violations co-locate — but co-location should be limited deliberately (a fixture violating all three criteria at once invites correlated verdicts and leaks label information across cells). A portfolio in the rough shape of **90–150 fixture products**, most carrying one criterion's violation and clean labels for the others, satisfies all three floors with diversity to spare.
- **`no-dark-patterns` is the binding form constraint.** Its enclave code cells need fixtures whose *source ships to the pipeline*. Real-world products satisfying "documented dark pattern AND published source" are the empty-by-construction class §4.3 names; this demand is met by implantation into open-source hosts (§5–§6) or it is not met at all.
- **Clean floors are as binding as violating ones.** ≥30 clean per criterion with *defensible* clean labels — and a clean label is a claim about absences (§4, O-2), which no enforcement record ever documents. Clean supply is construction or independent inspection, nothing else.

## 3. The public corpora as demand specification

The 152 public rows (37+5 `nst`, 46 `ndp`, 64 `nli`) are the corpus-as-arbiter statement of what each criterion's facts *are*. Since T-9, every row states the facts that decide it — which makes the public corpus a complete, priced bill of demands on the probe engine and fixture platform: whatever the sealed set contains, it will be made of these same fact-shapes. Each row below is classified by **observation channels** (what the audit must be able to do), **fixture tier** (what building it as a runnable target costs), and **live-cost flags** (what observing it on a product we don't control would cost).

**Channels** — `ui` interface walkthrough of covered surfaces (`ui*`: rendered-appearance facts — needs computed styles / rendered captures / vision-capable judging, not DOM text) · `acct` provisioned account with seeded state (`acct*`: heavy seeding — bulk items, org workspaces, plan history, billing/debt state) · `pay` payment instrument, paid state, charge/receipt observation · `t:X` longitudinal window (h/d/mo/y; `t:probe` = the window itself is the row's subject) · `msg` out-of-product messaging capture incl. absence monitoring · `sup` human-mediated support-channel interaction · `multi` cross-identity/session/device/variant comparison · `org` traffic-origin + interaction-timing variation · `net` network/DOM/computed-style instrumentation · `art` delivered-artifact inspection (export archives, diff vs seeded inventory) · `terms` terms/docs/help capture incl. absence sweeps · `· code` = a code-mode route exists (`no-dark-patterns` only).

**Fixture tiers** — **E1** static surface set · **E2** stateful flows, single sitting, real time · **E3** clock/schedule control, messaging jobs, support personas, or heavy seeding · **E4** conditional serving (origin/timing/variant/detection).

**Live-cost flags** — **W** live window ≥7 days · **R** repeated-trial rate sampling · **B** backend-truth: externally unobservable on a product we don't control · **S** live support-channel interaction · **D** dual-origin/timing probe infrastructure · **P** platform spread (mobile app / app store).

### 3.1 `no-subscription-trap` (42 rows)

| example_id | channels | tier | live |
|---|---|:---:|:---:|
| `viol-amazon-iliad` | ui acct pay | E2 | — |
| `viol-adobe-etf` | ui acct pay sup | E3 | S |
| `viol-syn-phonewall` | ui acct terms | E2 | — |
| `viol-syn-retention-maze` | ui acct pay | E2 | — |
| `viol-syn-trial-silent` | acct pay msg t:8d | E3 | W |
| `viol-syn-prechecked` | ui terms | E1 | — |
| `viol-syn-annual-lockstep` | ui acct pay | E2 | — |
| `viol-syn-downgrade-only` | ui acct pay | E2 | — |
| `viol-syn-email-confirm-expiry` | ui acct msg multi | E3 | R |
| `viol-syn-pause-resumes` | ui acct pay t:35d | E3 | W |
| `viol-syn-medium-switch` | ui acct pay multi | E2 | P |
| `clean-syn-oneclick` | ui acct pay t:cycle | E3 | W |
| `clean-syn-trial-notified` | acct pay msg t:8d | E3 | W |
| `clean-syn-annual-reminder` | acct pay msg t:1y | E3 | W |
| `clean-syn-symmetric` | ui acct pay | E2 | — |
| `clean-syn-inapp-store-cancel` | ui acct pay | E2 | P |
| `clean-syn-immediate-prorated` | ui acct pay t:d | E3 | W |
| `clean-syn-zero-offers` | ui acct pay | E2 | — |
| `clean-syn-explicit-consent` | ui | E1 | — |
| `clean-syn-trial-double-reminder` | acct pay msg t:8d | E3 | W |
| `clean-syn-cross-device` | ui acct pay multi | E2 | P |
| `bound-syn-skippable-offer` | ui acct pay | E2 | — |
| `bound-syn-plus-one-step` | ui acct pay | E2 | — |
| `bound-syn-weak-disclosure` | ui | E1 | — |
| `bound-syn-optional-survey` | ui acct pay | E2 | — |
| `bound-syn-unobserved-billing` | ui acct pay t:probe | E2 | — |
| `adv-syn-hidden-cancel` | ui* net | E1 | — |
| `adv-syn-latency` | ui acct pay net | E2 | — |
| `adv-syn-buried-view` | ui acct | E2 | — |
| `adv-syn-double-negative` | ui | E1 | — |
| `adv-syn-fake-countdown` | ui acct pay multi | E2 | — |
| `adv-syn-dismissible-gauntlet` | ui acct pay | E2 | — |
| `canary-syn-pagetext` | ui acct terms | E2 | — |
| `canary-syn-tos-note` | ui acct pay terms | E2 | — |
| `canary-syn-aria-label` | ui acct pay net | E2 | — |
| `defeat-syn-fingerprint` | ui acct pay org | E4 | D |
| `defeat-syn-timing` | ui acct pay org | E4 | D |
| `probe-tiny-decline-link` | ui* | E1 | — |
| `probe-plus-two-trivial` | ui acct pay | E2 | — |
| `probe-accordion-disclosure` | ui | E1 | — |
| `probe-email-cancel-reliable` | ui acct msg multi | E3 | R |
| `probe-persistent-offer` | ui acct pay | E2 | — |

Tier mix: **E1 7 · E2 23 · E3 10 · E4 2.** 30/42 rows require paid state; 6 require messaging capture; 7 carry live windows ≥7 days — one (`clean-syn-annual-reminder`) requires an *annual* cycle live, the single most expensive live observation in the corpus.

### 3.2 `no-dark-patterns` (46 rows, dual-mode)

| example_id | channels | tier | live |
|---|---|:---:|:---:|
| `viol-epic-controls` | ui acct pay · code | E2 | — |
| `viol-fashionnova-reviews` | multi t:wk · code | E3 | B |
| `viol-cnil-google-reject` | ui | E1 | — |
| `viol-booking-pressure` | ui multi t:d | E3 | W |
| `viol-syn-reset-countdown` | ui net multi · code | E2 | — |
| `viol-syn-toast-generator` | ui net · code | E2 | — |
| `viol-syn-shame-decline` | ui · code | E1 | — |
| `viol-syn-inverted-checkbox` | ui acct msg · code | E2 | — |
| `viol-syn-ghost-decline` | ui* net · code | E1 | — |
| `viol-syn-cart-insert` | ui acct · code | E2 | — |
| `viol-syn-forced-marketing-bundle` | ui · code | E1 | — |
| `viol-syn-fake-selected-state` | ui acct pay · code | E2 | — |
| `viol-syn-reject-resets` | ui multi t:14d · code | E3 | W |
| `viol-syn-consent-wall` | ui · code | E1 | — |
| `viol-syn-unsubscribe-maze` | ui acct msg · code | E2 | — |
| `clean-syn-true-deadline` | ui multi net t:d · code | E3 | W |
| `clean-syn-live-stock` | ui net multi pay · code | E3 | — |
| `clean-syn-honest-reviews` | ui · code | E2 | — |
| `clean-syn-neutral-decline` | ui · code | E1 | — |
| `clean-syn-plain-controls` | ui acct pay · code | E2 | — |
| `clean-syn-equal-consent` | ui · code | E1 | — |
| `clean-syn-cart-integrity` | ui acct pay · code | E2 | — |
| `clean-syn-respectful-prompt` | acct multi t:30d · code | E3 | W |
| `clean-syn-emphasized-cta-legible-alt` | ui* · code | E1 | — |
| `clean-syn-purchase-confirm` | ui acct pay · code | E2 | — |
| `clean-syn-factual-consequence` | ui · code | E1 | — |
| `bound-syn-recurring-flash-sale` | ui multi t:3d | E3 | W |
| `bound-syn-stale-toasts` | ui net | E2 | B |
| `bound-syn-guilt-copy` | ui · code | E1 | — |
| `bound-syn-subordinated-decline` | ui* · code | E1 | — |
| `bound-syn-bundled-donation` | ui acct · code | E2 | — |
| `bound-syn-session-reprompt` | ui acct · code | E2 | — |
| `bound-syn-second-session-reprompt` | acct multi t:14d · code | E3 | W |
| `bound-syn-variant-gated-consent` | ui multi | E4 | D |
| `bound-syn-prompt-carousel` | acct multi t:14d · code | E3 | W |
| `adv-syn-first-layer-asymmetry` | ui · code | E1 | — |
| `adv-syn-serverside-toasts` | ui multi net t:h | E3 | — |
| `adv-syn-css-lottery` | ui* net · code | E2 | — |
| `adv-syn-microcopy-inversion` | ui acct · code | E2 | — |
| `adv-syn-decoy-timer` | ui t:h · code | E2 | — |
| `adv-syn-emoji-shame` | ui* · code | E1 | — |
| `canary-syn-code-comment` | · code (behavioral: ui multi) | E2 | — |
| `canary-syn-consent-metadata` | ui net · code | E1 | — |
| `canary-syn-tos-instruction` | ui terms net · code | E2 | — |
| `defeat-syn-probe-clean-banner` | ui org | E4 | D |
| `defeat-syn-timer-suppress` | ui net org | E4 | D |

Tier mix: **E1 14 · E2 19 · E3 10 · E4 3.** Mode coverage: **39/46 rows carry a code route**; the 7 that don't are exactly the designed exceptions — the four enforcement anchors (no source available), the two by-design mode-evaders (`adv-syn-serverside-toasts`, `bound-syn-variant-gated-consent`), and `bound-syn-stale-toasts` (backend data age). Note the inversion on defeat devices: with *full* source submitted, conditional serving is self-revealing — code mode catches defeat devices trivially, so the defeat lane is a **behavioral-cell** problem, and code-cell fixtures for it only make sense as client-only submissions.

### 3.3 `no-lock-in` (64 rows)

| example_id | channels | tier | live |
|---|---|:---:|:---:|
| `viol-alexa-deletion` | enforcement-record (fixture: backend state) | E3 | B |
| `viol-syn-support-ticket-export` | ui acct terms | E2 | — |
| `viol-syn-paid-export-gate` | ui acct | E2 | — |
| `viol-syn-pdf-flatten` | acct art | E2 | — |
| `viol-syn-vendor-blob` | acct art terms | E2 | — |
| `viol-syn-missing-uploads` | acct* art | E2 | — |
| `viol-syn-sales-call-deletion` | ui acct | E2 | — |
| `viol-syn-resubscribe-to-delete` | ui acct pay | E2 | — |
| `viol-syn-deletion-gauntlet` | ui acct | E2 | — |
| `viol-syn-deactivation-masquerade` | acct t:60d | E3 | W |
| `viol-syn-marketing-after-delete` | acct msg t:40d | E3 | W |
| `viol-syn-downgrade-hostage` | ui acct* art | E3 | — |
| `viol-syn-stated-120d` | ui acct | E2 | — |
| `viol-syn-phonewall-cancel-first` | ui acct pay | E2 | — |
| `viol-syn-no-export-anywhere` | ui acct terms | E2 | — |
| `viol-syn-no-deletion-anywhere` | ui acct terms | E2 | — |
| `viol-syn-app-web-delete-switch` | ui acct pay multi | E2 | P |
| `viol-syn-terms-deactivation` | ui acct terms | E2 | — |
| `viol-syn-offer-reappears` | ui acct | E2 | — |
| `viol-syn-passive-reset` | acct msg t:31d | E3 | W |
| `viol-syn-prechecked-keep-data` | ui acct | E2 | — |
| `viol-syn-mixed-format` | acct* art | E2 | — |
| `viol-syn-grace-marketing` | acct msg t:27d | E3 | W |
| `clean-syn-full-takeout` | acct* art msg t:1d | E3 | — |
| `clean-syn-instant-csv` | acct art | E2 | — |
| `clean-syn-async-stated` | acct art msg t:1d | E3 | — |
| `clean-syn-simple-delete` | ui acct | E2 | — |
| `clean-syn-grace-window` | acct msg t:20d | E3 | W |
| `clean-syn-immediate-delete` | acct msg t:d | E2 | — |
| `clean-syn-export-prompt` | ui acct art | E2 | — |
| `clean-syn-org-admin-export` | acct* art | E3 | — |
| `clean-syn-zero-offer-exit` | ui acct | E2 | — |
| `clean-syn-standard-media` | acct* art | E2 | — |
| `clean-syn-cancel-then-delete` | ui acct pay | E2 | — |
| `clean-syn-email-confirm-delete` | acct msg multi | E3 | R |
| `clean-syn-unpaid-balance-settle` | ui acct* pay | E3 | — |
| `clean-syn-regulated-retention` | ui acct msg t:window | E3 | W |
| `bound-syn-manual-fulfillment` | acct sup msg t:3d | E3 | S |
| `bound-syn-documented-xml` | acct art terms | E2 | — |
| `bound-syn-stripped-metadata` | acct* art | E2 | — |
| `bound-syn-ninety-day-deferral` | ui acct | E2 | — |
| `bound-syn-single-offer` | ui acct | E2 | — |
| `bound-syn-unobserved-grace` | acct t:probe | E2 | — |
| `bound-syn-no-export-mention` | ui acct art | E2 | — |
| `bound-syn-manual-with-sla` | acct sup msg t:5d | E3 | S |
| `bound-syn-stated-45d` | ui acct | E2 | — |
| `bound-syn-pending-export` | acct t:12h | E3 | — |
| `bound-syn-id-upload-gate` | ui acct | E2 | — |
| `bound-syn-residual-message` | acct msg t:9d+ | E3 | W |
| `adv-syn-expiring-export-link` | acct msg multi t:d | E3 | R |
| `adv-syn-settings-only-export` | acct* art | E2 | — |
| `adv-syn-hidden-delete-control` | ui* acct net | E2 | — |
| `adv-syn-downgrade-maze` | ui acct | E2 | — |
| `adv-syn-format-shapeshifter` | acct art | E2 | — |
| `adv-syn-elapsed-no-artifact` | acct msg multi t:3d | E3 | R |
| `adv-syn-item-by-item` | ui acct* art | E3 | — |
| `adv-syn-truncated-collections` | acct* art | E3 | — |
| `adv-syn-exit-confirmshaming` | ui acct | E2 | — |
| `adv-syn-expiring-delete-confirm` | acct msg multi | E3 | R |
| `canary-syn-manifest-note` | acct art | E2 | — |
| `canary-syn-deletion-meta` | ui acct net t:window | E3 | W |
| `canary-syn-tos-reviewer-note` | acct terms msg multi | E3 | R |
| `defeat-syn-probe-good-export` | acct art org | E4 | D |
| `defeat-syn-scripted-delete` | ui acct org | E4 | D |

Tier mix: **E1 0 · E2 38 · E3 24 · E4 2.** No `no-lock-in` row is decidable without a provisioned account; 20 rows require export-artifact inspection against a seeded inventory; 11 require heavy seeding (bulk collections, org workspaces, plan history, metered-debt state); 8 carry live windows ≥7 days, topping out at 60 (`viol-syn-deactivation-masquerade`).

### 3.4 Aggregate

| | E1 | E2 | E3 | E4 | W | R | B | S | D | P |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `no-subscription-trap` (42) | 7 | 23 | 10 | 2 | 7 | 2 | 0 | 1 | 2 | 3 |
| `no-dark-patterns` (46) | 14 | 19 | 10 | 3 | 7 | 0 | 2 | 0 | 3 | 0 |
| `no-lock-in` (64) | 0 | 38 | 24 | 2 | 8 | 5 | 1 | 2 | 2 | 1 |
| **Total (152)** | **21** | **80** | **44** | **7** | **22** | **7** | **3** | **3** | **7** | **4** |

~36 rows (24%) carry a time channel of any length; 22 (14%) need ≥7-day windows live. 86% of rows sit at E2 or below — stateful app flows without clock or serving machinery.

## 4. Findings (O-1 … O-10)

**O-1 — The controllable clock is the single largest fixture lever.** 22 rows are ≥7-day observations against real time, up to annual (`clean-syn-annual-reminder`) and 60 days (`viol-syn-deactivation-masquerade`); ~36 carry time at all. In owned fixtures, a virtual time source driving billing, recovery windows, and scheduled messaging collapses every one of them to minutes; against live third-party products the same facts impose per-product audit-duration floors of weeks. Consequence: the fixture platform's first requirement is **virtual-clock-driven billing/scheduling**, and live-product cells must carry pre-registered window lengths in their cost model (PROTOCOL §10).

**O-2 — Clean verdicts are absence verdicts.** Nearly every clean row's deciding facts are absences: no retention offers, no post-cancel charge, no message after the window, no missing content type. Absences are decidable only against an enumerated scope — which surfaces were censused, which window was watched, how many trials were run. A missed surface on a violating product is a **false PASS**, the 5%-gate error. Consequence: the probe engine must produce a **surface census** (settings, help, docs, terms, footers) and bounded-window absence claims as first-class evidence, and clean labels in the sealed set must record the census/window they were labeled against.

**O-3 — Backend-truth rows are structurally unobservable live.** 3 rows (`viol-fashionnova-reviews`, `bound-syn-stale-toasts`, `viol-alexa-deletion`) turn on facts on the invisible side of the product boundary — withheld review queues, backend data age, post-deletion retention. No external probe establishes these on a product we don't control; enforcement discovery did, and owned fixtures do by construction. Consequence: this fact-class enters the sealed set **only** as fixtures or enforcement-anchored rows, and live-product cells cannot measure it — consistent with `no-lock-in` check 6's fail-before-`unobserved` design, and a stated external-validity limit of the behavioral tier.

**O-4 — Rate facts need pre-registered trial counts.** 7 rows turn on reliability rates ("frequently fails to arrive," "expires in minutes," instant-and-never-expires). A rate claim from n trials is a statistical claim; n must be fixed in advance or the fact is soft. Consequence: **new open parameter** — per-rate-fact trial counts and decision rules (added to PROTOCOL §12 by this audit).

**O-5 — Human-mediated channels are the costliest probe lane.** 3+ rows require interacting with support (phone/chat/tickets/staff-fulfilled exports). In fixtures this means **scripted support personas** (mailbox/chat automation with timed responses) — buildable, a distinct platform item. Live, it means real support interactions: slow, detection-prone, and ethically the most sensitive probe conduct; several rows (`viol-syn-phonewall`, `viol-syn-sales-call-deletion`, `bound-syn-id-upload-gate`) are deliberately decidable from the *demand* the product makes rather than from completing the interaction — a design pattern the sealed set should preserve.

**O-6 — The defeat lane needs dual infrastructure on both sides.** 7 rows require origin/timing/variant-conditional serving (E4) in the fixture AND dual-origin, timing-varied probing in the engine. This is the confirmed long pole of PROTOCOL §12.4 alongside synthetic-variant engineering. Code-mode note per §3.2: full-source submission makes conditional serving self-revealing, so defeat devices are meaningfully a behavioral-cell threat.

**O-7 — Rendered reality, not DOM text.** ~8 rows are decidable only at the rendered/interactive layer (computed styles, z-order interception, below-fold placement, emoji/mascot depiction) and two (`adv-syn-css-lottery`, `adv-syn-hidden-delete-control`) are engineered to *defeat* DOM-level review. Consequence: the probe engine judges from rendered captures and interaction attempts; judging depiction facts (`adv-syn-emoji-shame`) requires vision-capable judges — a pool-membership constraint to record at freeze (PROTOCOL §12.3).

**O-8 — Payment machinery is pervasive.** 41 rows require paid state, charges, receipts, or refunds. Fixtures need a simulated billing spine (aligned with O-1's clock); live cells need real payment instruments (already contemplated by Architecture §7 stealth) plus charge-observation windows.

**O-9 — Platform spread exists but is thin.** 4 rows need mobile-app or store-mediated fixtures. Store-mediated flows (`clean-syn-inapp-store-cancel`) are partially owned by the platform, not the product — an observation-boundary note the sealed set inherits. A small mobile-fixture track suffices; it need not gate the study.

**O-10 — The public corpus is 100% fixture-attainable; the gap is entirely on the live side.** No row's deciding facts are unattainable in an owned fixture — T-9 forced every row to state observable facts, and construction supplies them. The §4.3 anti-correlation is real but lands as *live*-attainability: 3 rows live-unattainable (B), 22 live-slow (W), 7 live-sampled (R), 7 needing dual-origin infra (D). The sealed corpus is therefore **buildable to the floors** — the open question is how much of it can be *real*, which is §5's subject, and the honest expectation set by §2 is: not much.

## 5. Supply — what the real world offers

Method: multi-agent web survey (2026-07-08), load-bearing claims cross-checked across independent research passes and, where marked *(confirmed)*, read against a primary source (enforcement press release, repository license file, product docs). *(reported)* = secondary source or single-pass claim. Dated estimates throughout; enforcement dockets move.

### 5.1 Enforcement-documented extractive cases (the violating anchors)

**US federal (FTC), through mid-2026** — the deepest vein, and it runs almost entirely to `no-subscription-trap` and `no-dark-patterns`:

| Case | Year(s) | Criteria (core/present) | Live-observability today |
|---|---|---|---|
| Amazon Prime ("Iliad Flow") | filed 2023 · settled 2025, $2.5B | nst core · ndp | remediated (decree: cancel as easy as signup) *(confirmed)* |
| Adobe (hidden ETF, cancel obstruction) | filed 2024 · $150M settlement announced 2026, order pending entry | nst core · ndp | remediation ordered but order not confirmed entered — recheck at freeze *(confirmed complaint + announcement; approval status unverified)* |
| Uber One | filed 2025 · **active litigation** | nst core · ndp | **likely still observable — no injunction** *(confirmed)* |
| Epic / Fortnite | 2022, $520M | ndp core · nst · nli (account locks) | remediated (hold-to-purchase shipped) *(confirmed)* |
| Match Group | filed 2019 · settled 2025, $14M | nst core · ndp core · nli (chargeback termination) | likely remediated, fresh order *(confirmed)* |
| Care.com | 2024, $8.5M | nst core · ndp (trick cancel buttons) | remediated *(confirmed)* |
| NGL Labs | 2024, $5M | ndp core · nst · nli (minors' data destruction) | partially remediated (adult flow clean) *(confirmed)* |
| ABCmouse / Age of Learning | 2020, $10M | nst core · ndp | remediated — longest compliance track record *(confirmed)* |
| FloatMe | 2024, $3M | nst · ndp (admitted intentional cancel friction) | likely remediated *(confirmed)* |
| Cerebral | 2024, >$7M | nst core · ndp · nli partial | remediated on paper; product downsized *(confirmed)* |
| Credit Karma | 2022–23, $3M | ndp (A/B-tested dark patterns, named as such) | remediated *(confirmed)* |
| Fashion Nova | 2022, $4.2M | ndp core (review suppression) | remediated; conduct now under the 2024 Fake Reviews Rule *(confirmed)* |
| MoviePass | 2021, injunction | ndp core (covert throttling) · nli loose | **unprobe-able** — company dissolved; the 2022 relaunch is a different product *(confirmed)* |
| Publishers Clearing House | 2023, $18.5M | ndp core · nli (ordered data deletion) | uncertain — bankruptcy, successor entity *(confirmed)* |
| Benefytt | 2022, $100M | ndp (junk-fee add-ons) | wound down *(confirmed)* |
| Genesis Tech | filed 2026 · active | nst · ndp | active litigation *(confirmed)* |
| Amazon Alexa (COPPA) | 2023, $25M | **nli core** — deletion requests undermined, retention | remediated for ordered (children's-data) scope *(confirmed)* |
| Ring | 2023, $5.8M | nli partial (ordered deletion of data/models) | remediated (ordered scope) *(confirmed)* |
| Blackbaud · Mobilewalla · X-Mode | 2024 | nli partial (retention/deletion orders) | remediated (ordered scope) *(confirmed/reported)* |
| Epic·Vizio·Google/YouTube·Meta posture | various | ndp/nli partial | various *(confirmed/reported)* |

Regulatory backdrop *(confirmed)*: the FTC's Click-to-Cancel / Negative Option Rule was **vacated in its entirety** (8th Cir., July 2025, procedural grounds; ANPRM to rebuild issued 2026) — `no-subscription-trap` enforcement rests on ROSCA + FTC Act §5 + state auto-renewal laws, which the 2025–26 cases post-date and survive on. This does not thin the fixture supply (the complaints stand as fact records) but is context the study report should carry.

**US state-level and CFPB** *(all confirmed against agency pages except as noted)*: CFPB v. TransUnion (2022 — deceptive "free score" buttons, obstructed cancel; a fourth US authority in play). CPPA's first orders: American Honda (2025, $632.5K — cookie-consent asymmetry treated explicitly as a dark pattern, GPC not honored) and Todd Snyder (2025, $345K — broken opt-out, photo-ID over-verification); Ford (2026). CA AG: Sephora (2022, first CCPA settlement), Healthline (2025, $1.55M — largest CCPA to date), DoorDash. The **California CART auto-renewal task force** (Bouqs, Thrive Market, LA Times, 2024 *(reported)*) is a recurring `nst` supply engine, as are ARL class actions (Peacock, System1) — private litigation, weaker ground truth than agency action but public fact records.

**EU and international** *(confirmed against EC/CNIL/CPPA primary pages; Italian AGCM multi-source-corroborated — the agency bot-blocks direct reads)*:

- **DSA Article 25 is producing live, adjudicated dark-pattern cases:** the **first-ever DSA fine — X, €120M (Dec 2025)** for the blue-checkmark deceptive-"verified" design, conduct **still live** pending appeal; TikTok addictive-design and Meta reporting-flow proceedings preliminary (2025–26). CPC-network commitments (Amazon Prime's 2022 two-click cancel — the cleanest changed-under-pressure record — Temu, Shein, Vinted drip fees, Viagogo countdowns) are fact-rich but are *commitments without admission*, weighted below fined/adjudicated cases.
- **UK CMA:** Wowcher (pre-ticked auto-enrolment, £4.27M refunded), **Emma Sleep** (restarting countdown timers — High Court order 2026), McAfee/Norton and the console trio (auto-renew defaults), a 2025 drip-pricing cohort (StubHub, viagogo, Wayfair — several still open, i.e. live), and a fresh Adobe ETF probe (2026, live). DMCC subscription rules delayed to ~2027.
- **Italy AGCM:** eDreams "Prime" (€9M, 2026 — trial→charge conversion plus active cancellation obstruction, **still live**, repeat offender), Amazon "Subscribe & Save" pre-checks (€10M), **Deghi** (€2M, 2026 — cyclically-renewed fake countdown, the freshest live specimen), Trustpilot (€4M).
- **France:** the CNIL cookie-refusal-parity cluster — Google (€150M 2021 + €325M 2025), Facebook, Amazon, Microsoft, TikTok, Shein (€150M 2025) — all remediated, which makes it double as a **remediation-verified clean-control set** for consent surfaces (§5.5). DGCCRF: Shein fake-discount fine (€40M, conduct reported still observable). And the survey's one true **post-termination-data enforcement anchor: Free/Freebox (CNIL, €300K) — reconditioned set-top boxes shipped to new customers still holding prior subscribers' photos** — a real-world `nli` check-6 shape beyond Alexa.
- **Germany:** the §312k "Kündigungsbutton" (cancel-button) cluster (Verivox, 1&1), with vzbv's sweep finding **58% of ~2,946 surveyed sites non-compliant** *(reported)* — a large, live, wild-caught `nst` reservoir, pending the study's own labeling.
- **GDPR, the `no-lock-in` side:** named erasure cases exist (AEPD v. Google €10M — right-to-be-forgotten form obstruction; the Irish DPC's Twitter/X photo-ID-to-delete matter; SATS; Danske Bank), and the **EDPB's 2025 coordinated enforcement framework on erasure** (32 DPAs, 764 controllers, 9 formal investigations opened, outcomes expected late-2026) is the pipeline to watch. **Standalone GDPR Article 20 (portability) enforcement: zero DPA fines, confirmed as an absence** — the export-side gap is global, not an FTC quirk.

**The three structural findings in this table:**

1. **Enforcement-documented ⇒ (almost always) remediated — quantified.** Globally deduplicated: `nst` ~30 documented products → **~4–6 still live-observable** (Uber One the US standout; eDreams, the UK Adobe probe, the German §312k reservoir); `ndp` ~52–55 documented → **~20 still live** (Temu, Shein, Deghi, X, TikTok, the UK drip cohort); `nli` ~12–15 documented → **~0 externally probe-able** (deletion violations only surface through account-based request audits). The §4.3 anti-correlation is confirmed and now has numbers.
2. **`no-lock-in`'s enforcement vein is deletion/retention, not export.** Alexa (deletion undermined) is the strongest anchor; Free/Freebox adds post-termination data; Ring/Blackbaud/Mobilewalla add retention orders; X's photo-ID-to-delete adds an over-verification gate. **Export/portability enforcement is empty worldwide** — no FTC action ever (2020 workshop only *(confirmed)*), zero Art. 20 fines *(confirmed)*. The `no-lock-in` corpus README's "thinness is itself part of this criterion's case" is confirmed and quantified: **export-side real supply = 0.**
3. **Enforcement exhibits decouple "usable fixture" from "still live."** Complaints and decisions embed the violating artifacts — the Amazon complaint's Iliad-Flow figures, Uber's cancel-maze walkthrough, CNIL's banner captures — frozen at violation time with an authority's characterization attached: the strongest available ground truth, unaffected by remediation. Supplemented by archive captures (static-snapshot caveat for flow-dependent patterns), the **usable** documented-real count tracks the *documented* column (~30/~54/~13), not the live column (~5/~20/~0). Re-implementation fidelity to the exhibit, not live observation, is what a documented-real fixture asserts — exactly how the public corpora already treat `viol-amazon-iliad` and `viol-adobe-etf` (dated observations, not standing truth). Adjudicated/fined cases (X, CNIL cluster, AGCM, Emma Sleep's court order, CFPB TransUnion) outrank commitments-without-admission for label defensibility.

### 5.2 The "documented-extractive AND code-inspectable" intersection

§4.3's named worry, now counted: across all surveyed classes, real products where a *documented* extraction pattern sits in *inspectable* code number roughly **four to six**, and they skew to telemetry/affiliate patterns rather than the three criteria's core shapes:

- **Brave** (MPL-2.0): affiliate-code autocomplete injection, 2020 — shipped in `brave-core`, removed by public commit *(confirmed)*. The cleanest specimen: extraction pattern, public code, public fix.
- **balenaEtcher** (Apache-2.0): pre-consent telemetry, module in-repo, conceded 2025 *(reported)*.
- **Homebrew** (BSD-2): opt-out-by-default analytics, in the public codebase *(reported)*.
- **Ubuntu Unity** (GPL): the 2012 Amazon "shopping lens" — local searches leaked to an affiliate pipeline; EFF-documented *(confirmed)*.
- **WordPress plugin admin nagging** (GPL): persistent free→paid upsell nags in plugin PHP — documented as annoyance, formal "deceptive" labeling weaker *(reported)*.
- Browser extensions (shipped JS = decompilation-free inspectability): **PayPal Honey** — the 2024–25 MegaLag/Edelman investigation extracted from the shipped extension code an alleged **tester-detection ("selective standdown") system**: profile the user for affiliate-industry signals, behave compliantly for suspected testers, drop the compliance behavior for ordinary shoppers *(confirmed as investigation-documented, source-code-grounded; litigation pending, not adjudicated)*. If the analysis holds, it is a real-world **defeat device** in a mass-market consumer product — directly anchoring the defeat lane's external validity. Also: Stylish (2018), The Great Suspender (2021), Avast/Jumpshot (2019–20) *(confirmed)*.

The instructive **negative** cases: VS Code's telemetry lives in Microsoft's proprietary build layer, not the MIT source (why VSCodium exists); Wikipedia's criticized donation banners are server-side campaign config, not shipped code; Audacity's 2021 controversy was policy/governance, not UI logic. And **no academic study audits open-source software as a category for dark patterns** *(confirmed)* — the canonical corpora (Mathur et al. 2019; Di Geronimo et al. 2020; Gunawan et al. 2022) target proprietary surfaces. Structural explanation: OSS mostly lacks the subscription substrate that breeds these patterns, and forkability punishes extraction fast (VSCodium, Stylus, Tenacity are all forks-as-discipline).

**Consequence for the `no-dark-patterns` code cells:** the real slice is ~5 fixtures, several off-center from the criterion's core checks. The code cells therefore run on **implanted synthetic variants** (§5.3) — which PROTOCOL §4.2 class 2 sanctions with the external-validity caveat attached and provenance blinded — plus the handful of real specimens, scored separately. The §4.3 kill-branch ("credible code-auditable extractive corpus cannot be assembled at all") is **not** triggered: it contemplated *found* corpora, and the sanctioned synthetic path is open. But the report must say plainly that code-cell results generalize through the implant assumption.

### 5.3 Implant-host capacity (the synthetic-variant supply)

Licensing is the gating constraint on republishing modified variants: permissive (MIT/Apache/BSD) and copyleft (GPL/AGPL — publish the modified source; aligned with this project anyway) both work; source-available licenses (BUSL, "Sustainable Use") do not — **Outline** (BUSL; its trial→read-only mechanic would have been a superb forced-continuity fixture), **NocoDB** (relicensed ~2026), and **Cal.com**'s post-relicense repo are excluded on this line *(confirmed/reported per item)*.

Verified host bench, ranked by native-flow coverage *(licenses confirmed against repos except where noted)*:

| Host | License | Native surfaces | Serves |
|---|---|---|---|
| **Ghost** | MIT | the full subscription lifecycle: tiers, carded trial with auto-charge, Stripe checkout, retention offers, cancel | nst★ ndp★ |
| **MIT Stripe starter kits** (SvelteKit SaaS Starter, next-saas-stripe-starter, Open SaaS) | MIT | signup/pricing/checkout/portal/trial — the whole app is the billing surface | nst★ ndp★ |
| **Twenty CRM** | AGPL-3.0 (avoid its enterprise-marked files) | billing settings, dual trial shapes, CSV export, danger-zone delete | nst ndp nli — best three-criterion spread |
| **Discourse** + subscriptions plugin | GPL-2.0+ core, **MIT plugin** | recurring subs, trials, webhook-dependent cancel (a ready-made "cancel silently fails" shape) | nst★ — implant lives entirely in the small MIT plugin: cheapest-to-audit diff |
| **WooCommerce + Subscriptions** | GPLv3 (extension paid but GPL) | the most consumer-realistic storefront/checkout | ndp★★ nst★ |
| **Documenso** | AGPL-3.0 | textbook delete-account flow with retention/anonymization messaging | **nli★★** |
| **Rocket.Chat** | MIT core (+ proprietary `ee/`) | native plan/renewal/cancel UI with built-in cancel-parity asymmetry between tiers; GDPR export + self-delete | nst★ nli★ (heavy setup) |
| **Medusa / Saleor** | MIT / BSD-3 | headless commerce; assemble-your-own surface | ndp nst (flexible, more build) |
| **Lago / Kill Bill** | AGPL / Apache-2.0 | billing **logic** — auto-renew, trial conversion, proration, dunning — as auditable code | nst ground truth for billing *behavior*, not UI |
| **Mastodon** | AGPL-3.0 | exemplary export/migration/delete — the **positive baseline** to implant degradations against | nli (gold standard) |
| + Listmonk, Plausible, Keila, Formbricks (billing dir is EE-licensed — build outside it) | AGPL variants | consent, unsubscribe-parity, churn-survey surfaces | ndp nli |

Capacity verdict: **high for all three criteria** — ~10 viable hosts, with per-criterion flagships (Ghost/starter kits for `nst`, WooCommerce for `ndp` storefront patterns, Documenso/Mastodon for `nli`). Honest gaps the build plan must engineer rather than find: **no surveyed OSS host natively ships drip pricing, fake scarcity, or social-proof machinery** (those are pure implants), and native trial-conversion-notice surfaces are rare (Ghost, Twenty). The billing-engine pair (Lago/Kill Bill) covers O-1's virtual-clock requirement at the logic layer — subscription-trap fixtures whose deciding facts are billing behavior can be built on engines where that behavior is code, then driven by a simulated clock.

### 5.4 Academic and research corpora

One root corpus dominates the text side: **Mathur et al. 2019** (~11K shopping sites → 1,818 labeled instances across 1,254 sites, 15 pattern types, the actual UI text segment per instance, GPL-3.0) — most Kaggle/HuggingFace "dark pattern" datasets are re-packages of it and count as one source *(confirmed)*. Around it: ec-darkpattern (1,818 positive + ~14K negative strings, Apache-2.0), **UIGuard** (1,660 mobile instances **with raw screenshots**, Zenodo), **AidUI** (301 instances, screenshots in-repo, MIT), Di Geronimo et al. 2020 (240 apps, 95% ≥1 pattern; only 15 session videos public), Gunawan et al. 2021 (105 services × 3 modalities, labels only), cookie-banner sets (Nouwens 2020, 680 CMP deployments — reject-parity is the structural analogue of cancel-parity; Bouhoula 2024, ~97K sites crawled, 2,353 annotated elements) *(all confirmed)*; AppRay 2024 (2,185 instances including 149 multi-page flows — the closest thing to flow coverage; public access unverified) *(uncertain)*. **DarkBench is out of scope** — it measures *LLM conversational* manipulation, not product UI *(confirmed)*. "ConTrust" does not exist as a dataset (confirmed absence). The Dark Patterns Tip Line is a manual harvesting source (vetted screenshot submissions, no bulk access/license).

Three survey results matter more than the inventory:

- **Coverage is single-moment, not flow.** These corpora label a string or a screen; `no-subscription-trap` and `no-lock-in` are *flow and policy* properties. Per-criterion: `ndp` gets thousands of usable instance-labels; `nst` gets a narrow slice (~40–80 obstruction/forced-continuity items; **zero** coverage of auto-renew consent, trial-conversion notice, or renewal reminders); `nli` gets **~0** — the concept is absent from every taxonomy surveyed. A 2024 unification study (68-type taxonomy) finds existing datasets cover ~44% of known types *(confirmed)*.
- **Role in this study: base rates, taxonomy, and contamination checks — not fixtures.** Entries document patterns at crawl-time on products nobody controls; they inform sealed-set shape, wild-prevalence claims (the Mathur/Di Geronimo base rates say extraction is common in the wild even as enforcement touches a sliver), and §4.1's memorization probes. Practitioner literature (CHI 2026) adds the enforcement-sampling caveat this audit should quote at freeze: only a tiny, non-random subset of real-world patterns is ever enforced.
- **SusBench (IUI 2026) validates the implant method itself:** 123 dark-pattern variants injected into 55 real sites, with human evaluators unable to distinguish injected from native patterns *(confirmed)*. That is peer-reviewed support for the external validity of PROTOCOL §4.2's synthetic-variant class — and a QA gate worth adopting: an implant that humans *can* pick out is a bad implant (§7).

### 5.5 Documented-clean controls

As predicted in §2: **"documented clean" barely exists as a third-party class**, because almost every source means "no documented violation" — absence of evidence. The survey found exactly four routes that convert absence into a positive, testable capability:

1. **First-party export/deletion verification (`nli`)** — the strong route. Self-service export surfaces (Google Takeout, Apple Data & Privacy, Facebook DYI) are directly probe-able end-to-end, and the PoPETs literature supplies the method and the aggregate prior: Rupp et al. 2022 *executed* Art. 17 deletion on 83 services with longitudinal verification (~73% complied; services anonymized — method, not roster) *(reported)*. ≥30 clean `nli` fixtures are attainable **by the study's own execution-verified probing** of major services, plus unmodified implant-host baselines (Mastodon's exemplary export is code-inspectable clean).
2. **Platform-mandated cancellation (`nst`)** — iOS/Play force a uniform low-step, store-mediated cancel with purchase-time renewal disclosure: an enforced, inspectable capability covering the entire store-subscription universe. **Sharp scope caveat:** it certifies the *store-mediated flow only* — the same vendor can run a web retention maze (O-9's observation boundary, now a labeling rule: platform-clean fixtures are scoped to the store flow).
3. **Remediation-verified cleans** — products operating under compliance orders whose flows were re-inspected post-order (ABCmouse's two-decade order tenure; the CNIL cookie cluster's remediated banners). Ground truth = order + the study's own re-verification, and the label carries its date.
4. **Construction** — unmodified implant hosts, clean by build.

What does *not* work: ToS;DR grades policy text, not runtime UI; Mozilla's list is off-target; the Data Transfer Initiative is a convener, not a certifier; **no dark-pattern-free certification exists at all** (the one advertised is not operational) *(confirmed)*. Consequence: **`ndp` clean labels rest entirely on the study's own documented inspection** (routes 3–4 plus §12.5's independent labelers with O-2's census discipline) — the thinnest clean cell in the matrix, and a stated credibility load rather than a blocker: self-labeled cleans are exactly why §9 separates labelers from pipeline operators.

### 5.6 Client-side decompilable middle ground

- **Mobile fleeceware** is well-documented by security vendors with named apps and scale figures (Sophos: ~600M installs across <25 apps at one 2020 count; Avast: 204 apps, >$400M revenue, 2021; named non-functional $9.99/week VPNs) *(confirmed)*. But **subscription enforcement is server-side** (StoreKit/Play Billing): an APK exposes the paywall/trial-framing UI half — sufficient ground truth for `ndp` and for `nst`'s disclosure/consent checks, **insufficient for billing-behavior checks** (conversion, honored-cancellation). Obfuscation degrades even the UI read; DMCA §1201 and EULA anti-RE clauses hedge the legal footing for anything beyond research use *(confirmed)*.
- **Browser extensions** are the highest-inspectability proprietary class (shipped JS, no decompilation) and supplied the survey's best real defeat-device specimen (Honey, §5.2).
- **Electron** apps unpack (`asar extract`) but carry the same server-side-billing limitation; no cleanly documented Electron subscription-trap case surfaced.

Net: the client-side middle is a real but *partial* supply class — strongest for `ndp` presentation facts, weakest exactly where `nst`'s behavioral checks live.

## 6. Gap analysis — demand vs. supply, per criterion

The floors are ≥60 violating + ≥30 clean per criterion (§2), in each cell's required form. What fills them, honestly labeled:

| | Violating floor (≥60) | Real-anchored ceiling | Still-live-extractive | Clean floor (≥30) |
|---|---|---|---|---|
| `no-subscription-trap` (behavioral) | reachable: ~30 exhibit-anchored re-implementations + synthetics | **~30 products** — but **0 found coverage of checks 5/6/7 shapes** (auto-renew consent, trial notice, reminders): those are authored regardless | ~4–6 (Uber One; eDreams; UK Adobe probe; §312k reservoir pending own labeling) | reachable: platform-mandate class (store-scoped labels) + remediation-verified + construction |
| `no-dark-patterns` (behavioral cells) | **clears from documented-real alone** (~52–55 products + exhibit figures + thousands of academic instance-labels for shape) | ~54 products | ~20 (Temu, Shein, Deghi, X, drip cohort…) | **the thinnest clean cell**: no third-party source exists; own documented inspection + construction + remediation-verified |
| `no-dark-patterns` (code cells) | reachable **only via implants**: real code-inspectable specimens ≈ 5, several off-center (telemetry/affiliate) | **~5** | n/a (submission-based) | construction (unmodified hosts, source shipped) |
| `no-lock-in` (behavioral) | reachable only via synthetics: ~13 anchors, **all deletion/retention-side**; **export-side real supply = 0 worldwide** | ~13 products (deletion side); 0 (export side) | **~0** externally probe-able | **the strongest clean cell**: first-party execution-verified probing (Rupp-method) + construction |
| all three | + sealed injection-canary subsets: construction only, by design | — | — | — |

**Per-criterion verdicts:**

- **`no-subscription-trap`:** the sealed violating set is roughly **half documented-real-anchored, half authored** — and the authored half is forced not by count but by *check coverage*: no enforcement action or dataset documents auto-renew-consent, trial-notice, or reminder facts at fixture grain. The clean set is attainable but every clean label carries a scope (store-mediated vs. web) and a date.
- **`no-dark-patterns`:** the split criterion. Behavioral cells are the study's best-supplied — a majority-real violating set is attainable, with ~20 live-labeled rows possible (drift-caveated, labeled at observation date). Code cells run **~90%+ implanted** no matter what; SusBench's indistinguishability result is the external-validity support, and the per-cell report must carry the implant assumption explicitly. Clean labels are the study's own work everywhere.
- **`no-lock-in`:** the inversion criterion. Violating supply is the world's thinnest (deletion anchors only; the export half of the criterion has literally zero documented-real instances to anchor on — synthetic by necessity, disclosed as such); clean supply is the world's strongest (export/deletion are positive capabilities you execute and verify). The EDPB erasure-framework outcomes (expected late-2026) are the one watch-item that could add anchors before freeze.

**Portfolio consequence (§2's 90–150 products):** after transatlantic dedup, the documented-real bench is ~60–80 distinct products carrying ~97 criterion-labels — enough to real-anchor roughly **half** the portfolio, concentrated in `ndp`-behavioral and `nst`. The other half is implant-built on the §5.3 bench.

**The §4.3 kill-branch, resolved:** "a credible code-auditable extractive corpus cannot be assembled at all" is **not triggered** — but only because PROTOCOL §4.2 sanctions synthetic variants. Found-corpus supply for the code cells is ~5 specimens. The honest statement for the study report: code-cell results generalize through the implant assumption (supported by SusBench and by provenance-blinding), not through found real-world code. The behavioral tier carries the external-validity weight, exactly as §4.3's fallback anticipated — the difference is that both tiers still run.

## 7. Implications for §12.1 and §12.4 (recommendations — resolutions happen at freeze)

**For §12.1 (kill thresholds, miss budgets, n per cell):**

1. **Keep the 5%/10% structure and the 3/ε floors unchanged.** Nothing in supply undermines the power logic, and every cell's floors are attainable via the sanctioned synthetic path. What supply *does* change is what a pass means — handled by stratification, not by moving thresholds.
2. **Pre-register real-slice stratified reporting.** Every §7 rate is reported overall **and** on the real-anchored stratum; the attainable ceilings from §6 (~30 / ~54 / ~5 / ~13-and-0) are recorded at freeze so the real slice cannot be retroactively overstated. A cell whose pass rests wholly on synthetic rows says so in the §7.3 attestation-facing record.
3. **Give absence-fact misses their own subtype** in the §3 miss classification (observation-failure: census gap vs. window gap vs. fact misread). O-2 says absence facts are where clean-side observation error lives; the census/window discipline is the direct lever on the 5% false-pass gate.
4. Item 9's parameters (rate-fact trial counts, window registry, census definition, vision-capable pools) were added to §12 by this audit and price directly into per-cell n and per-fixture cost.

**For §12.4 (fixture build plan and budget):**

1. **Build the implant-host platform first**, with four services amortized across all fixtures: the **virtual clock** (O-1 — turns the 44 E3-class rows from weeks of wall-time into minutes), messaging capture with absence monitoring, bulk/state seeding (plan history, org workspaces, metered debt, hundreds-per-collection), and scripted support personas (O-5). Host bench per §5.3: Ghost + the MIT starters (`nst`), WooCommerce (`ndp` storefront), Documenso + Mastodon (`nli`), Discourse's MIT plugin (cheapest-to-audit diffs), Lago/Kill Bill (billing-logic ground truth).
2. **The E4 lane is the confirmed long pole:** conditional-serving fixture infra + dual-origin/timing probe infra (7 corpus rows + the red-team lane). Honey's investigation-documented "selective standdown" is the realism template — profile-based compliance switching, thresholds tuned against discovery.
3. **Run an exhibit-derived re-implementation lane:** for each documented-real anchor, re-implement the enforcement exhibit's flow into a host; the label's claim is fidelity-to-exhibit (dated), not live truth; adjudicated/fined cases first, commitments second.
4. **Run the `nli` first-party probing lane** for clean labels: execution-verified export/deletion on major live services, Rupp-style longitudinal confirmation, O-1 windows priced in.
5. **Adopt a SusBench-style QA gate, pre-registered:** implants that human evaluators can distinguish from native patterns fail fixture QA. This converts §4.2's external-validity caveat from an assumption into a measured property of our own fixture set.
6. **Keep the mobile track small** (O-9: 4 rows) — fleeceware-style paywall/trial-framing fixtures; store-mediated flows carry platform-scoped labels per §5.5.
7. **Budget shape by tier mix** (§3.4: E1 21 · E2 80 · E3 44 · E4 7): E2 stateful-flow engineering is the bulk cost and is host-amortized; E3 is mostly a one-time platform cost (the clock) rather than per-fixture; E4 and the `ndp` code cells' 90-fixture source-shipping requirement are the specialized spends. Dollar figures are a freeze-time decision; this audit fixes the *shape*.

## 8. Limitations

- The §3 classification is authored judgment over row text, single-classifier; channel assignments on composite rows involve calls (e.g., whether a stated-fact row also needs its behavior observed). The tables are published precisely so these calls can be disputed row by row.
- §5's supply counts are dated estimates from a multi-pass web survey (2026-07-08) with per-claim confidence tags; enforcement dockets and datasets move. Counts are floors-of-knowledge, not floors-of-existence. Known soft spots, flagged inline: the Adobe order's entry status (announced 2026; entry unverified against a primary source — recheck at freeze); Italian AGCM matters corroborated multi-source but not read from the agency's own pages; the German §312k 58% figure is a consumer-association sweep, not an adjudicated count; EDPB erasure-framework outcomes still pending.
- Live-observability verdicts ("remediated," "still live") are reasoned estimates from orders and reporting, not live probes — re-verified per fixture at build time by design (§7).
- This audit prices *observation*; it does not re-litigate adjudication (Q1), which the §7.1 calibration gates own.

## 9. Changelog

- **0.1.0** (2026-07-08) — initial draft, complete: demand analysis (§2), full 152-row observation/fixture classification (§3), findings O-1…O-10 (§4), dated supply survey with per-claim confidence (§5), gap analysis with per-criterion verdicts and the §4.3 kill-branch resolution (§6), and §12.1/§12.4 recommendations (§7). Registered before any threshold finalization, per PROTOCOL §2/§4.3.
