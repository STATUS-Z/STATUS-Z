
import pathlib
import re
import sys

src = pathlib.Path("dark.svg").read_text(encoding="utf-8")

have_d = set(re.findall(r'<(?:path|rect|circle|ellipse|line|polyline|polygon)\b[^>]*\bid="([^"]+)"', src))

problems: list[str] = []
checked = 0

def nums(seq: str) -> list[str]:
    return [p for p in re.split(r"[;\s]+", seq.strip()) if p]

for m in re.finditer(r"<animate(?:Transform|Motion)?\b([^>]*?)(/>|>)", src, re.S):
    blob = m.group(1)
    a = dict(re.findall(r'([\w:-]+)="([^"]*)"', blob))
    line = src[: m.start()].count("\n") + 1
    checked += 1

    mode = a.get("calcMode", "linear")

    if "values" in a and "keyTimes" in a:
        v, k = nums(a["values"]), nums(a["keyTimes"])
        if len(v) != len(k):
            problems.append(f"line {line}: {len(v)} values vs {len(k)} keyTimes")
        kf = [float(x) for x in k]
        if kf and abs(kf[0]) > 1e-9:
            problems.append(f"line {line}: keyTimes starts at {kf[0]}, must be 0")
        if kf and abs(kf[-1] - 1) > 1e-9:
            problems.append(f"line {line}: keyTimes ends at {kf[-1]}, must be 1")
        if any(b < a2 - 1e-9 for a2, b in zip(kf, kf[1:])):
            problems.append(f"line {line}: keyTimes not monotonic")

    if mode == "spline" and "keySplines" in a:
        s = [x for x in a["keySplines"].split(";") if x.strip()]
        n = len(nums(a["values"])) if "values" in a else None
        if n is not None and len(s) != n - 1:
            problems.append(f"line {line}: {len(s)} keySplines vs {n} values (need {n-1})")
        if "keyTimes" in a:
            ktn = len(nums(a["keyTimes"]))
            if len(s) != ktn - 1:
                problems.append(f"line {line}: {len(s)} keySplines vs {ktn} keyTimes (need {ktn-1})")
        for i, sp in enumerate(s):
            parts = sp.split()
            if len(parts) != 4:
                problems.append(f"line {line}: keySpline[{i}] has {len(parts)} numbers, need 4")
            else:
                for j in (0, 2):
                    val = float(parts[j])
                    if not -1e-9 <= val <= 1 + 1e-9:
                        problems.append(f"line {line}: keySpline[{i}] x{1 if j==0 else 2}={val} outside [0,1]")

    b = a.get("begin")
    if b:
        raw = b.strip()
        if ";" in raw:
            bad = [p for p in raw.split(";")
                   if p.strip() and not re.fullmatch(r"-?\d+(\.\d+)?s?", p.strip())]
            if bad:
                problems.append(f"line {line}: unparsed begin list entry {bad[0]!r}")
        elif not re.fullmatch(r"-?\d+(\.\d+)?s?", raw) and "." not in raw:
            problems.append(f"line {line}: unparsed begin={b!r}")

for m in re.finditer(r'<mpath\b[^>]*href="#([^"]+)"', src):
    if m.group(1) not in have_d:
        problems.append(f"mpath -> #{m.group(1)} has no drawable element")

for m in re.finditer(r"<animateMotion\b([^>]*)>(.*?)</animateMotion>", src, re.S):
    a, body = m.group(1), m.group(2)
    if "mpath" not in body and "path=" not in a:
        problems.append(f"line {src[:m.start()].count(chr(10))+1}: animateMotion with no path")

print(f"checked {checked} animations")
if problems:
    print(f"\n{len(problems)} problem(s):\n")
    for p in problems:
        print("  " + p)
    sys.exit(1)

import xml.etree.ElementTree as ET

try:
    ET.parse("dark.svg")
except ET.ParseError as e:
    print(f"\nXML PARSE ERROR: {e}")
    sys.exit(1)

opens = len(re.findall(r"<g\b", src))
closes = len(re.findall(r"</g>", src))
if opens != closes:
    print(f"\nTAG IMBALANCE: {opens} <g> vs {closes} </g>")
    sys.exit(1)

print("all animations valid, document parses")
