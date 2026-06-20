# Токенизация для лексического анализа (stylo, TTR, гапаксы)
# Источник: books_clean/  ->  books_tokens/

library(readr)
library(stringr)
library(purrr)
library(dplyr)

clean_for_lexical <- function(input_file, output_file) {
  text <- read_lines(
    input_file,
    locale = locale(encoding = "UTF-8"),
    progress = FALSE
  ) |>
    paste(collapse = " ")

  text_clean <- text |>
    str_to_lower() |>
    str_replace_all("[^а-яёa-z\\s]", " ") |>
    str_squish()

  dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)
  write_lines(
    text_clean,
    output_file,
    locale = locale(encoding = "UTF-8")
  )

  invisible(text_clean)
}

tokenize_corpus <- function(
    metadata,
    input_col = "путь_полный_clean",
    output_col = "путь_полный_tokens"
) {
  pmap(metadata[c(input_col, output_col)], function(input_path, output_path) {
    if (!file.exists(input_path)) {
      stop("Нет файла: ", input_path)
    }
    clean_for_lexical(input_path, output_path)
  })

  invisible(metadata)
}
