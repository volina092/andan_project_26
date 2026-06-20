# Очистка корпуса: books/ -> books_clean/
# Исходники не изменяются. Кодировка: UTF-8.

library(readr)
library(stringr)
library(dplyr)
library(purrr)

# --- вспомогательные проверки строк -------------------------------------------

is_blank <- function(x) {
  is.na(x) | str_trim(x) == ""
}

is_page_number_line <- function(x) {
  str_detect(str_trim(x), "^\\d{1,3}$")
}

is_chapter_heading_line <- function(x) {
  str_detect(str_trim(x), "^(Глава|Эпилог|Пролог)\\s*\\d*$")
}

is_publisher_noise <- function(x) {
  str_detect(x, regex("©|ЛитРес|litres\\.ru|Издательство|ISBN|www\\.", ignore_case = TRUE))
}

is_notes_marker <- function(x) {
  str_detect(str_trim(x), "^notes\\d*$")
}

is_prose_line <- function(x) {
  x <- str_trim(x)
  if (is_blank(x)) return(FALSE)
  if (x == "* * *") return(FALSE)
  if (is_publisher_noise(x)) return(FALSE)
  if (is_chapter_heading_line(x)) return(FALSE)
  if (is_page_number_line(x)) return(FALSE)
  if (is_notes_marker(x)) return(FALSE)
  nchar(x) >= 50 && str_detect(x, "[.!?…:;—]")
}

# --- границы текста -----------------------------------------------------------

count_chapter_headings_back <- function(lines, from_idx) {
  k <- from_idx
  n_head <- 0L
  while (k >= 1L) {
    x <- str_trim(lines[[k]])
    if (is_blank(x) || is_page_number_line(x)) {
      k <- k - 1L
      next
    }
    if (is_chapter_heading_line(x)) {
      n_head <- n_head + 1L
      k <- k - 1L
    } else {
      break
    }
  }
  n_head
}

# Одна «Глава 1» перед текстом — оставляем; длинный список глав — оглавление, нет.
adjust_start_for_chapter <- function(lines, prose_idx) {
  if (prose_idx <= 1L) return(prose_idx)

  j <- prose_idx - 1L
  while (j >= 1L) {
    x <- str_trim(lines[[j]])
    if (is_blank(x) || is_page_number_line(x)) {
      j <- j - 1L
      next
    }
    if (is_chapter_heading_line(x) && count_chapter_headings_back(lines, j) == 1L) {
      return(j)
    }
    break
  }
  prose_idx
}

find_body_start <- function(lines) {
  n <- length(lines)
  if (n == 0) return(1L)

  i <- 1L
  if (str_trim(lines[[1]]) == "Annotation") {
    while (i <= n && str_trim(lines[[i]]) != "* * *") i <- i + 1L
    i <- i + 1L
  }

  while (i <= n) {
    if (is_prose_line(lines[[i]])) {
      return(adjust_start_for_chapter(lines, i))
    }
    i <- i + 1L
  }
  1L
}

find_body_end <- function(lines, start) {
  n <- length(lines)
  if (start > n) return(n)

  search_from <- max(start, floor(n * 0.82))
  tail_lines <- lines[search_from:n]

  footnote_hits <- which(
    str_detect(
      tail_lines,
      regex(
        "Прим\\.\\s*автора|автор из этических|совпадения случайны|^Примечания\\s*$",
        ignore_case = TRUE
      )
    )
  )

  if (length(footnote_hits)) {
    cut_at <- search_from + min(footnote_hits) - 1L
    while (cut_at > start && is_blank(lines[[cut_at]])) {
      cut_at <- cut_at - 1L
    }
    return(max(start, cut_at - 1L))
  }

  i <- n
  while (i > start && is_blank(lines[[i]])) i <- i - 1L

  while (i > start) {
    x <- str_trim(lines[[i]])
    if (is_page_number_line(x)) {
      j <- i
      while (j > start && (is_blank(lines[[j]]) || is_page_number_line(lines[[j]]))) {
        j <- j - 1L
      }
      if (j < i && nchar(str_trim(lines[[j]])) < 120) {
        i <- j
        next
      }
    }
    if (is_notes_marker(x)) {
      i <- i - 1L
      next
    }
    break
  }

  max(start, i)
}

