#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Consense
# Committed as-run for the panel-2026-07-06 evidence bundles (criteria/*/calibration/); paths assume the external kit layout described in criteria/ADJUDICATION.md.
"""Score adjudication response sheets against the private mappings.

Usage: python3 score.py /path/to/adjudications-dir
Expects <criterion>-1.csv and <criterion>-2.csv per criterion; mappings
are read from this kit directory. Computes the §7.1 metrics (Cohen's
kappa aggregate, exact-verdict agreement on boundary+adversarial pooled),
rater-vs-key diagnostics, and dumps every disagreement for analysis.
"""
import csv, pathlib, sys
from collections import Counter

KIT = pathlib.Path(__file__).parent
ADJ = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/home/user/chat/no-shit/adjudications")
CRITERIA = ["no-subscription-trap", "no-dark-patterns", "no-lock-in"]
VERDICTS = {"PASS", "CONDITIONAL", "FAIL", "INDETERMINATE"}

def read_sheet(path):
    out = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or not row[0].startswith("S") or not row[0][1:3].isdigit():
                continue
            sid = row[0].strip()
            verdict = (row[1] if len(row) > 1 else "").strip().upper()
            out[sid] = {
                "verdict": verdict,
                "failing": row[2].strip() if len(row) > 2 else "",
                "caveat": row[3].strip() if len(row) > 3 else "",
                "driver": row[4].strip() if len(row) > 4 else "",
                "underdet": row[5].strip() if len(row) > 5 else "",
                "diverge": row[6].strip() if len(row) > 6 else "",
                "notes": row[7].strip() if len(row) > 7 else "",
            }
    return out

def read_mapping(crit):
    out = {}
    with open(KIT / crit / "PRIVATE-mapping.csv", newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "neutral_id":
                continue
            out[row[0]] = {"example_id": row[1], "category": row[2], "expected": row[3], "checks": row[4]}
    return out

def kappa(pairs):
    n = len(pairs)
    if n == 0:
        return float("nan"), 0.0
    po = sum(1 for a, b in pairs if a == b) / n
    m1, m2 = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((m1[c] / n) * (m2[c] / n) for c in set(m1) | set(m2))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po

for crit in CRITERIA:
    r1 = read_sheet(ADJ / f"{crit}-1.csv")
    r2 = read_sheet(ADJ / f"{crit}-2.csv")
    mp = read_mapping(crit)
    sids = sorted(mp)
    covered = [s for s in sids if r1.get(s, {}).get("verdict") in VERDICTS and r2.get(s, {}).get("verdict") in VERDICTS]
    bad = [(s, r.get(s, {}).get("verdict")) for r in (r1, r2) for s in sids if r.get(s, {}).get("verdict") not in VERDICTS]

    pairs_all = [(r1[s]["verdict"], r2[s]["verdict"]) for s in covered]
    k_all, po_all = kappa(pairs_all)
    hard = [s for s in covered if mp[s]["category"] in ("boundary", "adversarial")]
    po_hard = sum(1 for s in hard if r1[s]["verdict"] == r2[s]["verdict"]) / len(hard) if hard else float("nan")

    key_ok1 = sum(1 for s in covered if r1[s]["verdict"] == mp[s]["expected"])
    key_ok2 = sum(1 for s in covered if r2[s]["verdict"] == mp[s]["expected"])
    both_against = [s for s in covered if r1[s]["verdict"] == r2[s]["verdict"] != mp[s]["expected"]]
    disagree = [s for s in covered if r1[s]["verdict"] != r2[s]["verdict"]]

    print(f"\n{'='*74}\n{crit}: n={len(sids)} covered={len(covered)} (corpus_covered={len(covered)/len(sids):.2f})")
    if bad:
        print(f"  UNPARSEABLE/MISSING verdicts: {bad}")
    print(f"  aggregate: exact={po_all:.3f} ({sum(1 for a,b in pairs_all if a==b)}/{len(pairs_all)})  Cohen's kappa={k_all:.3f}   [target >= 0.8]")
    print(f"  hard subset (boundary+adversarial, n={len(hard)}): exact={po_hard:.3f}   [target >= 0.80]")
    print(f"  vs authored key: rater1 {key_ok1}/{len(covered)}  rater2 {key_ok2}/{len(covered)}")
    if both_against:
        print(f"  BOTH-AGREE-AGAINST-KEY (suspect the key): ")
        for s in both_against:
            print(f"    {s} {mp[s]['example_id']} [{mp[s]['category']}] key={mp[s]['expected']} both={r1[s]['verdict']}")
    if disagree:
        print(f"  INTER-RATER DISAGREEMENTS ({len(disagree)}):")
        for s in disagree:
            m = mp[s]
            print(f"    {s} {m['example_id']} [{m['category']}] key={m['expected']} r1={r1[s]['verdict']} r2={r2[s]['verdict']}")
            for tag, r in (("r1", r1[s]), ("r2", r2[s])):
                blob = "; ".join(x for x in (r["failing"], r["caveat"], r["driver"], r["notes"]) if x)[:220]
                if blob:
                    print(f"      {tag}: {blob}")
    flags = [(s, tag, r[s]["underdet"] or r[s]["diverge"]) for s in covered for tag, r in (("r1", r1), ("r2", r2)) if r[s]["underdet"] or r[s]["diverge"]]
    if flags:
        print(f"  UNDERDETERMINED / DIVERGENCE flags ({len(flags)}):")
        for s, tag, txt in flags:
            print(f"    {s} {mp[s]['example_id']} [{tag}] {txt[:200]}")
