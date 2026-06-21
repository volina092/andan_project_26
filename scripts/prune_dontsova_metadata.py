# -*- coding: utf-8 -*-
"""Удалить из corpus_metadata_dontsova_full.csv строки без clean-файла."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "corpus_metadata_dontsova_full.csv"
CLEAN = ROOT / "books_dontsova_full_clean"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    rows = list(csv.DictReader(META.open(encoding="utf-8-sig")))
    kept: list[dict] = []
    removed: list[dict] = []

    for row in rows:
        path = CLEAN / Path(row["путь"])
        if path.exists():
            kept.append(row)
        else:
            removed.append(row)

    with META.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(kept)

    print(f"Было: {len(rows)}, осталось: {len(kept)}, удалено: {len(removed)}")
    for row in removed:
        print(f"  - {row.get('series_code', '')} {row['название']} | {row['путь']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
