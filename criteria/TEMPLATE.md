<!--
  Copy this file to criteria/<your-id>/SPEC.md and fill it in; extract the
  embedded manifest below into criteria/<your-id>/criterion.yaml, and create
  criteria/<your-id>/corpus/public/ for the labeled examples (§6).
  Normative rules for every field live in ../CRITERION-SPEC.md (section refs below).
  The candidate gate is CRITERION-SPEC §2.3; Appendix B restates it as a worklist.
-->

# `<id>` — `<Human-Readable Title>`

**Version:** 0.1.0 · **Status:** draft
**Spec:** conforms to CRITERION-SPEC 0.5.0

---

## 1. Guarantee (§3.1)

<!-- One or two plain sentences: what is a user of a passing product assured of?
     This is the sentence a non-expert reads off the badge. -->

## 2. Harm model (§3.2)

<!-- What extraction does this prevent? WHO is harmed, and WHEN?
     Make the DEFERRED harm explicit — the harm that arrives at cancellation /
     export / the third upsell, invisible at purchase time. A check that traces
     to no harm here does not belong in this criterion. -->

## 3. Scope (§3.3)

- **Covers:** <!-- bounded set of in-scope behaviors -->
- **Non-goals:** <!-- explicitly OUT of scope; silence invites creep -->
- **Related criteria:** <!-- id + relation: complements | overlaps | excludes.
     If a behavior could belong to two criteria, exactly one owns it. -->

## 4. Requirements → Checks (§3.4, §4)

<!-- Decompose the property into atomic, observable checks. One row per check.
     severity: blocking (fails the criterion) | caveat (its fail → CONDITIONAL) | advisory
     modes:    code | behavioral | either  (per check — criteria can split) -->

### Check `<check-id>`
- **Statement (keyword):** `MUST` … <!-- MUST | MUST_NOT | SHOULD | SHOULD_NOT | MAY -->
- **Modes:** behavioral <!-- code | behavioral | either -->
- **Evidence:** <!-- flow_transcript, screenshot, har_capture, step_count, source_ref, ... -->
- **Procedure:** <!-- how an auditor (human or model) gathers the evidence -->
- **Decision:** <!-- ordered cascade, first match wins (§4.6): na if … ; unobserved if … ; fail if … ; conditional if … (pass-with-named-caveat) ; pass otherwise.
     Parity: the fail branch MUST cover every violation shape the Statement names (§4.6, T-8) -->
- **Severity:** blocking <!-- blocking | caveat | advisory — MUST agree with the keyword: MUST/MUST_NOT → blocking, SHOULD/SHOULD_NOT → caveat, MAY → advisory (§4.1) -->

<!-- repeat per check -->

## 5. Aggregation & verdicts (§4.4, §4.5, §5)

<!-- Check outcomes: pass | conditional (pass-with-named-caveat) | fail | na (not applicable — ignored) | unobserved (blocking: → CONDITIONAL; non-blocking: no downgrade).
     Default aggregation (override only with justification):
     PASS          — all blocking checks pass (na excluded, at least one applying); no non-advisory conditional; no caveat-severity fail
     FAIL          — any blocking check fails (enumerate ALL failing blocking checks — §5.2)
     CONDITIONAL   — no blocking fail, but a non-advisory check returns conditional, a caveat-severity check fails, OR a blocking check is `unobserved` (partial scope)
                     (MUST enumerate which checks triggered the condition — machine-readable)
     INDETERMINATE — audit could not run or reach consensus at all (treated as absent);
                     also: every blocking check `na` → INDETERMINATE, never a vacuous PASS (§4.4)
     Advisory checks never move the verdict. -->

## 6. Corpus (§6)

<!-- Public labeled examples live in ./corpus/public/. Category minimums:
     clean (PASS) · violating (FAIL) · boundary (CONDITIONAL) ·
     adversarial/evasion (FAIL) · injection-canary (FAIL) ·
     defeat-device fixture (behavioral only).
     Balance positive/negative so BOTH false-pass and false-flag are measurable.
     Each row carries provenance (synthetic | documented-report | ftc-action …) and,
     for non-synthetic rows, observed_at — named-product behavior is only true as-of a date.
     Sealed set is hash-committed in the manifest, never published. -->

| example_id | category | expected | checks exercised | provenance | observed_at | note |
|------------|----------|----------|------------------|------------|-------------|------|
|            |          |          |                  |            |             |      |

## 7. Validation record (§7)

<!-- Nothing is measured at draft; state the path.
     draft → candidate: human-calibration gate (§7.1) — ≥2 independent adjudicators on the
       public corpus. Finalize ONE metric + thresholds (incl. the boundary+adversarial
       hard-subset floor) BEFORE adjudication begins.
     candidate → active: validation study (§7.2) on the SEALED corpus, per applicable model
       pool (enclave pool n/a for purely behavioral criteria). Kill thresholds; sealed set
       sized ≥ 3/ε per measured side. -->

