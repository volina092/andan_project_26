# -*- coding: utf-8 -*-
"""Таблица длин текстов части B: слова и токены (как в R/lexical_tokenize.R).

  python scripts/build_dontsova_full_length_table.py
"""

from __future__ import annotations

import csv
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "corpus_metadata_dontsova_full.csv"
CLEAN = ROOT / "books_dontsova_full_clean"
RAW = ROOT / "books_dontsova_full_corpora"
OUT = ROOT / "output" / "dontsova_full_clean_lengths.csv"

# Короткие повести/рассказы (~5–8 тыс. токенов), не полноценные романы серии.
SHORT_TEXT_IDS = {
    "viola_055",      # Балерина в бахилах
    "sergeeva_042",   # Секретное женское оружие
    "sergeeva_041",   # Рождественский кролик
    "podushkin_039",  # Подарок для бабушки
    "sergeeva_040",   # Белка с часами
    "evlampia_063",   # Ключ от денег
    "dasha_078",      # Настоящая рождественская сказка
    "dasha_079",      # Эскимос с Марса
}

# Не один роман / нет clean-файла / слишком короткий для stylo.
EXCLUDE_FROM_COMPARISON_IDS = SHORT_TEXT_IDS | {
    "podushkin_040",  # сборник «Книги 1–27»
    "sergeeva_002",   # Британец китайского производства (~13,5 тыс. токенов)
}

MIN_TOKENS_FOR_COMPARISON = 37_000

NON_LEX = re.compile(r"[^а-яёa-z\s]", re.IGNORECASE)


def clean_for_lexical(text: str) -> str:
    text = text.lower()
    text = NON_LEX.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def count_tokens(text: str) -> int:
    cleaned = clean_for_lexical(text)
    return len(cleaned.split()) if cleaned else 0


def count_words(text: str) -> int:
    return len(text.split()) if text.strip() else 0


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> Path:
    try:
        target = path
        with target.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return target
    except PermissionError:
        target = path.with_suffix(path.suffix + ".new")
        with target.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Файл занят, записано в: {target}")
        return target


def non_empty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)

    rows_out: list[dict] = []

    with META.open(encoding="utf-8-sig", newline="") as f:
        meta_rows = list(csv.DictReader(f))

    for row in meta_rows:
        raw_path = RAW / Path(row["путь_исходник"])
        clean_path = CLEAN / Path(row["путь"])

        raw_text = raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""
        clean_text = clean_path.read_text(encoding="utf-8") if clean_path.exists() else ""

        tokens_raw = count_tokens(raw_text)
        tokens_clean = count_tokens(clean_text)
        words_clean = count_words(clean_text)

        ratio = round(tokens_clean / tokens_raw, 3) if tokens_raw else None
        is_short = row["id"] in SHORT_TEXT_IDS
        # После умышленного усечения до 37k доля к сырому исходнику не признак поломки.
        damaged = tokens_clean == 0
        for_comparison = (
            row["id"] not in EXCLUDE_FROM_COMPARISON_IDS
            and tokens_clean >= MIN_TOKENS_FOR_COMPARISON
        )

        rows_out.append(
            {
                "id": row["id"],
                "series_code": row.get("series_code", ""),
                "серия": row.get("серия", ""),
                "название": row.get("название", ""),
                "год": row.get("год", ""),
                "имя_файла": row.get("имя_файла", ""),
                "путь_исходник": row.get("путь_исходник", ""),
                "путь_clean": row.get("путь", ""),
                "слова_clean": words_clean,
                "токены_clean": tokens_clean,
                "строки_clean": non_empty_lines(clean_text),
                "символы_clean": len(clean_text),
                "токены_исходник": tokens_raw,
                "доля_токенов_сохранено": ratio if ratio is not None else "",
                "короткий_текст": "да" if is_short else "",
                "для_сравнения": "да" if for_comparison else "",
                "повреждена_очисткой": "да" if damaged else "",
            }
        )

    rows_out.sort(key=lambda r: (r["токены_clean"], r["название"]))

    fieldnames = list(rows_out[0].keys()) if rows_out else []
    out_path = write_csv(OUT, fieldnames, rows_out)

    flags_by_id = {r["id"]: r for r in rows_out}
    meta_fieldnames = list(meta_rows[0].keys())
    for col in ("короткий_текст", "для_сравнения"):
        if col not in meta_fieldnames:
            meta_fieldnames.append(col)

    for row in meta_rows:
        flags = flags_by_id.get(row["id"], {})
        row["короткий_текст"] = flags.get("короткий_текст", "")
        row["для_сравнения"] = flags.get("для_сравнения", "")

    meta_path = write_csv(META, meta_fieldnames, meta_rows)

    damaged_rows = [r for r in rows_out if r["повреждена_очисткой"] == "да"]
    short_rows = [r for r in rows_out if r["короткий_текст"] == "да"]
    compare_rows = [r for r in rows_out if r["для_сравнения"] == "да"]
    tokens_clean = [r["токены_clean"] for r in rows_out]

    print(f"Записано: {out_path}")
    print(f"Метаданные: {meta_path}")
    print(f"Книг: {len(rows_out)}")
    print(
        "токены_clean: "
        f"min={min(tokens_clean)}, "
        f"median={int(statistics.median(tokens_clean))}, "
        f"max={max(tokens_clean)}"
    )
    print(f"Короткие тексты: {len(short_rows)}")
    print(f"Для сравнения (>= {MIN_TOKENS_FOR_COMPARISON} токенов): {len(compare_rows)}")
    print(f"Повреждённые / пустые: {len(damaged_rows)}")
    print()
    print("Короткие тексты (исключены из сравнения):")
    for r in sorted(short_rows, key=lambda x: x["токены_clean"]):
        print(f"  {r['токены_clean']:6d} tok | {r['series_code']} {r['название']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
