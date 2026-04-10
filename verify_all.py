
from __future__ import annotations

import math
import pathlib
import re

src = pathlib.Path("dark.svg").read_text(encoding="utf-8")

print("TASK 1  scanlines x2 -> x48, larger one kept")
bands = len(re.findall(r'from="-48" to="606"', src))
big = len(re.findall(r'<rect x="34" y="34" width="1054" height="48"', src))
print("        travelling bands: %d   (need 48)  %s" % (bands, "OK" if bands == 48 else "FAIL"))
print("        larger band kept: %d                %s" % (big, "OK" if big >= 1 else "FAIL"))

print("\nTASK 2  triangle + contents at 0.9x")
m = re.search(r'id="eye-triangle" d="M ([\d.]+) ([\d.]+) L ([\d.]+) ([\d.]+) L ([\d.]+) ([\d.]+) Z"', src)
ax, ay, bx, by, cx, cy = (float(g) for g in m.groups())
print("        path: apex (%.1f,%.1f) base y=%.1f corners %.1f..%.1f" % (ax, ay, by, cx, bx))
HEAD = [(930.0, 40.0), (1106.0, 336.0), (754.0, 336.0)]
exp = [(930 + (x - 930) * 0.9, 196 + (y - 196) * 0.9) for x, y in HEAD]
got = [(ax, ay), (bx, by), (cx, cy)]
dev = max(math.dist(e, g) for e, g in zip(exp, got))
print("        expected 0.9 of design: %s" % ["(%.1f,%.1f)" % p for p in exp])
print("        deviation from exact 0.9: %.2f units  %s" % (dev, "OK" if dev < 0.6 else "FAIL"))

for pat, label, want in (
    (r'translate\([\d.]+ [\d.]+\) scale\(0\.54\)', "lower eyes scale 0.54 (was 0.60)", 2),
    (r'translate\(930 196\) scale\(0\.9\)', "main eye wrapper scale 0.9", 1),
    (r'M930 59\.2 A41\.4 41\.4', "orbit r 46->41.4", 2),
):
    n = len(re.findall(pat, src))
    print("        %-34s %d sites  %s" % (label, n, "OK" if n >= want else "FAIL"))

print("\nTASK 3  terminal output weight parity")
TEXT_RE = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
items = []
for mm in TEXT_RE.finditer(src):
    a = dict(re.findall(r'([\w:-]+)="([^"]*)"', mm.group(1)))
    if "x" not in a or "y" not in a:
        continue
    y = float(a["y"])
    if y > 600:
        continue
    x = float(a["x"])
    size = float(a.get("font-size", 12.5))
    inner = mm.group(2)
    ts = re.findall(r'<tspan\b[^>]*dy="([\d.]+)"[^>]*>(.*?)</tspan>', inner, re.S)
    if ts:
        lines = [re.sub(r"<[^>]+>", "", t).strip() for _, t in ts]
        last = y + sum(float(d) for d, _ in ts)
    else:
        body = re.sub(r"<[^>]+>", "", inner).strip()
        if not body:
            continue
        lines = [body]
        last = y
    items.append(dict(x=x, y=y, last=last, size=size, n=len(lines), first=lines[0]))

spans, gaps, totals = [], [], []
for cx in (70.0, 570.0):
    col = sorted([i for i in items if abs(i["x"] - cx) < 1], key=lambda i: i["y"])
    cmds = [i for i in col if i["first"].startswith("$")]
    ends = []
    for k, c in enumerate(cmds):
        hi = cmds[k + 1]["y"] if k + 1 < len(cmds) else 1e9
        grp = [g for g in col if c["y"] <= g["y"] < hi]
        q = sum(g["n"] for g in grp if 12 <= g["size"] < 13)
        p = sum(g["n"] for g in grp if g["size"] == 11)
        totals.append(q + p)
        spans.append(max(g["last"] for g in grp) - (c["y"] - c["size"]))
        ends.append(max(g["last"] for g in grp))
    for k in range(len(cmds) - 1):
        gaps.append(cmds[k + 1]["y"] - ends[k])

print("        content lines per block: %s   %s"
      % (totals, "OK" if len(set(totals)) == 1 else "FAIL"))
print("        block spans:             %s   %s"
      % (["%.0f" % s for s in spans], "OK" if len(set(round(s) for s in spans)) == 1 else "FAIL"))
print("        inter-block gaps:        %s   %s"
      % (["%.0f" % g for g in gaps], "OK" if len(set(round(g) for g in gaps)) == 1 else "FAIL"))

print("\nTASK 5  Glass TTY VT220, embedded")
emb = "@font-face" in src and "Glass_TTY_VT220" not in src
face = "font-family: 'Glass TTY VT220';" in src
n_text = len(re.findall(r"<text\b", src))
n_stack = len(re.findall(r"Glass TTY VT220", src))
print("        @font-face present:      %s" % ("YES" if emb else "NO"))
print("        face declared:           %s" % ("YES" if face else "NO"))
print("        text elements:           %d" % n_text)
print("        carrying the stack:      %d   %s" % (n_stack - 1, "OK" if n_stack - 1 >= n_text else "FAIL"))

leftover = re.findall(r"scale\(0\.40\)", src)
print("\nSTALE  scale(0.40) occurrences remaining: %d" % len(leftover))
print("file %d bytes (%.2f MB)" % (len(src), len(src) / 1048576))
