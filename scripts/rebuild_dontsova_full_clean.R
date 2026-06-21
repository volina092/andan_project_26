#!/usr/bin/env Rscript
# Пересборка books_dontsova_full_clean/ с обновлённой логикой clean_corpus.R

args <- commandArgs(trailingOnly = TRUE)
force <- "--force" %in% args

root <- Sys.getenv("ANDAN_ROOT", unset = NA_character_)
if (is.na(root) || !nzchar(root)) {
  root <- normalizePath(file.path(dirname(sys.frame(1)$ofile %||% "."), ".."), winslash = "/")
}
if (!dir.exists(root)) {
  root <- normalizePath(getwd(), winslash = "/")
}

source(file.path(root, "R", "clean_corpus.R"))

meta_path <- file.path(root, "corpus_metadata_dontsova_full.csv")
if (!file.exists(meta_path)) {
  stop("Нет файла метаданных: ", meta_path)
}

meta <- readr::read_csv(
  meta_path,
  locale = readr::locale(encoding = "UTF-8"),
  show_col_types = FALSE
)

path_raw <- file.path(root, "books_dontsova_full_corpora")
path_clean <- file.path(root, "books_dontsova_full_clean")

meta <- meta %>%
  dplyr::mutate(
    path_in = file.path(path_raw, .data$путь_исходник),
    path_out = file.path(path_clean, .data$путь)
  )

ok <- 0L
skipped <- 0L

for (i in seq_len(nrow(meta))) {
  in_path <- meta$path_in[[i]]
  out_path <- meta$path_out[[i]]

  if (!file.exists(in_path)) {
    stop("Нет исходника: ", in_path)
  }
  if (!force && file.exists(out_path)) {
    skipped <- skipped + 1L
    next
  }

  if (i %% 25 == 1L || i == nrow(meta)) {
    message("Очистка ", i, "/", nrow(meta), ": ", basename(in_path))
  }
  clean_one_file(in_path, out_path)
  ok <- ok + 1L
}

message(
  "Готово: обработано ", ok, ", пропущено (уже есть) ", skipped,
  " -> ", normalizePath(path_clean)
)
