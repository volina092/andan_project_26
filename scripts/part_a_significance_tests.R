#!/usr/bin/env Rscript
#
# Часть A: статистические тесты для
# - лексических метрик (TTR / hapax)  [из books_lemmas/]
# - δ Бёрроуза                        [из output_stylo/stylo/all_40/distance_table_40.csv]
# - синтаксических метрик syntaxcomp  [из python_syntax part/output/syntaxcomp_metrics.csv]
#
# Скрипт НЕ трогает andan_project.Rmd. Он читает уже существующие артефакты и
# сохраняет краткий отчёт в output_stats/.
#
# Запуск (в RStudio):
# source("scripts/part_a_significance_tests.R")
#
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(stringr)
  library(tibble)
  library(purrr)
})

ROOT <- normalizePath(".", winslash = "/")

path_meta <- file.path(ROOT, "corpus_metadata.csv")
path_lemmas_root <- file.path(ROOT, "books_lemmas")
path_delta <- file.path(ROOT, "output_stylo", "stylo", "all_40", "distance_table_40.csv")
path_syntax <- file.path(ROOT, "python_syntax part", "output", "syntaxcomp_metrics.csv")

out_dir <- file.path(ROOT, "output_stats")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

stopifnot(file.exists(path_meta))
stopifnot(file.exists(path_delta))
stopifnot(file.exists(path_syntax))

meta <- read_csv(path_meta, show_col_types = FALSE, locale = locale(encoding = "UTF-8")) %>%
  mutate(
    год = suppressWarnings(as.integer(год)),
    фамилия = stringr::word(автор, -1),
    delta_label = str_squish(paste(фамилия, год, название)),
    lemma_path = file.path(path_lemmas_root, путь)
  )

authors_vec <- meta$автор
is_dontsova <- authors_vec == "Дарья Донцова"
author_group_2 <- ifelse(is_dontsova, "Донцова", "Дистракторы") %>% factor(levels = c("Донцова", "Дистракторы"))

fmt_p <- function(p) {
  if (is.na(p)) return(NA_character_)
  if (p < 1e-4) return(format(p, scientific = TRUE, digits = 2))
  format(round(p, 4), nsmall = 4)
}

cohen_d <- function(x, y) {
  x <- x[is.finite(x)]
  y <- y[is.finite(y)]
  nx <- length(x); ny <- length(y)
  if (nx < 2 || ny < 2) return(NA_real_)
  sx <- stats::var(x); sy <- stats::var(y)
  sp <- sqrt(((nx - 1) * sx + (ny - 1) * sy) / (nx + ny - 2))
  if (!is.finite(sp) || sp == 0) return(NA_real_)
  (mean(x) - mean(y)) / sp
}

# ----------------------------
# 1) δ Бёрроуза
# ----------------------------

delta_mat <- read_csv(path_delta, show_col_types = FALSE, locale = locale(encoding = "UTF-8")) %>%
  as.data.frame()

if (!"" %in% names(delta_mat)) {
  stop("distance_table_40.csv: не найден первый столбец с rownames (ожидается пустое имя колонки).")
}

rown <- delta_mat[[""]]
delta_mat[[""]] <- NULL
delta_mat <- as.matrix(delta_mat)
rownames(delta_mat) <- rown

# Сопоставим порядок meta <-> матрица
idx <- match(meta$delta_label, rownames(delta_mat))
if (any(is.na(idx))) {
  missing <- meta$delta_label[is.na(idx)]
  stop(
    "Не сопоставились названия для δ (первые 10):\n",
    paste(head(missing, 10), collapse = "\n"),
    "\nПроверьте, что distance_table_40.csv соответствует corpus_metadata.csv и формату «Фамилия Год Название»."
  )
}
delta_mat <- delta_mat[idx, idx, drop = FALSE]

# Для каждого текста Донцовой: средняя дистанция до Донцовой vs до дистракторов (paired t-test)
d_idx <- which(is_dontsova)
o_idx <- which(!is_dontsova)

within_mean <- vapply(d_idx, function(i) mean(delta_mat[i, setdiff(d_idx, i)]), numeric(1))
between_mean <- vapply(d_idx, function(i) mean(delta_mat[i, o_idx]), numeric(1))

