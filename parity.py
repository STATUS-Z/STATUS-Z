
from __future__ import annotations

import pathlib
from columns import column_origins
import re

src = pathlib.Path("dark.svg").read_text(encoding="utf-8")
_L, _R = column_origins(src)
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
    ts = re.findall(r'<tspan\b[^>]*dy="([\d.]+)"[^>]*>(.*?)</tspan>', inner, re.S)
    if ts:
        lines = [re.sub(r"<[^>]+>", "", t).strip() for _, t in ts]
        dys = [float(d) for d, _ in ts]
        last = y + sum(dys)
    else:
        body = re.sub(r"<[^>]+>", "", inner).strip()
        if not body:
            continue
        lines = [body]
        last = y
    items.append(dict(x=x, y=y, last=last, size=size, n=len(lines), lines=lines))

ok = True
for cx, name in ((_L, "LEFT"), (_R, "RIGHT")):
    col = sorted([i for i in items if abs(i["x"] - cx) < 1], key=lambda i: i["y"])
    cmds = [i for i in col if i["lines"][0].startswith("$")]
    print("══ %s column ══" % name)
    ends = []
    for i, c in enumerate(cmds):
        hi = cmds[i + 1]["y"] if i + 1 < len(cmds) else 1e9
        grp = [g for g in col if c["y"] <= g["y"] < hi]
        q = sum(g["n"] for g in grp if 12 <= g["size"] < 13)
        p = sum(g["n"] for g in grp if g["size"] == 11)
        a = [g for g in grp if g["size"] < 10]
        top = c["y"] - c["size"]
        bot = max(g["last"] for g in grp)
        ends.append(bot)
        mark = ""
        if q + p != 6:
            mark = "  <-- MISMATCH"
            ok = False
        print("  %-29s %dQ + %dP = %d   attr=%s  span %3.0f..%3.0f (h=%3.0f)%s"
              % (c["lines"][0], q, p, q + p,
                 "y" if a else "NONE", top, bot, bot - top, mark))
    for i in range(len(cmds) - 1):
        print("    gap %.0f" % (cmds[i + 1]["y"] - ends[i]))
    print()

print("ALL BLOCKS 6 CONTENT LINES:", "YES" if ok else "NO")
