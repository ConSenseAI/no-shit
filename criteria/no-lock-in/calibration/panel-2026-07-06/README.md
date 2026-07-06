# Cross-vendor calibration panel — 2026-07-06 (run 2)

Published evidence for the run recorded in `../../calibration-dryrun.md` (run 2) and SPEC §7. **Engineering dry-run — not the formal §7.1 gate**; `human_calibration` stays 0.

## Roster (per ADJUDICATION.md record standards)

| Rater | Identity | Lineage vs. authors | Packet variant | Access route | Disclosures |
|---|---|---|---|---|---|
| 1 | Claude | **author-lineage** — the keys were Claude-authored; agreement discounted in interpretation | A | not recorded | read the kit's coordinator README (methodology, no per-scenario labels) before adjudicating; did not open the mapping or generator |
| 2 | GPT-5 | **independent — carries the evidential weight** | not recorded | not recorded | none stated |

Coordinator: project owner. Criterion version adjudicated: **0.1.4** (current 0.1.5 differs only by the single-offer pitch-target sharpening — no decision changes). Blinding is honor-system plus packet construction; attestations are in the sheets verbatim.

## Results

n = 64, coverage 1.00. Inter-rater exact 64/64, **Cohen's κ = 1.00**; hard subset (boundary+adversarial, n = 22) 22/22; both raters 64/64 vs. the authored key; zero underdetermined. Scored with `tools/adjudication/score.py`.

## Files

- `mapping.csv` — neutral ID → row ID, category, expected verdict, exercised checks (private until scoring; published shuffles are burned — any later round regenerates with fresh seeds).
- `rater-1-claude.csv`, `rater-2-gpt5.csv` — verbatim response sheets, attestations included.
- Packets are reproducible byte-identically from `tools/adjudication/gen.py` (seeds in the mapping header).
