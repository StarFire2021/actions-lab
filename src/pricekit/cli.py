"""Command line interface.

Exists so the later labs have something that produces a file worth
uploading as an artifact and worth writing to a job summary.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from pricekit.core import summarize


def load_prices(path: Path) -> list[float]:
    """Read a CSV with a header row and a 'close' column."""
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "close" not in reader.fieldnames:
            raise ValueError("CSV must have a 'close' column")
        return [float(row["close"]) for row in reader]


def render_markdown(name: str, stats: dict[str, float]) -> str:
    lines = [
        f"## Summary for {name}",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Periods | {int(stats['count'])} |",
        f"| First | {stats['first']:.2f} |",
        f"| Last | {stats['last']:.2f} |",
        f"| Total return | {stats['total_return']:.2%} |",
        f"| Best period | {stats['best_period']:.2%} |",
        f"| Worst period | {stats['worst_period']:.2%} |",
        f"| Max drawdown | {stats['max_drawdown']:.2%} |",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pricekit")
    parser.add_argument("csv", type=Path, help="CSV file with a 'close' column")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        help="write the markdown report here instead of stdout",
    )
    args = parser.parse_args(argv)

    try:
        prices = load_prices(args.csv)
        report = render_markdown(args.csv.stem, summarize(prices))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report)
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
