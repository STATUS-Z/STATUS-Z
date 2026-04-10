
import asyncio
import io
import pathlib
import sys

from PIL import Image
from playwright.async_api import async_playwright

SVG = pathlib.Path("dark.svg").resolve()
CX, CY, SCALE = 930.0, 196.0, 0.62
BURST_R, BURST_W = 178, 46
DESIGNATOR_Y = 330.0

OUTER = (BURST_R + BURST_W / 2) * SCALE
INNER = (BURST_R - BURST_W / 2) * SCALE

SAMPLE_AT = [4.0, 24.0, 25.1, 25.4, 25.7, 26.0, 26.3, 27.5]

def bright_pct(img: Image.Image, box) -> float:
    x0, y0, x1, y1 = box
    px = img.load()
    n = b = 0
    for y in range(y0 * 2, y1 * 2, 2):
        for x in range(x0 * 2, x1 * 2, 2):
            r, g, bl = px[x, y]
            n += 1
            if 0.2126 * r + 0.7152 * g + 0.0722 * bl > 70:
                b += 1
    return b / max(n, 1) * 100

async def main() -> int:
    print("BURST GEOMETRY (banner units)")
    print(f"  band spans r {INNER:.1f} .. {OUTER:.1f}")
    print(f"  lowest reach  y = {CY + OUTER:.1f}")
    print(f"  designator    y = {DESIGNATOR_Y:.0f}")
    clearance = DESIGNATOR_Y - (CY + OUTER)
    print(f"  clearance     {clearance:+.1f} units")
    geom_ok = clearance > 4.0
    print(f"  verdict: {'clear' if geom_ok else 'TOO TIGHT'}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1100, "height": 640},
                                      device_scale_factor=2)
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(SVG.as_uri())

        rows = []
        last = 0.0
        for t in SAMPLE_AT:
            await page.wait_for_timeout(int((t - last) * 1000))
            last = t
            buf = await page.screenshot()
            img = Image.open(io.BytesIO(buf)).convert("RGB")
            desig = bright_pct(img, (884, 320, 976, 358))
            iris = bright_pct(img, (886, 152, 974, 240))
            rows.append((t, desig, iris))
            pathlib.Path("frames").mkdir(exist_ok=True)
            img.save(f"frames/b_{t:.1f}.png")

        await browser.close()

    print("MEASURED ACROSS THE BURST WINDOW")
    print(f"{'t (s)':>7}{'designator %':>15}{'iris %':>10}")
    for t, d, i in rows:
        print(f"{t:>7.1f}{d:>14.2f}%{i:>9.2f}%")

    desig_vals = [r[1] for r in rows]
    iris_vals = [r[2] for r in rows]
    d_lo, d_hi = min(desig_vals), max(desig_vals)
    i_lo, i_hi = min(iris_vals), max(iris_vals)

    print(f"\ndesignator range  {d_lo:.2f}% .. {d_hi:.2f}%   swing {d_hi-d_lo:.2f}pp")
    print(f"iris range        {i_lo:.2f}% .. {i_hi:.2f}%   swing {i_hi-i_lo:.2f}pp")
    if errors:
        print("\npage errors:")
        for e in errors[:5]:
            print("  " + e)

    ok = True
    if not geom_ok:
        print("\nFAIL: burst band within 4 units of the designator baseline")
        ok = False
    if d_hi - d_lo > 8:
        print(f"\nFAIL: designator swings {d_hi-d_lo:.1f}pp — the strobe is "
              f"visible over the text")
        ok = False
    if d_lo < 0.5:
        print("\nFAIL: designator unreadable at some sample")
        ok = False
    if i_lo < 1.0:
        print("\nFAIL: the banner eye underneath is no longer visible")
        ok = False
    if ok:
        print("\nPASS: burst contained, text stable, both eyes visible")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
