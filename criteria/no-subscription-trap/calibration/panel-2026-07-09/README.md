# Reliability panel — 2026-07-09 (COUNTED, §7.1(a))

The first **counted** calibration round under CRITERION-SPEC 0.7.0 (T-13): the full-corpus **reliability** component of the §7.1 gate. The 2026-07-06 cross-vendor panel (`../panel-2026-07-06/`) remains an uncounted dry-run. **The gate is not yet complete:** the human-anchor component (§7.1(b)) is pending; `draft` status holds until it passes.

## Roster (per ADJUDICATION.md 0.2.0 record standards)

| Rater | Identity | Lineage vs. authors | Packet variant | Access route | Disclosures |
|---|---|---|---|---|---|
| 1 | **GPT-5.5** (operator-stated; self-reports GPT-5-family "Codex" via the same route) | OpenAI — **independent, counted** | A | Claude Code Agent tool, `sonnet` slot aliased to the operator's `gpt[1m]` routing; fresh context; usage record shows exactly **1 tool call** (the single permitted read of its packet) | received only the kit prompt (instructions + rule excerpt + packet + sheet header); wrapper text recorded in the kit run log |
| 2 | **Gemini 3.5 Flash** (operator-selected; invoked as `gemini-3.5-flash`) | Google — **independent, counted** | B | `gemini` CLI 0.1.13, headless (`-p`), `GOOGLE_API_KEY` express mode, executed from an empty directory with all tool use forbidden | same kit-prompt-only delivery, piped on stdin; wrapper recorded in the kit run log |

**Counted-panel rule satisfied:** the two raters are mutually lineage-unrelated (OpenAI / Google) and neither shares the criteria's authoring lineage (Anthropic). Coordinator: project owner, operating through a Claude-driven harness whose role was mechanical (packet delivery, verbatim collection, scoring); the coordinator is not a rater. Criterion version adjudicated: **0.1.10** (current at run time; no changes between kit generation and the runs). Contamination note: the public corpus went public 2026-07-05, four days before this run — training-data memorization is implausible for either rater; the live leak vector (tools/search) was forbidden and attested. Blinding is honor-system plus packet construction, as always.

## Results (targets registered at v0.1.3: κ ≥ 0.8 aggregate AND ≥ 0.80 exact on boundary+adversarial pooled)

n = 42, coverage 1.00. Inter-rater exact **42/42, Cohen's κ = 1.000**; hard subset (boundary+adversarial, n = 11) **11/11**; both raters 42/42 vs. the authored key; zero underdetermined. **Reliability component: PASS.**

Divergence log: rater 1 flagged the separate-attempt recurrence cap on `probe-persistent-offer` as rule-over-instinct (verdict correct) — the third consecutive panel to log exactly this divergence (v0.1.0 probe, 2026-07-06 panel, now here). It remains a watch-item for the human anchor, not a rule defect.

## Files

- `mapping.csv` — neutral ID → row ID, category, expected verdict, exercised checks (published now; **these shuffles are burned** — any later reliability round regenerates with fresh seeds).
- `rater-1-gpt55.csv`, `rater-2-gemini35flash.csv` — verbatim response sheets, attestations included.
- `scoring.txt` — scorer output (`tools/adjudication/score.py` logic, run from the round-2 kit).
- The anchor-sample packets and their mapping remain **private** until the human-anchor component is scored; the round-2 kit generator publishes with that record (its determinism would derive the anchor mapping).
