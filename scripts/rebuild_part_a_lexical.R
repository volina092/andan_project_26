# Пересборка books_tokens/ и books_lemmas/ после truncate_clean_corpus.py
# Зависимости: udpipe (+ его транзитивные пакеты)

if (!requireNamespace("udpipe", quietly = TRUE)) {
  stop("Установите udpipe: install.packages('udpipe')")
}

project_root <- if (requireNamespace("rprojroot", quietly = TRUE)) {
  rprojroot::find_root(rprojroot::is_git_root)
} else {
  normalizePath(getwd(), winslash = "/")
}

path_meta <- file.path(project_root, "corpus_metadata.csv")
path_books_clean <- file.path(project_root, "books_clean")
path_tokens <- file.path(project_root, "books_tokens")
path_lemmas <- file.path(project_root, "books_lemmas")

meta <- read.csv(path_meta, fileEncoding = "UTF-8", stringsAsFactors = FALSE)
meta$folder_path_clean_texts <- file.path(path_books_clean, meta$папка, meta$имя_файла)
meta$folder_path_tokens <- file.path(path_tokens, meta$папка, meta$имя_файла)
meta$folder_path_lemmas <- file.path(path_lemmas, meta$папка, meta$имя_файла)

clean_for_lexical <- function(input_file, output_file) {
  text <- paste(readLines(input_file, encoding = "UTF-8", warn = FALSE), collapse = " ")
  text_clean <- tolower(text)
  text_clean <- gsub("[^а-яёa-z\\s]", " ", text_clean, perl = TRUE)
  text_clean <- gsub("\\s+", " ", text_clean, perl = TRUE)
  text_clean <- trimws(text_clean)
  dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)
  writeLines(text_clean, output_file, useBytes = FALSE)
  invisible(text_clean)
}

count_words <- function(path) {
  if (!file.exists(path)) return(NA_integer_)
  length(strsplit(readLines(path, encoding = "UTF-8", warn = FALSE), "\\s+")[[1]])
}

message("Токенизация ", nrow(meta), " файлов…")
for (i in seq_len(nrow(meta))) {
  clean_for_lexical(meta$folder_path_clean_texts[i], meta$folder_path_tokens[i])
}

model_info <- udpipe::udpipe_download_model(language = "russian")
udpipe_ru <- udpipe::udpipe_load_model(model_info$file_model)

lemmatize_text <- function(text, model = udpipe_ru) {
  annotated <- udpipe::udpipe(text, object = model)
  lemmas <- annotated$lemma[
    !annotated$upos %in% c("PUNCT", "SYM", "X") &
      grepl("^[а-яёa-z]+$", tolower(annotated$lemma), perl = TRUE)
  ]
  paste(tolower(lemmas), collapse = " ")
}

message("Лемматизация ", nrow(meta), " файлов (udpipe, ~несколько минут)…")
for (i in seq_len(nrow(meta))) {
  text <- paste(readLines(meta$folder_path_clean_texts[i], encoding = "UTF-8", warn = FALSE), collapse = "\n")
  lemmas <- lemmatize_text(text, model = udpipe_ru)
  lemmas <- gsub("\\s+", " ", trimws(lemmas))
  dir.create(dirname(meta$folder_path_lemmas[i]), recursive = TRUE, showWarnings = FALSE)
  writeLines(lemmas, meta$folder_path_lemmas[i], useBytes = FALSE)
  if (i %% 5 == 0) message("  ", i, "/", nrow(meta))
}

tokens <- vapply(meta$folder_path_tokens, count_words, integer(1))
lemmas <- vapply(meta$folder_path_lemmas, count_words, integer(1))
message("tokens: min=", min(tokens), " max=", max(tokens), " median=", median(tokens))
message("lemmas: min=", min(lemmas), " max=", max(lemmas), " median=", median(lemmas))
message("Готово.")
