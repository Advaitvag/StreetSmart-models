"""Draw the Gantt view of Table 1 from Task_List_and_Project_Plan.md.

Reads the task rows and milestone rows of Table 1 and the short task names of
Table 2, so the figure never drifts from the tables. Re-run after any date change:

    python plan_gantt.py            # writes Plan_Gantt.svg next to this script
"""
import re
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
PLAN = HERE.parent / "Task_List_and_Project_Plan.md"
OUT = HERE / "Plan_Gantt.svg"

# Reference palette: categorical slots 1-3 (validated all-pairs, light mode).
OWNER_COLOR = {"Advait": "#2a78d6", "Raihan": "#eb6834", "Sahil": "#1baf7a"}
SURFACE, INK, INK_2, INK_3 = "#ffffff", "#0b0b0b", "#52514e", "#8a8984"
NO_WORK, PROTECTED, GRID = "#dcdad4", "#efeee9", "#e4e2dc"

# Calendar windows from §0 and Table 1.
NO_WORK_WINDOWS = [
    ("Thanksgiving", date(2026, 11, 26), date(2026, 11, 27)),
    ("Finals", date(2026, 12, 7), date(2026, 12, 11)),
    ("Holiday freeze", date(2026, 12, 24), date(2027, 1, 1)),
    ("MLK", date(2027, 1, 18), date(2027, 1, 18)),
    ("Spring break", date(2027, 3, 15), date(2027, 3, 19)),
]
PROTECTED_BLOCKS = [
    ("Protected", date(2026, 11, 30), date(2026, 12, 4)),
    ("Protected", date(2027, 2, 1), date(2027, 2, 5)),
    ("Protected", date(2027, 3, 8), date(2027, 3, 12)),
    ("Protected", date(2027, 4, 5), date(2027, 4, 16)),
]
MAJOR = {"M3", "M7", "M9", "M11"}

