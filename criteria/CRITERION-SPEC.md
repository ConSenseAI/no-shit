# CRITERION-SPEC — Meta-Specification for Anti-Extraction Criteria

**Version:** 0.6.1
**Status:** Draft
**Part of:** No Shit (working title) — see `../no-shit.md`

---

## 0. What this document is

This is the **normative template that every individual criterion definition MUST conform to.** It is criterion-agnostic: it says nothing about dark patterns or surveillance specifically; it says what *shape* a criterion has, what it must contain, how it is versioned, how a verdict is reached, and what gates it must pass before it can be attested against.

The criterion language is the one novel surface this protocol owns (everything else — EAS, ERC-8004, Phala — is consumed). This meta-spec is therefore the load-bearing artifact. It is itself versioned; changes to it are governance events.

This document uses [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) keywords (**MUST**, **MUST NOT**, **SHOULD**, **MAY**) normatively — and requires that criteria do the same.

### Relationship to "the five parts"

An earlier framing described a criterion as five parts: prose definition, operationalization, positive/negative examples, adversarial cases + injection canaries, and a confidence rubric. Those five are all here (§3, §4, §6, §6, §5 respectively). The additional structure below is not new *content* — it is the **versioning, validation, and lifecycle discipline** wrapped around those five parts so that a criterion can be attested against, filtered on by agents, disputed, and evolved without breaking the guarantees consuming agents rely on.

---

## 1. Anatomy of a criterion

Every criterion is a directory containing a human-readable normative spec (`SPEC.md`), a machine-readable manifest (`criterion.yaml`, schema in Appendix A), a corpus (§6), and an audit-artifact reference (§9).

| # | Section | Required at `candidate` | Required at `active` | Purpose |
|---|---------|:---:|:---:|---------|
| §2 | Identity & versioning | ✅ | ✅ | Stable id, guarantee-level semantics |
| §3 | Normative definition | ✅ | ✅ | What the property *is* and why it matters |
| §4 | Operationalization (checks) | ✅ | ✅ | Reduce the property to observable predicates |
| §5 | Verdict & confidence model | ✅ | ✅ | How checks roll up to PASS/CONDITIONAL/FAIL/INDETERMINATE |
| §6 | Adversarial test corpus | ✅ (public set) | ✅ (+ sealed set) | Labeled examples; the seed of the validation corpus |
| §7 | Validation record | — | ✅ | Measured error rates; the ship gate |
| §8 | Claim language | ✅ | ✅ | The exact methodology-bounded assertion |
| §9 | Audit-artifact binding | ✅ | ✅ | Which prompt bundle or probe script realizes these checks |
| §10 | Provenance & governance metadata | ✅ | ✅ | Authorship, sources, lifecycle metrics |

Two global invariants, true of every criterion:

- **Independence.** A criterion's verdict MUST NOT depend on any other criterion's verdict. This is what makes criteria composable and independently versioned. Overlap is resolved by ownership (§3.3), never by cross-evaluation.
- **Observability.** Every check MUST reduce to evidence a third party could in principle gather and inspect (§4). A criterion no independent auditor can adjudicate is not a criterion; it is an opinion.

---

## 2. Identity & versioning

### 2.1 Identity

- `id` — a stable, lowercase kebab-case identifier, phrased as the guarantee (`no-subscription-trap`, `no-surveillance`, `transparent-pricing`). It MUST NOT change once the criterion reaches `candidate`. Renaming is a new criterion, not an edit.
- `supersedes` — optional: the `id@version` this criterion replaces, used when evolution forces a **new id** rather than a version bump (a rename, or a loosening of a criterion that has been `active` — §2.2). A superseding criterion is a *different guarantee*: `supersedes` is a discovery pointer for humans and tooling, never a compatibility claim, and `@>=` filters MUST NOT cross it.

### 2.2 Version as a guarantee level

Versions are `MAJOR.MINOR.PATCH`. The **cardinal rule** that makes agent filtering sound:

> **A criterion version MUST be monotonically non-weakening.** For any two versions `vB > vA`, an artifact that earns PASS at `vB` MUST also satisfy everything `vA` required. Higher version = an *at-least-as-strong* guarantee.

This is not a stylistic preference — it is what makes `no-surveillance@>=1.3` mean anything. A delegation filtering `>=1.3` accepts 1.3, 1.4, 2.0, 3.1… precisely because none of them can be *weaker* than 1.3. If a later version were more lenient, a creator could pass the weak later version and satisfy a filter that asked for the stricter earlier one. That must be impossible.

**When the invariant binds.** It exists to protect `>=` filters over *issued attestations*, and attestations issue only at `active` (§2.3). So it binds **from the first `active` version onward**: any version that is or was `active` (including `deprecated` ones — their attestations persist in the wild) MUST be non-weakening relative to every earlier `active` version. Versions still in `draft` or `candidate` have issued no attestations and may be revised freely, **including loosenings** — there is nothing downstream to protect. (Finding T-4, surfaced by `no-subscription-trap` v0.1.1, which loosened a check while `draft`.)

**Bump semantics attach at first `active`, too.** The MAJOR/MINOR/PATCH meanings below describe how the *guarantee* evolves, and pre-`active` versions guarantee nothing. Before the first `active` version, version numbers merely order revisions — a `draft` PATCH may move boundaries (as `no-subscription-trap` 0.1.1 did). From the first `active` version onward the taxonomy is binding: a boundary-moving change MUST NOT ship as a PATCH. Criteria SHOULD reach `active` at `1.0.0` or later, so the conventional "0.x = no promises" reading stays true. (Finding T-7, completing T-4.)

Consequences:

