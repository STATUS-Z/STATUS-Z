
import asyncio
import io
import pathlib
import sys

from PIL import Image
from playwright.async_api import async_playwright

SVG = pathlib.Path("dark.svg").resolve()
CX, CY = 930.0, 196.0
BANNER_IRIS = 44.0
SITE_IRIS = 46 * 0.62

def sample(img: Image.Image, r0: float, r1: float) -> tuple[float, float, float]:
    px = img.load()
    tot = [0.0, 0.0, 0.0]
    n = 0
    for y in range(int((CY - r1) * 2), int((CY + r1) * 2)):
        for x in range(int((CX - r1) * 2), int((CX + r1) * 2)):
            dx = x / 2 - CX
            dy = y / 2 - CY
            d = (dx * dx + dy * dy) ** 0.5
            if r0 <= d <= r1:
                p = px[x, y]
                tot[0] += p[0]
                tot[1] += p[1]
                tot[2] += p[2]
                n += 1
    if not n:
        return (0.0, 0.0, 0.0)
    return (tot[0] / n, tot[1] / n, tot[2] / n)

async def grab(hide: bool) -> Image.Image:
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1100, "height": 640}, device_scale_factor=2)
        await pg.goto(SVG.as_uri())
        await pg.wait_for_timeout(700)
        await pg.evaluate(
            """() => { const s=document.documentElement;
                       if(s.pauseAnimations) s.pauseAnimations();
                       if(s.setCurrentTime) s.setCurrentTime(6.0); }"""
        )
        if hide:
            ok = await pg.evaluate(
                """() => {
                    const g=[...document.querySelectorAll('g')]
                      .find(e=>(e.getAttribute('transform')||'').includes('scale(0.62)'));
                    if(!g) return false;
                    g.setAttribute('display','none');
                    return true;
                }"""
            )
            if not ok:
                raise SystemExit("site eye group not found")
        await pg.wait_for_timeout(160)
        buf = await pg.screenshot()
        await b.close()
    return Image.open(io.BytesIO(buf)).convert("RGB")

def main() -> int:
    shown = asyncio.run(grab(False))
    hidden = asyncio.run(grab(True))

    print(f"site iris r={SITE_IRIS:.1f}, banner iris r={BANNER_IRIS:.0f}")
    print()
    print("ANNUUS r=30..42 (banner iris only — site layer should not own this)")
    a = sample(shown, 30, 42)
    b = sample(hidden, 30, 42)
    print(f"  with site eye   rgb({a[0]:.0f}, {a[1]:.0f}, {a[2]:.0f})")
    print(f"  without         rgb({b[0]:.0f}, {b[1]:.0f}, {b[2]:.0f})")
    kept = (a[1] / b[1] * 100) if b[1] > 1 else 0
    print(f"  green channel retained  {kept:.0f}%")
    print()

    print("CORE r=0..25 (site iris owns this)")
    c = sample(shown, 0, 25)
    d = sample(hidden, 0, 25)
    print(f"  with site eye   rgb({c[0]:.0f}, {c[1]:.0f}, {c[2]:.0f})")
    print(f"  without         rgb({d[0]:.0f}, {d[1]:.0f}, {d[2]:.0f})")
    print()

    print("OUTER r=50..82 (banner sclera, site rings pass over)")
    e = sample(shown, 50, 82)
    f = sample(hidden, 50, 82)
    print(f"  with site eye   rgb({e[0]:.0f}, {e[1]:.0f}, {e[2]:.0f})")
    print(f"  without         rgb({f[0]:.0f}, {f[1]:.0f}, {f[2]:.0f})")

    magenta_present = a[0] > a[1] + 8
    print(f"\nbanner iris still magenta-tinted: {magenta_present} "
          f"(r={a[0]:.0f} vs g={a[1]:.0f})")

    ok = magenta_present and kept > 35
    print("PASS: both eyes read" if ok else
          "FAIL: the site eye has erased the banner eye")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
