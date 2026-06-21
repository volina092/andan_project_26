# -*- coding: utf-8 -*-
"""Перенос ручной очистки: books_doncova_full_handclean -> books_dontsova_full_clean."""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "corpus_metadata_dontsova_full.csv"
LENGTHS = ROOT / "output" / "dontsova_full_clean_lengths.csv"
HAND = ROOT / "books_doncova_full_handclean"
CLEAN = ROOT / "books_dontsova_full_clean"


def load_damaged_ids() -> set[str]:
    if not LENGTHS.exists():
        return set()
    with LENGTHS.open(encoding="utf-8-sig", newline="") as f:
        return {
            row["id"]
            for row in csv.DictReader(f)
            if row.get("повреждена_очисткой") == "да"
        }


def index_handclean() -> dict[str, Path]:
    by_source_name: dict[str, Path] = {}
    by_stem: dict[str, Path] = {}

    for path in HAND.rglob("*.txt"):
        by_source_name[path.name] = path
        by_stem[path.stem] = path

    return by_source_name, by_stem


def find_hand_file(
    row: dict,
    by_source_name: dict[str, Path],
    by_stem: dict[str, Path],
) -> Path | None:
    source_name = Path(row["путь_исходник"]).name
    if source_name in by_source_name:
        return by_source_name[source_name]

    title = row["название"]
    if f"{title}.txt" in by_source_name:
        return by_source_name[f"{title}.txt"]
    if title in by_stem:
        return by_stem[title]

    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    if not HAND.exists():
        print(f"Нет папки: {HAND}", file=sys.stderr)
        return 1

    damaged_ids = load_damaged_ids()
    by_source_name, by_stem = index_handclean()

    with META.open(encoding="utf-8-sig", newline="") as f:
        meta_rows = list(csv.DictReader(f))

    targets = [r for r in meta_rows if r["id"] in damaged_ids] if damaged_ids else []
    if not targets:
        print("Не найден список повреждённых книг — обрабатываю все файлы из handclean.")
        targets = meta_rows

    installed: list[tuple[str, Path, Path]] = []
    missing: list[str] = []
    unused = set(by_source_name.values())

    for row in meta_rows:
        if damaged_ids and row["id"] not in damaged_ids:
            continue

        src = find_hand_file(row, by_source_name, by_stem)
        if src is None:
            missing.append(f"{row['series_code']} {row['название']} ({row['путь_исходник']})")
            continue

        dst = CLEAN / Path(row["путь"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        installed.append((row["название"], src, dst))
        unused.discard(src)

    print(f"Скопировано в {CLEAN}: {len(installed)}")
    for title, src, dst in installed:
        print(f"  {src.relative_to(HAND)} -> {dst.relative_to(CLEAN)}")

    if missing:
        print(f"\nНе найдены в handclean ({len(missing)}):")
        for item in missing:
            print(f"  - {item}")
        return 1

    extra = sorted(unused)
    if extra:
        print(f"\nЛишние файлы в handclean ({len(extra)}):")
        for path in extra:
            print(f"  - {path.relative_to(HAND)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
