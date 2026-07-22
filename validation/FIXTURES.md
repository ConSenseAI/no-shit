# Fixture Build Plan

**Version:** 0.1.8 · **Status:** draft — §2's platform claims F0-proven 2026-07-10; F1 staged bench build 2026-07-11 + Ghost webhook-driven billing coupling proven 2026-07-16 ([`platform/`](../platform/)); first sealed tranche through the full §6 gate cycle 2026-07-17; **all staged violating tranches sealed 2026-07-22** (Ghost and Open SaaS legs through the same cycle; Open SaaS host leg bench-proven the same day); §7's stubs expanded to row grain at [`OBSERVATION-PARAMS.md`](OBSERVATION-PARAMS.md)
**Serves:** [`PROTOCOL.md`](PROTOCOL.md) §12.4 (fixture build plan and budget — this document is the plan; dollar figures and final numeric QA thresholds are fixed at freeze per §2) and §12.9 (observation-procedure parameters — §7 below drafts the proposals the freeze pins)
**Consumes:** [`ATTAINABILITY.md`](ATTAINABILITY.md) — the demand tables (§2–§3), findings O-1…O-10, the host bench (§5.3), the gap analysis (§6), and the §7 recommendations this plan converts into build items
**Platform tooling facts as of:** 2026-07-09 — documentation-level verification, tagged inline; F0 (§9) converts them to working fact

What this builds: the sealed corpus PROTOCOL §4.2 requires — a portfolio of roughly **90–150 fixture products** carrying ≥60 violating + ≥30 clean labels per criterion, in each cell's required form (probe-exercisable everywhere; dual-form source-shipping for `no-dark-patterns`' code cells), plus every criterion's sealed injection-canary subset. The attainability audit established that all 152 public-corpus fact-shapes are buildable as owned fixtures (O-10) and that four platform services amortize across nearly all of them (§7.2 item 1 there). This plan is organized accordingly: **platform first, then six lanes over it.**

---

## 1. Design rules (normative for every fixture)

1. **Product-level fixtures, per-criterion labels.** One fixture serves multiple cells; co-location of violations is limited deliberately (a fixture violating all three criteria invites correlated verdicts and leaks label information — ATTAINABILITY §2).
2. **Every fixture ships a fixture manifest** (§8): host + version pin, implant diff ref, per-criterion label with basis/date/scope (PROTOCOL §9), channels exercised, surface census, time script, seed spec, canary placements, role assignments, QA results. The sealed-manifest hash committed at freeze is a hash over these records.
3. **Builder ≠ labeler.** A builder never solely labels their own implant (PROTOCOL §9, construction basis); verification against the build spec is a second person's job.
4. **Implants are minimal, idiomatic diffs.** The violation is the diff; everything else stays the host's. Detectability is a QA-gated property (§6.1), not an assumption.
5. **The harness stays out of the artifact.** Clock control, mail sinks, seeding, and persona automation live in the deployment layer — never in submitted source (code cells) or page-visible surfaces (behavioral cells). A time-*abstraction* inside host code, where one must be introduced, is written as an idiomatic injected clock — which is how real codebases do it anyway.
6. **License hygiene** per ATTAINABILITY §5.3: permissive and copyleft hosts both work (AGPL → modified source is published, aligned with this project regardless); source-available licenses are excluded; EE-marked directories are avoided; host versions are pinned at build, so later relicensing (the NocoDB/Cal.com pattern) cannot reach back.

## 2. Platform — four amortized services (build these first)

### 2.1 Virtual clock (O-1 — the single largest lever)

Requirement: 44 E3-class rows and every W-flagged fact; collapse ≥7-day-to-annual observations into minutes; billing events, scheduled jobs, and message sends must all move together.

Mechanism ladder, chosen per host:

