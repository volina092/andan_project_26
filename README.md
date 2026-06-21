# Стилиометрический анализ текстов Донцовой

Исследовательский проект: проверка авторской однородности корпуса Дарьи Донцовой и сравнение с жанрово близкими авторами (TTR, гапаксы, δ Бёрроуза, MDS, синтаксические метрики).

Основной документ с кодом и результатами: [`andan_project.Rmd`](andan_project.Rmd).

## Части проекта

| Часть | Корпус | Задача |
|-------|--------|--------|
| **A** | 40 усечённых текстов (20 Донцова + по 5 дистракторов) | Отделяется ли Донцова от других авторов |
| **B** | 283 текста Донцовой (6 серий) | Есть ли внутриавторские различия по сериям и периодам |

## Данные и авторское право

**Тексты произведений в репозиторий не входят** (ограничения авторского права). В git хранятся:

- метаданные: `corpus_metadata.csv`, `corpus_metadata_dontsova_full.csv`;
- скрипты подготовки и анализа (`R/`, `scripts/`);
- агрегированные результаты (графики, таблицы расстояний, `table_with_frequencies.txt`).

Исходные и обработанные тексты нужно скачать локально:

**[Google Drive — корпус и метаданные](https://drive.google.com/drive/folders/1NPe0Bie78GWEhoG26tI2g0z1wCPiNzky)**

Ожидаемая локальная структура (после распаковки):

```
books/                          # исходники части A
books_clean/                    # усечённые тексты части A
books_dontsova_full_corpora/    # сырые тексты части B
books_dontsova_full_clean/      # очищенные и усечённые тексты части B
corpus_metadata.csv
corpus_metadata_dontsova_full.csv
```

Папки `books_tokens/`, `books_lemmas/`, `corpus_stylo/` и аналоги для части B создаются пайплайном в Rmd.

## Быстрый старт

1. Клонировать репозиторий.
2. Скачать данные с Google Drive в корень проекта.
3. Открыть `andan_project.Rmd` в RStudio и выполнять chunks по порядку (нужны пакеты: `tidyverse`, `stylo`, `udpipe`, `ggrepel` и др. — см. Rmd).

Для части B (после появления clean-текстов):

```bash
python scripts/truncate_dontsova_full_clean.py
python scripts/build_dontsova_full_metadata.py   # при пересборке метаданных
```

## Что в репозитории, а что нет

| В git | Не в git (`.gitignore`) |
|-------|-------------------------|
| `andan_project.Rmd`, `R/`, `scripts/` | `books/`, `books_clean/`, `books_*_tokens/`, `books_*_lemmas/` |
| CSV метаданных | `books_dontsova_full_corpora/`, `books_dontsova_full_clean/` |
| `output_stylo/**/*.png`, `.pdf`, `distance_table_*.csv` | `corpus_stylo/`, `corpus_stylo_dontsova_full/` |
| `table_with_frequencies.txt` | UDPipe-кэши (`python_syntax part/*cache_conllu*`) |
| | `*.RData`, `output/` |

## Если тексты уже были в git

`.gitignore` не убирает уже отслеживаемые файлы. Один раз локально:

```powershell
git rm -r --cached books/ books_clean/ books_tokens/ books_lemmas/
git rm -r --cached corpus_stylo/ corpus_stylo_test/
git rm -r --cached books_dontsova_full_corpora/ books_dontsova_full_clean/ 2>$null
```

Файлы на диске останутся; из следующего коммита они исчезнут. Если тексты уже попадали на GitHub, может понадобиться очистка истории (`git filter-repo` / BFG).

## Автор

Маша Волина — магистерский проект, 2026.
