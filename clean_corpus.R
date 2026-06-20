# Запуск очистки корпуса (из корня проекта в RStudio):
#
#   source("clean_corpus.R")
#
# Или:
#   source("R/clean_corpus.R")
#   stats <- clean_corpus()

source(file.path("R", "clean_corpus.R"), encoding = "UTF-8")

stats <- clean_corpus()

print(stats)

cat(
  "\nСводка:\n",
  "  медиана доли сохранённого текста: ",
  round(median(stats$доля_сохранено), 3),
  "\n",
  sep = ""
)
