# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fantlab_years import fetch_fantlab_books, build_year_lookup, lookup_year

books = fetch_fantlab_books()
print("books", len(books), Counter(b.series_code for b in books))
lookup = build_year_lookup(books)
print("lookup size", len(lookup))
print("sample", lookup_year(lookup, "ВТ", "Черт из табакерки"), lookup_year(lookup, "ДВ", "Дама с коготками"))
