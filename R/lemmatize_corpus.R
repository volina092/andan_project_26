# Лемматизация: books_clean/ -> books_lemmas/
# Требуется: install.packages("udpipe")

library(readr)
library(stringr)
library(dplyr)
library(udpipe)

lemmatize_text <- function(text, model) {
  annotated <- udpipe(text, object = model)

  annotated %>%
    filter(!upos %in% c("PUNCT", "SYM", "X")) %>%
    mutate(lemma = str_to_lower(lemma)) %>%
    filter(str_detect(lemma, "^[а-яёa-z]+$")) %>%
    pull(lemma) %>%
    paste(collapse = " ")
}

lemmatize_for_lexical <- function(input_file, output_file, model) {
  text <- read_lines(
    input_file,
    locale = locale(encoding = "UTF-8"),
    progress = FALSE
  ) |>
    paste(collapse = "\n")

  text_lemmas <- lemmatize_text(text, model = model) |>
    str_squish()

  dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)
  write_lines(text_lemmas, output_file)

  invisible(text_lemmas)
}

lemmatize_corpus <- function(
    metadata,
    input_col = "folder_path_clean_texts",
    output_col = "folder_path_lemmas",
    model
) {
  for (i in seq_len(nrow(metadata))) {
    input_path <- metadata[[input_col]][i]
    output_path <- metadata[[output_col]][i]
    message("Лемматизирую ", i, "/", nrow(metadata), ": ", basename(input_path))

    if (!file.exists(input_path)) {
      stop("Нет файла: ", input_path)
    }
    lemmatize_for_lexical(input_path, output_path, model = model)
  }

  invisible(metadata)
}
