# -*- coding: utf-8 -*-
"""Статистика длины текстов в books_dontsova_full_clean/."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "books_dontsova_full_clean"
META = ROOT / "corpus_metadata_dontsova_full.csv"


def main() -> None:
    meta_by_path: dict[str, dict] = {}
    if META.exists():
        with META.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                meta_by_path[row["путь"].replace("\\", "/")] = row

    rows: list[tuple[int, int, int, Path]] = []
    for path in sorted(CLEAN.rglob("*.txt")):
        text = path.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        words = len(text.split())
        chars = len(text)
        rows.append((words, len(lines), chars, path))

    rows.sort(key=lambda x: x[0])
    words_only = [r[0] for r in rows]
    sorted_words = sorted(words_only)

    print(f"Files: {len(rows)}")
    print(
        "Words: "
        f"min={min(words_only)}, "
        f"median={sorted_words[len(sorted_words) // 2]}, "
        f"mean={sum(words_only) / len(words_only):.0f}, "
        f"max={max(words_only)}"
    )
    print()
    print("Shortest 10 (words | lines | chars | file):")
    for w, ln, ch, path in rows[:10]:
        rel = path.relative_to(CLEAN).as_posix()
        meta = meta_by_path.get(rel, {})
        label = meta.get("название", path.stem)
        code = meta.get("series_code", "")
        prefix = f"{code} " if code else ""
        print(f"  {w:6d} | {ln:5d} | {ch:7d} | {prefix}{label} ({rel})")

    under_10k = [r for r in rows if r[0] < 10_000]
    if under_10k:
        print()
        print(f"Suspiciously short (<10000 words): {len(under_10k)} books")

    plausible = [r for r in rows if r[0] >= 10_000]
    if plausible:
        w, ln, ch, path = plausible[0]
        rel = path.relative_to(CLEAN).as_posix()
        meta = meta_by_path.get(rel, {})
        print()
        print(f"Shortest with >= 10000 words ({len(plausible)}/{len(rows)} books):")
        print(
            f"  {w} words | {ln} lines | {ch} chars | "
            f"{meta.get('series_code', '')} {meta.get('название', path.stem)} ({rel})"
        )


if __name__ == "__main__":
    main()
