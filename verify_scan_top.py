
from __future__ import annotations

import asyncio
import pathlib

from PIL import Image, ImageChops
from playwright.async_api import async_playwright

URI = "file:///" + str(pathlib.Path("dark.svg").resolve()).replace("\\", "/")

async def main() -> None:
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": 1122, "height": 640}, device_scale_factor=2)
        await pg.goto(URI)
        await pg.wait_for_timeout(2000)

        print("root children in paint order (last few)")
        print("-" * 62)
        order = await pg.evaluate("""() => {
            const out = [];
            [...document.documentElement.children].forEach((el, i) => {
                const tag = el.tagName.toLowerCase();
                if (tag !== 'g' && tag !== 'rect') return;
                const txt = (el.textContent || '').trim().slice(0, 22);
                out.push({
                    i, tag,
                    rects: el.querySelectorAll('rect').length,
                    clip: (el.getAttribute('clip-path') || '').replace('url(#', '').replace(')', ''),
                    first: (el.firstElementChild?.tagName || '') + ' ' + txt,
                });
            });
            return out;
        }""")
        for o in order[-6:]:
            print(f"  node {o['i']:>2}  <{o['tag']}>  rects={o['rects']:>2}  clip={o['clip']:<16} "
                  f"{o['first'][:34]}")

        pos = await pg.evaluate("""() => {
            const kids = [...document.documentElement.children];
            const idxOf = (pred) => kids.findIndex(pred);
            const scan = idxOf(el => el.tagName === 'g' &&
                el.getAttribute('clip-path') === 'url(#panel-interior)' &&
                el.querySelectorAll('rect').length > 40);
            const text = idxOf(el => el.tagName === 'g' &&
                (el.getAttribute('clip-path') || '').startsWith('url(#reveal-'));
            const tri = idxOf(el => el.querySelector && el.querySelector('#eye-triangle'));
            return { scan, text, tri, total: kids.length };
        }""")
        print()
        print(f"  scanline bands node index : {pos['scan']}   (of {pos['total']})")
        print(f"  first text column index   : {pos['text']}")
        print(f"  scanlines after text      : {pos['scan'] > pos['text'] if pos['scan'] >= 0 and pos['text'] >= 0 else 'n/a'}")

        print()
        print("pixel test on a text row")
        print("-" * 62)
        clip = {"x": 70, "y": 180, "width": 460, "height": 26}
        await pg.evaluate("() => document.documentElement.pauseAnimations()")
        await pg.evaluate("() => document.documentElement.setCurrentTime(3.0)")
        await pg.wait_for_timeout(250)
        await pg.screenshot(path="frames/so_on.png", clip=clip)
        n = await pg.evaluate("""() => {
            let c = 0;
            for (const g of document.querySelectorAll('g[clip-path="url(#panel-interior)"]')) {
                if (g.querySelectorAll('rect').length > 40) { g.style.display = 'none'; c++; }
            }
            return c;
        }""")
        await pg.wait_for_timeout(250)
        await pg.screenshot(path="frames/so_off.png", clip=clip)
        print(f"  hid {n} scanline group(s)")

        a = Image.open("frames/so_on.png").convert("L")
        o = Image.open("frames/so_off.png").convert("L")
        pa, po = a.load(), o.load()
        w, h = a.size
        brighter = darker = 0
        for y in range(h):
            for x in range(w):
                d = pa[x, y] - po[x, y]
                if d > 3:
                    brighter += 1
                elif d < -3:
                    darker += 1
        print(f"  pixels brighter WITH scanlines: {brighter}")
        print(f"  pixels darker  WITH scanlines: {darker}")
        print(f"  net effect: {'scanlines ADD light over the text (on top)' if brighter > darker * 2 else 'inconclusive'}")

        await b.close()

asyncio.run(main())
