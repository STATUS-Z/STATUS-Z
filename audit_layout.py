
from __future__ import annotations

import pathlib
import re
import sys

FRAME_PAD = 34.0

def frame_from_viewbox(src: str) -> tuple[float, float, float, float]:
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', src)
    if not m:
        raise SystemExit("viewBox not found; cannot derive frame bounds")
    w, h = float(m.group(1)), float(m.group(2))
    return (FRAME_PAD, FRAME_PAD, w - FRAME_PAD, h - FRAME_PAD)

FRAME_X0, FRAME_Y0, FRAME_X1, FRAME_Y1 = 34.0, 34.0, 1256.0, 606.0

COLUMN_SPLIT = 289.5
LEFT_MAX = 499.0
RIGHT_MIN = 509.0
RIGHT_MAX = 1052.0

from columns import column_origins

EYE_BAND_Y0 = 60.0
EYE_BAND_Y1 = 600.0
EYE_BAND_X0 = 1060.0

ADV = 0.50

TEXT_RE = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')

def attrs(blob: str) -> dict[str, str]:
    return {k: v for k, v in ATTR_RE.findall(blob)}

def px(value: str | None, default: float = 0.0, em_base: float = 0.0) -> float:
    if not value:
        return default
    m = re.match(r"(-?[\d.]+)\s*(em|px|%)?", value.strip())
    if not m:
        return default
    n = float(m.group(1))
    unit = m.group(2) or ""
    if unit == "em":
        return n * em_base
    return n

def run_width(text: str, size: float, tracking: float) -> float:
    n = len(text)
    if n == 0:
        return 0.0
    return n * size * ADV + max(0, n - 1) * tracking

def inherited_sizes(src: str) -> dict[int, float]:
    out: dict[int, float] = {}
    stack: list[float] = [12.0]
    for m in re.finditer(r"<(/?)g\b([^>]*)>|<text\b([^>]*)>", src):
        closing, gattrs, tattrs = m.group(1), m.group(2), m.group(3)
        if gattrs is not None:
            if closing:
                if len(stack) > 1:
                    stack.pop()
            else:
                a = attrs(gattrs)
                stack.append(px(a.get("font-size"), stack[-1]))
        elif tattrs is not None:
            a = attrs(tattrs)
            out[m.start()] = px(a.get("font-size"), stack[-1])
    return out

def main() -> int:
    src = pathlib.Path("dark.svg").read_text(encoding="utf-8")

    global FRAME_X0, FRAME_Y0, FRAME_X1, FRAME_Y1
    FRAME_X0, FRAME_Y0, FRAME_X1, FRAME_Y1 = frame_from_viewbox(src)

    global COLUMN_SPLIT, RIGHT_MIN, LEFT_MAX
    _left, _right = column_origins(src)
    COLUMN_SPLIT = (_left + _right) / 2
    RIGHT_MIN = _right
    LEFT_MAX = round(_right - 10.0, 1)
    sizes = inherited_sizes(src)

    rows: list[tuple[float, float, float, float, str]] = []
    problems: list[str] = []

    for m in TEXT_RE.finditer(src):
        a = attrs(m.group(1))
        if "x" not in a or "y" not in a:
            continue
        inherited = sizes.get(m.start(), 12.0)

        inner = m.group(2)
        if "<tspan" in inner:
            tspans = re.findall(r'<tspan\b([^>]*)>(.*?)</tspan>', inner, re.S)
            cur_x = px(a.get("x"))
            cur_y = px(a.get("y"))
            size = px(a.get("font-size"), inherited)
            track = px(a.get("letter-spacing"), 0.0, em_base=size)
            for tb, ttext in tspans:
                ta = attrs(tb)
                if "x" in ta:
                    cur_x = px(ta["x"])
                if "dy" in ta:
                    cur_y += px(ta["dy"])
                if "dx" in ta:
                    cur_x += px(ta["dx"])
                t = re.sub(r"<[^>]+>", "", ttext).strip()
                if not t:
                    continue
                w = run_width(t, size, track)
                rows.append((cur_y, cur_x, cur_x + w, size, t))
            continue

        text = re.sub(r"<[^>]+>", "", inner).strip()
        if not text:
            continue

        if re.search(r'attributeName="x"', inner):
            continue

        x = px(a.get("x"))
        y = px(a.get("y"))
        size = px(a.get("font-size"), inherited)
        track = px(a.get("letter-spacing"), 0.0, em_base=size)
        w = run_width(text, size, track)
        rows.append((y, x, x + w, size, text))

    for y, x, x2, size, text in rows:
        if x2 > FRAME_X1 - 12:
            problems.append(
                f"OVERFLOWS FRAME  y={y:.0f} x2={x2:.0f} (max {FRAME_X1 - 12:.0f})  {text[:50]!r}"
            )
        if x < LEFT_MAX and x2 > LEFT_MAX:
            problems.append(
                f"CROSSES GUTTER   y={y:.0f} x={x:.0f}..{x2:.0f}  {text[:50]!r}"
            )
        if RIGHT_MIN - 4 <= x and x2 > RIGHT_MAX:
            in_header = y < 74.0
            if not in_header:
                problems.append(
                    f"RIGHT OVERFLOW   y={y:.0f} x2={x2:.0f} (max {RIGHT_MAX:.0f})  {text[:50]!r}"
                )

    def in_eye_band(r: tuple[float, float, float, float, str]) -> bool:
        y, x = r[0], r[1]
        return EYE_BAND_Y0 <= y <= EYE_BAND_Y1 and x >= EYE_BAND_X0

    left = sorted((r for r in rows if r[1] < COLUMN_SPLIT), key=lambda r: r[0])
    right = sorted((r for r in rows if r[1] >= COLUMN_SPLIT and not in_eye_band(r)), key=lambda r: r[0])

    def x_overlaps(a, b) -> bool:
        return a[1] < b[2] + 1.0 and b[1] < a[2] + 1.0

    for name, col in (("left", left), ("right", right)):
        for a, b in zip(col, col[1:]):
            gap = b[0] - a[0]
            need = max(a[3], b[3]) * 1.06
            if 0.4 < gap < need and x_overlaps(a, b):
                problems.append(
                    f"V-COLLIDE {name}  y={a[0]:.0f}->{b[0]:.0f} gap={gap:.1f} need={need:.1f}  "
                    f"{a[4][:24]!r} / {b[4][:24]!r}"
                )

    print(f"measured {len(rows)} runs ({len(left)} left, {len(right)} right)")
    if problems:
        print(f"\n{len(problems)} problem(s):\n")
        for p in problems:
            print("  " + p)
        return 1

    print("clean")
    if left:
        w = max(left, key=lambda r: r[2])
        print(f"  widest left : x2={w[2]:.0f} of {LEFT_MAX:.0f}   {w[4][:40]!r}")
    if right:
        w = max(right, key=lambda r: r[2])
        print(f"  widest right: x2={w[2]:.0f} of {RIGHT_MAX:.0f}   {w[4][:40]!r}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
