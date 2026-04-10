
from __future__ import annotations

import collections
import pathlib
import re

P = pathlib.Path("dark.svg")
s = P.read_text(encoding="utf-8")

print("=" * 78)
print("1. DOCUMENT")
print("=" * 78)
m = re.search(r'viewBox="([^"]+)"', s)
print(f"  viewBox          {m.group(1) if m else '?'}")
print(f"  bytes            {len(s):,}")
print(f"  lines            {s.count(chr(10)):,}")

print()
print("=" * 78)
print("2. ELEMENT CENSUS (by tag)")
print("=" * 78)
tags = collections.Counter(re.findall(r"<([a-zA-Z][\w:-]*)\b", s))
ANIM = {"animate", "animateMotion", "animateTransform"}
for tag, n in sorted(tags.items(), key=lambda kv: -kv[1]):
    if tag in ANIM:
        continue
    print(f"  {tag:<18} {n:>6}")

print()
print("  animations:")
for tag in sorted(ANIM):
    print(f"  {tag:<18} {tags.get(tag, 0):>6}")

print()
print("=" * 78)
print("3. GROUPS (each a layer)")
print("=" * 78)
groups = []
for m in re.finditer(r"<g\b([^>]*)>", s):
    a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
    groups.append({
        "line": s[:m.start()].count("\n") + 1,
        "id": a.get("id", ""),
        "transform": a.get("transform", ""),
        "opacity": a.get("opacity", ""),
        "clip": a.get("clip-path", "").replace("url(#", "").replace(")", ""),
        "style": a.get("style", ""),
        "fill": a.get("fill", ""),
    })
print(f"  total <g> elements: {len(groups)}")
print()
print(f"  {'line':>6}  {'id':<16} {'clip':<16} {'op':<6} transform / style")
for g in groups:
    detail = g["transform"] or g["style"]
    if g["id"] or g["clip"] or g["opacity"] or detail:
        print(f"  {g['line']:>6}  {g['id'][:16]:<16} {g['clip'][:16]:<16} "
              f"{g['opacity'][:6]:<6} {detail[:42]}")

print()
print("=" * 78)
print("4. ANIMATIONS")
print("=" * 78)

anims = []
for m in re.finditer(
    r"<(animate|animateMotion|animateTransform)\b([^>]*?)(/>|>)",
    s,
):
    kind, attrs, _ = m.group(1), m.group(2), m.group(3)
    a = dict(re.findall(r'([\w:-]+)="([^"]*)"', attrs))
    anims.append({
        "kind": kind,
        "line": s[:m.start()].count("\n") + 1,
        "attr": a.get("attributeName", ""),
        "type": a.get("type", ""),
        "dur": a.get("dur", ""),
        "begin": a.get("begin", ""),
        "repeat": a.get("repeatCount", ""),
        "from": a.get("from", ""),
        "to": a.get("to", ""),
        "values": a.get("values", ""),
        "href": a.get("href", ""),
    })

print(f"  total animation elements: {len(anims)}")

dur = collections.Counter(x["dur"] for x in anims)
print()
print("  by duration:")
for d, n in sorted(dur.items(), key=lambda kv: -kv[1]):
    print(f"    {d or '(none)':<10} {n:>4}")

attr = collections.Counter(
    (x["kind"], x["attr"] or ("type=" + x["type"] if x["type"] else "")) for x in anims)
print()
print("  by kind and attribute:")
for (k, a), n in sorted(attr.items(), key=lambda kv: -kv[1]):
    print(f"    {k:<18} {a:<22} {n:>4}")

print()
print("  the period set (dur values, unique):")
per = sorted({float(x["dur"][:-1]) for x in anims
              if x["dur"].endswith("s") and x["dur"][:-1].replace(".", "").isdigit()})
print(f"    {per}")
