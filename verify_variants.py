
from __future__ import annotations

import pathlib
import re

s = pathlib.Path("dark.svg").read_text(encoding="utf-8")

ti = s.index('<g id="transplant"')
depth, k = 0, ti
while k < len(s):
    if s.startswith("<g ", k) or s.startswith("<g>", k):
        depth += 1
    elif s.startswith("</g>", k):
        depth -= 1
        if depth == 0:
            break
    k += 1
tr = s[ti:k + 4]

ANIM = list(re.finditer(r"<animateTransform\b([^>]*?)/>", tr, re.S))
assert len(ANIM) == 2

for axis, m in enumerate(ANIM):
    a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
    values = a["values"].split(";")
    kts = [float(x) for x in a["keyTimes"].split(";")]
    spl = [x for x in a.get("keySplines", "").split(";") if x.strip()]
    comp = 0 if axis == 0 else 1

    print(f"axis {axis}  dur={a['dur']}  values={len(values)}  keyTimes={len(kts)}  "
          f"keySplines={len(spl)}")

    ok_spl = len(spl) == len(kts) - 1
    print(f"  keySplines == keyTimes-1 : {ok_spl}")

    mono = all(kts[i] < kts[i + 1] for i in range(len(kts) - 1))
    print(f"  keyTimes strictly increasing : {mono}")
    if not mono:
        bad = [i for i in range(len(kts) - 1) if kts[i] >= kts[i + 1]][:3]
        print(f"    first offenders at index {bad}: "
              f"{[(kts[i], kts[i+1]) for i in bad]}")

    print(f"  {'slice':>6} {'refix':>7} {'signs':>7}  first 16 signs")
    sigs = []
    for vi in range(4):
        lo, hi = vi / 4, (vi + 1) / 4
        idx = [i for i, t in enumerate(kts) if lo <= t < hi]
        amps = []
        for i in idx:
            try:
                amps.append(float(values[i].split(",")[comp]))
            except Exception:
                pass
        dist = []
        for v in amps:
            if not dist or abs(v - dist[-1]) > 1e-9:
                dist.append(v)
        sg = "".join("+" if v > 0 else "-" if v < 0 else "0" for v in dist)
        sigs.append(sg)
        print(f"  {vi:>6} {len(dist):>7} {len(sg):>7}  {sg[:16]}")

    print(f"  all four sign sequences distinct : {len(set(sigs)) == 4}")

    def mags_at(vi):
        lo, hi = vi / 4, (vi + 1) / 4
        out = []
        for i, t in enumerate(kts):
            if lo <= t < hi:
                try:
                    out.append(round(abs(float(values[i].split(",")[comp])), 2))
                except Exception:
                    pass
        d = []
        for v in out:
            if not d or v != d[-1]:
                d.append(v)
        return d

    m0 = mags_at(0)
    same = all(mags_at(vi) == m0 for vi in range(1, 4))
    print(f"  magnitudes identical across slices : {same}")
    print()
