"""Render the last year of GitHub contributions as an SVG card for the README.

Usage: python3 contributions.py <github-user> <out.svg>

Reads the public calendar at https://github.com/users/<user>/contributions (the
same data as the graph on the profile page) and draws it in the README palette.
Uses only the standard library so the workflow needs no installs. If the page
cannot be parsed, it exits non-zero and leaves the existing SVG untouched.
"""
import re
import sys
import urllib.request
from datetime import date

CELL, GAP = 11, 3
STEP = CELL + GAP
PAD_X, PAD_TOP, PAD_BOTTOM = 25, 26, 22
LABEL_W = 30   # weekday labels
HEAD_H = 34    # title row
MONTH_H = 18   # month labels
LEGEND_H = 30

BG, BORDER = "#0B0B0B", "#232323"
GOLD, TEXT, DIM = "#D4AF37", "#ECECEC", "#8B8B8B"
LEVELS = ["#171717", "#4A3C16", "#7D6420", "#B08F2C", "#D4AF37"]
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def fetch(user):
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "profile-readme-contribution-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse(page):
    """Return ({date: level}, total) from the calendar HTML."""
    levels = {}
    for m in re.finditer(r"<td\b[^>]*\bdata-date=\"(\d{4}-\d{2}-\d{2})\"[^>]*>", page):
        lvl = re.search(r"\bdata-level=\"([0-4])\"", m.group(0))
        levels[date.fromisoformat(m.group(1))] = int(lvl.group(1)) if lvl else 0

    total = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", page)
    if total:
        total = int(total.group(1).replace(",", ""))
    else:
        counts = re.findall(r"<tool-tip\b[^>]*>\s*(\d+) contributions? on", page)
        total = sum(int(c) for c in counts)
    return levels, total


def render(levels, total):
    start = min(levels)
    start = date.fromordinal(start.toordinal() - (start.weekday() + 1) % 7)  # back to Sunday
    cols = (max(levels) - start).days // 7 + 1

    grid_x = PAD_X + LABEL_W
    grid_y = PAD_TOP + HEAD_H + MONTH_H
    width = grid_x + cols * STEP - GAP + PAD_X
    height = grid_y + 7 * STEP - GAP + LEGEND_H + PAD_BOTTOM

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
        f'<title id="title">{total} contributions in the last year</title>',
        f"<style>text{{font-family:{FONT};fill:{DIM};font-size:10px}}"
        f".h{{font-size:14px;font-weight:600;fill:{GOLD}}}.n{{font-size:12px}}</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<text class="h" x="{PAD_X}" y="{PAD_TOP + 10}">Contributions</text>',
        f'<text class="n" x="{width - PAD_X}" y="{PAD_TOP + 10}" text-anchor="end">'
        f"{total:,} in the last year</text>",
    ]

    # month labels where a new month starts, skipping ones that would collide
    last_col = -3
    for c in range(cols):
        first = date.fromordinal(start.toordinal() + 7 * c)
        prev = date.fromordinal(first.toordinal() - 7)
        if (c == 0 and first.day <= 7) or (c > 0 and first.month != prev.month):
            if c - last_col >= 3:
                out.append(f'<text x="{grid_x + c * STEP}" y="{grid_y - 7}">{MONTHS[first.month - 1]}</text>')
                last_col = c

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="{PAD_X}" y="{grid_y + row * STEP + 9}">{name}</text>')

    # cells, one group per week; weeks fade in left to right once
    for c in range(cols):
        cells = []
        for r in range(7):
            d = date.fromordinal(start.toordinal() + 7 * c + r)
            if d not in levels:
                continue
            cells.append(
                f'<rect x="{grid_x + c * STEP}" y="{grid_y + r * STEP}" width="{CELL}" height="{CELL}" '
                f'rx="2.5" fill="{LEVELS[levels[d]]}"/>'
            )
        if cells:
            t = 0.15 + c * 0.015
            out.append(
                f'<g><set attributeName="opacity" to="0" begin="0s" end="{t:.3f}s"/>'
                f'<animate attributeName="opacity" from="0" to="1" begin="{t:.3f}s" dur="0.35s"/>'
                + "".join(cells) + "</g>"
            )

    # legend
    ly = grid_y + 7 * STEP - GAP + 18
    lx = width - PAD_X - (5 * STEP - GAP) - 28
    out.append(f'<text x="{lx - 6}" y="{ly + 9}" text-anchor="end">Less</text>')
    for i, colour in enumerate(LEVELS):
        out.append(f'<rect x="{lx + i * STEP}" y="{ly}" width="{CELL}" height="{CELL}" rx="2.5" fill="{colour}"/>')
    out.append(f'<text x="{lx + 5 * STEP + 3}" y="{ly + 9}">More</text>')

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main(user, path):
    levels, total = parse(fetch(user))
    if len(levels) < 300:
        sys.exit(f"Only parsed {len(levels)} days; GitHub's page format may have changed. Leaving {path} as is.")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render(levels, total))
    print(f"Wrote {path}: {len(levels)} days, {total} contributions")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
