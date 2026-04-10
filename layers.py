
from __future__ import annotations

import collections
import pathlib
import re

s = pathlib.Path("dark.svg").read_text(encoding="utf-8")

HEAD = re.compile(r"<!--\s*(?:[─═]+\s*)?([A-Za-z][^\n]{0,70}?)(?:\s*[─═]+)?\s*(?:-->|\n)", re.M)

marks = []
for m in re.finditer(r"<!--\s*[─═]{2,}\s*([^\n]{1,70})", s):
    marks.append((m.start(), m.group(1).strip(" ─═-")))
for m in re.finditer(r"<!--\s{2,}([A-Z][A-Za-z ,]{4,60})\.\s", s):
    marks.append((m.start(), m.group(1).strip()))
marks = sorted({p: t for p, t in marks}.items())
if not marks:
    marks = [(0, "document")]

DRAW = ("path", "circle", "rect", "line", "text", "use", "ellipse", "tspan", "mpath")
ANIM = ("animate", "animateMotion", "animateTransform")

spans = []
for i, (pos, title) in enumerate(marks):
    end = marks[i + 1][0] if i + 1 < len(marks) else len(s)
    spans.append((title, pos, end))

print("=" * 78)
print("LAYER-BY-LAYER")
print("=" * 78)
rows = []
for title, a, b in spans:
    chunk = s[a:b]
    tags = collections.Counter()
    for t in DRAW + ANIM:
        n = len(re.findall(r"<%s\b" % t, chunk))
        if n:
            tags[t] = n
    if not tags:
        continue
    periods = collections.Counter()
    for m in re.finditer(r'dur="([\d.]+)s"', chunk):
        periods[m.group(1)] += 1
    rows.append((title, tags, periods))

for title, tags, periods in rows:
    total = sum(v for k, v in tags.items() if k in DRAW)
    anims = sum(v for k, v in tags.items() if k in ANIM)
    print(f"\n{title[:70]}")
    print(f"  drawable {total:>4}   animations {anims:>4}")
    if tags:
        print("  " + ", ".join(f"{k}×{v}" for k, v in sorted(tags.items(), key=lambda kv: -kv[1])))
    if periods:
        plist = sorted(periods.items(), key=lambda kv: float(kv[0]))
        print("  periods: " + ", ".join(f"{d}s×{n}" for d, n in plist))
