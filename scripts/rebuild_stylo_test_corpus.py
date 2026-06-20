"""Мини-корпус для smoke-теста stylo: 4 книги × 5000 слов."""
import csv
from pathlib import Path

root = Path(__file__).resolve().parent.parent
meta = list(csv.DictReader(open(root / "corpus_metadata.csv", encoding="utf-8-sig")))

test_files = {
    "01_Букет_прекрасных_дам.txt",
    "Близкие_люди.txt",
    "Татьяна_Полякова_-_01._Капкан_на_спонсора_(1999).txt",
    "05_Смерть_ради_смерти.txt",
}
max_words = 5000

out = root / "corpus_stylo_test"
if out.exists():
    for f in out.glob("*.txt"):
        f.unlink()
else:
    out.mkdir()

n = 0
for row in meta:
    if row["имя_файла"] not in test_files:
        continue
    src = root / "books_tokens" / row["папка"] / row["имя_файла"]
    words = [w for w in src.read_text(encoding="utf-8").split() if w][:max_words]
    dst = out / f"{row['папка']}__{row['имя_файла']}"
    dst.write_text("\n".join(words) + "\n", encoding="utf-8")
    n += 1
    print(row["автор"], "->", dst.name, "words:", len(words))

print("total:", n)
