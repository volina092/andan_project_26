# -*- coding: utf-8 -*-
"""Усечение books_clean/ до одинаковой длины (часть A, 40 текстов).

Сначала режет исходники в books_clean/, затем в Rmd пересоберите tokens и lemmas:
  tokenize_corpus()
  lemmatize_corpus(skip_existing = FALSE)

Пример:
  python scripts/truncate_clean_corpus.py
  python scripts/truncate_clean_corpus.py --max-words 27000 --boundary word
  python scripts/truncate_clean_corpus.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "corpus_metadata.csv"
CLEAN_DIR = ROOT / "books_clean"

SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def word_count_lines(lines: list[str]) -> int:
    return sum(len(line.split()) for line in lines if line.strip())


def truncate_lines_word(lines: list[str], max_words: int) -> list[str]:
    if max_words <= 0:
        return []

    out: list[str] = []
    count = 0

    for line in lines:
        if not line.strip():
            if count >= max_words:
                break
            out.append(line)
            continue

        words = line.split()
        if count + len(words) <= max_words:
            out.append(line)
            count += len(words)
        else:
            remaining = max_words - count
            if remaining > 0:
                out.append(" ".join(words[:remaining]))
            break

    while out and not out[-1].strip():
        out.pop()

    return out


def truncate_text_sentence(text: str, max_words: int) -> str:
    sentences = [s.strip() for s in SENT_SPLIT.split(text.replace("\n", " ")) if s.strip()]
    chosen: list[str] = []
    count = 0

    for sentence in sentences:
        n = len(sentence.split())
        if not n:
            continue
        if count + n > max_words:
            break
        chosen.append(sentence)
        count += n

    return "\n".join(chosen)


def truncate_file(path: Path, max_words: int, boundary: str) -> tuple[int, int]:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    before = word_count_lines(lines)

    if before <= max_words:
        return before, before

    if boundary == "word":
        new_lines = truncate_lines_word(lines, max_words)
        new_text = "\n".join(new_lines)
        if original.endswith("\n"):
            new_text += "\n"
    else:
        new_text = truncate_text_sentence(original, max_words)
        if original.endswith("\n"):
            new_text += "\n"

    path.write_text(new_text, encoding="utf-8", newline="\n")
    after = word_count_lines(new_text.splitlines())
    return before, after


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Усечение books_clean/ до max слов.")
    parser.add_argument("--max-words", type=int, default=27000)
    parser.add_argument(
        "--boundary",
        choices=("word", "sentence"),
        default="word",
        help="word — ровно max слов; sentence — целые предложения, сумма ≤ max",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not META.exists():
        raise SystemExit(f"Нет метаданных: {META}")

    rows = list(csv.DictReader(META.open(encoding="utf-8-sig")))
    stats: list[tuple[str, str, int, int]] = []

    for row in rows:
        path = CLEAN_DIR / row["папка"] / row["имя_файла"]
        title = row["название"]
        if not path.exists():
            print(f"WARN: нет файла {path}")
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        before = word_count_lines(lines)

        if args.dry_run:
            after = min(before, args.max_words) if args.boundary == "word" else before
            if args.boundary == "sentence" and before > args.max_words:
                after = word_count_lines(
                    truncate_text_sentence(path.read_text(encoding="utf-8"), args.max_words).splitlines()
                )
            stats.append((row["автор"], title, before, after))
            continue

        before, after = truncate_file(path, args.max_words, args.boundary)
        stats.append((row["автор"], title, before, after))

    print(f"Корпус: {len(stats)} файлов, max = {args.max_words}, boundary = {args.boundary}")
    if args.dry_run:
        print("(dry-run — файлы не изменены)")

    stats.sort(key=lambda x: x[3])
    print("\nСамые короткие после усечения:")
    for author, title, before, after in stats[:3]:
        print(f"  {after:>6} слов | было {before:>6} | {author} | {title}")

    print("\nСамые длинные до усечения:")
    for author, title, before, after in sorted(stats, key=lambda x: x[2], reverse=True)[:3]:
        print(f"  {after:>6} слов | было {before:>6} | {author} | {title}")

    after_counts = [s[3] for s in stats]
    print(
        f"\nПосле: min={min(after_counts)}, max={max(after_counts)}, "
        f"median={sorted(after_counts)[len(after_counts)//2]}"
    )

    if not args.dry_run:
        print("\nДальше в R: tokenize_corpus(); lemmatize_corpus(skip_existing = FALSE)")


if __name__ == "__main__":
    main()
