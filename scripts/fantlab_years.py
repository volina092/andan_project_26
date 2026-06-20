# -*- coding: utf-8 -*-
"""Годы публикации книг Донцовой с FantLab (autor14039)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

import requests

FANTLAB_URL = "https://fantlab.ru/autor14039"
USER_AGENT = "andan_project/1.0 (academic corpus metadata)"

ENTRY_RE = re.compile(
    r'<a href="/work\d+">([^<]+)</a>(.{0,500}?)\((\d{4})\)',
    re.S,
)
ALT_RE = re.compile(r"\[=([^]]+)\]")

SERIES_MARKERS: list[tuple[str, str]] = [
    ("виола тараканова", "ВТ"),
    ("детектив на диете", "ТС"),
    ("татьяна сергеева", "ТС"),
    ("джентльмен сыска", "ИП"),
    ("иван подушкин", "ИП"),
    ("евлампия романова", "ЕР"),
    ("любимица фортуны", "СК"),
    ("степанида козлова", "СК"),
    ("любительница частного сыска", "ДВ"),
    ("даша васильева", "ДВ"),
]


@dataclass(frozen=True)
class FantlabBook:
    series_code: str
    title: str
    year: int
    alt_titles: tuple[str, ...]


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = s.replace("ё", "е")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def detect_series_code(line: str) -> str | None:
    low = norm_title(line)
    for marker, code in SERIES_MARKERS:
        if marker in low:
            return code
    return None


def clean_link_title(raw: str) -> str:
    title = re.sub(r"\s+", " ", raw).strip()
    return title.lstrip("+").strip()


def parse_alt_titles(tail: str) -> list[str]:
    alts: list[str] = []
    for chunk in ALT_RE.findall(tail):
        for part in re.split(r"\s*=\s*", chunk):
            part = part.strip(" ,;")
            if part:
                alts.append(part)
    return alts


def parse_cycles_html(html: str) -> list[FantlabBook]:
    books: list[FantlabBook] = []
    current_code: str | None = None

    for m in re.finditer(r'<a href="/work\d+">([^<]+)</a>', html):
        title = clean_link_title(m.group(1))
        tail = html[m.end() : m.end() + 600]
        year_m = re.search(r"\((\d{4})\)", tail)
        code = detect_series_code(title)

        if code and year_m is None:
            current_code = code
            continue

        if year_m is None or current_code is None:
            continue

        alts = parse_alt_titles(tail[: year_m.start()])
        books.append(
            FantlabBook(
                series_code=current_code,
                title=title,
                year=int(year_m.group(1)),
                alt_titles=tuple(alts),
            )
        )

    return books


def fetch_fantlab_books(url: str = FANTLAB_URL, timeout: int = 30) -> list[FantlabBook]:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return parse_cycles_html(resp.text)


def build_year_lookup(books: Iterable[FantlabBook]) -> dict[tuple[str, str], int]:
    lookup: dict[tuple[str, str], int] = {}
    for book in books:
        keys = {norm_title(book.title)} | {norm_title(t) for t in book.alt_titles}
        for key in keys:
            lookup[(book.series_code, key)] = book.year
            lookup.setdefault(("*", key), book.year)
    return lookup


def lookup_year(
    lookup: dict[tuple[str, str], int],
    series_code: str,
    title: str,
) -> int | None:
    key = norm_title(title)
    return lookup.get((series_code, key)) or lookup.get(("*", key))