1. **Engine-native clocks** where billing behavior is the deciding layer. Kill Bill runs a server-global movable clock in test mode (`org.killbill.server.test.mode=true` → `/1.0/kb/test/clock`; movable both directions) *(confirmed 2026-07-09, Kill Bill docs)*. Stripe sandbox **test clocks** simulate subscription lifecycles from a frozen start time — forward-only, ≤2 billing intervals per advance, ≤3 customers per clock *(confirmed 2026-07-09, Stripe docs)*. Stripe-coupled hosts (Ghost, the MIT starters) ride test clocks for billing-side facts; the caps fit fixture shape (1–3 accounts each) but bind the time script — an annual-reminder fact is several stepped advances, not one jump. **F0-proven (2026-07-10)**, with two provisioning findings: Stripe **key scope** is the binding constraint, not the clock caps (a test-clock-only restricted key proves clock mechanics but blocks the subscription lifecycle — fixture keys need customer/subscription/invoice/event/product scopes, and a scope pre-flight belongs in fixture setup; with the key re-scoped the full trial→convert→$12-charge→cancel lifecycle proved 9/9 the same day); and Kill Bill clock moves must land at explicit datetimes *past* the boundary — a bare date is midnight, which sits *before* same-day event instants and silently converts nothing (the harness promotes bare dates to noon).
2. **Stack-level fake time** for app-side schedulers: LD_PRELOAD time interception (libfaketime-class) driven by a shared control file mounted across the fixture's containers. Needed because host cron/queue workers — trial reminders, scheduled deletion jobs, export-link expiry — read the app clock, not Stripe's. **F0 caveat (2026-07-10): this rung is glibc-only.** musl/alpine host images (Documenso among them) cannot preload glibc libfaketime; check the image's libc *first*, and give musl hosts a glibc sidecar in the same stack (F0's proven pattern — a day-30 job crossed in ~1 s) or rung 3.
3. **Harness-triggered jobs** as the fallback: where a host's scheduler resists fake time, the harness fires the host's own job code explicitly at scripted virtual times. The job's code remains the host's; only the trigger moves.

**Coupling rule:** each fixture's engine clock, app clock, and messaging jobs advance under one **time script**, recorded in the manifest; every longitudinal fact in the label cites script positions (`T0` signup → `T0+8d` charge + notice). Known drift risks to engineer around at F0, recorded per fixture: TLS certificate validity under far-future jumps (fixtures run HTTP-internal or under a long-validity internal CA) and timestamp skew between engine time and app time across webhooks.

### 2.2 Messaging capture with absence monitoring (O-2, the `msg` channel)

A per-fixture SMTP sink (Mailpit-class; F0-verified) captures all outbound mail; **the sink log is the msg-channel census**, and sink retention must be unbounded while any absence window is open (no auto-prune). Absence claims take the form "no message matching M within script window [T0+a, T0+b]" and are first-class evidence artifacts — log excerpt plus window citation — because clean verdicts are absence verdicts and a missed message is a false-PASS path (O-2). Non-mail channels (SMS, push) follow the same pattern through provider-sandbox sinks or host-level notification interception. **F1 finding (2026-07-11): absence windows anchor to completed-delivery events, never timers.** Host senders are asynchronous and rate-limited (listmonk's campaign queue) or flush-cycled (wp-cron); mail queued but unsent when a timer closes the window is a false-clean path. The platform pattern: open the window on a sender-finished signal (campaign-finished status, completed cron flush), close it the same way, and reserve `settle` margins for transport latency only.

### 2.3 State seeding and the payment spine (`acct*`, O-8)

A per-host seeding API supplies what heavy rows need: bulk content (hundreds-per-collection, for truncation shapes), org workspaces, plan/billing *history* (backdated timestamps written directly — history is seeded, not simulated through the clock), metered debt, paid states. The payment spine is engine test machinery — Stripe test mode, WooCommerce's test gateway, Kill Bill's payment test plugin (which can also be told to *fail* payments, covering dunning shapes) — producing charges, receipts, and refunds observable as engine events plus receipt mail in the sink.

### 2.4 Scripted support personas (O-5)

Mailbox/chat automation with virtual-clock-timed responses; persona scripts are fixture config. The corpus's demand-decidable design pattern is preserved: where a row is decidable from the *demand* the product makes (phone-wall, sales-call requirement, ID-upload gate), the fixture presents the demand and no fulfillment machinery is needed; personas exist for the rows where fulfillment timing itself decides (manual export against a stated SLA).

## 3. Host bench assignments

The verified bench from ATTAINABILITY §5.3, turned into build assignments:

| Host | Criteria | Assignment |
|---|---|---|
| **Ghost** + MIT Stripe starters | nst★ ndp | flagship `nst` implant hosts — native full subscription lifecycle (tiers, carded trial, checkout, retention offer, cancel); Stripe test clocks |
| **WooCommerce + Subscriptions** | ndp★ nst | storefront patterns: scarcity, social proof, drip pricing, countdowns — **pure implants** (no surveyed OSS host ships these natively); most consumer-realistic checkout. F1 note (2026-07-11): WooCommerce Subscriptions is commercially distributed (paid, GPL) — build-time decision: one paid license or a free wordpress.org stand-in (`subscriptions-for-woocommerce`, `flexible-subscriptions`); the bench leg is proven without it |
| **Twenty CRM** | nst ndp nli | the deliberate-co-location fixtures (limited by rule 1); avoid enterprise-marked files |
| **Discourse** + MIT subscriptions plugin | nst | cheapest-to-audit diffs — the implant lives entirely in the small MIT plugin; ready-made "cancel silently fails" shape (webhook-dependent cancel). F1 note (2026-07-11): discourse-subscriptions is now bundled into Discourse core (standalone repo archived 2025-07-14; license still MIT) — the plugin directory remains the small implant surface, pinned via the core SHA |
| **Documenso** | nli★ | deletion-flow implants + textbook clean baseline (retention/anonymization messaging) |
| **Mastodon** | nli★ | gold-standard export/migration/delete baseline; degradation implants built *against* it |
| **Rocket.Chat** | nst nli | tier-asymmetric cancel parity; GDPR export + self-delete (heavy setup — later phase) |
| **Medusa / Saleor** | ndp nst | assemble-your-own commerce surfaces where a shape fits no packaged host |
| **Lago / Kill Bill** | nst (logic) | billing-*behavior* ground truth: auto-renew, trial conversion, proration, dunning as auditable code; Kill Bill is the clock reference implementation |
| Listmonk / Plausible / Keila / Formbricks | ndp nli | consent, unsubscribe-parity, churn-survey surfaces (Formbricks billing dir is EE — build outside it). F1 note (2026-07-11): listmonk, plausible, and formbricks proven as bench legs — the class's three distinct surfaces covered; **keila deferred** (its newsletter shapes duplicate listmonk's). Formbricks pins **v3.16.1**: pgvector is a hard DB requirement, and 5.x is a five-service rearchitecture with no published CE image past 3.16.1 at review time |

