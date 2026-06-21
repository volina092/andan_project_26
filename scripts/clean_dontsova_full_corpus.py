# -*- coding: utf-8 -*-
"""Очистка полного корпуса Донцовой (часть B): аннотации, сноски, служебный шум.

Использует ту же логику, что R/clean_corpus.R.

  python scripts/clean_dontsova_full_corpus.py
  python scripts/clean_dontsova_full_corpus.py --force
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "corpus_metadata_dontsova_full.csv"
RAW_DIR = ROOT / "books_dontsova_full_corpora"
CLEAN_DIR = ROOT / "books_dontsova_full_clean"

PAGE_NUMBER = re.compile(r"^\d{1,3}$")
CHAPTER = re.compile(r"^(Глава|Эпилог|Пролог)\s*\d*$", re.IGNORECASE)
PUBLISHER = re.compile(r"©|ЛитРес|litres\.ru|Издательство|ISBN|www\.", re.IGNORECASE)
NOTES = re.compile(r"^notes\d*$", re.IGNORECASE)
FB2 = re.compile(r"fb2|Black Jack|создание fb2|издательского текста", re.IGNORECASE)
AUTHOR = re.compile(r"^Дарья\s+Д[Оо][Нн]цова\s*$", re.IGNORECASE)
FOOTNOTE_TAIL = re.compile(
    r"Прим\.\s*автора|автор из этических|совпадения случайны|^Примечания\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def is_blank(x: str) -> bool:
    return not x or not x.strip()


def trim(x: str) -> str:
    return x.strip()


def is_page_number_line(x: str) -> bool:
    return bool(PAGE_NUMBER.match(trim(x)))


def is_chapter_heading_line(x: str) -> bool:
    return bool(CHAPTER.match(trim(x)))


def is_publisher_noise(x: str) -> bool:
    return bool(PUBLISHER.search(x))


def is_notes_marker(x: str) -> bool:
    return bool(NOTES.match(trim(x)))


def is_fb2_noise(x: str) -> bool:
    return bool(FB2.search(x))


def is_dontsova_author_line(x: str) -> bool:
    return bool(AUTHOR.match(trim(x)))


def is_prose_line(x: str) -> bool:
    x = trim(x)
    if is_blank(x):
        return False
    if x == "* * *":
        return False
    if is_publisher_noise(x):
        return False
    if is_chapter_heading_line(x):
        return False
    if is_page_number_line(x):
        return False
    if is_notes_marker(x):
        return False
    return len(x) >= 50 and bool(re.search(r"[.!?…:;—]", x))


def count_chapter_headings_back(lines: list[str], from_idx: int) -> int:
    k = from_idx
    n_head = 0
    while k >= 0:
        x = trim(lines[k])
        if is_blank(x) or is_page_number_line(x):
            k -= 1
            continue
        if is_chapter_heading_line(x):
            n_head += 1
            k -= 1
        else:
            break
    return n_head


def adjust_start_for_chapter(lines: list[str], prose_idx: int) -> int:
    if prose_idx <= 0:
        return prose_idx

    j = prose_idx - 1
    while j >= 0:
        x = trim(lines[j])
        if is_blank(x) or is_page_number_line(x):
            j -= 1
            continue
        if is_chapter_heading_line(x) and count_chapter_headings_back(lines, j) == 1:
            return j
        break
    return prose_idx


def find_prose_start_from(
    lines: list[str], from_idx: int, after_author: bool = False
) -> int:
    n = len(lines)
    i = max(0, from_idx)

    while i < n:
        x = trim(lines[i])
        if is_blank(x) or is_fb2_noise(x) or is_page_number_line(x):
            i += 1
            continue
        if is_chapter_heading_line(x):
            if count_chapter_headings_back(lines, i) == 1:
                j = i + 1
                while j < n:
                    if is_prose_line(lines[j]):
                        return adjust_start_for_chapter(lines, j)
                    j += 1
            else:
                while i < n and is_chapter_heading_line(trim(lines[i])):
                    i += 1
                continue
        if is_prose_line(lines[i]) and not after_author:
            return adjust_start_for_chapter(lines, i)
        i += 1

    return max(0, from_idx)


def find_early_author_line(lines: list[str], max_line: int = 40) -> int | None:
    n = min(len(lines), max_line)
    for i in range(n):
        if is_dontsova_author_line(lines[i]):
            return i
    return None


def find_body_start(lines: list[str]) -> int:
    if not lines:
        return 0

    if trim(lines[0]) == "Annotation":
        i = 0
        while i < len(lines) and trim(lines[i]) != "* * *":
            i += 1
        return find_prose_start_from(lines, i + 1)

    author_idx = find_early_author_line(lines)
    if author_idx is not None:
        return find_prose_start_from(lines, author_idx + 1, after_author=True)

    return find_prose_start_from(lines, 0)


def find_body_end(lines: list[str], start: int) -> int:
    n = len(lines)
    if start >= n:
        return n - 1

    search_from = max(start, int(n * 0.82))
    tail_lines = lines[search_from:]

    footnote_hits = [
        i
        for i, line in enumerate(tail_lines)
        if FOOTNOTE_TAIL.search(line)
    ]

    if footnote_hits:
        cut_at = search_from + min(footnote_hits)
        while cut_at > start and is_blank(lines[cut_at]):
            cut_at -= 1
        return max(start, cut_at - 1)

    i = n - 1
    while i > start and is_blank(lines[i]):
        i -= 1

    while i > start:
        x = trim(lines[i])
        if is_page_number_line(x):
            j = i
            while j > start and (is_blank(lines[j]) or is_page_number_line(lines[j])):
                j -= 1
            if j < i and len(trim(lines[j])) < 120:
                i = j
                continue
        if is_notes_marker(x):
            i -= 1
            continue
        break

    return max(start, i)


def drop_noise_lines(lines: list[str]) -> list[str]:
    return [
        line
        for line in lines
        if not is_publisher_noise(line)
        and not is_notes_marker(line)
        and not is_page_number_line(line)
        and not is_fb2_noise(line)
    ]


def clean_text_lines(lines: list[str]) -> list[str]:
    if not lines:
        return []

    start = find_body_start(lines)
    end = find_body_end(lines, start)
    body = lines[start : end + 1]
    body = drop_noise_lines(body)
    body = [line for idx, line in enumerate(body) if not is_blank(line) or idx > 0]

    while body and is_blank(body[-1]):
        body.pop()

    return body


def clean_one_file(path_in: Path, path_out: Path) -> dict:
    text = path_in.read_text(encoding="utf-8")
    lines = text.splitlines()
    cleaned = clean_text_lines(lines)

    path_out.parent.mkdir(parents=True, exist_ok=True)
    path_out.write_text("\n".join(cleaned) + ("\n" if cleaned else ""), encoding="utf-8")

    return {
        "lines_in": len(lines),
        "lines_out": len(cleaned),
        "chars_in": sum(len(line) for line in lines),
        "chars_out": sum(len(line) for line in cleaned),
    }


def load_meta() -> list[dict]:
    with META.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    parser = argparse.ArgumentParser(description="Очистка books_dontsova_full_clean/")
    parser.add_argument("--force", action="store_true", help="перезаписать существующие файлы")
    args = parser.parse_args()

    if not META.exists():
        print(f"Нет метаданных: {META}", file=sys.stderr)
        return 1

    meta = load_meta()
    ok = 0
    skipped = 0

    for i, row in enumerate(meta, start=1):
        in_path = RAW_DIR / Path(row["путь_исходник"])
        out_path = CLEAN_DIR / Path(row["путь"])

        if not in_path.exists():
            print(f"Нет исходника: {in_path}", file=sys.stderr)
            return 1

        if not args.force and out_path.exists():
            skipped += 1
            continue

        if i == 1 or i % 25 == 0 or i == len(meta):
            print(f"Очистка {i}/{len(meta)}: {in_path.name}")

        clean_one_file(in_path, out_path)
        ok += 1

    print(f"Готово: обработано {ok}, пропущено {skipped} -> {CLEAN_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
