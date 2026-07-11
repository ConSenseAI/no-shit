# No Shit

Machine-verifiable, criterion-specific claims about the anti-extraction properties of software — dark patterns, subscription traps, surveillance, lock-in. A creator submits code (or a live product gets mystery-shopped by probe agents), a multi-model LLM consensus audit runs inside a trusted execution environment against a public, versioned criterion, and a signed attestation is published where humans, procurement teams, and buyers' agents can verify it.

**Status: early development.** The design document, criterion layer, and validation protocol are published living drafts — published early on purpose: the spec being citable matters more than the pipeline being ready. The first running code landed 2026-07-10: the F0 fixture-platform proof (`platform/`) — virtual-clock, mail-sink, seeding, and persona machinery demonstrated end-to-end on real hosts. The audit pipeline itself does not exist yet. (The name is a working title; the citable spec layer will carry a neutral technical name — see the design doc's *Naming* section.)

## What's here

| Artifact | What it is | Status |
|---|---|---|
| [`no-shit.md`](no-shit.md) | The design document — architecture, threat model & validation plan, economics, distribution strategy | Living draft |
| [`criteria/CRITERION-SPEC.md`](criteria/CRITERION-SPEC.md) | The meta-specification every criterion must conform to: check structure, verdict semantics, versioning invariants, corpus and calibration requirements | v0.7.0, draft |
| [`criteria/TEMPLATE.md`](criteria/TEMPLATE.md) | Copy-this skeleton for authoring a new criterion | Tracks CRITERION-SPEC |
| [`criteria/ADJUDICATION.md`](criteria/ADJUDICATION.md) | Instructions for the §7.1 calibration gates (full-corpus reliability panels + human-anchor samples): what adjudicators do (sendable as-is) and the coordinator protocol — blinded packet prep, scoring, recording | v0.2.1, draft |
| [`criteria/no-subscription-trap/`](criteria/no-subscription-trap/) | The first criterion: cancellation must be symmetric to signup — spec, machine-readable manifest, labeled public corpus, calibration records | v0.1.11, draft |
| [`criteria/no-dark-patterns/`](criteria/no-dark-patterns/) | The second criterion: choice interfaces must be honest — no fabricated pressure signals, trick controls, consent asymmetry, or sneaked additions. The first dual-mode (code + behavioral) criterion | v0.1.9, draft |
| [`criteria/no-lock-in/`](criteria/no-lock-in/) | The third criterion, completing the Stage 0 set: you can leave with your stuff — self-service export in standard formats, complete; self-service deletion that is honored; no obstruction on the way out | v0.1.7, draft |
| [`validation/PROTOCOL.md`](validation/PROTOCOL.md) | The Stage 0 validation-study protocol: corpus and fixture construction, model pools, procedure under test, metrics, and the pre-stated kill criteria — freezes into the study's pre-registration before any execution | v0.1.5, draft |
| [`validation/ATTAINABILITY.md`](validation/ATTAINABILITY.md) | The corpus-attainability audit (PROTOCOL §4.3): what the sealed corpus must contain vs. what the real world supplies with defensible ground truth — all 152 public rows classified by observation channels and fixture cost, findings feeding the fixture build plan and threshold finalization | v0.1.2, draft |
| [`validation/FIXTURES.md`](validation/FIXTURES.md) | The fixture build plan (PROTOCOL §12.4): a four-service fixture platform — virtual clock, messaging capture, state seeding, support personas — host-bench assignments, six build lanes from enforcement-exhibit re-implementations to the defeat-device lane, pre-registered QA gates, and sequencing to freeze | v0.1.3, draft |
| [`validation/OBSERVATION-PARAMS.md`](validation/OBSERVATION-PARAMS.md) | The observation parameters (PROTOCOL §12.9) at row grain: a 17-class window registry over all 152 public corpus rows, the surface-census definition that scopes absence claims (with per-criterion keyword lists), rate-fact trial rules, and the vision-capable-judging pool constraint — every numeric a proposal until the freeze pins it | v0.1.0, draft |
| [`platform/`](platform/) | The fixture platform itself — the repo's first running code: compose legs proving the build plan's riskiest claims on real hosts (Kill Bill engine clock, Stripe sandbox test clocks, libfaketime, per-fixture mail sinks with first-class absence assertions, scripted personas) | F0 proven 2026-07-10 · F1 underway |

## The idea, briefly

Anti-extraction quality is a credence good: the extractive product looks identical or better at purchase time, and the harm arrives later — at cancellation, at export, at the third dark-pattern upsell. Markets under-reward what buyers can't verify. This protocol supplies the missing information layer: formally specified criteria, audits whose error rates are measured and published before anything ships, and attestations that agents acting under delegated purchase criteria can filter on. The lineage is private, voluntary certification — UL, Consumer Reports, Let's Encrypt — rebuilt for agent-mediated markets.

Everything is open: criteria, audit prompts, orchestration code, attestation schemas. The validation study gates the pipeline — kill criteria are stated in advance, and if multi-model consensus can't judge these properties reliably, that result gets published too.

**No token. No coin. Ever.** Attestations are published to open registries (an EAS schema and a public transparency log); the chain layer is a notary, not an economy.

## Reading order

1. [`no-shit.md`](no-shit.md) — start with *Summary*, *Problem Statement*, and *Threat Model & Validation*.
2. [`criteria/CRITERION-SPEC.md`](criteria/CRITERION-SPEC.md) — the rules criteria are built under.
3. [`criteria/no-subscription-trap/SPEC.md`](criteria/no-subscription-trap/SPEC.md) — the mold applied once, end to end.

## Licensing & citation

Prose (specs, criteria, corpora, this document) is [CC-BY-4.0](LICENSE); code is [Apache-2.0](LICENSE-CODE); machine-readable manifests are dual-licensed. Details in [`LICENSING.md`](LICENSING.md). Copyright [Consense](NOTICE).

To cite this work, use [`CITATION.cff`](CITATION.cff).
