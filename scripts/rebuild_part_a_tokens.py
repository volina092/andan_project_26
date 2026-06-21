# -*- coding: utf-8 -*-
"""Пересборка books_tokens/ из усечённого books_clean/ (часть A)."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "corpus_metadata.csv"
CLEAN = ROOT / "books_clean"
TOKENS = ROOT / "books_tokens"

NON_LEX = re.compile(r"[^а-яёa-z\s]", re.IGNORECASE)


def clean_for_lexical(text: str) -> str:
    text = text.lower()
    text = NON_LEX.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = list(csv.DictReader(META.open(encoding="utf-8-sig")))
    counts: list[int] = []

    for row in rows:
        src = CLEAN / row["папка"] / row["имя_файла"]
        dst = TOKENS / row["папка"] / row["имя_файла"]
        text = clean_for_lexical(src.read_text(encoding="utf-8"))
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        counts.append(len(text.split()))

    print(f"Токенизировано: {len(rows)} файлов")
    print(f"tokens: min={min(counts)}, max={max(counts)}, median={sorted(counts)[len(counts)//2]}")


if __name__ == "__main__":
    main()
