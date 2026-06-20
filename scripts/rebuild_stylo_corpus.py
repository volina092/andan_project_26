import csv
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent.parent
meta = list(csv.DictReader(open(root / "corpus_metadata.csv", encoding="utf-8-sig")))

for name in ("corpus_stylo", "corpus_stylo_dontsova"):
    d = root / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()

for row in meta:
    src = root / "books_tokens" / row["папка"] / row["имя_файла"]
    dst_name = f"{row['папка']}__{row['имя_файла']}"
    text = src.read_text(encoding="utf-8")
    words = [w for w in text.split() if w]
    for out_dir in (root / "corpus_stylo",):
        (out_dir / dst_name).write_text("\n".join(words) + "\n", encoding="utf-8")
    if row["автор"] == "Дарья Донцова":
        (root / "corpus_stylo_dontsova" / dst_name).write_text(
            "\n".join(words) + "\n", encoding="utf-8"
        )

all_txt = list((root / "corpus_stylo").glob("*.txt"))
subdirs = [p.name for p in (root / "corpus_stylo").iterdir() if p.is_dir()]
dontsova_txt = list((root / "corpus_stylo_dontsova").glob("*.txt"))
print("corpus_stylo txt:", len(all_txt))
print("corpus_stylo subdirs:", subdirs)
print("corpus_stylo_dontsova txt:", len(dontsova_txt))
