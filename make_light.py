
from __future__ import annotations

import pathlib
import re

from light_table import COLOR_MAP

dark = pathlib.Path("dark.svg").read_text(encoding="utf-8")

out = dark
for d, l in COLOR_MAP:
    out = re.sub(re.escape(d) + r"(?![0-9a-fA-F])", l, out)

leftover = [d for d, _ in COLOR_MAP
            if re.search(re.escape(d) + r"(?![0-9a-fA-F])", out)]
print("dark-only colours remaining in light: %d %s" % (len(leftover), leftover or ""))

pathlib.Path("light.svg").write_text(out, encoding="utf-8")
print("light.svg %d bytes (dark %d)" % (len(out), len(dark)))

def counts(s: str) -> dict[str, int]:
    return {
        "text": len(re.findall(r"<text\b", s)),
        "tspan": len(re.findall(r"<tspan\b", s)),
        "animate": len(re.findall(r"<animate\b", s)),
        "animateMotion": len(re.findall(r"<animateMotion\b", s)),
        "animateTransform": len(re.findall(r"<animateTransform\b", s)),
        "path": len(re.findall(r"<path\b", s)),
        "rect": len(re.findall(r"<rect\b", s)),
        "@font-face": len(re.findall(r"@font-face", s)),
    }

cd, cl = counts(dark), counts(out)
for k in cd:
    flag = "OK" if cd[k] == cl[k] else "MISMATCH"
    print("  %-15s dark %-4d light %-4d %s" % (k, cd[k], cl[k], flag))
