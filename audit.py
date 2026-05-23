#!/usr/bin/env python3
"""
audit.py — flags possible duplicate stops in busdata.json.
Run after build.py. Heuristics over-flag on purpose: every pair below is a
*candidate* for a human to confirm, not an automatic merge. Confirmed pairs go
into SPELLING / ALIASES in build.py; false alarms get left alone.
"""
import json, re
from itertools import combinations

stops = [s["name"] for s in json.load(open("busdata.json"))["stops"]]
print(f"{len(stops)} stops\n")

def lev(a, b):
    if abs(len(a) - len(b)) > 3:
        return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

squash = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

print("=== near-identical spelling (edit distance <=2 on squashed form) ===")
print("    confirm each: same place -> add to SPELLING; different -> ignore\n")
sq = [(s, squash(s)) for s in stops]
shown = set()
hits = 0
for (a, sa), (b, sb) in combinations(sq, 2):
    d = 0 if sa == sb else lev(sa, sb)
    if d <= 2 and min(len(sa), len(sb)) >= 5:
        pair = tuple(sorted((a, b)))
        if pair not in shown:
            tag = "SAME squashed" if sa == sb else f"dist {d}"
            print(f"    {a:<26}  <->  {b:<26}  [{tag}]")
            shown.add(pair)
            hits += 1
print(f"\n  {hits} candidate pairs — most are false alarms; eyeball them.")
