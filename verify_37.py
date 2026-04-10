
from __future__ import annotations

import asyncio
import pathlib
import re

from PIL import Image
from playwright.async_api import async_playwright

P = pathlib.Path("dark.svg")
s = P.read_text(encoding="utf-8")
URI = "file:///" + str(P.resolve()).replace("\\", "/")

print("=" * 70)
print("1. PHASE PERIOD")
print("=" * 70)
phases = re.findall(
    r'values="(0;0;1;1|0\.5;0\.5;1;1)"\s*\n\s*keyTimes="([^"]+)" dur="(\d+)s"', s)
print(f"  phase animations found: {len(phases)}")
for vals, kt, dur in phases:
    print(f"    values={vals:<14} keyTimes={kt:<22} dur={dur}s"
          + ("   flip at %.0fs" % (float(dur) * 0.5)))

print()
print("=" * 70)
print("2. GAZE VARIANTS")
print("=" * 70)
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

for axis, m in enumerate(re.finditer(r"<animateTransform\b([^>]*?)/>", tr, re.S)):
    a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
    values = a["values"].split(";")
    kts = [float(x) for x in a["keyTimes"].split(";")]
    spl = [x for x in a.get("keySplines", "").split(";") if x.strip()]
    comp = 0 if axis == 0 else 1
    mono = all(kts[i] < kts[i + 1] for i in range(len(kts) - 1))
    print(f"  axis {axis}  dur={a['dur']}  values={len(values)}  keyTimes={len(kts)}  "
          f"splines={len(spl)}  monotonic={mono}  splines==kt-1:{len(spl) == len(kts) - 1}")

    sigs = []
    for vi in range(3):
        lo, hi = vi / 3, (vi + 1) / 3
        idx = [i for i, t in enumerate(kts) if lo <= t < hi]
        dist = []
        for i in idx:
            try:
                v = float(values[i].split(",")[comp])
            except Exception:
                continue
            if not dist or abs(v - dist[-1]) > 1e-9:
                dist.append(v)
        sigs.append("".join("+" if v > 0 else "-" if v < 0 else "0" for v in dist))
    print(f"    three sign sequences distinct: {len(set(sigs)) == 3}")
    for vi, sg in enumerate(sigs):
        print(f"      slice {vi}: {len(sg)} refixations  {sg[:14]}")

async def rendered() -> None:
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": 1122, "height": 640}, device_scale_factor=2)
        await pg.goto(URI)
        await pg.wait_for_timeout(1800)
        await pg.evaluate("() => document.documentElement.pauseAnimations()")

        print()
        print("=" * 70)
        print("3. RENDERED PUPIL POSITION, MATCHED OFFSETS")
        print("=" * 70)
        for offset in (10.0, 22.0):
            cent = []
            for vi in range(3):
                t = offset + vi * 37.0
                await pg.evaluate("t => document.documentElement.setCurrentTime(t)", t)
                await pg.wait_for_timeout(160)
                p = pathlib.Path("frames") / f"v3_{offset}_{vi}.png"
                await pg.screenshot(path=str(p), clip={"x": 880, "y": 280, "width": 100, "height": 80})
                im = Image.open(p).convert("L")
                px = im.load()
                w, h = im.size
                sx = sy = n = 0
                for y in range(h):
                    for x in range(w):
                        if px[x, y] < 45:
                            sx += x
                            sy += y
                            n += 1
                cent.append((round(sx / n, 1), round(sy / n, 1)) if n else None)
            print(f"  offset {offset}: {cent}")
            print(f"    distinct: {len(set(cent))} of 3"
                  + ("   OK" if len(set(cent)) == 3 else "   <-- NOT DISTINCT"))

        print()
        print("=" * 70)
        print("4. OPACITY FLIP AT 37s")
        print("=" * 70)
        for t in (30.0, 36.9, 37.1, 60.0, 73.9, 74.1):
            await pg.evaluate("t => document.documentElement.setCurrentTime(t)", t)
            await pg.wait_for_timeout(140)
            op = await pg.evaluate("""() => {
                const g = document.querySelector('g[clip-path="url(#reveal-1)"]');
                const tr = document.querySelector('g[transform="translate(0 30.4)"]');
                return {
                    columns: g ? +getComputedStyle(g).opacity : -1,
                    transplant: tr ? +getComputedStyle(tr).opacity : -1,
                };
            }""")
            print(f"  t={t:>6.1f}  columns {op['columns']:.2f}   transplant {op['transplant']:.2f}")

        await b.close()

asyncio.run(rendered())