MONTHS = {"Oct": 10, "Nov": 11, "Dec": 12, "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4}


def parse_date(text):
    m = re.search(r"(Oct|Nov|Dec|Jan|Feb|Mar|Apr) (\d+)", text)
    month = MONTHS[m[1]]
    return date(2026 if month >= 8 else 2027, month, int(m[2]))


def section(text, start, end):
    return text[text.index(start):text.index(end)]


def load_plan():
    text = PLAN.read_text()
    table1 = section(text, "# 3. Table 1", "# 4. Table 2")
    table2 = section(text, "# 4. Table 2", "# 5. Work")
    short = {k: v.strip().replace("`", "") for k, v in re.findall(r"^\| (T\d\d) \| ([^|]+)\|", table2, re.M)}
    tasks = []
    for tid, rest in re.findall(r"^\| (T\d\d) \|(.*)$", table1, re.M):
        cells = [c.strip() for c in rest.split("|")]
        tasks.append(dict(
            id=tid, name=short[tid], owner=cells[1], start=parse_date(cells[2]),
            work_end=parse_date(cells[3]), half_day="(noon)" in cells[3],
            finish=parse_date(cells[5]), critical="★" in cells[7],
        ))
    milestones = [(mid, parse_date(d)) for mid, d in re.findall(
        r"^\| \*\*(M\d+)\*\* \|(?:[^|]*\|){5} \*\*([^*]+)\*\* \|", table1, re.M)]
    return tasks, milestones


def segments(start, end, from_start=False):
    """Split [start, end] (inclusive) into runs that skip the no-work windows.

    A run normally opens on a weekday; with from_start it opens on `start` itself,
    so a buffer that follows Friday's work does not show the weekend as a gap.
    """
    off = set()
    for _, a, b in NO_WORK_WINDOWS:
        d = a
        while d <= b:
            off.add(d)
            d += timedelta(1)
    runs, run_start, d = [], None, start
    while d <= end:
        if d in off:
            if run_start:
                runs.append((run_start, d))
                run_start = None
        elif run_start is None and (d.weekday() < 5 or (from_start and d == start)):
            run_start = d
        d += timedelta(1)
    if run_start:
        runs.append((run_start, end + timedelta(1)))
    return runs


def num(d):
    return matplotlib.dates.date2num(d)


def main():
    tasks, milestones = load_plan()
    # DejaVu Sans is the fallback for the ★ glyph.
    plt.rcParams.update({"font.family": ["Noto Sans", "DejaVu Sans"], "font.size": 7.5,
                         "svg.fonttype": "path"})
    fig, ax = plt.subplots(figsize=(10, 6.4))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    x0, x1 = date(2026, 10, 26), date(2027, 4, 19)
    n = len(tasks)
    ax.set_xlim(num(x0), num(x1))
    ax.set_ylim(n - 0.4, -1.6)

    # Calendar bands sit behind everything.
    for label, a, b in NO_WORK_WINDOWS + PROTECTED_BLOCKS:
        color = PROTECTED if label == "Protected" else NO_WORK
        ax.axvspan(num(a), num(b + timedelta(1)), color=color, lw=0, zorder=0)
        ax.text(num(a) + (num(b + timedelta(1)) - num(a)) / 2, n - 0.6, label, rotation=90,
                ha="center", va="bottom", fontsize=6, color=INK_2, zorder=1)

    # Month gridlines, recessive.
    m = date(2026, 11, 1)
    while m < x1:
        ax.axvline(num(m), color=GRID, lw=0.6, zorder=0.5)
        m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)

    bar_h = 0.56
    gap = 0.12  # ~2px surface gap between the work and buffer segments
    for i, t in enumerate(tasks):
        color = OWNER_COLOR[t["owner"]]
        buffer_start = t["work_end"] + timedelta(0 if t["half_day"] else 1)
        work = [(num(a), num(b)) for a, b in segments(t["start"], t["work_end"])]
        buffer = [(num(a), num(b)) for a, b in segments(buffer_start, t["finish"], from_start=True)]
        if t["half_day"]:  # "Jan 21 (noon)": work stops at midday and the buffer takes the afternoon
            work[-1] = (work[-1][0], work[-1][1] - 0.5)
            buffer[0] = (buffer[0][0] + 0.5, buffer[0][1])
        for a, b in work:
            ax.add_patch(Rectangle((a, i - bar_h / 2), b - a, bar_h,
                                   facecolor=color, lw=0, zorder=3))
        for a, b in buffer:
            ax.add_patch(Rectangle((a + gap, i - bar_h / 2), b - a - gap, bar_h,
                                   facecolor=color, alpha=0.32, lw=0, zorder=3))
        if t["critical"]:
            ax.add_patch(Rectangle((num(t["start"]), i - bar_h / 2 - 0.08),
                                   num(t["finish"] + timedelta(1)) - num(t["start"]), bar_h + 0.16,
                                   fill=False, ec=INK, lw=0.9, zorder=4))

    # Milestones: dashed line at the end of the milestone day, label above the plot.
    for mid, d in milestones:
        x = num(d + timedelta(1))
        major = mid in MAJOR
        ax.vlines(x, -0.7, n - 0.4, color=INK if major else INK_3, lw=0.9 if major else 0.6,
                  linestyles=[(0, (3, 2))], zorder=2)
        ax.text(x, -1.0, mid, ha="center", va="bottom", fontsize=7.5 if major else 7,
                fontweight="bold" if major else "normal", color=INK if major else INK_2)

    labels = [f"{'★ ' if t['critical'] else ''}{t['id']}  {t['name']}  ({t['owner']})" for t in tasks]
    ax.set_yticks(range(n), labels)
    for tick, t in zip(ax.get_yticklabels(), tasks):
        tick.set_color(INK)
        if t["critical"]:
            tick.set_fontweight("bold")
    ax.tick_params(axis="y", length=0, pad=6)

    ticks, d = [], date(2026, 11, 1)
    while d < x1:
        ticks.append(d)
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    ax.set_xticks([num(d) for d in ticks],
                  [d.strftime("%b %Y") if d.month == 1 or d == ticks[0] else d.strftime("%b") for d in ticks])
    ax.tick_params(axis="x", colors=INK_2, length=3, color=GRID)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK_3)

    handles = [Patch(facecolor=c, label=o) for o, c in OWNER_COLOR.items()]
    handles += [
        Patch(facecolor=OWNER_COLOR["Advait"], alpha=0.32, label="Buffer (lighter tint)"),
        Patch(facecolor="none", edgecolor=INK, lw=0.9, label="★ Critical path"),
        Line2D([], [], color=INK, lw=0.9, ls=(0, (3, 2)), label="Milestone (bold = major)"),
        Patch(facecolor=NO_WORK, label="No planned work"),
        Patch(facecolor=PROTECTED, label="Protected block"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=len(handles), frameon=False,
               fontsize=7, handlelength=1.4, columnspacing=1.2, labelcolor=INK_2,
               bbox_to_anchor=(0.5, 0.995))
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(OUT, facecolor=SURFACE)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
