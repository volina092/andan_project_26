# -*- coding: utf-8 -*-
"""Усечение books_dontsova_full_clean/ до одинаковой длины (часть B).

Лимит — **лексические токены** (как в R/lexical_tokenize.R), граница — целое предложение.

  python scripts/truncate_dontsova_full_clean.py
  python scripts/truncate_dontsova_full_clean.py --max-tokens 37000 --dry-run
  python scripts/truncate_dontsova_full_clean.py --only-compare

После усечения пересоберите tokens/lemmas для части B в Rmd.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "corpus_metadata_dontsova_full.csv"
CLEAN_DIR = ROOT / "books_dontsova_full_clean"

SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")
NON_LEX = re.compile(r"[^а-яёa-z\s]", re.IGNORECASE)


def clean_for_lexical(text: str) -> str:
    text = text.lower()
    text = NON_LEX.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def count_lexical_tokens(text: str) -> int:
    cleaned = clean_for_lexical(text)
    return len(cleaned.split()) if cleaned else 0


def truncate_text_sentence_tokens(text: str, max_tokens: int) -> str:
    sentences = [s.strip() for s in SENT_SPLIT.split(text.replace("\n", " ")) if s.strip()]
    chosen: list[str] = []
    count = 0

    for sentence in sentences:
        n = count_lexical_tokens(sentence)
        if not n:
            continue
        if count + n > max_tokens:
            break
        chosen.append(sentence)
        count += n

    return "\n".join(chosen)


def truncate_file(path: Path, max_tokens: int) -> tuple[int, int]:
    original = path.read_text(encoding="utf-8")
    before = count_lexical_tokens(original)

    if before <= max_tokens:
        return before, before

    new_text = truncate_text_sentence_tokens(original, max_tokens)
    if original.endswith("\n"):
        new_text += "\n"

    path.write_text(new_text, encoding="utf-8", newline="\n")
    after = count_lexical_tokens(new_text)
    return before, after


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Усечение books_dontsova_full_clean/ по лексическим токенам."
    )
    parser.add_argument("--max-tokens", type=int, default=37000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--only-compare",
        action="store_true",
        help="только строки с для_сравнения=да в метаданных",
    )
    args = parser.parse_args()

    if not META.exists():
        print(f"Нет метаданных: {META}", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(META.open(encoding="utf-8-sig")))
    if args.only_compare:
        rows = [r for r in rows if r.get("для_сравнения") == "да"]

    stats: list[tuple[str, str, int, int]] = []
    changed = 0

    for row in rows:
        path = CLEAN_DIR / Path(row["путь"])
        title = row["название"]
        if not path.exists():
            print(f"WARN: нет файла {path}")
            continue

        original = path.read_text(encoding="utf-8")
        before = count_lexical_tokens(original)

        if args.dry_run:
            if before <= args.max_tokens:
                after = before
            else:
                after = count_lexical_tokens(
                    truncate_text_sentence_tokens(original, args.max_tokens)
                )
            stats.append((row.get("series_code", ""), title, before, after))
            continue

        before, after = truncate_file(path, args.max_tokens)
        if after < before:
            changed += 1
        stats.append((row.get("series_code", ""), title, before, after))

    print(
        f"Корпус: {len(stats)} файлов, max = {args.max_tokens} токенов, "
        f"boundary = sentence"
    )
    if args.dry_run:
        print("(dry-run — файлы не изменены)")
    else:
        print(f"Усечено файлов: {changed}")

    stats.sort(key=lambda x: x[3])
    print("\nСамые короткие после усечения:")
    for code, title, before, after in stats[:5]:
        print(f"  {after:>6} tok | было {before:>6} | {code} | {title}")

    print("\nСамые длинные до усечения:")
    for code, title, before, after in sorted(stats, key=lambda x: x[2], reverse=True)[:5]:
        print(f"  {after:>6} tok | было {before:>6} | {code} | {title}")

    after_counts = [s[3] for s in stats]
    print(
        f"\nПосле: min={min(after_counts)}, max={max(after_counts)}, "
        f"median={sorted(after_counts)[len(after_counts)//2]}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