# --- очистка ------------------------------------------------------------------

drop_noise_lines <- function(lines) {
  lines[
    !is_publisher_noise(lines) &
      !is_notes_marker(lines) &
      !is_page_number_line(lines)
  ]
}

clean_text_lines <- function(lines) {
  if (!length(lines)) return(character())

  start <- find_body_start(lines)
  end <- find_body_end(lines, start)
  body <- lines[start:end]
  body <- drop_noise_lines(body)
  body <- body[!is_blank(body) | seq_along(body) > 1L]

  while (length(body) && is_blank(body[[length(body)]])) {
    body <- body[-length(body)]
  }

  body
}

clean_one_file <- function(path_in, path_out) {
  lines <- read_lines(
    path_in,
    locale = locale(encoding = "UTF-8"),
    progress = FALSE
  )

  cleaned <- clean_text_lines(lines)

  dir.create(dirname(path_out), recursive = TRUE, showWarnings = FALSE)
  write_lines(
    cleaned,
    path_out,
    locale = locale(encoding = "UTF-8"),
    na = ""
  )

  invisible(list(
    path_in = path_in,
    path_out = path_out,
    lines_in = length(lines),
    lines_out = length(cleaned),
    chars_in = sum(nchar(lines)),
    chars_out = sum(nchar(cleaned))
  ))
}

clean_corpus <- function(
    path_raw = file.path(project_root, "books"),
    path_clean = file.path(project_root, "books_clean"),
    metadata_path = file.path(project_root, "books", "corpus_metadata.csv")
) {
  if (!dir.exists(path_raw)) {
    stop("Не найдена папка с исходниками: ", path_raw)
  }

  meta <- read_csv(
    metadata_path,
    locale = locale(encoding = "UTF-8"),
    show_col_types = FALSE
  )

  stats <- pmap_dfr(
    list(
      in_path = file.path(path_raw, meta$папка, meta$имя_файла),
      out_path = file.path(path_clean, meta$папка, meta$имя_файла),
      title = meta$название
    ),
    function(in_path, out_path, title) {
      if (!file.exists(in_path)) {
        stop("Нет файла: ", in_path)
      }
      res <- clean_one_file(in_path, out_path)
      tibble(
        название = title,
        строк_было = res$lines_in,
        строк_стало = res$lines_out,
        символов_было = res$chars_in,
        символов_стало = res$chars_out,
        доля_сохранено = round(res$chars_out / res$chars_in, 3)
      )
    }
  )

  meta_clean <- meta %>%
    mutate(
      путь_clean = file.path(папка, имя_файла),
      путь_полный_clean = file.path(path_clean, папка, имя_файла)
    )

  write_csv(
    meta_clean,
    metadata_path,
    locale = locale(encoding = "UTF-8")
  )

  message("Готово: ", nrow(stats), " файлов -> ", normalizePath(path_clean))
  stats
}

# корень проекта (RStudio Project или git)
project_root <- local({
  root <- Sys.getenv("ANDAN_ROOT", unset = NA_character_)
  if (!is.na(root) && nzchar(root) && dir.exists(root)) {
    return(root)
  }
  if (requireNamespace("rprojroot", quietly = TRUE)) {
    return(rprojroot::find_root(rprojroot::is_git_root))
  }
  this_file <- tryCatch(sys.frame(1)$ofile, error = function(e) NULL)
  if (!is.null(this_file) && !is.na(this_file)) {
    return(normalizePath(file.path(dirname(this_file), ".."), winslash = "/", mustWork = FALSE))
  }
  normalizePath(getwd(), winslash = "/", mustWork = FALSE)
})
