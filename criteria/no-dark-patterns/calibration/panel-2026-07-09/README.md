# Reliability panel — 2026-07-09 (COUNTED, §7.1(a))

The first **counted** calibration round under CRITERION-SPEC 0.7.0 (T-13): the full-corpus **reliability** component of the §7.1 gate. The 2026-07-06 cross-vendor panel (`../panel-2026-07-06/`) remains an uncounted dry-run. **The gate is not yet complete:** the human-anchor component (§7.1(b)) is pending; `draft` status holds until it passes.

## Roster (per ADJUDICATION.md 0.2.0 record standards)

| Rater | Identity | Lineage vs. authors | Packet variant | Access route | Disclosures |
|---|---|---|---|---|---|
| 1 | **GPT-5.5** (operator-stated; self-reports GPT-5-family "Codex" via the same route) | OpenAI — **independent, counted** | A | Claude Code Agent tool, `sonnet` slot aliased to the operator's `gpt[1m]` routing; fresh context; usage record shows exactly **1 tool call** (the single permitted read of its packet) | received only the kit prompt; wrapper text recorded in the kit run log |
| 2 | **Gemini 3.5 Flash** (operator-selected; invoked as `gemini-3.5-flash`) | Google — **independent, counted** | B | `gemini` CLI 0.1.13, headless (`-p`), `GOOGLE_API_KEY` express mode, executed from an empty directory with all tool use forbidden | same kit-prompt-only delivery, piped on stdin; wrapper recorded in the kit run log |

**Counted-panel rule satisfied:** mutually lineage-unrelated (OpenAI / Google), neither authoring-lineage (Anthropic). Coordinator: project owner via a Claude-driven harness in a mechanical role. Criterion version adjudicated: **0.1.8** (current at run time). Contamination note: corpus public 2026-07-05, four days before the run; tools/search forbidden and attested. Blinding: honor-system plus packet construction.

## Results (targets registered at v0.1.4: κ ≥ 0.8 aggregate AND ≥ 0.80 exact on boundary+adversarial pooled)

n = 46, coverage 1.00. Inter-rater exact **46/46, Cohen's κ = 1.000**; hard subset (boundary+adversarial, n = 15) **15/15**; both raters 46/46 vs. the authored key; zero underdetermined. **Reliability component: PASS.**

The §12 watch-items (check 6 strictness, check 5's middle band, check 8's aggregate arm) all held blind on a second unrelated lineage pair; they stand for the human anchor, where the policy questions belong.

## Files

- `mapping.csv` — neutral ID → row ID, category, expected verdict, exercised checks (published now; **these shuffles are burned**).
- `rater-1-gpt55.csv`, `rater-2-gemini35flash.csv` — verbatim response sheets, attestations included. (Format note, verbatim-preserved: rater 1's PASS rows carry one extra empty field — notes land in a ninth column; verdicts unaffected.)
- `scoring.txt` — scorer output.
- Anchor packets/mapping and the round-2 generator stay private until the human-anchor component is scored.