tt_delta_paired <- t.test(within_mean, between_mean, paired = TRUE, alternative = "less")

# PERMANOVA по δ
if (!requireNamespace("vegan", quietly = TRUE)) {
  stop("Нужен пакет vegan для PERMANOVA: install.packages('vegan')")
}
perm_delta <- vegan::adonis2(stats::as.dist(delta_mat) ~ authors_vec, permutations = 999)

# ----------------------------
# 2) Синтаксис: совокупность метрик + PERMANOVA
# ----------------------------

syntax <- read_csv(path_syntax, show_col_types = FALSE, locale = locale(encoding = "UTF-8")) %>%
  mutate(
    год = suppressWarnings(as.integer(год)),
    delta_label = str_squish(paste(stringr::word(автор, -1), год, название))
  )

syntax2 <- meta %>%
  select(автор, папка, имя_файла, delta_label) %>%
  left_join(
    syntax %>% select(-автор, -название, -серия, -год, -папка, -имя_файла),
    by = "delta_label"
  )

num_cols <- syntax2 %>% select(where(is.numeric)) %>% names()
num_cols <- setdiff(num_cols, character(0))

X_syn <- syntax2 %>% select(all_of(num_cols)) %>% as.data.frame()

# Уберём колонки с NA/нулевой дисперсией
ok_col <- vapply(X_syn, function(v) {
  v <- v[is.finite(v)]
  length(v) >= 5 && stats::sd(v) > 0
}, logical(1))
X_syn <- X_syn[, ok_col, drop = FALSE]

if (ncol(X_syn) < 3) {
  stop("Слишком мало числовых синтаксических метрик после фильтрации.")
}

X_syn_scaled <- scale(X_syn)

# PCA -> PC1 как 1D агрегат для t-test (Донцова vs дистракторы)
pca_syn <- stats::prcomp(X_syn_scaled, center = FALSE, scale. = FALSE)
pc1_syn <- pca_syn$x[, 1]
tt_syn_pc1 <- t.test(pc1_syn[is_dontsova], pc1_syn[!is_dontsova])

# PERMANOVA по синтаксическим метрикам
dist_syn <- stats::dist(X_syn_scaled)
perm_syn <- vegan::adonis2(dist_syn ~ authors_vec, permutations = 999)

# ----------------------------
# 3) Лексика: совокупность метрик + PERMANOVA (если есть books_lemmas)
# ----------------------------

compute_lexical <- function(path) {
  if (!file.exists(path)) return(tibble(tokens = NA_integer_, types = NA_integer_, ttr = NA_real_, hapax = NA_integer_,
                                       hapax_per_type = NA_real_, hapax_per_token = NA_real_))
  txt <- readLines(path, encoding = "UTF-8", warn = FALSE)
  w <- unlist(strsplit(paste(txt, collapse = " "), "\\s+"))
  w <- w[nzchar(w)]
  tokens <- length(w)
  if (tokens == 0) {
    return(tibble(tokens = 0L, types = 0L, ttr = NA_real_, hapax = 0L, hapax_per_type = NA_real_, hapax_per_token = NA_real_))
  }
  tab <- table(w)
  types <- length(tab)
  hapax <- sum(tab == 1)
  tibble(
    tokens = tokens,
    types = types,
    ttr = types / tokens,
    hapax = hapax,
    hapax_per_type = ifelse(types > 0, hapax / types, NA_real_),
    hapax_per_token = hapax / tokens
  )
}

lex <- meta %>%
  mutate(lex = purrr::map(lemma_path, compute_lexical)) %>%
  tidyr::unnest(lex)

lex_ok <- lex %>% filter(is.finite(ttr), is.finite(hapax_per_type), is.finite(hapax_per_token))

lex_tests <- NULL
perm_lex <- NULL
tt_lex_pc1 <- NULL

if (nrow(lex_ok) == nrow(meta)) {
  X_lex <- lex_ok %>% select(ttr, hapax_per_type, hapax_per_token) %>% as.data.frame()
  X_lex_scaled <- scale(X_lex)
  pca_lex <- stats::prcomp(X_lex_scaled, center = FALSE, scale. = FALSE)
  pc1_lex <- pca_lex$x[, 1]
  tt_lex_pc1 <- t.test(pc1_lex[is_dontsova], pc1_lex[!is_dontsova])
  perm_lex <- vegan::adonis2(stats::dist(X_lex_scaled) ~ authors_vec, permutations = 999)
} else {
  message("Лексические метрики: пропуск (нет всех файлов в books_lemmas/).")
}

