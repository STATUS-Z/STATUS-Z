
from __future__ import annotations

import pathlib
from columns import column_origins
import re

ADV = 0.50
src = pathlib.Path("dark.svg").read_text(encoding="utf-8")
TEXT_RE = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)

items = []
for m in TEXT_RE.finditer(src):
    a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
    if "x" not in a or "y" not in a:
        continue
    y = float(a["y"])
    if y > 600:
        continue
    x = float(a["x"])
    size = float(a.get("font-size", 12.5))
    inner = m.group(2)
    ts = re.findall(r'<tspan\b[^>]*>(.*?)</tspan>', inner, re.S)
    lines = [re.sub(r"<[^>]+>", "", t).strip() for t in ts]
    if not lines:
        body = re.sub(r"<[^>]+>", "", inner).strip()
        lines = [body] if body else []
    lines = [l for l in lines if l]
    if not lines:
        continue
    items.append(dict(x=x, y=y, size=size, lines=lines))

print("%-10s %6s %6s %9s %9s %9s" %
      ("block", "lines", "chars", "ink-em", "widest", "fill%"))
print("-" * 56)

rows = []
for cx in column_origins(src):
    col = sorted([i for i in items if abs(i["x"] - cx) < 1], key=lambda i: i["y"])
    cmds = [i for i in col if i["lines"][0].startswith("$")]
    for k, c in enumerate(cmds):
        hi = cmds[k + 1]["y"] if k + 1 < len(cmds) else 1e9
        grp = [g for g in col if c["y"] <= g["y"] < hi]
        nlines = sum(len(g["lines"]) for g in grp)
        chars = sum(len(l) for g in grp for l in g["lines"])
        inkem = sum(len(l) * g["size"] for g in grp for l in g["lines"])
        widest = max(len(l) * g["size"] * ADV for g in grp for l in g["lines"])
        fill = widest / (486.0 if cx == 70 else 482.0) * 100
        rows.append((c["lines"][0][:28], nlines, chars, inkem, widest, fill))

for r in rows:
    print("%-10s %6d %6d %9.0f %9.0f %8.0f%%" % (r[0][:10], r[1], r[2], r[3], r[4], r[5]))

print()
for label, idx in (("lines", 1), ("chars", 2), ("ink-em", 3)):
    vals = [r[idx] for r in rows]
    spread = (max(vals) / min(vals) - 1) * 100
    print("%-8s min %-6.0f max %-6.0f spread %5.1f%%   %s"
          % (label, min(vals), max(vals), spread,
             "BALANCED" if spread < 12 else "UNEVEN"))
