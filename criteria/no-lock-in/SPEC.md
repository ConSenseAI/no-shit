# `no-lock-in` — No Lock-In

**Version:** 0.1.0 · **Status:** draft
**Conforms to:** CRITERION-SPEC 0.6.0 (`../CRITERION-SPEC.md`)
**Observation mode:** behavioral (single-mode — see §4)

---

## 1. Guarantee (§3.1)

You can leave with your stuff. Your data exports self-service, in standard machine-readable formats, complete, on the plan you are on; your account deletes self-service without talking to a human; the way out is not obstructed; and a deletion means deleted.

## 2. Harm model (§3.2)

Lock-in extracts through **switching costs**, and it is the credence good whose deferral is longest: nothing about lock-in is visible while you are happily using the product. The harm arrives only at the exit — often years after purchase:

- **At export** — the data you created is hostage: there is no export, or it costs extra, or it arrives as a flattened PDF or a proprietary blob only the same vendor can read, or it silently omits half of what you made. Each of these converts "I want to switch" into "I must abandon my work," which prices the switch at re-creation cost.
- **At deletion** — the account cannot die: deletion requires a human channel, a retention gauntlet, or a payment; or "deletion" is a deactivation that quietly resurrects with a login. The user who cannot leave cleanly remains billable, marketable, and countable.
- **Compounding over time** — every month of continued use deepens the hostage pile, so the extraction *grows* precisely as the user's wish to leave grows. This is why the market cannot price it at purchase: the buyer evaluating two products sees identical onboarding and cannot see the exit.

The burden falls on individuals (lost work, zombie accounts) and — the procurement wedge this criterion serves — on **organizations**, whose vendor risk is exactly the cost of getting their data out; data-exportability questions already gate enterprise deals, answered today with questionnaire theater rather than verification.

Grounding (§10): GDPR Arts. 20 (portability: "structured, commonly used and machine-readable format") and 17 (erasure); CCPA/CPRA portability and deletion rights; the EU Data Act's switching and data-egress provisions; DMA Art. 6(9); the platform norm that apps offering account creation must offer in-app deletion.

**Anti-creep anchor.** Every check traces to one harm: *the cost of leaving is inflated by withholding the user's data or the account's death.* A proposed check that does not reduce exit cost does not belong here.

## 3. Scope (§3.3)

