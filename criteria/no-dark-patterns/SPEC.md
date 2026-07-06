# `no-dark-patterns` — No Dark Patterns

**Version:** 0.1.0 · **Status:** draft
**Conforms to:** CRITERION-SPEC 0.5.0 (`../CRITERION-SPEC.md`)
**Observation modes:** code + behavioral (every check is `either`-mode — see §4)

---

## 1. Guarantee (§3.1)

The interfaces through which you choose — buying, consenting, declining — show you real information and honest controls. No fabricated countdowns, stock counts, or activity feeds; no shame-worded or trick-worded choices; no hidden or disguised options; declining is as easy as accepting; nothing is added to your order or account without your explicit choice; and declined prompts stay declined.

## 2. Harm model (§3.2)

Dark patterns extract at the **decision moment** — money, data, and attention are taken through choices the user did not mean to make — but the harm is a textbook credence good, and the deferral runs *deeper* here than for most extraction: the manipulated interface does not merely look normal at decision time, it looks **better** (an urgent deal, a popular product, a one-click consent). The harm arrives later and often invisibly:

- **On the bill** — an add-on that was never chosen, a charge from a control that didn't say it was a purchase (discovered at statement time, or never).
- **In the inbox and the data trail** — marketing enrollment and data consents extracted through pre-selection, asymmetric choices, or inverted wording (discovered as spam and as tracking, attributed to nothing).
- **Never** — the counterfactual choice is invisible to its own victim. A user pressured by a fabricated countdown into buying does not learn the timer was fake; a user who couldn't find the decline button does not know it existed. This is precisely why market feedback fails to price the behavior, and why the property must be verified rather than reviewed.

The burden falls hardest on the hurried, the elderly, the less digitally literate, and users operating in a second language — the populations with the least slack to parse a trick question or hunt for a suppressed decline control.

Grounding (§10): the FTC's dark-patterns framework (2022 staff report; Epic Games and Fashion Nova actions), the EU's interface-manipulation prohibitions (DSA Art. 25, UCPD guidance, CNIL consent-asymmetry decisions), CCPA's symmetry-in-choice rules, and the research taxonomies (Brignull; Mathur et al.; Gray et al.).

**Anti-creep anchor.** Every check below traces to one of three harms: *money taken through a choice the user didn't knowingly make*, *consent extracted the user didn't knowingly give*, or *a decision forced through fabricated decision-inputs*. A proposed check that traces to none of these does not belong in this criterion.

## 3. Scope (§3.3)

**Covers** — interface **choice architecture** on the product's covered surfaces:

- **Pressure signals** displayed where choices are made: urgency (countdowns, deadlines), scarcity (stock/demand claims), social proof (activity feeds, testimonials, review aggregates) — *their truthfulness, not their tone*.
- **Choice controls**: the wording, semantics, and visual presentation of accept/decline options; consent and permission prompts; defaults and pre-selections.
- **Order/account integrity**: what ends up in a cart, order, account, or enrollment versus what the user affirmatively chose.
- **Prompt recurrence**: whether a declined prompt stays declined.

**Covered surfaces** = purchase and checkout flows, consent and permission prompts, offer/upsell/enrollment prompts, and any surface where the product asks the user to choose — **except the surfaces excluded below.**

**Non-goals** (explicitly out of scope, owned elsewhere or deferred):