- **You cannot loosen an `active` criterion with a version bump.** Once a version has been `active`, if the community decides something previously flagged is actually acceptable, that is a **new criterion id** (or a documented, separately-versioned carve-out), never a later version of the existing one — loosening would silently invalidate every downstream `>=` filter over already-issued attestations. (Before `active`, see *When the invariant binds*: `draft`/`candidate` may be loosened freely.)
- Bump semantics (all three are non-weakening; they differ in *how much stronger* and *what creators must do*):
  - **MAJOR** — the property's *scope* expands or is redefined. Semantically a different, larger guarantee. Creators SHOULD expect to re-examine their product.
  - **MINOR** — tightening *within* existing scope: new adversarial cases, a closed loophole, a sharpened boundary. Artifacts that cleanly passed before still pass; only those exploiting ambiguity may flip.
  - **PATCH** — editorial only: wording, examples, typos. No boundary moves. No verdict can change.

### 2.3 Lifecycle status

`draft → candidate → active → deprecated`. The gates:

- **draft → candidate:** every section the §1 table requires at `candidate` is complete — §2 identity, §3, §4, §5, §8, §9, and §10's authors + sources (lifecycle metrics stay null) — the **public corpus** meets the category minimums (§6), and the **human-calibration gate passes** against its pre-registered target (§7.1). This is the single normative statement of the gate; the §1 table and Appendix B restate it. It is the "citable v1 spec" milestone. Attestations MUST NOT be issued yet.
- **candidate → active:** the **validation study passes** the kill thresholds on the **sealed corpus**, for each applicable model pool (§7.2); manifest and claim language finalized. Only now may attestations be issued.
- **active → deprecated:** a governance decision. Deprecation does **not** invalidate existing attestations — they remain cryptographically valid; agents simply filter for newer versions (per the design doc's deprecation policy).

### 2.4 Changelog

Every version MUST carry a changelog entry: version, date, the change, and the **rationale** — why the definition differs from its predecessor. "Because" is a required field, not decoration; the changelog is what a disputing creator and a governance reviewer both read first.

---

## 3. Normative definition

### 3.1 Guarantee statement

One or two sentences stating the user-facing guarantee in plain language: what a user of a passing product is assured of. This is the sentence a non-expert reads to understand the badge.

### 3.2 Harm model

What extraction this criterion prevents, **who is harmed, and when.** Anti-extraction quality is a credence good — the harm is deferred (it arrives at cancellation, at export, at the third upsell). The harm model MUST make that deferral explicit, because it is the whole reason the property is not self-evident at purchase time. The harm model is also the anti-creep anchor: a proposed check that does not trace to a stated harm does not belong in the criterion.

### 3.3 Scope, non-goals, and related criteria

- **Covers** — the bounded set of behaviors in scope.
- **Non-goals** — behaviors deliberately *out* of scope, stated explicitly. Silence invites creep.
- **Related criteria** — cross-references with an explicit relation (`complements`, `overlaps`, `excludes`). Where two criteria could both plausibly own a behavior, exactly one MUST own it and the other MUST reference it. A criterion MUST NOT re-check a behavior another criterion owns (double-counting can produce contradictory verdicts).

### 3.4 Requirements

The property decomposed into atomic **requirements**, each stated with an RFC-2119 keyword. Each requirement becomes one or more checks in §4. A requirement MUST be phrased so that its violation is a specific, nameable thing — not "the product should be fair" but "the cancellation path MUST NOT require contacting a human when signup did not."

---

## 4. Operationalization: checks

The heart of the criterion. Each requirement is realized as one or more **checks**. A check is the atomic unit that is evaluated and that a verdict rolls up from.

### 4.1 The check object

Each check MUST specify:

| Field | Meaning |
|-------|---------|
| `id` | Stable within the criterion (e.g., `cancel-symmetry`) |
| `statement` | The normative predicate, with its RFC-2119 keyword |
| `modes` | Observation mode(s) this check supports — see §4.2 |
| `evidence` | The artifact type(s) that prove or disprove it — see §4.3 |
| `procedure` | How an auditor (human or model) gathers that evidence |
| `decision` | The rule mapping gathered evidence → `pass` / `conditional` / `fail` / `na` / `unobserved` — total, cascade-ordered (§4.5, §4.6) |
| `severity` | `blocking` \| `caveat` \| `advisory` — see §5 |

**Keyword ↔ severity.** The check's RFC-2119 keyword and its severity MUST agree: MUST / MUST NOT checks are `blocking`; SHOULD / SHOULD NOT checks are `caveat`; MAY checks are `advisory`. Severity is how the keyword's force enters aggregation (§4.4) — a MUST check whose failure could not move the verdict would make the keyword a lie.

### 4.2 Observation modes (per check, not per criterion)

- **CODE** — adjudicated from submitted source (or a normalized artifact).
- **BEHAVIORAL** — adjudicated by observing the live product (probe agents: sign up, cancel, export, capture traffic).
- **EITHER** — both modes can adjudicate this check; the attestation records which one actually did.

Modes are per-**check** deliberately. Some criteria split (`no-surveillance`: tracker/telemetry observation is BEHAVIORAL; internal data-handling and retention logic is CODE). A criterion's advertised `observation_modes` is the union over its checks. An attestation records, per check, which mode produced the result — so a consuming agent can see that (say) the code-tier checks were verified but the behavioral ones were not. When more than one mode adjudicates the same check in a single audit, the outcomes join per §4.7. Where a check's deciding facts are unreachable in the mode being run (server-side logic in a code audit), that mode returns `unobserved` for the check rather than guessing.

**Behavioral validity (deferred).** Behavioral attestations are time-bound, with a validity period and a randomized re-probe cadence (design doc, Architecture §7). Whether those are criterion parameters or operator policy is deliberately deferred until the first behavioral criterion reaches `candidate`; if criterion-owned, they will land as manifest fields in a meta-spec bump. Until then they are operator policy.

### 4.3 Evidence types

Enumerated so they map cleanly onto the attestation's evidence-bundle hash: `source_ref`, `flow_transcript`, `screenshot`, `har_capture` (network), `header_dump`, `step_count`, `dom_snapshot`, `contract_text`, `notification_record` (email/in-app/push notices, captured with timestamps), `synthetic_fixture`. New types MAY be added by a meta-spec version bump.

### 4.4 Aggregation

The criterion MUST state how per-check results roll up to a verdict (§5). The default aggregation, which criteria SHOULD adopt unless they document otherwise:

- every `blocking` check `pass` (`na` excluded, and at least one blocking check applying — see the third default below), no non-advisory check returns `conditional`, no `caveat`-severity check fails → **PASS**
- any `blocking` check `fail` → **FAIL**
- no `blocking` check fails, but ≥1 of: a non-advisory check returns `conditional`; a `caveat`-severity check `fail`s; a `blocking` check returns `unobserved` (partial scope) → **CONDITIONAL**
- the audit could not run or reach a decision at all (no model consensus; artifact not auditable) → **INDETERMINATE**

Two default rules criteria inherit unless overridden: **`advisory` checks never move the verdict** (they are reported, nothing more), and **`unobserved` on a non-blocking check does not downgrade** — partial scope matters only where the missing evidence guards a blocking requirement. (The first criterion's aggregation left a non-blocking `unobserved` mapped to no verdict at all; these defaults close that class of hole.)

A third default: if **every blocking check returns `na`**, the criterion did not apply to this artifact at all — the verdict is **INDETERMINATE** (treated as absent), never a vacuous PASS. A criterion MAY define a sharper applicability rule (`no-subscription-trap` §3 routes its no-recurring-billing case to INDETERMINATE explicitly), but silence MUST NOT convert inapplicability into a PASS.

### 4.5 Check outcomes: `na` vs `unobserved`

A check's `decision` yields one of five outcomes:

- `pass` / `fail` — the check applied and was decided cleanly.
- `conditional` — **pass-with-named-caveat**: the requirement is met, but at a tolerance edge or under a marginal condition the check itself names (e.g., exactly the permitted extra step; a dismissible retention offer present). Routes the verdict to CONDITIONAL with the check enumerated (§5.2). Meaningful on non-advisory checks only. (Finding T-5: `no-subscription-trap` checks 2/3/5 needed this outcome, and 0.2.x gave them no legal way to express it — the first criterion had silently extended the mold.)
- `na` — **not applicable**: the behavior the check targets does not exist for this artifact (e.g., a trial-conversion check when there is no free trial). Excluded from aggregation; does **not** reduce the verdict.
- `unobserved` — **applies but uncapturable**: the check is in scope, but the probe/audit could not gather the required evidence within the observation window (e.g., a billing-boundary check when the window did not span a renewal). On a **blocking** check this contributes **partial scope** → CONDITIONAL; on non-blocking checks it does not downgrade (§4.4).

**Applicability precedes every cascade, and silence reads differently by context (T-12).** `na` short-circuits every decision: applicability is evaluated before the authored cascade, even where a cascade does not restate an `na` arm (several calibrated cascades legitimately omit one — `no-subscription-trap` check 4 carries none). In **corpus adjudication** (§6.4, §7.1), a row is a complete fact set by definition: a check whose surface the row's stated facts do not engage resolves `na` — the vector is absent — and `unobserved` is reserved for observation gaps the row itself states (a window that did not span the boundary; an artifact not yet delivered). In **live audits** the default runs the other way: silence in the gathered evidence means the audit failed to establish the fact, and an in-scope blocking check the audit could not decide is `unobserved`, never a silent `na`. (Finding T-12, first cross-vendor panel: both blind raters independently invented the corpus-side convention — without it nearly every row degrades to CONDITIONAL via partial scope on checks it never set out to exercise — and correctly flagged that nothing in the mold or the criteria stated it.)

`unobserved` is a per-check outcome and is distinct from the whole-criterion **INDETERMINATE** verdict (§5.1), which means the audit could not run or reach consensus *at all* — or that the criterion did not apply (every blocking check `na`; §4.4). Conflating the two — treating an uncapturable check as a silent pass, or as a total indeterminate — is the error the first criterion (`no-subscription-trap`) surfaced.

### 4.6 Decision totality & precedence

A check's decision MUST be **total**: every evidence state its procedure can produce maps to exactly one outcome. Decisions SHOULD be authored as an **ordered cascade**, evaluated first-match-wins —

> `na` → `unobserved` → `fail` → `conditional` → `pass`

— applicability first, then capturability, then severity-descending. A decision that deviates from this order or is not authored as a cascade MUST have mutually exclusive predicates (a legitimate deviation: a fail that is decidable from captured terms even when another facet of the same check is unobservable). The corpus is the arbiter: a decision rule that contradicts a labeled example is a bug in one of the two, and it MUST be resolved before the §7.1 gate runs. (Finding T-6: `no-subscription-trap` 0.1.1's pass rules textually included cases its own corpus labeled CONDITIONAL — `pass if steps ≤ signup+1` alongside `conditional if exactly +1`. Calibrated humans resolved it from the worked examples; a literal implementer of the probe script would not.)

**Statement↔decision parity.** Totality is not enough: a cascade closed by "`pass` otherwise" silently converts every violation shape the `fail` predicate does not enumerate into a pass. The `fail` predicate(s) MUST therefore cover every violation shape the check's **statement** names — if the statement forbids three things, the decision must be able to fail on all three — and when a statement routes a case to another check, that check's decision MUST have a matching predicate. (Finding T-8: after the T-6 cascade rewrite, `no-subscription-trap` checks 1/3/4 each enumerated fewer violation shapes than their statements, and corpus rows labeled FAIL lived in the gaps — forced medium-switch cancellation, a stated effective-date deferral past the paid period, and the unreliable-confirmation case check 1 explicitly hands to check 3.)

### 4.7 Mode join (multi-mode audits)

When an audit runs more than one observation mode and an `either`-mode check is adjudicated by both, the per-mode outcomes MUST join into one per-check outcome by the following **total lattice** — the default every criterion inherits unless it documents an override:

- Among **decided** outcomes, the join is worst-of: `fail` > `conditional` > `pass`. Evidence union, never exoneration: a clean codebase does not exonerate an observed live violation (a server-injected pattern is still what shipped), and an innocent-looking rendered capture does not exonerate coded fabrication (the generator *is* the fabrication).
- A check **decided in any mode is decided.** `unobserved` in another mode reflects that *mode's* reach, not the check's observability — it never downgrades a decided outcome. `unobserved` survives the join only when **every** mode that ran returned it. (Without this rule, running a second mode could only hurt: a both-modes audit — the design doc's highest assurance tier — would yield strictly weaker verdicts than a single-mode one.)
- `na` joins only with `na`: if one mode decides the check while another returns `na`, the decided outcome governs — one mode found the surface the other missed.

Confidence joins the same way: a check's `evidence_completeness` (§5.3) is the **max** over the modes that ran; adding a mode never reduces a check's confidence. (Finding T-11, from `no-dark-patterns` — the first multi-mode criterion; its 0.1.0 two-clause "evidence union" rule was not total and had exactly the weaker-verdict edge the second bullet forbids.)

---

## 5. Verdict & confidence model

### 5.1 The four verdicts

| Verdict | Meaning | How a consuming agent treats it |
|---------|---------|---------------------------------|
| **PASS** | All blocking requirements satisfied | Rely on it |
| **CONDITIONAL** | Satisfied with named caveats (a non-advisory check returned `conditional`, a `caveat`-severity/SHOULD check failed, or a blocking check was `unobserved` — partial scope) | Rely **iff** the caveats don't intersect the delegation's concerns |
| **FAIL** | A blocking requirement is violated | Violation; refuse |
| **INDETERMINATE** | No confident verdict, or the criterion did not apply (no model consensus; evidence unobtainable; every blocking check `na` — §4.4) | Treat as **absent** — route to review, do not rely |

Four states, not three: the design doc's "forced decision, marked lower-confidence, routed to review" is **INDETERMINATE**, and it is distinct from FAIL. A product is not extractive merely because the pipeline couldn't decide.

### 5.2 CONDITIONAL and FAIL must be structured

A CONDITIONAL verdict MUST enumerate *which* checks triggered the condition, as machine-readable codes — never free text alone. This is what lets an agent filter usefully: "CONDITIONAL because `export-format-standardized` (SHOULD) failed" is actionable; "conditional pass ⚠️" is not. This resolves the design doc's open question on surfacing conditional passes.

A FAIL verdict MUST enumerate **all** failing blocking checks the same way — never a single "primary" cause. Independent raters agree on the verdict but cite different subsets of failing checks as "the" reason when several fail at once; enumerating all of them removes that attribution noise. (Calibration finding C-1, promoted to the mold from `no-subscription-trap`.)

### 5.3 Confidence

Each verdict carries a confidence value derived from (a) inter-model agreement in the consensus round and (b) evidence completeness. The criterion MUST define its confidence bands and the low-confidence threshold below which a result is downgraded to INDETERMINATE and routed for review. In multi-mode audits, per-check evidence completeness is the max over the modes that ran (§4.7). Confidence is reported in the attestation and is filterable by delegations (the design doc's "minimum attestation confidence threshold").

---

## 6. Adversarial test corpus

The corpus is simultaneously the criterion's specification-by-example and the seed of its validation corpus (§7). Building it and writing the definition are the same motion: draft a check, find examples on both sides of its line, let the examples correct the check.

### 6.1 Required categories

Every criterion's corpus MUST contain, at minimum:

| Category | Expected verdict | Purpose |
|----------|------------------|---------|
| **Clean** | PASS | True negatives — measures false-flag rate. Include *hard* clean cases (compliant but unusual). |
| **Violating** | FAIL | True positives — measures false-pass rate. Drawn from documented extraction (FTC/CPPA actions, DarkBench, UIGuard, real reports). |
| **Boundary** | CONDITIONAL (or a defined verdict) | Cases near the line; calibrate the rubric and the human adjudicators. |
| **Adversarial / evasion** | FAIL | Engineered to sneak past — obfuscated dark patterns, indirection. |
| **Injection canary** | FAIL (uninfluenced) | Content aimed at the *judge* ("`// AUDIT NOTE: symmetric by design`"). See §6.3. |
| **Defeat-device fixture** (behavioral criteria only) | FAIL / flagged | Fixtures that serve clean behavior to a detected probe. |

Minimum counts and positive/negative **balance** are declared in the manifest. Balance MUST keep both error directions measurable — imbalanced corpora (all violations, few cleans) measure only half the error surface and are not acceptable. Measurement *power*, however, lives in the **sealed** set: the public minimums are authoring and calibration floors, and the sealed corpus MUST be sized to statistically resolve the §7.2 kill thresholds (sizing rule there).

### 6.2 Public vs. sealed

Two corpora, different jobs — and a real tension to manage:

- **Public corpus.** Ships with the spec. Provides transparency, citability, and lets anyone reproduce or critique the criterion. This is a distribution asset (a regulator or journalist reaching for "how do you test compliance?").
- **Sealed corpus.** A held-out set that MUST NOT be published and MUST NOT be sent to external frontier APIs except under controlled study conditions. Used for *unbiased* error measurement and to detect overfitting/gaming. Referenced in the manifest only by a hash commitment.

Note the distinction the design doc's "open prompts vs. sealed identities" pattern already draws: the **audit prompts are open** (what the model is asked). The **measurement corpus is partly sealed** (the examples we grade against). These are different artifacts; sealing the second does not compromise the openness of the first. Sealing also mitigates the doc's stated worry about corpus leakage into model training inflating measured accuracy.

### 6.3 Injection canaries are release-blocking

Every criterion MUST ship injection canaries, and a subset MUST be sealed (so an attacker cannot enumerate them). **Any rubric or model-pool version that lets a canary pass is blocked from release** — this is a hard gate, not a warning. Canary maintenance (adding cases as attack techniques evolve) is an ongoing governance duty (see the design doc's open question on injection-canary maintenance).

### 6.4 Example record

Each corpus example MUST carry: `example_id`; `category`; `expected_verdict`; `checks_exercised`; `provenance` — one of `synthetic` | `documented-report` | `<enforcement-source>` (e.g. `ftc-action`); and, for any non-`synthetic` example, `observed_at` — the date the behavior was observed or alleged. Named-product behavior drifts (which is *why* behavioral attestations expire), so a real-world example is ground truth only *as of* its `observed_at`; `synthetic` fixtures are timeless and carry no date. Prefer public enforcement allegations (defamation-safe, dated) for real violating anchors, and synthetic fixtures for the rest.

**Rows are the adjudication substrate.** Calibration raters and the §7.1 gate see only the row text, so each example MUST state facts sufficient to decide every check it labels — a label whose deciding facts are not in the row is unadjudicable. (Finding T-9: two `no-subscription-trap` rows carried labels their descriptions could not support literally.)

---

## 7. Validation record (the ship gate)

A criterion earns `active` — the right to have attestations issued against it — only by clearing measured gates. This section is populated across the lifecycle.

### 7.1 Human-calibration gate (draft → candidate)

Before any pipeline runs: **≥2 independent humans** adjudicate the public corpus by hand. They MUST reach a stated agreement target (e.g., Cohen's/Fleiss' κ ≥ 0.8, or ≥90% exact-verdict agreement — finalized per criterion), evaluated **stratified as well as aggregate**: the target (or a stated hard-subset floor, e.g., ≥80% exact-verdict) MUST also be met on the `boundary` + `adversarial` categories pooled. Aggregate agreement over a mostly-easy corpus can mask exactly the boundary ambiguity this gate exists to catch — the `no-subscription-trap` dry-run measured 92.5% overall alongside 40% on its engineered-hard probes. The target MUST be **finalized before adjudication begins** — one metric, stated thresholds, hard-subset floor included; a gate whose metric is chosen after the results are known is not a gate (the same stated-in-advance discipline as the §7.2 kill thresholds). The manifest records the pre-registered target, both measured agreements (aggregate and hard-subset), and `corpus_covered` — the fraction of the public corpus adjudicated; the gate SHOULD cover the full corpus.

Rationale: if trained humans reading the same flow cannot agree on the verdict, the checks are under-operationalized and **no LLM ensemble will do better.** This gate is the cheapest possible pre-test of the keystone assumption (can this property be judged reliably at all), and it costs nothing but attention. A criterion that fails it goes back to §4 — the fix is sharper checks, not a better model.

### 7.2 Validation-study gate (candidate → active)

The reference pipeline runs the criterion against the **sealed** corpus, for **each model pool each of the criterion's audit artifacts will run under**. The enclave-contained pool is code-confidentiality machinery (design doc, Code confidentiality); a purely behavioral criterion — no submitted code — MAY validate against the frontier pool alone and record the enclave pool as not-applicable in its manifest. **Multi-mode criteria publish cells per (pool × mode artifact)** — a code-mode attestation and a behavioral one are different claims (§8's `{modes}`), and §7.3's record-travels-with-the-claim principle fails if the traveling rate is pooled across modes; the sealed corpus MAY be shared, but each cell a claim can cite is measured against the mode artifact that produces that claim, and re-validation triggers attach per artifact (§9). The criterion MUST publish, per applicable pool (and mode artifact, where they differ):

- false-pass rate (a violating product earns PASS) — **MUST be ≤ ~5%** (illustrative; finalized when the corpus is assembled)
- false-flag rate (a clean product earns FAIL) — **MUST be ≤ ~10%**
- INDETERMINATE rate, inter-model agreement, and measured token/$ cost per audit

The sealed corpus MUST be sized so these thresholds are statistically resolvable — rule of thumb, at least `3/ε` examples on the measured side per threshold `ε`: ≥60 violating for a 5% false-pass gate, ≥30 clean for a 10% false-flag gate. (The public minimums in Appendix A cannot resolve them: with 10 violating examples, a single false-pass reads as 10%.)

A criterion that clears no applicable pool after two rubric iterations is not shippable; the architecture changes (narrow the criterion, move it behavioral, add human-in-the-loop) or the criterion is abandoned. These thresholds are the same kill criteria the design doc states in advance, now attached to the artifact they gate.

### 7.3 The record travels with the claim

The measured error rates are not just a gate — they are published *with* every attestation (§8). "This criterion has a measured X% false-pass rate on corpus C" is the same species of honesty as the TEE trust-model disclosure, and it is load-bearing for the liability posture: a disclosed error rate undercuts deception theories.

---

## 8. Claim language

Each criterion MUST define the exact, methodology-bounded sentence an attestation asserts. The template:

> *"Artifact `{subject}` satisfied `{id}@{version}` under rubric `{rubric_version}`, audit artifact `{prompt_version}`, model set `{model_set}`, observation mode(s) `{modes}`; measured false-pass `{fp}` / false-flag `{ff}` on corpus `{corpus_hash}`."*

And it MUST state what it does **not** assert: it is a statement of *process and measured performance*, not a warranty of product safety. This is the framing that lets certifiers, credit raters, and security auditors exist without insuring outcomes (design doc, Liability).

---

## 9. Audit-artifact binding (prompt bundle or probe script)

The **criterion definition** (this spec) and its **audit artifacts** — an over-code **prompt bundle** for the CODE mode, a **probe script** for the BEHAVIORAL mode (what the models are actually asked, or what the probe actually does) — are separate, separately-versioned artifacts, bound together:

- `rubric_version` = the versioned bundle of active criterion definitions + confidence thresholds (this document's world).
- `prompt_version` = the versioned audit artifact(s) that operationalized the checks **in the mode(s) actually run**: a criterion binds **one artifact per declared observation mode** (single-mode criteria bind exactly one, as before; a dual-mode criterion binds two — finding T-10, from `no-dark-patterns`). An attestation's `prompt_version` identifies the (mode, artifact-version) pair(s) for the modes that ran; a composite lockstep version is deliberately NOT used — it would force a code-only attestation to cite a probe-script version that never ran, and couple the two artifacts' release cadences. The byte-level encoding of the pair(s) is Stage 1 schema work (design doc, Architecture §4).

A criterion MUST reference the audit-artifact version(s) it was validated against; re-validation (§7.2) is required **per artifact** — when the criterion changes materially, or when *that* artifact does. One artifact may re-validate without touching the other's record. The audit artifact MUST present all submitted code, content, page/app output, and probe observations to the judges as **quoted untrusted data, never as instructions** (injection hardening, design doc Threat Model §1). The mapping from checks (§4) to prompt sections or probe steps MUST be explicit, so a reader can see which realizes which requirement.

> Note (meta): the design doc's glossary formerly defined "rubric" as criterion-language + prompts + thresholds as one unit, while the attestation schema carried `rubric_version` and `prompt_version` as separate fields. This spec resolved the conflict by treating them as two bound-but-independently-versioned artifacts; the design-doc glossary and schema were brought into line 2026-07-01.

---

## 10. Provenance & governance metadata

Every criterion carries: `authors`, `reviewers`, cited `sources` (research, enforcement actions), and lifecycle metrics that populate over time:

- `first_active` date — powers "time-under-criterion" creator-history metrics (design doc, Layer 2).
- `delegation_inclusion_count` — how many active purchase delegations reference this criterion; the design doc's governance-weight and dead-letter signal. Populated post-launch.
- `overturn_rate` — fraction of this criterion's verdicts overturned on dispute, per version. A high overturn rate means a broken criterion and feeds rubric iteration. Populated post-launch.

---

## Appendix A — Machine-readable manifest schema (`criterion.yaml`)

The prose `SPEC.md` is normative; `criterion.yaml` is its machine-readable projection and MUST agree with it. The pipeline and consuming agents read the manifest. The manifest is also the criterion's **audit-output type** in the design doc's sense (Architecture §1, "a typed schema for what the audit output contains"): the check ids, the five check outcomes (§4.5), and the verdict enum (§5.1) define the shape of a result; the byte-level `results` encoding is Stage 1 schema work (design doc, Architecture §4).

```yaml
id: <kebab-case-id>
version: 0.1.0                      # MAJOR.MINOR.PATCH, monotonically non-weakening (§2.2)
status: draft                      # draft | candidate | active | deprecated
title: <human-readable title>
supersedes: null                   # id@version this replaces, or null

guarantee: >                       # §3.1 — plain-language user-facing assurance
  ...
harm_model: >                      # §3.2 — who is harmed, and when (deferred harm explicit)
  ...
scope:                             # §3.3
  covers: [ ... ]
  non_goals: [ ... ]
  related:
    - { id: <other-criterion>, relation: complements|overlaps|excludes }

observation_modes: [ behavioral ]  # §4.2 — union over checks: code | behavioral

checks:                            # §4.1
  - id: <check-id>
    statement: "<predicate>"
    keyword: MUST                  # MUST | MUST_NOT | SHOULD | SHOULD_NOT | MAY
    modes: [ behavioral ]          # code | behavioral | either
    evidence: [ flow_transcript, screenshot, step_count ]
    procedure: >
      ...
    decision: >
      ordered cascade, first match wins (§4.6):
      na if ... (not applicable); unobserved if ... (applies, uncapturable);
      fail if ...; conditional if ... (pass-with-named-caveat); pass otherwise
    severity: blocking             # blocking | caveat | advisory

aggregation:                       # §4.4 / §5 — default shown; override explicitly
  pass_if:          "all blocking checks pass (na excluded, and at least one blocking check applied — §4.4); no non-advisory check conditional; no caveat-severity check fails"
  fail_if:          "any blocking check fails (enumerate ALL failing blocking checks — §5.2)"
  conditional_if:   "no blocking fail AND (a non-advisory check returns conditional OR a caveat-severity check fails OR a blocking check is unobserved / partial scope)"
  indeterminate_if: "audit could not run or reach consensus at all; or every blocking check returned na (criterion did not apply — §4.4)"
  # advisory checks never move the verdict; unobserved on non-blocking checks does not downgrade (§4.4)

verdicts: [ PASS, CONDITIONAL, FAIL, INDETERMINATE ]

confidence:                        # §5.3
  method: "<how confidence is computed>"
  bands: { high: ">=0.90", medium: ">=0.70 and <0.90", low: "<0.70 -> INDETERMINATE + review" }

corpus:                            # §6
  public: ./corpus/public/
  sealed_ref: <hash-commitment>
  minimums: { clean: 10, violating: 10, boundary: 5, adversarial: 5, injection_canary: 3, defeat_device: 2 }  # defeat_device: behavioral criteria only

validation:                        # §7 — nulls until measured; gates status transitions
  human_calibration:               # §7.1 — target pre-registered BEFORE adjudication begins
    target: { aggregate: null, hard_subset: null, registered_at: null }   # e.g. "Cohen's kappa >= 0.8" / ">=80% exact-verdict on boundary+adversarial pooled"
    adjudicators: 0
    agreement_aggregate: null
    agreement_hard_subset: null    # boundary+adversarial pooled
    corpus_covered: null           # fraction of public-corpus rows adjudicated (SHOULD be 1.0)
  frontier_pool:  { false_pass: null, false_flag: null, indeterminate: null, agreement: null, cost_usd: null }
  enclave_pool:   { false_pass: null, false_flag: null, indeterminate: null, agreement: null, cost_usd: null }   # n/a if the audit artifact never runs under it (§7.2)
  kill_thresholds: { false_pass_max: 0.05, false_flag_max: 0.10 }   # illustrative until the corpus is assembled (§7.2); sealed set sized >= 3/epsilon per side

claim_template: >                  # §8
  "Artifact {subject} satisfied {id}@{version} under rubric {rubric_version},
   audit artifact {prompt_version}, model set {model_set}, modes {modes};
   measured false-pass {fp} / false-flag {ff} on corpus {corpus_hash}."

prompt_bundle: { ref: <uri-or-path>, version: null }   # §9 — single-mode criteria: the one audit artifact (prompt bundle for code, probe script for behavioral); key name tracks the attestation's prompt_version field
# Multi-mode criteria bind one artifact per declared mode instead (§9, T-10):
# prompt_bundle:
#   code:       { ref: <uri-or-path>, version: null }   # prompt bundle
#   behavioral: { ref: <uri-or-path>, version: null }   # probe script
# and their validation cells split per (pool x mode artifact) (§7.2), e.g.:
#   frontier_pool: { code: { false_pass: null, ... }, behavioral: { false_pass: null, ... } }

provenance:                        # §10
  authors: [ ... ]
  reviewers: [ ... ]
  sources: [ ... ]
  first_active: null
  delegation_inclusion_count: null
  overturn_rate: null
  changelog:
    - { version: 0.1.0, date: <YYYY-MM-DD>, change: "initial draft", rationale: "..." }
```

---

## Appendix B — Minimum-viable criterion

Not every field must be filled to *start*. The normative gate is §2.3; this appendix restates it as a worklist.

**To begin hand-validation (the §7.1 gate), a criterion needs:**

1. `id`, `version` (`0.x`), `status: draft`
2. `guarantee` + `harm_model` + `scope` (§3)
3. at least the **blocking** `checks`, each with all seven §4.1 fields — `id`, `statement`, `modes`, `evidence`, `procedure`, `decision`, `severity`
4. `aggregation` and the confidence bands (§4.4, §5 — defaults are fine)
5. a **public corpus** meeting the category minimums (§6)
6. the claim language (§8), the audit-artifact binding (§9 — one artifact per declared mode; artifacts may be planned, versions null), and §10's authors + sources

**To reach `candidate`:** all of the above, plus the **human-calibration gate passed** against a pre-registered target (§7.1).

Everything else — sealed corpus, measured validation record, audit-artifact version, governance lifecycle metrics — is populated on the path from `candidate` to `active`. The point of the mold is that authoring day one is light; the rigor accretes exactly where it pays off (at the ship gate and in disputes), not up front.

---

## Changelog

- **0.6.1** (2026-07-06) — **T-12 — silence semantics** (§4.5): applicability (`na`) short-circuits every decision even where a cascade omits an explicit `na` arm; in **corpus adjudication** a row is a complete fact set — checks its facts do not engage resolve `na`, with `unobserved` reserved for observation gaps the row itself states; in **live audits** the default inverts — an in-scope blocking check the audit could not decide is `unobserved`, never a silent `na`. From the first cross-vendor calibration panel (Claude + GPT-5, full corpora, blinded packets, 152/152): both raters independently invented the same convention and flagged the gap — perfect agreement meant the convention was *shared*, not that it was *stated*. Additive default; cascades omitting `na` arms are now legal by rule rather than by charity, and no criterion decision text changes.
- **0.6.0** (2026-07-06) — Multi-mode machinery, from authoring and reviewing the first dual-mode criterion (`no-dark-patterns` 0.1.0/0.1.1). **T-10 — one audit artifact per declared mode** (§9): the old "prompt bundle *or* probe script" disjunction could not represent a dual-mode criterion; a criterion now binds one artifact per mode, the attestation's `prompt_version` identifies the (mode, version) pair(s) actually run (no composite lockstep version — a code-only attestation must never cite a probe script that never ran), re-validation attaches per artifact, and §7.2 validation cells split per **(pool × mode artifact)** so measured error rates travel with the claim they describe (§7.3; a code-mode claim must not carry behaviorally-diluted rates). Appendix A shows both manifest shapes — the flat single-artifact form stays legal for single-mode criteria (`no-subscription-trap` unchanged). **T-11 — mode-join lattice** (new §4.7, referenced from §4.2 and §5.3): when both modes adjudicate one check, outcomes join worst-of over decided (`fail` > `conditional` > `pass`); a check decided in any mode is decided — `unobserved` elsewhere never downgrades it (the criterion's own first-draft rule had the perverse edge this forbids: both-modes audits yielding weaker verdicts than single-mode); `unobserved` survives only if every mode that ran returned it; `na` joins only `na`; per-check confidence completeness = max over modes. Overridable per criterion with documentation. Also: §4.2 states that a mode in which a check's deciding facts are unreachable returns `unobserved` rather than guessing; Appendix B item 6 pluralized. Additive for single-mode criteria; the multi-mode rules bind only criteria that declare them (both current criteria are `draft` — T-4 window regardless).
- **0.5.0** (2026-07-03) — External reviewer pass (pre-publication gate). **The candidate gate was stated three incompatible ways** (§1 table vs §2.3 vs Appendix B); §2.3 is now the single normative statement — §10's authors + sources join it, and "MAY NOT" → MUST NOT — while Appendix B is rewritten as a worklist of the same set (begin-hand-validation vs reach-candidate split; all seven §4.1 check fields named — it had dropped `statement` and `severity`). **Manifest:** `validation.human_calibration` expanded so the §7.1 record is actually representable (pre-registered target, aggregate and hard-subset agreements, `corpus_covered` — now defined in §7.1); `supersedes` defined (§2.1 — new-id discovery pointer; `@>=` filters MUST NOT cross it). **New default rules:** keyword ↔ severity MUST agree (§4.1: MUST → `blocking`, SHOULD → `caveat`, MAY → `advisory`); every-blocking-check-`na` → INDETERMINATE, never a vacuous PASS (§4.4). Also: behavioral validity-period/re-probe-cadence ownership explicitly deferred to the first behavioral `candidate` (§4.2); the manifest declared the criterion's audit-output type, byte encoding deferred to Stage 1 (Appendix A); sealed-corpus and cross-criterion ownership rules now carry MUST NOT keywords (§6.2, §3.3); §9's meta-note set to past tense (the design-doc glossary was fixed 2026-07-01); "non-advisory" qualifier restored in §5.1; confidence bands made half-open at 0.90; §6.3's canary-duty pointer corrected (§10 holds metadata, not duties); `kill_thresholds` marked illustrative in the manifest comment. TEMPLATE: the mandatory **Severity** field added to the check block (it was missing); copy instruction now describes the file → directory split; skeleton synced. Re-verify residue folded in same day: §4.5/§5.1 INDETERMINATE glosses aligned with the new inapplicability route, and `pass_if` now requires at least one applying blocking check. Additive or tightening — the two tightenings (keyword ↔ severity, all-blocking-`na`) are taken in the zero-attestation T-4 window, as 0.4.0's rename was; the one manifest-shape change (`human_calibration`) is migrated by `no-subscription-trap` 0.1.5.
- **0.4.0** (2026-07-02) — Second review pass. **T-8:** statement↔decision parity — a check's `fail` predicate MUST cover every violation shape its statement names; "`pass` otherwise" cascades were silently converting un-enumerated violations into passes (§4.6). **T-9:** corpus rows are the adjudication substrate and MUST state facts sufficient to decide every check they label (§6.4). Severity level `conditional` renamed **`caveat`** (§4.1, §4.4, §5.1, Appendix A) — it collided with the check *outcome* `conditional` (T-5) and the *verdict* CONDITIONAL; a breaking manifest rename taken now, while the only criterion is `draft` with zero attestations (the T-4 window). FAIL verdicts MUST enumerate all failing blocking checks (§5.2 — calibration finding C-1 promoted to the mold). §7.1 agreement targets MUST be finalized before adjudication begins (stated-in-advance discipline).
- **0.3.0** (2026-07-01) — Repo review against the design goals. **T-5:** added the fifth check outcome `conditional` (pass-with-named-caveat) that `no-subscription-trap` checks 2/3/5 were already emitting with no legal home (§4.1, §4.4, §4.5, Appendix A); default aggregation now also states that advisory checks never move the verdict and that `unobserved` on non-blocking checks does not downgrade. **T-6:** decisions MUST be total, and SHOULD be cascade-ordered (`na` → `unobserved` → `fail` → `conditional` → `pass`) or have mutually exclusive predicates; corpus disagreement with a decision rule blocks the §7.1 gate (new §4.6). **T-7:** bump semantics attach at first `active` — pre-`active` versions carry no compatibility semantics; first `active` SHOULD be ≥ 1.0.0 (§2.2, completing T-4). Also: §7.2 scoped to the model pools the audit artifact runs under (enclave pool n/a for purely behavioral criteria) and gained a sealed-corpus sizing rule (≥ 3/ε on the measured side; public minimums are calibration floors, not measurement power — §6.1); §7.1 agreement target now stratified with a hard-subset floor (the dry-run's aggregate-masks-structure lesson); added `notification_record` evidence type (§4.3 — checks capturing notices had no enumerated type); §8 and Appendix A claim templates say "audit artifact," finishing T-2's propagation.
- **0.2.1** (2026-07-01) — Scoped the monotonic-non-weakening invariant to `active` versions (§2.2): `draft`/`candidate` have issued no attestations and may be revised freely, including loosenings. (Finding T-4, from `no-subscription-trap` v0.1.1 loosening a check while draft.)
- **0.2.0** (2026-07-01) — Split check outcome `unobserved` from `na` and routed `unobserved` → CONDITIONAL (§4.4, §4.5, §5.1, Appendix A); generalized §9 from *prompt-bundle* to *audit-artifact* (prompt bundle **or** probe script); added the corpus **example record** with `provenance` + `observed_at` (§6.4); added an optional `defeat_device` corpus minimum. All three surfaced by authoring the first criterion, `no-subscription-trap` (findings T-1/T-2/T-3). Non-weakening, backward-compatible additions.
- **0.1.0** — initial meta-spec.
