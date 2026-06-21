# -*- coding: utf-8 -*-
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "corpus_metadata_dontsova_full.csv"
CLEAN = ROOT / "books_dontsova_full_clean"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    rows = list(csv.DictReader(META.open(encoding="utf-8-sig")))
    meta_by_path = {r["путь"].replace("\\", "/"): r for r in rows}
    clean_paths = {p.relative_to(CLEAN).as_posix() for p in CLEAN.rglob("*.txt")}

    missing_files = sorted(set(meta_by_path) - clean_paths)
    orphan_files = sorted(clean_paths - set(meta_by_path))

    print(f"metadata: {len(rows)}, clean files: {len(clean_paths)}")
    print(f"\nВ метаданных, но нет файла ({len(missing_files)}):")
    for path in missing_files:
        r = meta_by_path[path]
        print(f"  {r.get('series_code', '')} | {r['название']} | {path}")

    print(f"\nФайл есть, но нет в метаданных ({len(orphan_files)}):")
    for path in orphan_files:
        print(f"  {path}")


if __name__ == "__main__":
    main()
