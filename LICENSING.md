# Licensing

This repository uses two licenses, split by artifact class:

| Artifact class | License | File |
|---|---|---|
| Specifications, criterion definitions, corpora, design documents, and all other prose | [CC-BY-4.0](LICENSE) | `LICENSE` |
| Source code — audit pipeline, probe scripts, prompt bundles, CLI, and other tooling | [Apache-2.0](LICENSE-CODE) | `LICENSE-CODE` |

Everything in this repository today is prose and therefore CC-BY-4.0. The Apache-2.0 grant applies to code artifacts as they land.

## Dual-licensed machine-readable artifacts

Machine-readable criterion manifests (`criterion.yaml`), schema definitions, and the manifest/schema snippets embedded in the specifications are additionally available under Apache-2.0, so implementers can copy them directly into code without license gymnastics:

`SPDX-License-Identifier: CC-BY-4.0 OR Apache-2.0`

## Copyright

Copyright © 2026 Consense.

Individual contributors retain authorship credit in each artifact's provenance metadata (CRITERION-SPEC §10); those credits are historical record, not license notices. The Apache-2.0 copyright notice for code artifacts lives in `NOTICE`, which redistributors preserve per Apache-2.0 §4(d).

## Attribution

For the purposes of CC-BY-4.0 §3(a)(1)(A), attribution is designated to **Consense** and this repository: identify the source as Consense, by the repository at `https://github.com/ConSenseAI/no-shit` and, where applicable, the artifact and its version (e.g., `no-subscription-trap@0.1.4`, `CRITERION-SPEC 0.4.0`). No attribution to any individual is requested or required.

## Forks and modified versions

Forking is an explicitly supported governance exit for this protocol (see the design document, *Governance — Forkability*). Two obligations travel with that freedom, both from CC-BY-4.0 itself:

- **Modified versions must be marked as modified** (§3(a)(1)(B)). A derivative criterion with different semantics must say so; it must not present itself as the original text.
- **No endorsement** (§2(a)(6)). Use of these materials does not imply endorsement by, or any connection with, Consense.

Criterion identifiers and versions carry semantics that consuming agents rely on. A fork that changes a criterion's meaning should publish under its own identifiers (and will, at the protocol layer, necessarily publish under its own attestation schema UID and auditor identity).