- **The cancellation flow and the auto-renewal disclosure/consent facts of signup** → **`no-subscription-trap`**, which owns dark patterns on those surfaces (its §3.3; reciprocal exclusion here). Within a signup flow, the auto-renewal disclosure and its consent control are theirs; *everything else* in signup — pre-checked marketing boxes, fake urgency banners, sneaked add-ons — is this criterion's.
- **Price honesty and completeness** — drip pricing, hidden mandatory fees, misleading price framing → **`transparent-pricing`**. This criterion owns *unconsented additions to the order*; whether the *disclosed price itself* is honest is theirs. (A sneaked $2.99 line item violates this criterion because it wasn't chosen, not because of its amount.)
- **The substance of data practices** — what is collected, shared, sold, retained → **`no-surveillance`** (future criterion). This criterion owns *manipulation of the consent interface*; what happens to the data after consent is theirs.
- **Data export and account deletion** → **`no-lock-in`** (including deletion-flow obstruction — the account-exit analogue of the cancellation carve-out).
- **Advertising and content claims** beyond the enumerated interface pressure signals — product-quality claims, endorsements, "pre-approved" offers — are deception law's domain, not interface choice architecture. A criterion that owned every false statement would own everything.
- **Engagement-maximizing design as such** — infinite scroll, autoplay, streaks, gamification. Real, but it needs its own harm model and bright lines; folding it in here would make this criterion unjudgeable. Candidate future criterion.
- Obstruction-family patterns live where their surface lives: the canonical roach motel (subscription cancellation) is `no-subscription-trap`'s; deletion difficulty is `no-lock-in`'s; obstruction of *declining* on covered surfaces is here (checks 5, 6, 8).

**Related criteria:**
- `overlaps` → **`no-subscription-trap`**: it **owns** dark patterns within cancellation and renewal-consent flows; this criterion **excludes** that surface and defers there (CRITERION-SPEC §3.3, exactly one owner — stated on both sides).
- `complements` → **`transparent-pricing`** (price honesty), **`no-lock-in`** (exit rights), **`no-surveillance`** (future; data-practice substance behind the consent interfaces this criterion polices).

**Applicability.** If the artifact presents **no covered choice surfaces at all** — no purchase flow, no consent or permission prompts, no offers, no selectable options (e.g., a static content page, a CLI tool with no commercial or consent surface) — the criterion does not apply: every blocking check returns `na` and the verdict is **INDETERMINATE** (treated as absent), never a vacuous PASS (CRITERION-SPEC §4.4; this is the first criterion drafted under that 0.5.0 default).

## 4. Requirements → Checks (§3.4, §4)

**On observation modes.** This criterion is deliberately **dual-mode**, and every check is `either`. The design doc stakes out `no-dark-patterns` as *"the criterion most judgeable from client-side source … the keystone test of code-audit judgment"* (MVP, Stage 0): fabricated urgency is a `Date.now()+600` seed with no backend deadline; fabricated social proof is a hardcoded name array on an RNG interval; an inverted checkbox is a negated handler; a suppressed decline control is a CSS rule. The same facts are observable behaviorally (a timer that resets per session; identical "recent purchase" toasts served to every fresh identity; the rendered flow). Per CRITERION-SPEC §4.2, the attestation records per check which mode actually adjudicated it. Where the deciding logic is server-side and only behavioral evidence can reach it, a code-mode run returns `unobserved` for that check rather than guessing. (This is the first multi-mode criterion authored against the mold — a deliberate test that per-check modes and `either` hold up, the complement of `no-subscription-trap`'s single-mode test.)

**Mode-join rule (when both modes run in one audit).** Outcomes join by **evidence union, not vote**: a check `fail`s if *either* mode's evidence establishes a fail shape; it `pass`es only when the falsification procedure of every mode that ran completed without findings. A clean codebase does not exonerate an observed live violation (the violation may be server-injected — that is what shipped to users); an innocent-looking rendered surface does not exonerate coded fabrication (the RNG *is* the fabrication). (Recorded as finding T-11, §11 — the mold has no default for this yet.)

Severity legend: **blocking** fails the criterion; **caveat** — its `fail` → CONDITIONAL; **advisory** informational (none here).

| # | check_id | keyword | severity | one-line |
|---|----------|---------|----------|----------|
| 1 | `no-false-urgency-or-scarcity` | MUST NOT | blocking | countdowns/deadlines/stock claims must be real |
| 2 | `no-fabricated-social-proof` | MUST NOT | blocking | activity feeds/testimonials/aggregates must reflect real data |
| 3 | `no-confirmshaming` | MUST NOT | blocking | declining never requires a shame-worded choice |
| 4 | `no-trick-wording` | MUST NOT | blocking | no inverted/misstated control semantics |
| 5 | `no-visual-interference` | MUST NOT | blocking | no concealed options or disguised affordances |
| 6 | `choice-symmetry` | MUST | blocking | declining costs no more actions than accepting; nothing pre-selected |
| 7 | `no-unconsented-additions` | MUST NOT | blocking | nothing joins the order/account without an affirmative choice |
| 8 | `no-nagging-after-decline` | SHOULD NOT | caveat | declined prompts stay declined |

### Check 1 — `no-false-urgency-or-scarcity`
- **Statement (MUST NOT):** Covered surfaces MUST NOT display urgency or scarcity signals that are false: countdown timers or deadlines not tied to a real expiry (they reset, persist past zero, or gate nothing that actually changes); "limited time" claims with no real limit; stock, availability, or demand claims ("only 3 left", "12 people viewing") not backed by the real state they purport to report; or a technically-real signal deployed so that the urgency it communicates about the **material** decision is false (see decision).
- **Modes:** either
- **Evidence:** `source_ref` (timer seeding, stock/viewer-count generation), `dom_snapshot`, `screenshot`, `flow_transcript` (cross-session/cross-identity comparison, post-expiry re-visit), `har_capture` (whether displayed counts come from a backend at all).
- **Procedure:** Inventory urgency/scarcity signals on covered surfaces. CODE: trace each displayed value to its source — server-supplied state vs client-side generation (RNG, constants, per-load seeds). BEHAVIORAL: revisit across sessions/identities and past the stated expiry; record whether the timer resets, the offer survives its own deadline, or the counts regenerate implausibly.
- **Decision (cascade, first match wins — CRITERION-SPEC §4.6):** `na` — no urgency or scarcity signals on any covered surface. `unobserved` — signals present, but the falsification procedure could not complete within the window (e.g., no post-expiry or cross-session observation possible, and no code access). `fail` — any displayed signal is fabricated: the timer resets or its expiry changes nothing (the offer persists); the claimed limit does not exist; a count is generated client-side or by rule with no backing state; or a real signal about an immaterial element is presented so as to fabricate urgency about the material one (a real "free sticker" countdown juxtaposed to imply the cart price expires — the price urgency communicated is false). `conditional` — every signal is literally true but engineered to mislead at the margin: a real, expiring timer whose equivalent offer relaunches immediately after expiry (serial "flash" sales making permanent pricing look time-limited). `pass` — otherwise: every displayed signal is backed by real state (or there are honest signals only).
- **Severity:** blocking
- *Boundary:* the tone or prominence of a **true** signal is not this check's concern — truthful urgency is legitimate commerce. Falsity is the predicate.

### Check 2 — `no-fabricated-social-proof`
- **Statement (MUST NOT):** Covered surfaces MUST NOT display social-proof signals that are fabricated or that misrepresent the data behind them: activity notifications ("X just bought Y") generated rather than drawn from real events; testimonials or reviews that do not exist or were not made by users; or displayed aggregates (ratings, counts) curated to misrepresent the underlying data — including suppressing negative entries while presenting the remainder as the whole.
- **Modes:** either
- **Evidence:** `source_ref` (static name/message arrays, notification generators, review-filter logic), `har_capture` (whether activity data is fetched from any backend), `dom_snapshot`, `flow_transcript` (cross-session/cross-identity comparison), `screenshot`.
- **Procedure:** Inventory social-proof elements. CODE: trace displayed events/aggregates to their source; flag client-side generation and filtered aggregation. BEHAVIORAL: compare feeds across fresh identities and sessions (identical "recent" sequences to every visitor indicate generation); cross-check displayed aggregates against enumerable detail (review counts vs listed reviews).
- **Decision (cascade):** `na` — no social-proof elements on covered surfaces. `unobserved` — elements present, but neither source tracing nor cross-session falsification was possible within the window. `fail` — a signal is fabricated (generated events, invented testimonials) or the displayed aggregate misrepresents the underlying data (negative entries suppressed from an aggregate presented as complete). `conditional` — signals are drawn from real data but framed to mislead at the margin: real events presented with false recency ("just bought" toasts replaying days-old orders as live). `pass` — otherwise: displayed social proof traces to real events/users and aggregates reflect the underlying data.
- **Severity:** blocking

### Check 3 — `no-confirmshaming`
- **Statement (MUST NOT):** On covered surfaces, declining an offer, enrollment, or consent MUST NOT require selecting a control worded to shame, belittle, or guilt the decliner — whether by self-disparagement ("No thanks, I like paying full price") or by editorializing the decline as harmful or foolish ("No, I don't want to protect my family").
- **Modes:** either
- **Evidence:** `screenshot`, `dom_snapshot` (the decline control's text), `source_ref` (string resources/templates).
- **Procedure:** Inventory offer/consent prompts on covered surfaces; capture the exact wording of each decline control and its immediate framing.
- **Decision (cascade):** `na` — no prompts with an accept/decline choice on covered surfaces. `unobserved` — such prompts exist but their decline controls could not be captured within the window. `fail` — any decline control is shame-worded (self-disparaging, or editorializing the decline as harmful/foolish/shameful). `conditional` — decline controls are neutrally worded, but the prompt's surrounding copy leans on guilt- or fear-framing to pressure the choice (loss language aimed at the decliner) while both options remain neutrally labeled. `pass` — otherwise: declining is available through neutrally worded controls.
- **Severity:** blocking
- *Boundary:* stating a factual consequence of declining ("you will lose access to X") is not confirmshaming; weaponizing the choice control's own wording is. The `conditional` band exists for pressure-copy around neutral controls.

### Check 4 — `no-trick-wording`
- **Statement (MUST NOT):** Choice controls on covered surfaces MUST NOT carry wording or semantics that invert or materially misstate their effect: double negatives ("Uncheck to not receive…"); checkboxes/toggles whose label polarity is reversed relative to their effect; mixed opt-in/opt-out semantics within one form engineered to confuse; or action controls whose label materially misstates what they do — including controls that place a charge or commitment without saying so.
- **Modes:** either
- **Evidence:** `dom_snapshot` (labels vs control state), `source_ref` (handlers — what the control actually toggles/submits), `screenshot`, `flow_transcript` (what following the control actually did).
- **Procedure:** Inventory choice controls on covered surfaces; for each, compare the label's plain-language meaning against the control's actual effect (CODE: the handler; BEHAVIORAL: exercise it and observe). Flag negation stacking, reversed polarity, mixed semantics, and label↔effect mismatches.
- **Decision (cascade):** `na` — no choice controls on covered surfaces (no forms, toggles, or action prompts). `unobserved` — controls exist but their effects could not be established within the window (not exercisable, no code access). `fail` — any control's wording inverts or materially misstates its effect: a double negative or reversed polarity governs a consent/enrollment; adjacent controls mix opt-in and opt-out semantics such that a consistent reading produces the wrong result; or an action control effects a charge/commitment its label does not state. `pass` — otherwise: control labels state their effects plainly and polarity is consistent.
- **Severity:** blocking
- *Boundary:* verbose-but-accurate wording is not trick wording (density without inversion passes); inversion, reversal, and misstatement are the predicates. Whether a charge-placing control was *presented as a choice at all* is check 7's question; *mislabeled* controls are this check's.

### Check 5 — `no-visual-interference`
- **Statement (MUST NOT):** On covered surfaces, the product MUST NOT use visual presentation to hide or disguise choices: a decline/close/opt-out option rendered effectively undiscoverable (contrast, size, or placement far outside where a user would reasonably look — concealment); interactive elements disguised as something else (ads styled as content or system UI, fake close buttons, simulated OS dialogs); or visual state that misrepresents what is selected.
- **Modes:** either
- **Evidence:** `screenshot` (rendered presentation — primary), `dom_snapshot` (computed styles, z-order, positioning), `source_ref` (styling/overlay logic).
- **Procedure:** For each covered surface with competing options, capture the rendered presentation; record the discoverability of the disfavored option (contrast, size, position, occlusion) and whether any interactive element masquerades as content or system UI. CODE corroborates with the styling rules that produce the rendering.
- **Decision (cascade):** `na` — no covered surfaces presenting competing options or third-party/promotional elements. `unobserved` — such surfaces exist but rendered presentation could not be captured within the window. `fail` — an available option is concealed (rendered at near-invisible contrast/size, positioned where a user would not reasonably find it, or occluded), or an interactive element is disguised as content or system UI. `conditional` — the disfavored option is legible and discoverable in-flow but **materially subordinated** (e.g., a small plain text-link set against a large accent button) — visible, but styled to be overlooked. `pass` — otherwise: competing options are presented with ordinary emphasis differences at most (both legible, discoverable, presented as controls).
- **Severity:** blocking
- *Boundary:* three calibrated bands — ordinary CTA emphasis (both options clearly presented) = `pass`; legible-but-materially-subordinated = `conditional`; effectively undiscoverable or disguised = `fail`. Within this criterion's surfaces only; the cancel-control analogue inside cancellation flows is `no-subscription-trap` check 3's.

### Check 6 — `choice-symmetry`
- **Statement (MUST):** Where a covered surface asks the user to accept or decline something optional — a data/marketing consent, a permission, an optional add-on or enrollment — declining MUST be available with parity: reachable in **no more user actions than accepting**, present on the **same surface** where acceptance is offered, and never **pre-selected** toward acceptance (no pre-ticked consent boxes, no default-on optional add-ons presented as chosen).
- **Modes:** either
- **Evidence:** `flow_transcript`, `step_count` (actions to accept vs actions to decline), `dom_snapshot` (default states, what the first layer presents), `screenshot`, `source_ref` (default values, branch structure).
- **Procedure:** Inventory optional accept/decline prompts on covered surfaces. For each: count minimum user actions to complete acceptance and to complete declination; record whether decline is present on the first surface or requires navigation; record default states of consent/add-on controls.
- **Decision (cascade):** `na` — no optional accept/decline prompts on covered surfaces. `unobserved` — prompts exist but the decline path could not be exercised or counted within the window (e.g., variant-gated). `fail` — declining requires **more actions** than accepting (including exactly one more — reject behind an expander or second layer when accept is one action); or decline is absent from the surface where acceptance is offered (reachable only via navigation elsewhere); or the optional choice is pre-selected toward acceptance. `pass` — otherwise: decline available in actions ≤ accept, on the same surface, defaults neutral or off.
- **Severity:** blocking
- *Boundary:* deliberately strict, with no `conditional` band: action-count parity is the crispest operationalization of "declining as easy as accepting" (CCPA §7004's symmetry rule; the CNIL consent decisions; EDPB taskforce), and a strict opening position is free to loosen while `draft` (T-4 window) if calibration shows humans read one-expand-reject as a caveat rather than a violation — flagged in §12. This check owns the **structural** facts (counts, presence, defaults); the *visual styling* of the same prompt is check 5's, and its *wording* is checks 3/4's — one owner per fact, no double-counting. The auto-renewal consent control at signup is `no-subscription-trap` check 5's; a marketing checkbox on the same screen is this check's.

### Check 7 — `no-unconsented-additions`
- **Statement (MUST NOT):** The product MUST NOT add items, services, enrollments, or charges to a user's order or account without an affirmative choice: no sneaking items into a cart; no bundling an unrelated enrollment silently into another action; no charging an interaction that was not presented as a purchase or commitment.
- **Modes:** either
- **Evidence:** `flow_transcript` (what was selected vs what the order/account contains), `screenshot` (order review, receipts), `dom_snapshot`, `notification_record` (order confirmations), `source_ref` (cart-mutation/enrollment logic), `har_capture`.
- **Procedure:** Exercise the purchase/enrollment flow selecting only explicit choices; diff the resulting order/account state against the user's affirmative selections. CODE: inspect cart-mutation and enrollment triggers for paths not gated on an explicit user choice.
- **Decision (cascade):** `na` — no order, enrollment, or charge-capable flows on covered surfaces. `unobserved` — flows exist but order/account state could not be reached or read within the window (e.g., payment stage not exercisable). `fail` — anything appears in the order or account that the user never affirmatively selected: a silently added line item; an enrollment bundled unstated into an unrelated action; a charge triggered by an interaction not presented as a purchase/commitment. `conditional` — the addition was disclosed on the committing surface but not separately choosable (a stated extra bundled into a single "Continue" with no independent opt-out control) — disclosed, but consent was not distinct. `pass` — otherwise: order and account contain exactly what was affirmatively chosen; optional extras were offered unselected.
- **Severity:** blocking
- *Boundary:* the **amount or honesty of a disclosed price** is `transparent-pricing`'s; this check owns whether the *addition was chosen*. A pre-selected add-on **presented as a choice** is check 6's pre-selection shape; an addition **never presented as a choice at all** is this check's. Recurring-billing consent is `no-subscription-trap` check 5's.

### Check 8 — `no-nagging-after-decline`
- **Statement (SHOULD NOT):** A prompt the user has declined (a rating request, notification/permission ask, upsell, install banner) SHOULD NOT be re-presented within the same session, re-presented so often across sessions that it functions as wearing the user down, or re-presented so as to block task progress.
- **Modes:** either
- **Evidence:** `flow_transcript` (decline events and re-presentations, with timestamps), `screenshot`, `source_ref` (re-prompt scheduling/persistence logic).
- **Procedure:** Decline each recurring-prompt type once; continue using the product across the observation window; record every re-presentation of a declined prompt (same-session, cross-session counts, task-blocking behavior). CODE corroborates via the persistence and re-trigger logic.
- **Decision (cascade):** `na` — no declinable recurring prompts on covered surfaces, or none were declined during observation. `unobserved` — prompts were declined but the window was too short to observe recurrence behavior. `fail` — a declined prompt re-presents within the same session; or re-presents **three or more** times across the observation window; or a re-presentation blocks task progress until re-answered. `conditional` — a declined prompt re-presents exactly **twice** across the window (persistent, at the tolerance edge, but not wearing-down). `pass` — otherwise: declined prompts stay dismissed for the session and reappear at most once across the window.
- **Severity:** caveat
- *Note:* thresholds (same-session; 2 vs ≥3 per window) are deliberately explicit so two adjudicators converge, and are first-draft values for calibration to stress (§12). The counting unit is the prompt *type*, not the pixel-identical dialog. As `caveat` severity, `fail` here contributes CONDITIONAL, never FAIL (CRITERION-SPEC §4.4).

## 5. Aggregation & verdicts (§4.4, §5)

Default aggregation, inherited from CRITERION-SPEC §4.4 (`na` excluded; advisory absent here):

| Verdict | Condition |
|---|---|
| **PASS** | All blocking checks (1–7) `pass` (with `na` excluded and **at least one blocking check applying**), no check returns `conditional`, and check 8 is `pass`, `na`, or `unobserved`. |
| **CONDITIONAL** | No blocking `fail`, but ≥1 of: any check returns `conditional` (possible on 1, 2, 3, 5, 7, 8 as currently decided); check 8 (`caveat`) `fail`s; a **blocking** check is `unobserved` (partial scope). MUST enumerate the triggering check_ids. |
| **FAIL** | Any blocking check (1–7) returns `fail`. Enumerate **all** failing blocking checks (CRITERION-SPEC §5.2, C-1). |
| **INDETERMINATE** | The audit could not run or reach consensus at all; **or every blocking check returned `na`** — the artifact has no covered choice surfaces, so the criterion did not apply (§3 Applicability; CRITERION-SPEC §4.4). Treated as absent. |

Check 8 `unobserved` does not downgrade (non-blocking partial scope — CRITERION-SPEC §4.4): prompt-recurrence behavior is unobservable in short windows, and forcing CONDITIONAL for a SHOULD-check the window couldn't reach would make the caveat meaningless (same reasoning as `no-subscription-trap` check 7).

**Attribution.** On FAIL, enumerate all failing blocking checks; on CONDITIONAL, enumerate the specific triggering check(s) — machine-readable, per CRITERION-SPEC §5.2.

**Confidence** (§5.3): `min` over contributing checks of `(model_agreement × evidence_completeness)`, where `evidence_completeness` reflects how much of each check's falsification procedure actually completed **in the mode(s) run** (a check decided code-side with full source access scores higher than one decided from a single rendered capture). Bands: high ≥ 0.90; medium ≥ 0.70 and < 0.90; low < 0.70 → downgrade to INDETERMINATE + route to review.

## 6. Corpus (§6)

Seed corpus and provenance discipline live in `./corpus/public/README.md`. Rules specific to this criterion:

- **Named-product entries cite public enforcement records** (FTC actions, CNIL decisions, EU CPC commitments — factual, dated, defamation-safe), tagged with the enforcement source and `observed_at`. Everything else is synthetic fixtures targeting specific checks and boundaries.
- **Dual-mode rows state which mode decides them** where it matters: several fixtures are engineered to be decidable in one mode and invisible in the other (server-side toast generation defeats code audit; client-side seeds defeat a single behavioral capture) — these anchor the mode-join rule (§4) and the `unobserved` arms.
- The public corpus **meets the `candidate` category minimums** (37 examples). The remaining gate to `candidate` is the §7 human-calibration pass.

## 7. Validation record (§7)

`status: draft` — nothing is measured yet. Path to promotion:

- **draft → candidate:** run the **human-calibration gate** (CRITERION-SPEC §7.1): ≥2 independent adjudicators over the public corpus against a **pre-registered target**. The target is *not yet registered* — it MUST be finalized (one metric, thresholds, boundary+adversarial hard-subset floor) **before** formal adjudication begins, and is expected to mirror the sibling criterion's (Cohen's κ ≥ 0.8 aggregate AND ≥80% exact-verdict on boundary+adversarial pooled). Engineering dry-runs (blind LLM panels, as run for `no-subscription-trap`) come first and do not consume the gate.
- **candidate → active:** run the validation study (CRITERION-SPEC §7.2) on the **sealed** corpus for **each applicable model pool — both pools apply here**: this criterion is the code-audit keystone, so the enclave-contained pool is *not* n/a (unlike the purely behavioral sibling); the design doc's two-pool comparison lands on this criterion first. Publish per-pool false-pass / false-flag / indeterminate / agreement / cost. Kill thresholds: false-pass ≤ ~5%, false-flag ≤ ~10%; sealed set sized ≥ 3/ε per side (≥60 violating, ≥30 clean). Only then may attestations issue.

## 8. Claim language (§8)

> "Artifact `{subject}` satisfied `no-dark-patterns@{version}` under rubric `{rubric_version}`, audit artifact `{prompt_version}`, model set `{model_set}`, modes `{modes}`; measured false-pass `{fp}` / false-flag `{ff}` on corpus `{corpus_hash}`."

`{modes}` is load-bearing for this criterion in a way it is not for single-mode criteria: it tells the consumer *which kind of claim this is*. A code-mode attestation binds a code hash (`{subject}` = hash; immutable); a behavioral-mode attestation binds a service identity over an observation window (`eap.behavioral.v1`; expires); a both-modes attestation is the strongest available (design doc, Verification spectrum).

**Does NOT assert:** price honesty or completeness (`transparent-pricing`); anything about the cancellation flow or auto-renewal consent (`no-subscription-trap`); what happens to data after consent (`no-surveillance`, future); export/deletion (`no-lock-in`); truthfulness of advertising content beyond the enumerated interface pressure signals; surfaces, variants, or A/B arms not exercised by the audit; future behavior beyond a behavioral run's window.

## 9. Audit-artifact binding (§9)

Because this criterion is dual-mode, it binds **two audit-artifact realizations** (both planned; versions null until validation):

- **Prompt bundle** (CODE mode): presents submitted source, markup, styles, and string resources to the judges as **quoted untrusted data, never instructions** — comments and identifiers are exactly where this criterion's injection canaries live. Explicit check → prompt-section mapping required at `candidate`.
- **Probe script** (BEHAVIORAL mode): mystery-shops covered surfaces (fresh identities, cross-session revisits, post-expiry checks, decline-then-continue sequences), treating all page/app content as untrusted data; stealth properties (residential egress, realistic timing) are governed by the design doc, Architecture §7. Explicit check → probe-step mapping required at `candidate`.

The mold currently models a criterion as binding **one** audit artifact (prompt bundle *or* probe script) under a single `prompt_version` — recorded as finding **T-10** (§11). Until the mold rules, this criterion treats `prompt_version` as identifying the artifact(s) for the mode(s) actually run, and the manifest carries one `prompt_bundle` reference per mode.

## 10. Provenance & governance metadata (§10)

- **Authors:** Scott Helvick
- **Reviewers:** —
- **Sources:**
  - Brignull, H. — deceptive.design (dark-pattern taxonomy: confirmshaming, sneaking, trick wording, visual interference, fake urgency/scarcity/social proof, nagging).
  - Mathur, A. et al., "Dark Patterns at Scale: Findings from a Crawl of 11K Shopping Websites" (2019) — prevalence taxonomy; documented fabricated countdowns and activity messages in the wild.
  - Gray, C. et al., "The Dark (Patterns) Side of UX Design" (CHI 2018).
  - FTC Staff Report, "Bringing Dark Patterns to Light" (September 2022).
  - OECD, "Dark Commercial Patterns" (2022).
  - FTC v. Epic Games, Inc. (2022–2023) — alleged counterintuitive, inconsistent button configuration placing charges from single presses not presented as purchases; $245M order. Public record.
  - FTC v. Fashion Nova, LLC (2022) — alleged suppression of sub-4-star reviews while displaying the remainder; settlement. Public record.
  - CNIL, deliberations SAN-2022-003 (Google) and SAN-2022-004 (Facebook), January 2022 — cookie-consent asymmetry (accept in one click; refusal requiring several actions); fines. Public record.
  - European Commission / CPC network — Booking.com commitments on pressure messaging (scarcity/urgency presentation), 2019–2020; CPC sweep of online shops finding manipulative practices on 148 of 399 sites (2023). Public records.
  - EDPB Cookie Banner Taskforce report (January 2023) — first-layer reject expectations.
  - CCPA regulations, 11 CCR §7004 — "symmetry in choice"; consent obtained through dark patterns is not consent.
  - EU Digital Services Act, Art. 25 — prohibition on deceptive/manipulative interface design; UCPD guidance (2021/C 526/01).
  - UIGuard (Chen et al., 2023) — automated dark-pattern detection in mobile UIs; DarkBench (2025) — dark-pattern benchmark for conversational interfaces. Candidate adversarial-case sources per the design doc.
- **first_active:** —
- **delegation_inclusion_count / overturn_rate:** — (post-launch)
- **Changelog:**
  - `0.1.0` — initial draft (2026-07-06). Eight checks; dual-mode (every check `either` — the first multi-mode criterion, per the design doc's "keystone test of code-audit judgment"); scope boundaries drawn against `no-subscription-trap` (cancellation + renewal-consent surfaces excluded, both sides now stating the same owner), `transparent-pricing` (price honesty), `no-surveillance` (data-practice substance; the consent *interface* is owned here), `no-lock-in` (export/deletion). Strict opening position on check 6 (no conditional band; one-extra-action reject = fail) taken deliberately in the T-4 window, flagged for calibration (§12). Mode-join rule stated (§4) pending a mold default (T-11); dual-artifact binding recorded as mold finding T-10.

## 11. Findings against CRITERION-SPEC 0.5.0

Authoring the first **dual-mode** criterion surfaced two gaps in the mold — the same motion by which `no-subscription-trap` surfaced T-1/T-2/T-3 (single-mode) and T-5/T-6 (cascade discipline). Recorded here pending a meta-spec decision; **not** silently worked around:

- **T-10 — §9 assumes one audit artifact per criterion.** The mold binds "an over-code **prompt bundle** for code-tier criteria, *or* a **probe script** for behavioral criteria," and Appendix A carries a single `prompt_bundle: { ref, version }`. A dual-mode criterion realizes its checks in **two** artifacts (one per mode), and an audit may run one or both. Open questions for the mold: does `prompt_version` in the attestation identify a composite bundle, or the artifact(s) for the mode(s) actually run? Should the manifest's `prompt_bundle` become per-mode (a map keyed by mode)? This criterion's interim answer (§9): one reference per mode; `prompt_version` identifies what actually ran.
- **T-11 — no mode-join rule for `either` checks.** When both modes adjudicate the same check in one audit, the mold does not say how their outcomes combine. This criterion states the rule it believes should be the default (§4): **evidence union** — `fail` if either mode establishes a fail shape; `pass` only when every mode that ran completed its falsification procedure clean; neither mode exonerates the other (server-injected violations are invisible to code; coded fabrication can render innocently in a single capture). Candidate for promotion to CRITERION-SPEC §4.2 or §4.6.

## 12. Calibration queue (pre-first-dry-run)

No calibration has run yet. The engineered boundaries a first blind-panel dry-run (and later the formal §7.1 gate) must stress, stated in advance:

- **Check 6 strictness** — the deliberate no-conditional-band position: is one-extra-action reject (single in-place expand) read by independent raters as FAIL (as decided, per CCPA symmetry / CNIL) or as a caveat? If calibration says the strict line costs agreement, loosening is free while `draft` (T-4 window) — but the default is to hold the enforced-standard line. (`adv-syn-first-layer-asymmetry` is the anchor row.)
- **Check 5's three-band lane** — ordinary emphasis (`clean-syn-emphasized-cta-legible-alt`, pass) vs materially-subordinated (`bound-syn-subordinated-decline`, conditional) vs concealed (`viol-syn-ghost-decline`, fail): do raters place the middle case consistently?
- **Check 1's technically-true band** — recurring flash sale (`bound-syn-recurring-flash-sale`, conditional) vs decoy timer (`adv-syn-decoy-timer`, fail): does "literally true but materially misleading about the decision" split raters?
- **Check 8's counting thresholds** — same-session / 2× / ≥3× per window: are the counts adjudicable from transcripts alone, and is the prompt-*type* counting unit stable?
- **Mode-join cases** — `adv-syn-serverside-toasts` (behavioral-only decidable) and `viol-syn-reset-countdown` (decidable in both): do raters given only one mode's evidence reach the outcomes the mode-join rule predicts?
