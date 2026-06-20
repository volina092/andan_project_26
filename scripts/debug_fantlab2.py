# -*- coding: utf-8 -*-
import re
import requests
from fantlab_years import ENTRY_RE, detect_series_code, clean_link_title, parse_cycles_html

r = requests.get("https://fantlab.ru/autor14039", headers={"User-Agent": "test"}, timeout=30)
r.encoding = r.apparent_encoding or "utf-8"
text = r.text

matches = ENTRY_RE.findall(text)
print("entry matches", len(matches))

current = None
headers = 0
books = 0
for raw_title, tail, year_str in matches[:30]:
    title = clean_link_title(raw_title)
    code = detect_series_code(title)
    is_header = bool(code and not any(ch.isdigit() for ch in title[:6]))
    if is_header:
        current = code
        headers += 1
        kind = "HEADER"
    elif current:
        books += 1
        kind = "BOOK"
    else:
        kind = "SKIP"
    print(kind, current, year_str, title[:50])

print("--- parse_cycles_html ---")
all_books = parse_cycles_html(text)
print("total books", len(all_books))
