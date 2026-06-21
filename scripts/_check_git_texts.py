import subprocess
from pathlib import Path

repo = Path(__file__).resolve().parents[1]

def list_files(ref: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", ref],
        text=True,
        errors="replace",
    )
    return [line.strip('"') for line in out.splitlines() if line.strip()]

for ref in ("origin/master", "HEAD"):
    files = list_files(ref)
    groups = {
        "books/*.txt": [f for f in files if f.startswith("books/") and f.endswith(".txt")],
        "books_clean/*.txt": [f for f in files if f.startswith("books_clean/") and f.endswith(".txt")],
        "books_tokens|lemmas": [f for f in files if f.startswith(("books_tokens/", "books_lemmas/"))],
        "books_dontsova_full* txt": [f for f in files if "books_dontsova_full" in f and f.endswith(".txt")],
        "corpus_stylo txt": [f for f in files if f.startswith("corpus_stylo/") and f.endswith(".txt")],
        "conllu cache": [f for f in files if "cache_conllu" in f],
        "zip": [f for f in files if f.endswith(".zip")],
    }
    print(f"=== {ref} ===")
    for name, items in groups.items():
        print(f"  {name}: {len(items)}")
    print()
