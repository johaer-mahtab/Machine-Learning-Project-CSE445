#!/usr/bin/env python3
"""Combine every raw CSV file in ``raw_data/`` into one CSV file.

Rows are copied as-is from each source file, except that ``post_id`` is
renumbered sequentially from 1 to the total number of combined rows. The
result is written to ``raw_data/combined_raw_data.csv``.

Usage:
    python support/combine_all_raw_csv_data.py

The output file is excluded from the inputs, so running the script again
replaces the previous combined file instead of duplicating its rows.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DATA_DIR = PROJECT_ROOT / "raw_data"
OUTPUT_FILENAME = "combined_raw_data.csv"


def find_input_files(raw_data_dir: Path, output_path: Path) -> list[Path]:
    """Return the CSV files to combine, sorted by name.

    The output file is skipped so that re-running the script does not
    combine previously combined data into itself.
    """
    files = sorted(
        (
            path
            for path in raw_data_dir.glob("*.csv")
            if path.resolve() != output_path.resolve()
        ),
        key=lambda path: path.name.lower(),
    )
    if not files:
        raise FileNotFoundError(f"No CSV files found in {raw_data_dir}")
    return files


def combine_csv_files(
    raw_data_dir: Path, output_path: Path
) -> tuple[list[tuple[Path, int]], int]:
    """Combine all CSVs in ``raw_data_dir`` into ``output_path``.

    Returns the per-file row counts and the total number of rows written.
    """
    input_files = find_input_files(raw_data_dir, output_path)

    fieldnames: list[str] | None = None
    combined_rows: list[dict[str, str]] = []
    file_counts: list[tuple[Path, int]] = []

    for path in input_files:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []

            if "post_id" not in headers:
                raise ValueError(f"{path.name}: missing required column 'post_id'")

            if fieldnames is None:
                # Keep post_id first while preserving the source column order.
                fieldnames = ["post_id"] + [
                    name for name in headers if name != "post_id"
                ]
            elif headers != fieldnames:
                raise ValueError(
                    f"{path.name}: columns do not match the other CSV files.\n"
                    f"  expected: {fieldnames}\n"
                    f"  found:    {headers}"
                )

            rows = [
                row
                for row in reader
                if any((value or "").strip() for value in row.values())
            ]

        combined_rows.extend(rows)
        file_counts.append((path, len(rows)))

    assert fieldnames is not None  # find_input_files guarantees at least one file

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(output_path.name + ".tmp")

    try:
        with temp_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fieldnames, extrasaction="ignore"
            )
            writer.writeheader()
            for new_post_id, row in enumerate(combined_rows, start=1):
                row["post_id"] = str(new_post_id)
                writer.writerow(row)
        temp_path.replace(output_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise

    return file_counts, len(combined_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine all raw CSV files into one CSV with sequential post IDs."
    )
    parser.add_argument(
        "--raw-data-dir",
        type=Path,
        default=DEFAULT_RAW_DATA_DIR,
        help=f"Directory containing the raw CSV files (default: {DEFAULT_RAW_DATA_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Path for the combined CSV "
            f"(default: <raw-data-dir>/{OUTPUT_FILENAME})"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_data_dir: Path = args.raw_data_dir.resolve()
    output_path: Path = (
        args.output.resolve()
        if args.output is not None
        else raw_data_dir / OUTPUT_FILENAME
    )

    try:
        file_counts, total = combine_csv_files(raw_data_dir, output_path)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for path, count in file_counts:
        print(f"  {path.name}: {count} rows")
    print(f"Combined {len(file_counts)} files ({total} rows) into {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