**Covers** — the exit lifecycle of an account and its data:
- **Data export**: availability (self-service, on the current tier, at no additional charge), format (machine-readable, standard), and completeness (the user's contributed content and its reconstruction metadata).
- **Account deletion**: availability (self-service, same medium, no human intervention, no payment gate) and **honoring** (deleted means deleted — no silent reactivation, no post-deletion marketing).
- **Obstruction within the export and deletion flows** (this criterion's owned dark-pattern surface — see Related).
- Surfacing export before deletion (data-loss protection at the exit).

**Tier note (procurement).** Checks apply at whichever account tier the probe exercises — individual or workspace/organization admin. "Current tier" means: data created on a tier is exportable on that tier; export is not a paid upgrade or a metered egress charge.

**Non-goals** (explicitly out of scope, owned elsewhere or deferred):
- **Cancelling recurring billing** → **`no-subscription-trap`**. Cancellation and deletion are *sequential* exits with one owner each: stopping payment is theirs; killing the account and taking your data is this criterion's. A flow that conflates them is judged by each criterion on its own facts.
- **Exit pricing** — early-termination fees, final-bill honesty → **`transparent-pricing`** (the `no-subscription-trap` calibration already routes the Adobe ETF *fee* there; same rule here). The *existence* of a paywall on export/deletion is this criterion's (checks 1/4); the *honesty of the amount* is theirs.
- **Data-practice substance** — what the provider retains, shares, or processes internally after deletion → **`no-surveillance`** (future). This criterion owns the **observable** exit facts: the flows, the export artifact, and observable honoring (reactivation, post-deletion messaging, documented persistence). Backend retention policy beyond observables is theirs; when authored, it MUST exclude the observable exit-flow facts and defer here.
- **Obstruction outside the export/deletion flows** → **`no-dark-patterns`** (reciprocal: its scope excludes these flows and defers here — stated on its side since its 0.1.1).
- **Interoperability and migration guarantees** — API access, import tooling at the destination, third-party importability of the export, format-conversion fidelity. This criterion guarantees you leave *with your data in a standard form*, not that any particular competitor can ingest it.
- **Contractual data-return clauses** (B2B MSAs) — contract law; only the product surface is probed.
- **Device/hardware lock-in**; **content the user does not own** (other users' data, licensed catalog content) — exports cover the user's own contributed data and account records.

**Related criteria:**
- `complements` → **`no-subscription-trap`** (billing exit vs account/data exit — the two halves of leaving; highest assurance is both passing).
- `overlaps` → **`no-dark-patterns`**: this criterion **owns** obstruction within the export and deletion flows (check 5); `no-dark-patterns` owns choice-architecture manipulation everywhere else and already states the reciprocal exclusion (its §3, since 0.1.1).
- `complements` → **`transparent-pricing`** (exit-fee honesty) and **`no-surveillance`** (future; MUST exclude observable exit-flow facts and defer here — recorded on this side because that criterion is unauthored).

**Applicability.** If the observed product has **no persistent user account and no user-contributed or account data** (a stateless tool; nothing to export, nothing to delete), the criterion is not probeable: every blocking check returns `na` and the verdict is **INDETERMINATE** (treated as absent, CRITERION-SPEC §4.4) — never a vacuous PASS.

## 4. Requirements → Checks (§3.4, §4)

**On observation mode.** This criterion is **behavioral by nature**, single-mode — the second such (after `no-subscription-trap`), and the first authored natively against CRITERION-SPEC 0.6.0. Whether a deletion is honored, whether an export is complete, and what the exit flow actually serves are **server-side facts**: client source can corroborate that controls exist, but it cannot prove the export's contents or the account's death, so no check declares a `code` mode and source is never authoritative here. Per CRITERION-SPEC §9 (0.6.0), the single declared mode binds a single audit artifact — a probe script — under the flat manifest shape.

Severity legend: **blocking** fails the criterion; **caveat** — its `fail` → CONDITIONAL; **advisory** informational (none here).

| # | check_id | keyword | severity | one-line |
|---|----------|---------|----------|----------|
| 1 | `self-service-export` | MUST | blocking | your data exports self-service, on your tier, free |
| 2 | `standard-export-format` | MUST | blocking | exports are machine-readable, standard formats |
| 3 | `export-completeness` | MUST | blocking | the export contains what you made |
| 4 | `self-service-deletion` | MUST | blocking | the account deletes self-service, no human, no paywall |
| 5 | `no-exit-flow-obstruction` | MUST NOT | blocking | no gauntlets/burial/tricks in export or deletion flows |
| 6 | `deletion-honored` | MUST | blocking | deleted means deleted — no silent resurrection |
| 7 | `pre-deletion-export-prompt` | SHOULD | caveat | the deletion flow offers your data first |

### Check 1 — `self-service-export`
- **Statement (MUST):** A user MUST be able to obtain an export of their contributed content and account data via **self-service**, on the **tier where the data was created**, at **no additional charge** — not gated on a human-mediated channel (contact support, sales, a scheduled call), not gated behind a paid upgrade or a data-egress fee. Asynchronous preparation with a stated completion expectation is self-service; a **reliable** automated delivery step (emailed download link) is allowed — an unreliable or quickly-expiring one is not an availability failure but obstruction (check 5).
- **Modes:** behavioral
- **Evidence:** `flow_transcript`, `screenshot` (export controls and any gates), `dom_snapshot`, `notification_record` (delivery/ready notices), `har_capture`.
- **Procedure:** On an account holding contributed data on its current tier, locate and exercise the export path end-to-end using only self-service controls; record any human-mediated gate, upgrade/paywall gate, or charge; record delivery mechanics and stated completion expectations.
- **Decision (cascade, first match wins — CRITERION-SPEC §4.6):** `na` — the account holds no user-contributed or account data to export. `unobserved` — account/settings surfaces could not be reached or the flow could not be exercised within the window. `fail` — no export path exists; **or** export is available only through a human-mediated channel; **or** export of data created on the current tier is gated behind a paid upgrade or an additional charge (the egress-fee shape). `conditional` — initiation is self-service but completion is human-mediated with no stated timeframe (a "request my data" control fulfilled manually by staff). `pass` — otherwise: self-service initiation and delivery on the current tier at no charge (asynchronous with stated completion is fine; reliable automated delivery is fine).
- **Severity:** blocking

### Check 2 — `standard-export-format`
- **Statement (MUST):** The export MUST be **structured, machine-readable data in commonly-used formats** for the data types exported (JSON/CSV/XML for structured content; original or standard containers for media) — not a flattened rendering of structured content (PDF, screenshots), not an undocumented proprietary blob, and not an artifact consumable only by re-importing into the same vendor. Machine-readability is judged **in substance**: a standard wrapper around opaque payloads does not qualify.
- **Modes:** behavioral
- **Evidence:** `flow_transcript`, `screenshot`, `har_capture` (the artifact itself and its delivery), `contract_text` (format documentation, where published).
- **Procedure:** Obtain the export; inspect its formats against the account's data types; test that structured content is present as structured data (parse it); check any nonstandard format for published documentation.
- **Decision (cascade):** `na` — no export exists or is obtainable (that gate is check 1's finding; there is no artifact to assess — the `no-subscription-trap` check-2 channel-`na` precedent). `unobserved` — an export was initiated but no artifact was delivered within the window. `fail` — structured content is exported only as flattened renderings (PDF/images); **or** the artifact is an undocumented proprietary format; **or** it is consumable only by the same vendor's import; **or** a standard wrapper carries opaque payloads (machine-readable in name only). `conditional` — machine-readable and **documented** but nonstandard (a custom schema with published documentation — the tolerance edge). `pass` — otherwise: structured, commonly-used, machine-readable formats appropriate to the exported data types.
- **Severity:** blocking

### Check 3 — `export-completeness`
- **Statement (MUST):** The export MUST contain the user's contributed content — every **material content type** present in the account (documents, posts, uploads, contacts, records) — together with the **organizing metadata** (structure, titles, tags, timestamps, relations) needed to reconstruct it elsewhere; not a token subset engineered to look complete.
- **Modes:** behavioral
- **Evidence:** `flow_transcript` (account-contents inventory vs export diff), `screenshot`, `har_capture` (the artifact).
- **Procedure:** Enumerate the probe account's contributed content types and a sample inventory; obtain the export; diff — every content type present in the account must appear in the export, and reconstruction metadata must survive.
- **Decision (cascade):** `na` — no export exists or is obtainable (check 1's finding). `unobserved` — the account's contents could not be enumerated or diffed against the artifact within the window. `fail` — a material user-contributed content type present in the account is absent from the export. `conditional` — contributed content is complete, but organizing metadata is omitted or degraded such that reconstruction elsewhere is materially impaired (structure collapsed, tags/relations dropped). `pass` — otherwise: content types complete with reconstruction metadata.
- **Severity:** blocking

### Check 4 — `self-service-deletion`
- **Statement (MUST):** Account deletion MUST be available **self-service, in the medium where the account is used, without human intervention and without a payment gate** — not "email us to delete," not a scheduled retention call, not a different medium than the account's own (an in-app account whose deletion exists only on desktop web), and not gated behind reactivating or re-entering payment. A reasonable re-authentication step (password/2FA confirm) is fine. A stated, bounded **recovery window** (≤ 30 days) before permanent deletion is fine — it protects against accidental deletion; deferral beyond it is not.
- **Modes:** behavioral
- **Evidence:** `flow_transcript`, `screenshot` (the deletion path and terminal state), `dom_snapshot`, `contract_text` (stated deletion/recovery terms).
- **Procedure:** From account settings, attempt deletion end-to-end using only self-service controls in the account's medium; record any human-mediated gate, medium switch, or payment/reactivation gate; capture the stated effective/recovery terms.
- **Decision (cascade):** `na` — no persistent user account exists (nothing to delete). `unobserved` — deletion surfaces could not be reached within the window. `fail` — no deletion path exists; **or** deletion is gated on a human-mediated channel; **or** deletion requires a different medium than the account's own; **or** deletion is gated behind payment or plan reactivation (must resubscribe to reach the delete control). `conditional` — deletion is self-service but completion is deferred beyond a stated recovery window of 30 days (e.g., "your account will be deleted after 90 days"). `pass` — otherwise: self-service in-medium deletion, no human or payment gate, immediate or within a stated ≤30-day recovery window (re-auth confirm fine).
- **Severity:** blocking

### Check 5 — `no-exit-flow-obstruction`
- **Statement (MUST NOT):** The export and deletion flows MUST NOT deploy obstruction dark patterns: retention or diversion interstitials that cannot *each* be declined in a single action; a **gauntlet** of them (three or more in one flow, even if each is dismissible) or an interstitial that reappears after being declined within the same attempt; confirmshaming as the only path forward; trick-worded or inverted confirmations; visual **concealment or burial** of the export or delete controls (including a mandatory multi-screen detour before the real control appears); mandatory free-text "reason" entry; manufactured latency; **unreliable or expiring confirmation/delivery mechanics** (the case check 1 routes here); or deceptive-pressure content injected into the flow.
- **Modes:** behavioral
- **Evidence:** `flow_transcript` (timestamps evidence latency), `screenshot`, `dom_snapshot` (control styling, emphasis, hit-areas).
- **Procedure:** Walk both flows; at each interstitial record single-action dismissibility and whether the proceed control is clearly presented, not visually subordinated, and actually interactable; note forced surveys, offers, detours, delay, and delivery-mechanic reliability.
- **Decision (cascade):** `na` — neither an export path nor a deletion path exists at all (those gates are checks 1/4's findings; there is no flow to walk). `unobserved` — flows exist but could not be walked within the window. `fail` — any obstruction shape from the statement: a non-single-action-dismissible interstitial; **three or more** retention/diversion interstitials in one flow (offers, surveys, pause/downgrade pitches, mandatory detour screens — plain confirmations excluded) or same-attempt reappearance after decline; confirmshaming as the only path; a trick-worded or inverted confirmation; concealment or burial of the export/delete control (including a control rendered but not interactable, or reachable only through a mandatory unrelated wizard); a mandatory free-text reason; manufactured latency; unreliable/expiring confirmation or delivery mechanics; or deceptive-pressure content. `conditional` — **one or two** retention offers / exit surveys, each dismissible or skippable in a single action (present but not obstructive; recurrence only on later, *separate* attempts stays `conditional`). `pass` — otherwise: no retention interventions at all; plain confirmations and a reasonable re-auth step are not offers.
- **Severity:** blocking
- *Ownership:* this is the dark-pattern surface this criterion owns (§3.3) — the exit-flow analogue of `no-subscription-trap` check 3, whose calibrated volume rule (≥3 / same-attempt reappearance; 1–2 dismissible = conditional) is adopted verbatim.

### Check 6 — `deletion-honored`
- **Statement (MUST):** A completed deletion MUST be honored: the account MUST NOT remain observably live or silently restorable past the stated recovery window; user data MUST NOT observably persist under the account after completion (including as established by documented third-party evidence such as enforcement findings); and provider-initiated messaging to the account MUST wind down — continued marketing to a deleted account's address is treating the account as live. A terminal state the flow *presents* as deletion counts as deletion — a deactivation masquerading as deletion violates this check.
- **Modes:** behavioral
- **Evidence:** `screenshot` (terminal confirmation, stated terms), `flow_transcript` (post-deletion login attempt after the stated window), `notification_record` (post-deletion messaging), `contract_text`.
- **Procedure:** Complete deletion; capture stated effective/recovery terms. After the stated recovery window (where the observation window permits), attempt login and record whether the account or its data silently restores; monitor the account's address for provider messaging beyond transactional wind-down.
- **Decision (cascade — `fail` precedes `unobserved`, a permitted §4.6 deviation: the terms-based shapes are decidable from captured terms even when the post-window boundary is not):** `na` — no deletion path exists (check 4's finding; no completed deletion to assess). `fail` — the stated terms contradict deletion (the flow presents deletion but the terms describe deactivation or indefinite retention-for-reactivation without user choice); **or** login after the stated recovery window silently restores the account and its data; **or** user data under the account observably persists after completion, including via documented third-party evidence; **or** marketing to the account's address continues beyond a stated wind-down. `unobserved` — no terms-decidable trap, but the post-window state is not observable within the observation window (recovery window exceeds it) → partial scope, CONDITIONAL — **not** `pass`. `pass` — terminal deletion confirmed; the post-window boundary was observed with no restoration, no persistence, messaging wound down.
- **Severity:** blocking

### Check 7 — `pre-deletion-export-prompt`
- **Statement (SHOULD):** Where an export path exists, the deletion flow SHOULD surface export availability (an affordance or clear pointer) before the terminal action — deleting is the moment data loss becomes irreversible, and a genuine exit offers the user their data on the way out.
- **Modes:** behavioral
- **Evidence:** `flow_transcript`, `screenshot` (pre-terminal screens).
- **Procedure:** Walk the deletion flow to (not through) the terminal action; record whether export is surfaced anywhere before it.
- **Decision (cascade):** `na` — no export path exists (check 1's finding), or no deletion path exists (check 4's). `unobserved` — the deletion flow could not be reached within the window. `fail` — the flow reaches its terminal action with no export affordance or mention anywhere before it (→ contributes CONDITIONAL, not FAIL, since SHOULD). `pass` — export is surfaced before finalization.
- **Severity:** caveat
- *Note:* a retention *offer* dressed as an export prompt still counts under check 5's rules; this check asks only whether export is genuinely surfaced.

## 5. Aggregation & verdicts (§4.4, §5)

Default aggregation, inherited from CRITERION-SPEC §4.4:

| Verdict | Condition |
|---|---|
| **PASS** | All blocking checks (1–6) `pass` (with `na` excluded and **at least one blocking check applying**), no check returns `conditional`, and check 7 is `pass`, `na`, or `unobserved`. |
| **CONDITIONAL** | No blocking `fail`, but ≥1 of: any check returns `conditional` (possible on 1, 2, 3, 4, 5 as currently decided); check 7 (`caveat`) `fail`s; a **blocking** check is `unobserved` (partial scope). MUST enumerate the triggering check_ids. |
| **FAIL** | Any blocking check (1–6) returns `fail`. Enumerate **all** failing blocking checks (CRITERION-SPEC §5.2). |
| **INDETERMINATE** | The probe could not provision an account or reach the exit surfaces at all; or model consensus not reached; **or every blocking check returned `na`** — no account and no data, the criterion did not apply (§3 Applicability). Treated as absent. |

Check 7 `unobserved` does not downgrade (non-blocking partial scope). Check 6 `unobserved` is expected to be **common** — recovery windows often exceed probe windows — and deliberately yields CONDITIONAL (partial scope) rather than PASS: an attestation that never observed the post-deletion boundary should say so. Operators SHOULD size observation windows past the stated recovery window where a clean PASS matters.

**Attribution.** On FAIL, enumerate all failing blocking checks; on CONDITIONAL, the triggering check(s) — machine-readable (CRITERION-SPEC §5.2).

**Confidence** (§5.3): `min` over contributing checks of `(model_agreement × evidence_completeness)`, where `evidence_completeness` reflects how much of each check's procedure completed (e.g., a check-6 decided with the post-window boundary observed scores higher than one decided from terms alone). Bands: high ≥ 0.90; medium ≥ 0.70 and < 0.90; low < 0.70 → downgrade to INDETERMINATE + route to review.

## 6. Corpus (§6)

Seed corpus and provenance discipline live in `./corpus/public/README.md`. Rules specific to this criterion:

- **Named-product entries cite public enforcement records**; everything else is synthetic. Deletion/export enforcement is **thinner on the ground** than dark-pattern enforcement — one enforcement anchor ships at 0.1.0 (the 2023 DOJ/FTC Alexa deletion action) and sourcing further dated `dpa-decision` anchors (GDPR Art. 17 sanctions) is queued corpus work. That thinness is itself part of the case for this criterion: lock-in is under-enforced relative to its procurement salience.
- The public corpus **meets the `candidate` category minimums** (38 examples). The remaining gates to `candidate` are a calibration dry-run and the §7 human-calibration pass.

## 7. Validation record (§7)

`status: draft` — nothing is measured yet. Path to promotion:

- **draft → candidate:** run the **human-calibration gate** (CRITERION-SPEC §7.1): ≥2 independent human adjudicators over the public corpus against a **pre-registered target**. The target is *not yet registered* — it MUST be finalized before formal adjudication begins and is expected to mirror the siblings' (κ ≥ 0.8 aggregate AND ≥80% exact-verdict on boundary+adversarial pooled). A blind LLM dry-run (the `no-dark-patterns` method) comes first and does not consume the gate.
- **candidate → active:** the validation study (CRITERION-SPEC §7.2) on the **sealed** corpus — purely behavioral, so likely the frontier pool alone with the enclave pool recorded n/a (the `no-subscription-trap` shape). Publish false-pass / false-flag / indeterminate / agreement / cost. Kill thresholds: false-pass ≤ ~5%, false-flag ≤ ~10%; sealed set ≥ 3/ε per side (≥60 violating, ≥30 clean). Only then may attestations issue.

Behavioral note: like the sibling, probe observations sit close to ground truth; the harder validation targets are **defeat-device red-teaming** and check 6's window economics (how often the post-deletion boundary is actually observable).

## 8. Claim language (§8)

> "Service `{service_identity}` was observed to satisfy `no-lock-in@{version}` under rubric `{rubric_version}`, probe script `{prompt_version}`, model set `{model_set}`, modes `{modes}`, over observation window `{window}`; measured false-pass `{fp}` / false-flag `{ff}` on corpus `{corpus_hash}`."

**Does NOT assert:** future behavior beyond the window; billing-cancellation conduct (`no-subscription-trap`); exit-fee honesty (`transparent-pricing`); backend retention/processing beyond the observable exit facts (`no-surveillance`, future); that any third party can import the export; anything about tiers, plans, or surfaces the probe did not exercise.

## 9. Audit-artifact binding (§9)

Single-mode behavioral: the bound artifact is a **probe script** (flat single-artifact shape per CRITERION-SPEC 0.6.0 §9), versioned as `prompt_version` and re-validated when it or the criterion changes materially. Obligations:

- **Injection hardening:** all page/app/notification/export-artifact content is untrusted **data**, never instruction — export archives are a novel injection surface (a bundled "AUDIT-NOTE" file is content aimed at the judge) and MUST be treated exactly like page text; detected instruction-shaped content is ignored and recorded as a finding.
- **Check → probe-step mapping** MUST be explicit (provision account with seeded content types → exercise export → inspect artifact → walk deletion → post-window re-probe → notification monitoring).
- **Stealth** (residential egress, realistic timing, real payment instruments where a tier requires them) is governed by the design doc, Architecture §7. Check 6 adds a **window-sizing** duty: where the stated recovery window exceeds the observation window, the attestation records check 6 as `unobserved` (partial scope) rather than extrapolating.

## 10. Provenance & governance metadata (§10)

- **Authors:** Scott Helvick
- **Reviewers:** —
- **Sources:**
  - GDPR, Art. 20 (data portability — "structured, commonly used and machine-readable format") and Art. 17 (right to erasure).
  - CCPA/CPRA — Cal. Civ. Code §1798.105 (deletion), §1798.130 (portability of disclosed data).
  - EU Data Act (Regulation (EU) 2023/2854) — cloud-switching and data-egress-charge provisions (applicable from September 2025).
  - EU Digital Markets Act, Art. 6(9) — end-user data portability for gatekeepers.
  - United States v. Amazon.com, Inc. (Alexa) — DOJ-filed FTC action (2023, $25M civil penalty): alleged retention of children's voice data and geolocation despite deletion requests and stated deletion practices. Public record.
  - Apple App Store Review Guideline 5.1.1(v) (2022) — apps supporting account creation must offer in-app account deletion; the platform norm behind check 4's in-medium rule.
  - Brignull, deceptive.design — "roach motel" (the exit-obstruction lineage behind check 5).
- **first_active:** —
- **delegation_inclusion_count / overturn_rate:** — (post-launch)
- **Changelog:**
  - `0.1.0` — initial draft (2026-07-06). Third and final Stage 0 criterion (design doc, MVP). Seven checks; single-mode behavioral (second such, after `no-subscription-trap`); scope drawn against `no-subscription-trap` (billing exit vs account/data exit), `transparent-pricing` (exit-fee honesty; the Adobe-ETF routing precedent), `no-surveillance` (observable exit facts owned here; backend substance theirs — reciprocal MUST-exclude recorded on this side), and `no-dark-patterns` (whose 0.1.1 scope already excludes these flows; check 5 is the owned surface, adopting `no-subscription-trap` check 3's calibrated volume rule verbatim). Check 6's fail-before-`unobserved` deviation mirrors the sibling's check 4 (terms-decidable shapes). One enforcement anchor (DOJ/FTC Alexa deletion, 2023); further `dpa-decision` anchors queued — deletion/export enforcement is thin, which is part of this criterion's case. **First criterion authored natively against CRITERION-SPEC 0.6.0: zero new mold findings** — the mold has now absorbed a single-mode behavioral, a dual-mode, and a second single-mode criterion without modification; the flat §9 single-artifact shape and the §7.2 single-pool validation cells applied cleanly.

## 11. Calibration queue (pre-first-dry-run)

No calibration has run yet. The boundaries a first blind-panel dry-run (and later the §7.1 gate) must stress, stated in advance:

- **Check 1's conditional band** — self-service initiation with human fulfillment (`bound-syn-manual-fulfillment`) vs the human-channel fail: is "who completes it" adjudicable from transcripts?
- **Check 2's substance rule** — JSON-washing (`adv-syn-format-shapeshifter`, fail) vs documented-custom-schema (`bound-syn-documented-xml`, conditional) vs standard formats: does "machine-readable in substance" hold across raters?
- **Check 3's materiality** — a missing content type (fail) vs degraded reconstruction metadata (conditional) vs the settings-only decoy (`adv-syn-settings-only-export`, fail): where do raters put "material"?
- **Check 4's 30-day line** — the stated-recovery-window pass vs the 90-day deferral conditional; and payment-gated deletion (`viol-syn-resubscribe-to-delete`) as fail.
- **Check 5's adopted volume rule** — does the sibling's calibrated ≥3 boundary transfer to export/deletion flows without re-splitting raters (incl. the mandatory-detour burial shape, `adv-syn-downgrade-maze`)?
- **Check 6's evidence reach** — terms-decidable fails vs the `unobserved`-is-common reality (`bound-syn-unobserved-grace`); and the enforcement-evidence route (`viol-alexa-deletion`): do raters accept documented third-party evidence as the row states it?