## 8. Claim language (§8)

> "Artifact `{subject}` satisfied `<id>@{version}` under rubric `{rubric_version}`, audit artifact `{prompt_version}`, model set `{model_set}`, modes `{modes}`; measured false-pass `{fp}` / false-flag `{ff}` on corpus `{corpus_hash}`."

**Does NOT assert:** <!-- e.g., product safety, future versions, unaudited config -->

## 9. Audit-artifact binding (§9)

<!-- Which prompt bundle (code) or probe script (behavioral) realizes these checks.
     Required at candidate. State: artifact type + path (may be planned); injection
     hardening (all audited content presented as quoted untrusted data, never
     instructions); the explicit check → prompt-section / probe-step mapping.
     The version (`prompt_version`) may stay null until validation (§7.2). -->

## 10. Provenance & governance (§10)

<!-- Authors, reviewers, cited sources (research, enforcement actions), and the
     changelog (every version: change + rationale — §2.4). Lifecycle metrics
     (first_active, delegation_inclusion_count, overturn_rate) populate post-launch. -->

---

## Manifest — `criterion.yaml` (Appendix A)

```yaml
# SPDX-License-Identifier: CC-BY-4.0 OR Apache-2.0
# SPDX-FileCopyrightText: <year> Consense
id: <id>
version: 0.1.0
status: draft
title: <title>
supersedes: null

guarantee: >
  <fill §1>
harm_model: >
  <fill §2>
scope:
  covers: [ ]
  non_goals: [ ]
  related: [ ]

observation_modes: [ ]        # union over checks: code | behavioral

checks:
  - id: <check-id>
    statement: "<predicate>"
    keyword: MUST
    modes: [ behavioral ]
    evidence: [ ]
    procedure: >
      ...
    decision: >
      ordered cascade, first match wins (§4.6):
      na if ...; unobserved if ...; fail if ...; conditional if ...; pass otherwise
    severity: blocking             # blocking | caveat | advisory — MUST agree with keyword (§4.1)

aggregation:
  pass_if:          "all blocking checks pass (na excluded, and at least one blocking check applied — §4.4); no non-advisory check conditional; no caveat-severity check fails"
  fail_if:          "any blocking check fails (enumerate ALL failing blocking checks — §5.2)"
  conditional_if:   "no blocking fail AND (a non-advisory check returns conditional OR a caveat-severity check fails OR a blocking check is unobserved / partial scope)"
  indeterminate_if: "audit could not run or reach consensus at all; or every blocking check returned na (criterion did not apply — §4.4)"
  # advisory checks never move the verdict; unobserved on non-blocking checks does not downgrade (§4.4)

verdicts: [ PASS, CONDITIONAL, FAIL, INDETERMINATE ]

confidence:
  method: "<how computed>"
  bands: { high: ">=0.90", medium: ">=0.70 and <0.90", low: "<0.70 -> INDETERMINATE + review" }

corpus:
  public: ./corpus/public/
  sealed_ref: <hash-commitment>
  minimums: { clean: 10, violating: 10, boundary: 5, adversarial: 5, injection_canary: 3, defeat_device: 2 }  # defeat_device: behavioral only

validation:
  human_calibration:               # §7.1 — target pre-registered BEFORE adjudication begins
    target: { aggregate: null, hard_subset: null, registered_at: null }   # e.g. "Cohen's kappa >= 0.8" / ">=80% exact-verdict on boundary+adversarial pooled"
    adjudicators: 0
    agreement_aggregate: null
    agreement_hard_subset: null    # boundary+adversarial pooled
    corpus_covered: null           # fraction of public-corpus rows adjudicated (SHOULD be 1.0)
  frontier_pool:  { false_pass: null, false_flag: null, indeterminate: null, agreement: null, cost_usd: null }
  enclave_pool:   { false_pass: null, false_flag: null, indeterminate: null, agreement: null, cost_usd: null }   # n/a if the audit artifact never runs under it (§7.2)
  kill_thresholds: { false_pass_max: 0.05, false_flag_max: 0.10 }   # illustrative until the corpus is assembled (§7.2); sealed set sized >= 3/epsilon per side

claim_template: >
  "Artifact {subject} satisfied <id>@{version} under rubric {rubric_version},
   audit artifact {prompt_version}, model set {model_set}, modes {modes};
   measured false-pass {fp} / false-flag {ff} on corpus {corpus_hash}."

prompt_bundle: { ref: <uri-or-path>, version: null }   # §9 — the audit artifact: prompt bundle (code) OR probe script (behavioral); key name tracks the attestation's prompt_version field

provenance:
  authors: [ ]
  reviewers: [ ]
  sources: [ ]
  first_active: null
  delegation_inclusion_count: null
  overturn_rate: null
  changelog:
    - { version: 0.1.0, date: <YYYY-MM-DD>, change: "initial draft", rationale: "..." }
```
