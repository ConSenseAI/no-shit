# Fixture manifest & dossier format

Formalizes [`validation/FIXTURES.md`](../../validation/FIXTURES.md) §8: the
per-fixture record that gets hashed into the sealed manifest at freeze, and the
**Lane-1 dossier** — the research-stage draft of that record (an enforcement
exhibit worked into a build-ready fixture spec, FIXTURES §4 Lane 1).

The **format** (this directory: field spec, template, validator, a fictional
example) is public. **Instances are sealed-side** and live outside this
repository until the study report reveals the corpus (PROTOCOL §4.2, §9) — a
dossier names which exhibit becomes which fixture with what expected labels,
which is exactly what provenance-blinding protects.

## Files

- [`DOSSIER-TEMPLATE.yaml`](DOSSIER-TEMPLATE.yaml) — copy-this skeleton, field comments inline
- [`example-dossier.yaml`](example-dossier.yaml) — complete **fictional** example (passes validation)
- [`validate.py`](validate.py) — stdlib+PyYAML domain validator: `python3 validate.py <dossier.yaml> [...]`

## Field spec (summary — the template carries per-field comments)

| Block | What it fixes |
|---|---|
| `dossier`, `criterion`, `status` | identity; `status: draft-dossier` until a builder picks it up |
| `anchor` | the enforcement case: authority, `action_type` (`fined`/`adjudicated`/`settlement`/`commitment`/`complaint-filed` — descending label strength per PROTOCOL §9 basis 1), conduct/filed/order dates |
| `exhibit` | the evidence: sources with per-source `confidence` (`confirmed` = read from a primary record; `reported` = secondary) and `retrieved` dates; `flow_documented` — the violating flow step-by-step, **each step citing the exhibit** (complaint paragraph, decision section, figure, archive capture); `gaps` — what the exhibit does NOT establish (honesty field, mandatory) |
| `fixture_spec` | the build: bench `host` + rationale, `implant_outline`, `channels` (ATTAINABILITY §3 vocabulary), `tier` (E1–E4), time-script/seeding needs |
| `expected_labels` | per-criterion expected verdict + failing checks **by SPEC check number**, `basis: enforcement-exhibit`, `basis_date`, `scope` (fidelity-to-exhibit at the record's date — never live truth) |
| `build_estimate`, `open_questions` | S/M/L + what a builder must resolve |

Validation is domain-aware, not generic JSON Schema: criterion IDs, verdict and
basis enums, channel vocabulary, tier range, ISO dates, confidence tags, and
the citation-per-flow-step rule are all checked. The full JSON-Schema rendering
of the *fixture manifest* (the post-build record) is a freeze-time artifact;
this validator is normative until then.
