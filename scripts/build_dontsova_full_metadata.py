# -*- coding: utf-8 -*-
"""Сканирует books_dontsova_full_corpora/ и создаёт corpus_metadata_dontsova_full.csv."""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "books_dontsova_full_corpora"
OUT_CSV = ROOT / "corpus_metadata_dontsova_full.csv"
OUT_CSV_FALLBACK = ROOT / "corpus_metadata_dontsova_full.new.csv"
MAIN_META = ROOT / "corpus_metadata.csv"
XLSX = ROOT / "АнДан корпус СПИСОК ПРОИЗВЕДЕНИЙ по авторам.xlsx"

SERIES_FOLDERS = {
    "txt ВиолаТараканова": ("viola", "Виола Тараканова", "ВТ"),
    "txt ДашаВасильева": ("dasha", "Даша Васильева", "ДВ"),
    "txt ЕвлампияРоманова": ("evlampia", "Евлампия Романова", "ЕР"),
    "txt ИванПодушкин": ("podushkin", "Иван Подушкин", "ИП"),
    "txt СтепанидаКозлова": ("kozlova", "Степанида Козлова", "СК"),
    "txt ТатьянаСергеева": ("sergeeva", "Татьяна Сергеева", "ТС"),
}

FORBIDDEN_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
YEAR_IN_TITLE_RE = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")

# тексты-сборники / не один автор — не включаются в CSV
SKIP_SOURCE_TITLE_KEYS = {
    "кекс от сапожника",
}

# сборники / дубликаты, которых нет на FantLab как отдельных книг
MANUAL_YEARS: dict[tuple[str, str], int] = {
    ("ДВ", "темное прошлое конька горбунка сборник"): 2010,
    ("ИП", "цикл джентльмен сыска иван подушкин книги 1 27"): 2002,
}


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = s.replace("ё", "е")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def parse_title(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"^(?:донцова\s+)?\d+[\.\)]?\s*", "", stem, flags=re.IGNORECASE)
    return stem.strip(" .")


def safe_book_filename(series_code: str, title: str) -> str:
    clean = FORBIDDEN_FILENAME_CHARS.sub(" ", title)
    clean = re.sub(r"\s+", " ", clean).strip()
    return f"{series_code}_{clean}.txt"


def load_local_year_lookup() -> dict[tuple[str, str], int]:
    years: dict[tuple[str, str], int] = {}

    if MAIN_META.exists():
        df = pd.read_csv(MAIN_META, encoding="utf-8-sig")
        for _, row in df.iterrows():
            if row.get("автор") == "Дарья Донцова" and pd.notna(row.get("год")):
                key = norm_title(str(row["название"]))
                years[("*", key)] = int(row["год"])

    if XLSX.exists():
        xl = pd.ExcelFile(XLSX)
        for sheet in xl.sheet_names:
            df = pd.read_excel(XLSX, sheet_name=sheet)
            if {"название", "год"}.issubset(df.columns):
                for _, row in df.iterrows():
                    if pd.notna(row.get("название")) and pd.notna(row.get("год")):
                        key = norm_title(str(row["название"]))
                        years[("*", key)] = int(row["год"])

    return years


def load_fantlab_year_lookup() -> dict[tuple[str, str], int]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from fantlab_years import build_year_lookup, fetch_fantlab_books

    books = fetch_fantlab_books()
    return build_year_lookup(books)


def resolve_year(
    title: str,
    series_code: str,
    fantlab: dict[tuple[str, str], int],
    local: dict[tuple[str, str], int],
) -> int | str:
    key = norm_title(title)
    manual = MANUAL_YEARS.get((series_code, key)) or MANUAL_YEARS.get(("*", key))
    if manual:
        return int(manual)

    for source in (fantlab, local):
        year = source.get((series_code, key)) or source.get(("*", key))
        if year:
            return int(year)

    m = YEAR_IN_TITLE_RE.search(title)
    if m:
        return int(m.group(0))

    return ""


def unique_filename(series_code: str, title: str, used: set[str]) -> str:
    fname = safe_book_filename(series_code, title)
    if fname not in used:
        used.add(fname)
        return fname

    n = 2
    while True:
        alt = safe_book_filename(series_code, f"{title} ({n})")
        if alt not in used:
            used.add(alt)
            return alt
        n += 1


def main() -> None:
    if not RAW_DIR.exists():
        raise SystemExit(f"Нет папки: {RAW_DIR}")

    print("Загрузка годов с FantLab…")
    fantlab_years = load_fantlab_year_lookup()
    local_years = load_local_year_lookup()

    rows: list[dict] = []
    used_names: set[str] = set()

    for folder, (slug, series_name, series_code) in SERIES_FOLDERS.items():
        series_dir = RAW_DIR / folder
        if not series_dir.exists():
            print(f"WARN: нет папки {folder}")
            continue

        files = sorted(series_dir.glob("*.txt"), key=lambda p: p.name.lower())
        for i, path in enumerate(files, start=1):
            title = parse_title(path.name)
            if norm_title(title) in SKIP_SOURCE_TITLE_KEYS:
                print(f"SKIP (сборник): {path.name}")
                continue
            year = resolve_year(title, series_code, fantlab_years, local_years)
            fname = unique_filename(series_code, title, used_names)

            rel_src = f"{folder}/{path.name}".replace("\\", "/")
            rows.append(
                {
                    "id": f"{slug}_{i:03d}",
                    "автор": "Дарья Донцова",
                    "название": title,
                    "серия": series_name,
                    "series_code": series_code,
                    "год": year,
                    "series_slug": slug,
                    "имя_файла": fname,
                    "путь_исходник": rel_src,
                    "путь": f"{slug}/{fname}",
                }
            )

    rows.sort(key=lambda r: (r["series_code"], r["название"].lower()))

    fieldnames = [
        "id",
        "автор",
        "название",
        "серия",
        "series_code",
        "год",
        "series_slug",
        "имя_файла",
        "путь_исходник",
        "путь",
    ]

    written_to = None
    for path in (OUT_CSV, OUT_CSV_FALLBACK):
        try:
            with path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            written_to = path
            break
        except PermissionError:
            continue

    if written_to is None:
        raise SystemExit(
            f"Не удалось записать CSV — закройте {OUT_CSV.name} в Excel и запустите снова."
        )

    if written_to == OUT_CSV_FALLBACK:
        print(
            f"WARN: {OUT_CSV.name} занят — сохранено в {OUT_CSV_FALLBACK.name}. "
            "Закройте CSV в Excel и запустите снова или переименуйте .new.csv вручную."
        )

    with_year = sum(1 for r in rows if r["год"] != "")
    print(f"Записано: {len(rows)} книг -> {written_to}")
    print(f"Год известен для {with_year} из {len(rows)}.")
    if with_year < len(rows):
        missing = [r for r in rows if r["год"] == ""]
        print(f"Без года ({len(missing)}):")
        for r in missing[:15]:
            print(f"  {r['series_code']}: {r['название']}")
        if len(missing) > 15:
            print(f"  … и ещё {len(missing) - 15}")


if __name__ == "__main__":
    main()
