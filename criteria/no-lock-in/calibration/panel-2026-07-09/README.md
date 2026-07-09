# Reliability panel — 2026-07-09 (COUNTED, §7.1(a))

The first **counted** calibration round under CRITERION-SPEC 0.7.0 (T-13): the full-corpus **reliability** component of the §7.1 gate. The 2026-07-06 cross-vendor panel (`../panel-2026-07-06/`) remains an uncounted dry-run. **The gate is not yet complete:** the human-anchor component (§7.1(b)) is pending; `draft` status holds until it passes.

## Roster (per ADJUDICATION.md 0.2.0 record standards)

| Rater | Identity | Lineage vs. authors | Packet variant | Access route | Disclosures |
|---|---|---|---|---|---|
| 1 | **GPT-5.5** (operator-stated; self-reports GPT-5-family "Codex" via the same route) | OpenAI — **independent, counted** | A | Claude Code Agent tool, `sonnet` slot aliased to the operator's `gpt[1m]` routing; fresh context; usage record shows exactly **1 tool call** (the single permitted read of its packet) | received only the kit prompt; wrapper text recorded in the kit run log |
| 2 | **Gemini 3.5 Flash** (operator-selected; invoked as `gemini-3.5-flash`) | Google — **independent, counted** | B | `gemini` CLI 0.1.13, headless (`-p`), `GOOGLE_API_KEY` express mode, executed from an empty directory with all tool use forbidden | same kit-prompt-only delivery, piped on stdin; wrapper recorded in the kit run log |

**Counted-panel rule satisfied:** mutually lineage-unrelated (OpenAI / Google), neither authoring-lineage (Anthropic). Coordinator: project owner via a Claude-driven harness in a mechanical role. Criterion version adjudicated: **0.1.6** (current at run time). Contamination note: corpus public 2026-07-05, four days before the run; tools/search forbidden and attested. Blinding: honor-system plus packet construction. Stated in the run log **before scoring**: rater 2 is a Flash-tier model by deliberate operator choice, so tier is a candidate explanation for any agreement shortfall — recorded so interpretation can weigh it.

## Results (targets registered at v0.1.3: κ ≥ 0.8 aggregate AND ≥ 0.80 exact on boundary+adversarial pooled)

n = 64, coverage 1.00. Inter-rater exact **59/64 (0.922), Cohen's κ = 0.862** — above the 0.8 target; hard subset (boundary+adversarial, n = 22) **22/22 (1.000)**. Vs. the authored key: rater 1 **64/64**, rater 2 59/64. Zero underdetermined. **Reliability component: PASS.**

## Disagreement classification (all five, per ADJUDICATION.md)

All five disagreements are one systematic pattern from one rater: on **clean rows whose text ends at a completed deletion** (`clean-syn-email-confirm-delete`, `clean-syn-simple-delete`, `clean-syn-zero-offer-exit`, `clean-syn-unpaid-balance-settle`, `clean-syn-cancel-then-delete`), rater 2 returned CONDITIONAL with check 6 treated as `unobserved` ("deletion aftermath is unobserved"). The instructions state the T-12 rule explicitly: scenario silence is absence (`na`); `unobserved` is reserved for observation gaps **the scenario itself states**. The same rater applied the stated-gap arm correctly where it exists (`bound-syn-unobserved-grace` → CONDITIONAL; `clean-syn-grace-window`, `clean-syn-immediate-delete` → PASS on stated clean aftermaths), so the rule text decides these five and one rater slipped: **classification = misread ×5 (single-rater, systematic)** — the *live-audit* default (undecidable in-scope check → `unobserved`) imported into corpus adjudication, exactly the pull T-12 was legislated against. No rule gap: the counted rule text answers the case; no row bug: the rows' facts support their labels. Retained as a human-anchor watch-item: T-12 silence semantics on clean deletion rows (three of the five sit in exit-flow shapes the anchor sample already stresses).

Mechanical note (verbatim-preserved): rater 2 wrote per-row rationale text into the underdetermined/divergence column on all 64 rows — column drift, not underdetermined claims; verdict and caveat columns parse cleanly and are what the metrics read.

## Files

- `mapping.csv` — neutral ID → row ID, category, expected verdict, exercised checks (published now; **these shuffles are burned**).
- `rater-1-gpt55.csv`, `rater-2-gemini35flash.csv` — verbatim response sheets, attestations included.
- `scoring.txt` — scorer output, including the five-disagreement dump.
- Anchor packets/mapping and the round-2 generator stay private until the human-anchor component is scored.
