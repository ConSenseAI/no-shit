# No Shit

Machine-verifiable, criterion-specific claims about the anti-extraction properties of software — dark patterns, subscription traps, surveillance, lock-in. A creator submits code (or a live product gets mystery-shopped by probe agents), a multi-model LLM consensus audit runs inside a trusted execution environment against a public, versioned criterion, and a signed attestation is published where humans, procurement teams, and buyers' agents can verify it.

**Status: visioning / pre-development.** Nothing here runs yet. What exists is the design document and the first drafts of the criterion layer, published early on purpose: the spec being citable matters more than the pipeline being ready. (The name is a working title; the citable spec layer will carry a neutral technical name — see the design doc's *Naming* section.)

## What's here

| Artifact | What it is | Status |
|---|---|---|
| [`no-shit.md`](no-shit.md) | The design document — architecture, threat model & validation plan, economics, distribution strategy | Living draft |
| [`criteria/CRITERION-SPEC.md`](criteria/CRITERION-SPEC.md) | The meta-specification every criterion must conform to: check structure, verdict semantics, versioning invariants, corpus and calibration requirements | v0.6.0, draft |
| [`criteria/TEMPLATE.md`](criteria/TEMPLATE.md) | Copy-this skeleton for authoring a new criterion | Tracks CRITERION-SPEC |
| [`criteria/no-subscription-trap/`](criteria/no-subscription-trap/) | The first criterion: cancellation must be symmetric to signup — spec, machine-readable manifest, labeled public corpus, calibration records | v0.1.8, draft |
| [`criteria/no-dark-patterns/`](criteria/no-dark-patterns/) | The second criterion: choice interfaces must be honest — no fabricated pressure signals, trick controls, consent asymmetry, or sneaked additions. The first dual-mode (code + behavioral) criterion | v0.1.5, draft |
| [`criteria/no-lock-in/`](criteria/no-lock-in/) | The third criterion, completing the Stage 0 set: you can leave with your stuff — self-service export in standard formats, complete; self-service deletion that is honored; no obstruction on the way out | v0.1.3, draft |

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
