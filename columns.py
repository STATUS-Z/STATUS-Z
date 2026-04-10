
from __future__ import annotations

import pathlib
import re

def column_origins(svg_text: str) -> tuple[float, float]:
    xs = set()
    for m in re.finditer(r'<text x="([\d.]+)"[^>]*font-size="13"[^>]*>\$ ', svg_text):
        xs.add(float(m.group(1)))
    if len(xs) != 2:
        raise SystemExit("expected 2 column origins, found %s" % sorted(xs))
    return tuple(sorted(xs))

if __name__ == "__main__":
    s = pathlib.Path("dark.svg").read_text(encoding="utf-8")
    left, right = column_origins(s)
    print("left column  x=%.1f" % left)
    print("right column x=%.1f" % right)
    print("split        x=%.1f" % ((left + right) / 2))