# ----------------------------
# Report
# ----------------------------

report <- tibble::tribble(
  ~block, ~test, ~comparison, ~stat, ~p_value, ~effect,
  "delta", "t-test paired", "mean δ внутри Донцовой < mean δ Донцова×дистракторы",
  unname(tt_delta_paired$statistic), tt_delta_paired$p.value,
  cohen_d(within_mean, between_mean),
  "delta", "PERMANOVA", "δ distances ~ author",
  unname(perm_delta$F[1]), perm_delta$`Pr(>F)`[1],
  perm_delta$R2[1],
  "syntax", "t-test PC1", "PC1(syntax) Донцова vs дистракторы",
  unname(tt_syn_pc1$statistic), tt_syn_pc1$p.value,
  cohen_d(pc1_syn[is_dontsova], pc1_syn[!is_dontsova]),
  "syntax", "PERMANOVA", "dist(syntax z) ~ author",
  unname(perm_syn$F[1]), perm_syn$`Pr(>F)`[1],
  perm_syn$R2[1]
)

if (!is.null(perm_lex)) {
  report <- bind_rows(
    report,
    tibble(
      block = "lexical",
      test = "t-test PC1",
      comparison = "PC1(lexical) Донцова vs дистракторы",
      stat = unname(tt_lex_pc1$statistic),
      p_value = tt_lex_pc1$p.value,
      effect = cohen_d(
        stats::prcomp(scale(lex_ok %>% select(ttr, hapax_per_type, hapax_per_token)), center = FALSE, scale. = FALSE)$x[, 1][is_dontsova],
        stats::prcomp(scale(lex_ok %>% select(ttr, hapax_per_type, hapax_per_token)), center = FALSE, scale. = FALSE)$x[, 1][!is_dontsova]
      )
    ),
    tibble(
      block = "lexical",
      test = "PERMANOVA",
      comparison = "dist(lexical z) ~ author",
      stat = unname(perm_lex$F[1]),
      p_value = perm_lex$`Pr(>F)`[1],
      effect = perm_lex$R2[1]
    )
  )
}

report_fmt <- report %>%
  mutate(
    stat = round(stat, 4),
    p = vapply(p_value, fmt_p, character(1)),
    effect = round(effect, 4)
  ) %>%
  select(block, test, comparison, stat, p, effect)

write_csv(report_fmt, file.path(out_dir, "part_a_significance_report.csv"))

md <- c(
  "# Часть A — статистические тесты (сводка)",
  "",
  sprintf("- Дата: %s", format(Sys.time(), "%Y-%m-%d %H:%M")),
  "- Корпус: 40 текстов (20 Донцова + 20 дистракторы)",
  "",
  "## Что тестируется",
  "- **δ Бёрроуза**: проверка, что книги Донцовой ближе друг к другу, чем к дистракторам (paired t-test по средним дистанциям).",
  "- **Синтаксис**: 1D агрегат (PC1 по z-оценкам метрик) + PERMANOVA по полному профилю.",
  "- **Лексика**: (если доступны `books_lemmas/`) 1D агрегат (PC1 по TTR и гапаксам) + PERMANOVA.",
  "",
  "## Результаты (кратко)",
  "",
  paste0(
    report_fmt %>%
      mutate(line = sprintf("- **%s / %s**: p = %s; effect = %s", block, test, p, effect)) %>%
      pull(line),
    collapse = "\n"
  ),
  "",
  "## Примечания по интерпретации",
  "- Для **δ** выбран paired t-test на уровне *текстов* (n=20 у Донцовой): это аккуратнее, чем t-test по всем парам дистанций, которые не независимы.",
  "- Для **синтаксиса/лексики** t-test делается по PC1 (сводный профиль); PERMANOVA даёт p-value и R² для мультивариантного различия по автору.",
  ""
)

writeLines(md, file.path(out_dir, "part_a_significance_report.md"), useBytes = TRUE)

message("OK: сохранено в ", out_dir)
