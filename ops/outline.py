#!/usr/bin/env python3
"""Outline of a large Markdown file with current line ranges, layer by layer, so an agent reads only the lines it needs
(the owner's rule of layered indexes and small parts, 2026-10-25). For files that live sessions keep editing (exec
plans, specs, runbooks) this replaces splitting: nothing moves, line citations stay valid, the ranges are always current.

  python3 ops/outline.py FILE                  the top layer: headings, line ranges, size, number of sub-headings
  python3 ops/outline.py FILE --under "Task 22"  the layer below the heading that best matches the text
  python3 ops/outline.py FILE --under "Task 22" --under "Step 17"   one more layer down
  python3 ops/outline.py FILE --grep "Decision 21"  every heading containing the text, with its range
  python3 ops/outline.py FILE --show "Step 17"     the lines of that section, numbered, in one call
  python3 ops/outline.py FILE --under "Task 22" --show "Step 17"   the same, narrowed first

Then read only that range (Read with offset and limit, or `sed -n 'A,Bp' FILE`), or let --show print it: one call instead
of outline, grep and sed (measured 2026-10-25: 10% of an agent's calls were the 2nd or 3rd look-up step in the same file).
--show prints at most --max-lines lines (default 120) and names the rest. Headings inside code fences are ignored.
At most --max rows (default 60) are printed; a longer layer names the next level to drill into.
"""

import argparse
import re

HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
# plan steps and numbered bold items count as headings below ######: `- [ ] **Step 5: ...**` and `3. **Decision ...**`
STEP = re.compile(r"^- \[[ xX]\] \*\*(.+?)\*\*")
NUMBOLD = re.compile(r"^(\d+)\. \*\*(.+?)\*\*")


def headings(lines):
    out, fence = [], None
    for i, ln in enumerate(lines):
        m = FENCE.match(ln)
        if m:
            fence = None if fence == m.group(1) else (fence or m.group(1))
            continue
        if fence is None:
            h = HEAD.match(ln)
            if h:
                out.append([i, len(h.group(1)), h.group(2).strip(), None])
            elif st := STEP.match(ln):
                out.append([i, 7, st.group(1).strip(), None])
            elif nb := NUMBOLD.match(ln):
                out.append([i, 8, f"{nb.group(1)}. {nb.group(2).strip()}", None])
    for k, h in enumerate(out):  # end: the next heading of the same or a higher level
        h[3] = next((x[0] for x in out[k + 1 :] if x[1] <= h[1]), len(lines))
    return out


def row(h, lines, heads):
    i, lv, t, end = h
    kb = sum(len(x.encode()) for x in lines[i:end]) / 1024
    subs = sum(1 for x in heads if i < x[0] < end)
    mark = "#" * lv if lv <= 6 else ("- step" if lv == 7 else "  -")
    return f"{mark} {t[:110]}  [lines {i + 1}-{end}, {kb:.0f} KB{f', {subs} sub-headings' if subs else ''}]"


def layer(heads, lo, hi, base):
    """The shallowest level of headings strictly inside (lo, hi) deeper than base."""
    inner = [h for h in heads if lo <= h[0] < hi and h[1] > base]
    if not inner:
        return []
    top = min(h[1] for h in inner)
    return [h for h in inner if h[1] == top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--under", action="append", default=[])
    ap.add_argument("--grep")
    ap.add_argument("--show", help="print the section whose heading best matches the text, with line numbers")
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--max-lines", type=int, default=120, help="lines printed by --show before it stops")
    a = ap.parse_args()
    # split at "\n" only, as grep -n and sed count: str.splitlines also breaks at U+2028/U+2029 and friends
    with open(a.file, encoding="utf-8", errors="replace", newline="\n") as fh:
        lines = fh.readlines()
    heads = headings(lines)
    total = sum(len(x.encode()) for x in lines) / 1024
    print(f"{a.file}: {len(lines)} lines, {total:.0f} KB, {len(heads)} headings")
    if a.grep:
        hits = [h for h in heads if a.grep.lower() in h[2].lower()]
        for h in hits[: a.max]:
            print(row(h, lines, heads))
        if len(hits) > a.max:
            print(f"... {len(hits) - a.max} more; narrow the text")
        return
    lo, hi, base = 0, len(lines), 0
    for text in a.under:  # each --under narrows inside the previous one: --under "Task 22" --under "Step 17"
        t = text.lower()
        hits = [h for h in heads if lo <= h[0] < hi and h[1] > base and t in h[2].lower()]
        if not hits:
            raise SystemExit(f"no heading under lines {lo + 1}-{hi} contains {text!r}; try --grep")
        h = min(hits, key=lambda h: (not h[2].lower().startswith(t), h[1], h[0]))
        print("under: " + row(h, lines, heads))
        lo, hi, base = h[0] + 1, h[3], h[1]
    if a.show:  # the section itself, numbered like grep -n, so the lines can be cited
        t = a.show.lower()
        hits = [h for h in heads if lo - 1 <= h[0] < hi and t in h[2].lower()]
        if not hits:
            raise SystemExit(f"no heading under lines {lo + 1}-{hi} contains {a.show!r}; try --grep")
        h = min(hits, key=lambda h: (not h[2].lower().startswith(t), h[1], h[0]))
        print("show: " + row(h, lines, heads))
        end = min(h[3], h[0] + a.max_lines)
        for i in range(h[0], end):
            print(f"{i + 1}: {lines[i].rstrip(chr(10))}")
        if end < h[3]:
            print(
                f"... {h[3] - end} more lines ({end + 1}-{h[3]}); --show a sub-heading, a larger --max-lines, "
                f"or `sed -n '{end + 1},{h[3]}p'`"
            )
        return
    rows = layer(heads, lo, hi, base)
    while len(rows) == 1 and not a.under:  # one heading over the whole file (its title): go one layer down
        h = rows[0]
        print("in: " + row(h, lines, heads))
        lo, hi, base = h[0] + 1, h[3], h[1]
        rows = layer(heads, lo, hi, base)
    if not rows:
        print(f"no sub-headings; read lines {lo + 1}-{hi}")
        return
    if lo < rows[0][0]:
        print(f"(text before the first sub-heading: lines {lo + 1}-{rows[0][0]})")
    for h in rows[: a.max]:
        print(row(h, lines, heads))
    if len(rows) > a.max:
        print(f'... {len(rows) - a.max} more at this level; use --grep "<text>" or a larger --max')


if __name__ == "__main__":
    main()