## 4. Lanes

- **Lane 1 — exhibit-derived re-implementations** (violating, real-anchored). For each documented-real anchor, re-implement the enforcement exhibit's flow into a host. Label basis: **enforcement-exhibit** — fidelity-to-exhibit at the record's date, not live truth; adjudicated/fined cases first, commitments-without-admission second (PROTOCOL §9). Supply ceilings: ~30 `nst` / ~54 `ndp` / ~13 `nli` (deletion side only).
- **Lane 2 — authored implants** (violating, synthetic). Fills the remaining violating floors and — decisively — the **zero-found-supply check shapes**: `nst` checks 5/6/7 (auto-renew consent, trial notice, reminders) and the entire `nli` export side, which no enforcement record anywhere documents. Label basis: **construction.** Gated by §6.1 indistinguishability.
- **Lane 3 — unmodified-baseline cleans** (construction). Every bench host's clean deploy is a clean fixture; census and windows recorded at labeling. For code cells, the unmodified source ships.
- **Lane 4 — first-party execution-verified cleans** (`nli`, live services). Rupp-method export/deletion probing on major services — execute, verify artifacts, confirm longitudinally. The strongest clean cell in the matrix; bound by real calendar windows, so it starts earliest (§9).
- **Lane 5 — E4 defeat lane** (the confirmed long pole, O-6). Conditional-serving fixture infrastructure — origin/timing/variant/detection switches in fixture config, with Honey's investigation-documented "selective standdown" as the realism template — plus the engine-side dual-origin, timing-varied probe infrastructure. Seven corpus shapes plus the red-team lane. Code-mode note carried from ATTAINABILITY §3.2: full-source submission makes conditional serving self-revealing, so this lane's weight is behavioral.
- **Lane 6 — mobile mini-track** (O-9, four shapes). Fleeceware-style paywall/trial-framing fixtures; store-mediated flows carry platform-scoped labels (the store's flow, not the vendor's web flow).

**Canaries:** every criterion's sealed canary subset is construction-only by design — placements (page text, markup, code comments, export artifacts, ToS) are recorded in the manifests of lane-2/3 fixtures that host them.

## 5. Coverage vs. the floors

Expected fill per measured cell, with the real-slice ceilings that get recorded at freeze so the real stratum cannot be retroactively overstated (PROTOCOL §7-report stratification; ATTAINABILITY §6):

| Cell | Floor | Violating fill | Clean fill | Real-anchored ceiling |
|---|---|---|---|---|
| `nst` × behavioral | ≥60V + ≥30C | L1 (~25–30) + L2 (incl. all check-5/6/7 shapes — found supply 0) | L3 + platform-mandate class (store-scoped labels) + remediation-verified | ~30 products |
| `nli` × behavioral | ≥60V + ≥30C | L1 deletion-side (~13) + L2 (export side 100% authored — real supply 0 worldwide) | **L4 execution-verified + L3** (strongest clean cell) | ~13 deletion / 0 export |
| `ndp` × behavioral | ≥60V + ≥30C | L1 (majority-real attainable) + L2 | L3 + own two-labeler inspection (**thinnest clean cell**) | ~54 products |
| `ndp` × code (×2 pools) | ≥60V + ≥30C, source ships | L2 ~90%+ + ~5 real specimens, **scored separately** | L3 unmodified hosts, source shipped | ~5 |
| all × canary subsets | per criterion | construction only | — | — |

Fixture inventory above the floors is what makes the §8 iteration folds possible (fold A / fold B per the burn discipline); headroom targets are a freeze-time sizing decision alongside §12.1–2.

## 6. QA gates (structure now; numerics at freeze)

1. **Indistinguishability (SusBench-style, pre-registered).** Blinded human evaluators are shown implant-host surfaces mixed with unmodified-host surfaces; an implant that evaluators can reliably pick out **fails fixture QA** and is rebuilt. This converts PROTOCOL §4.2's synthetic-variant external-validity caveat from an assumption into a measured property of our own fixture set, with peer-reviewed support for the method (SusBench, IUI 2026). Panel size and the distinguishability threshold are pinned at freeze.
2. **Exhibit fidelity (lane 1).** The re-implementation is checked against the enforcement exhibit (complaint figures, decision walkthroughs, archive captures) by someone other than the builder; the label claims fidelity-to-exhibit at the record's date.
3. **Construction verification.** A non-builder verifies each implant and baseline against its build spec before labeling (PROTOCOL §9, basis 2).
4. **Live re-verification at build time.** Any "still-live / remediated" supply claim this plan consumes is re-checked when the fixture is built (ATTAINABILITY §8's soft spots, including the Adobe order-entry status).
5. **Manifest completeness.** A fixture without a recorded census, window citations, time script, and label scope does not enter the sealed set.

**Build conventions (hardened by the sealed tranches, 2026-07-17 and 2026-07-22 — normative for every fixture):**

- **Out-of-band truth channels.** Fixture ground truth — the state that seals the answer key — is read from the harness side (host CLI, direct DB queries), never from self-describing state endpoints on the product's public surface. Verification scaffolding reachable by a probe is both a gate-1 tell (a probe can enumerate routes and find a self-confessing oracle) and harness-in-artifact contamination of the violation diff.
- **Non-vacuous assertions.** Every deciding-fact assertion in a proof script must be able to fail on a broken implant. Asserting a value the implant itself authors (an editorial `effect: none` field) is tautological and forbidden.
- **Claims match observations.** Transcripts state the evidence mode honestly: client-side mechanics established from served HTML/JS are code evidence, never claimed as observed browser behavior; time-crossing facts re-capture the rendered surface after the boundary, not only backend state.
- **Census substantiation.** A message sink's presence is not a census: each run enumerates and classifies what was actually emitted per observation window, or proves the sink empty. Multi-event runs census each event in its own before/after window.
- **Diff purity.** `diff_ref` carries only the implant; harness plumbing (mail rerouting, loaders, generated bytecode) lives outside the violation diff.
- **Manifest precision.** Time scripts are T0-relative advance/assert positions; version pins record the enforced image digests plus run-observed app versions; every claimed surface (payment, messaging) was exercised by the run or is stated as unexercised.
- **Empirical mutation checks.** Before a fixture is reported built, its proof runs against a *corrected* copy of the implant (scratch copy, isolated compose project): the flow must FAIL when the dark pattern is removed or repaired. Non-vacuity is demonstrated, not argued — and verification repeats the probe independently.
- **Site-scope negative censuses.** An absence deciding fact ("no self-service X exists") is proven at site scope — the served route surface is enumerated and each candidate asserted absent — never only at page scope. Link censuses on visited pages miss surfaces the proof never traverses.
- **Scaffold hygiene.** Any scaffold copied between fixtures is diffed against its source before self-check. Every served surface must appear in the fixture's census; a served surface the proof never visits is a defect even when all assertions pass.
- **Attestation-log automation.** Self-check attestations are emitted by the run pipeline at completion of the run they certify — never hand-written afterward or batch-stamped. An attestation whose timestamp precedes its evidence is a false record even if later validated.

## 7. §12.9 proposals (the freeze pins the numbers)

*Expanded to row grain at [`OBSERVATION-PARAMS.md`](OBSERVATION-PARAMS.md) (0.1.2) — the four stubs below remain as summaries; the row-level tables there are what the freeze pins.*

- **7.1 Window registry.** Every longitudinal fact class carries a pre-registered observation window, tabulated as a protocol appendix at freeze: trial-notice (8d-class), pause-resume (35d-class), deactivation-masquerade (60d), annual reminder (1y), grace windows (20–60d), residual messaging (9d+), export-link expiry (hours–days), deletion-confirmation windows. Fixture observation = clock-scripted exact positions; live observation = pre-registered wall-time windows priced into the cell's cost model. Every absence claim cites its window.
- **7.2 Surface-census definition.** Proposed censused set per fixture: all settings/account/billing surfaces; help/docs searched over a criterion keyword list; terms/privacy pages; footers; primary-nav sweep to a fixed depth; plus each SPEC §9's criterion-specific surfaces. Absence claims are scoped to the census; the census is recorded in the manifest (O-2). Keyword lists and sweep depth are pinned at freeze.
- **7.3 Rate-fact trials (O-4).** Structure: a per-fact table of trial count n and decision rule. In fixtures the rate is constructed, so n is chosen to detect the built rate with ≥99% probability; in live cells a pre-registered default n applies with the exact binomial bound reported alongside the claim. Proposed live default: n = 8; per-fact rules at freeze.
- **7.4 Vision-capable judging (O-7; binds §12.3).** Any pool measured on a cell containing rendered-appearance rows (`ui*`) must judge from rendered captures and its members must be vision-capable; a pool lacking the capability excludes those rows from its cells and the exclusion is disclosed per cell in the report.

## 8. Fixture manifest (schema sketch)

The per-fixture record — machine-readable, hashed into the sealed manifest at freeze; formalized against CRITERION-SPEC's manifest conventions before then:

```yaml
fixture_id:            # neutral, stable
host: {name, version_pin, license}
lane:                  # 1–6
diff_ref:              # implants: the violation diff (the whole claim)
labels:                # per criterion present
  - {criterion, version, expected_verdict, deciding_facts,
     basis: enforcement-exhibit|construction|execution-verified|inspection,
     basis_date, scope}
channels:              # ui/acct/pay/t:X/msg/sup/multi/org/net/art/terms/code
census:                # surfaces enumerated at labeling (7.2)
time_script:           # T0-relative advance/assert positions (2.1)
seed_spec:             # accounts, content volumes, histories, debt states
canaries:              # placements, if host to any
roles: {builders, labelers, verifiers}   # builder ≠ labeler
qa: {indistinguishability, fidelity, construction_check, live_recheck}
```

## 9. Sequencing

- **F0 — platform proof.** The four services stood up on two flagship hosts (Ghost for the `nst` shape, Documenso or Mastodon for the `nli` shape); the exit test is one fixture per host whose time script drives engine clock + app clock + sink jobs through a full trial-convert-cancel (resp. delete-confirm-window) cycle in minutes. F0 converts §2.1's tooling claims into working fact. **Done (2026-07-10, [`platform/`](../platform/)), three legs:** Kill Bill — full trial→convert→$29.95-charge→cancel-at-boundary on the engine clock, 39 virtual days in ~96 s, plugin invoice/payment mail in the sink; Documenso — real signup→verify→delete flow, +31 virtual days in seconds via the glibc sidecar, post-deletion absence window held, persona round-trip; Ghost + Stripe — sandbox test-clock script landing exact `frozen_time` at every position with forward-only enforced, Ghost member→sink flow 9/9; subscription lifecycle proven 9/9 after the key re-scope, and the **full webhook-driven billing coupling proven browserless 2026-07-16** (real Stripe events → Stripe CLI `listen` → Ghost member state, trial→convert→renewal→cancel, on SQLite + MySQL 8; hosted-Checkout card entry deferred — see the ghost leg README). Findings folded into §2.1–§2.2 (0.1.1); coupling into 0.1.6.
- **F1 — E2 bulk.** The volume phase: stateful single-sitting flows (80 of 152 public shapes are E2) across the bench, host-amortized. **Underway (2026-07-11)** — first two staged bench legs proven: listmonk (bulk seed, campaign→sink census, unsubscribe parity with per-address absence) and WooCommerce (132-product one-pass seed, plain-HTTP checkout E2, cron-flush-anchored absence, rung-3 clock). Build-machine disk model: staged rotation — digest-pinned images pruned between hosts, durable state bind-mounted outside the docker store. **First sealed fixture tranche completed 2026-07-17** on the WooCommerce leg through the full §6 cycle — build → non-builder verification (gates 2–5; gate 1 deferred to the freeze panel) → fix wave → independent delta re-verification → label; instances sealed per the standing order (build → QA → label → seal). The cycle's operational lessons are promoted above as §6 build conventions; gate-4 live re-checks at build upgraded two anchors' basis strength. **All staged violating tranches sealed 2026-07-22:** the Ghost legs (subscription-trap and consent shapes, including the persona and test-clock waves) and the Open SaaS leg completed the same cycle; across successive waves the verification gate's major-defect count fell to zero as each wave's caught defect class was promoted into the next wave's build conventions (the four 2026-07-22 additions above). The Open SaaS host leg was bench-proven the same day (browserless webhook-driven billing lifecycle with test-clock trial conversion and renewal; hosted-Checkout card entry honestly deferred — see the opensaas leg README). Next: lane-3 clean controls, then the gate-1 freeze panel.
- **F2 — E3.** Clock-dependent fixtures (44 shapes) — cheap once F0's clock works; mostly time scripts and messaging jobs.
- **F3 — E4 + red team.** Conditional serving and dual-origin probe infrastructure last, because both sides must exist to test either.
- **Parallel from day 0 — Lane 4.** Live `nli` execution-verified probing is calendar-bound (real deletion windows, real export SLAs); it starts before everything else and runs alongside.
- **Order to freeze:** build → QA → label → seal (manifest hash) → **freeze** (PROTOCOL §2) → run. The fold partition (§12.2) is computed on the sealed inventory at freeze.

## 10. Budget shape (dollars at freeze)

By the demand tier mix (E1 21 · E2 80 · E3 44 · E4 7, which the sealed set mirrors): **E2 flow engineering is the bulk cost** and is host-amortized; **E3 is mostly the one-time platform cost** (clock, sink, personas) plus per-fixture scripts; the **specialized spends** are the E4 lane, the `ndp` code cells' ~90-fixture source-shipping requirement, and QA labor (indistinguishability panels, two-labeler inspection); **Lane 4 costs calendar and accounts**, not engineering. Dollar figures are fixed at freeze on this shape.

## 11. Limitations

- Tooling claims (Stripe test-clock caps, Kill Bill test-mode clock, LD_PRELOAD fake time per host) are verified at documentation level as of 2026-07-09, not in-hand; F0 exists to retire exactly this risk before the bulk build.
- The plan prices the *public corpus's* fact-shapes; the sealed set is authored to those shapes, but its exact composition is a freeze-time artifact — §5 states expectations, not commitments.
- Live-lane calendar time is irreducible: annual-cycle facts are out of live reach within any reasonable study window (fixture-only, per O-1), and backend-truth facts remain fixture/enforcement-only (O-3) — both stated external-validity limits of the behavioral tier, carried into the report.

## 12. Changelog

- **0.1.8** (2026-07-22) — All staged violating tranches sealed through the full §6 gate cycle (the Ghost subscription-trap and consent legs, then the Open SaaS leg; instances sealed). Four further build conventions promoted to §6, each born as a defect class one wave's verification caught and the next wave's builds were required to prevent: **empirical mutation checks** (a proof must fail on a corrected implant — demonstrated on scratch copies by builders, repeated independently by verifiers), **site-scope negative censuses** (absence facts proven over the enumerated served route surface, not page-level link censuses — the class that caught served out-of-exhibit surfaces a proof never visited), **scaffold hygiene** (cross-fixture scaffold copies diffed against source; every served surface censused), and **attestation-log automation** (self-check lines emitted by the run pipeline at completion; batch-stamped attestations are false records even when later validated). Under these compounding conventions the per-wave major-defect count fell monotonically to zero across the tranche. The **Open SaaS host leg** was bench-proven (cold start, real SMTP capture, out-of-band DB truth, webhook-driven billing with test-clock conversion and renewal; hosted-Checkout entry and production-build parity honestly deferred — see the leg README). Gate-4 discipline extended with a characterization rule for interlocutory records: preliminary findings entered on an unopposed showing are recorded as within-tier corroboration with the posture stated, never as adjudication; consent-based interlocutory orders are posture only. No plan-structure changes.

- **0.1.7** (2026-07-17) — First sealed fixture tranche through the full §6 gate cycle (WooCommerce leg; instances sealed). Non-builder verification caught systemic proof-rigor defects that the builders' green self-reports missed — self-describing state endpoints on product surfaces (a gate-1 tell and harness-in-artifact contamination), tautological assertions that could not fail on a broken implant, transcript claims exceeding what the run observed, and unsubstantiated message censuses — all fixed and promoted to §6 as normative **build conventions** (out-of-band truth channels; non-vacuous assertions; claims-match-observations; census substantiation; diff purity; manifest precision). Gate-4 live re-checks at build upgraded two anchors' basis strength (one primary record newly readable via browser-UA retrieval; one target case closed with a final infringement notice mid-build) — gate 4 earning its keep. Builder≠verifier≠labeler independence held operationally across the cycle (two builder agents, an independent verifier lineage, coordinator labeling). No plan-structure changes.

- **0.1.6** (2026-07-16) — Ghost billing-coupling proven browserless (§2.3 payment spine): a real webhook-driven subscription lifecycle (Stripe CLI `listen` → Ghost `WEBHOOK_SECRET` local mode) mutates Ghost member state through trial→convert→renewal→cancel on **both SQLite and MySQL 8** (22/22 each); the member↔customer and product↔tier links are bootstrapped exactly as Checkout would, and the `checkout.session.completed` hosted-card entry is honestly **deferred** (Stripe has no faithful browserless completion API). §8's manifest sketch gains a validator (`platform/manifest/validate_fixture.py`) enforcing the shape plus the builder≠labeler/verifier independence rule. No plan-structure changes.

- **0.1.5** (2026-07-11) — §3 light-class row (Listmonk/Plausible/Keila/Formbricks): three of four proven as F1 bench legs covering the class's three distinct surfaces; keila deferred as duplicative of listmonk; Formbricks build constraints recorded (v3.16.1 pin — pgvector hard requirement, 5.x rearchitecture without a published CE image at review time). No plan-structure changes.

- **0.1.4** (2026-07-11) — §3 Discourse row: discourse-subscriptions is bundled into Discourse core (standalone repo archived 2025-07-14; still MIT; plugin dir remains the implant surface, pinned via the core SHA) — found during the F1 discourse leg and independently verified against the archived repo. No plan changes.

- **0.1.3** (2026-07-11) — F1 stage 1: first two bench legs proven (listmonk, WooCommerce — `platform/` F1 table). Findings folded: §2.2 gains the event-anchored absence-window rule (async/rate-limited senders make timer-closed windows a false-clean path); §3's WooCommerce row records the Subscriptions licensing constraint (paid plugin — license-or-stand-in decision at build). §9's F1 item marked underway. No plan-structure changes.

- **0.1.2** (2026-07-10) — §7's four proposal stubs expanded to row grain at [`OBSERVATION-PARAMS.md`](OBSERVATION-PARAMS.md) 0.1.0; pointer added. No plan changes.

- **0.1.1** (2026-07-10) — F0 executed and proven ([`platform/`](../platform/), the repo's first running code); findings folded back: §2.1 rung 1 gains the Stripe key-scope provisioning constraint and the Kill Bill bare-date/noon rule (both found empirically); rung 2 marked glibc-only with the musl-sidecar pattern; §2.2 gains the no-prune-during-absence-windows rule; §9's F0 item recorded done with per-leg results. No plan-structure changes.

- **0.1.0** (2026-07-09) — initial draft: design rules, the four-service platform (virtual clock with a per-host mechanism ladder, messaging capture with absence monitoring, state seeding + payment spine, scripted support personas), host-bench assignments, six lanes, coverage-vs-floors table with real-slice ceilings, QA gates (SusBench-style indistinguishability pre-registered), §12.9 parameter proposals (window registry, census definition, rate-fact trials, vision-capable pools), fixture-manifest schema sketch, F0–F3 sequencing, budget shape. Engine-clock tooling verified at documentation level 2026-07-09.
