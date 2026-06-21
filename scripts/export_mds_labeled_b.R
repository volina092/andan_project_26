#!/usr/bin/env Rscript
# Генерация MDS с подписями (год; год + название) для части B.
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(tibble)
  library(stringr)
  library(ggplot2)
})

project_root <- normalizePath(".", winslash = "/")
path_meta_b <- file.path(project_root, "corpus_metadata_dontsova_full.csv")
out_dir <- file.path(project_root, "output_stylo", "stylo", "dontsova_full")
rdata_path <- file.path(out_dir, "delta_dontsova.RData")

if (!file.exists(rdata_path)) stop("Нет ", rdata_path)
load(rdata_path)

if (!requireNamespace("ggrepel", quietly = TRUE)) {
  stop("Установите ggrepel: install.packages('ggrepel')")
}

meta_b <- read_csv(path_meta_b, show_col_types = FALSE, locale = locale(encoding = "UTF-8")) %>%
  mutate(stylo_id = sub("\\.txt$", "", имя_файла))

cyr_font <- if (.Platform$OS.type == "windows") "Segoe UI" else "DejaVu Sans"
grDevices::pdf.options(family = cyr_font)

theme_cyr <- function(base_size = 11) {
  theme_minimal(base_size = base_size, base_family = cyr_font) +
    theme(text = element_text(family = cyr_font))
}

ggsave_pdf <- function(filename, plot, width, height) {
  save_ok <- function(device, ...) {
    tryCatch({
      ggsave(filename, plot, width = width, height = height, device = device, ...)
      TRUE
    }, error = function(e) {
      message(basename(filename), ": ", device, " — ", conditionMessage(e))
      FALSE
    })
  }

  if (capabilities("cairo") && save_ok(grDevices::cairo_pdf, family = cyr_font)) {
    return(invisible(filename))
  }
  if (!save_ok(grDevices::pdf, family = cyr_font)) {
    stop("Не удалось сохранить PDF: ", filename, call. = FALSE)
  }
  invisible(filename)
}

delta_mat <- delta_dontsova
mfw_lab <- stylo_mfw_dontsova
tag_b <- paste0("full_", n_b)

file_ids <- rownames(delta_mat)
if (is.null(file_ids) || any(file_ids == "", na.rm = TRUE)) {
  file_ids <- colnames(delta_mat)
}

stylo_labels <- meta_b %>%
  mutate(
    подпись = str_squish(paste(серия, название)),
    подпись_краткая = str_squish(paste(coalesce(as.character(год), ""), название)),
    подпись_год = coalesce(as.character(год), "?")
  )

file_ids_norm <- sub("\\.txt$", "", file_ids)
stylo_ids_norm <- sub("\\.txt$", "", stylo_labels$stylo_id)

idx <- match(file_ids_norm, stylo_ids_norm)
pretty_labels <- stylo_labels$подпись[idx]
pretty_short <- stylo_labels$подпись_краткая[idx]
pretty_year <- stylo_labels$подпись_год[idx]
series_vec <- stylo_labels$серия[idx]
years <- stylo_labels$год[idx]

ord <- order(series_vec, pretty_labels)
delta_mat <- delta_mat[ord, ord, drop = FALSE]
pretty_labels <- pretty_labels[ord]
pretty_short <- pretty_short[ord]
pretty_year <- pretty_year[ord]
series_vec <- series_vec[ord]
years <- years[ord]

rownames(delta_mat) <- colnames(delta_mat) <- pretty_labels

assign_year_period <- function(
  y,
  anchor = 1999L,
  first_end = 2004L,
  span = 5L,
  last_start = 2020L,
  last_end = 2025L
) {
  y <- suppressWarnings(as.integer(y))
  vapply(y, function(one) {
    if (is.na(one)) return("год неизвестен")
    if (one <= first_end) return(paste0(anchor, "–", first_end))
    if (one >= last_start) return(paste0(last_start, "–", last_end))
    y0 <- first_end + 1L
    start <- y0 + span * floor((one - y0) / span)
    paste0(start, "–", start + span - 1L)
  }, character(1))
}

year_period_levels <- function(years) {
  lv <- unique(assign_year_period(years))
  lv[order(suppressWarnings(as.integer(sub("–.*", "", lv))), na.last = TRUE)]
}

year_period_factor <- function(years) {
  factor(assign_year_period(years), levels = year_period_levels(years))
}

mds_xy <- cmdscale(as.dist(delta_mat), k = 2)
mds_df <- tibble(
  подпись = pretty_short,
  подпись_год = pretty_year,
  серия = series_vec,
  год = years,
  период = year_period_factor(years),
  X1 = mds_xy[, 1],
  X2 = mds_xy[, 2]
)

p_mds_period <- mds_df %>%
  ggplot(aes(x = X1, y = X2, colour = период)) +
  geom_point(size = 1.8, alpha = 0.85) +
  labs(
    title = paste0("MDS по δ, цвет — период издания (Донцова, n = ", n_b, ", MFW = ", mfw_lab, ")"),
    subtitle = "Периоды по 5 лет; первый: 1999–2004, последний: 2020–2025",
    x = "Dim 1", y = "Dim 2", colour = "Период"
  ) +
  theme_cyr() +
  theme(legend.text = element_text(size = 8))

p_mds_year <- mds_df %>%
  ggplot(aes(x = X1, y = X2, colour = серия)) +
  geom_point(size = 1.6, alpha = 0.75) +
  ggrepel::geom_text_repel(
    aes(label = подпись_год),
    size = 2.2, max.overlaps = Inf, family = cyr_font, min.segment.length = 0
  ) +
  labs(
    title = paste0("MDS по δ, подписи — год (Донцова, n = ", n_b, ", MFW = ", mfw_lab, ")"),
    x = "Dim 1", y = "Dim 2", colour = "Серия"
  ) +
  theme_cyr() +
  theme(legend.text = element_text(size = 8))

p_mds_year_title <- mds_df %>%
  ggplot(aes(x = X1, y = X2, colour = серия)) +
  geom_point(size = 1.6, alpha = 0.75) +
  ggrepel::geom_text_repel(
    aes(label = подпись),
    size = 1.7, max.overlaps = Inf, family = cyr_font, min.segment.length = 0
  ) +
  labs(
    title = paste0("MDS по δ, подписи — год и название (Донцова, n = ", n_b, ", MFW = ", mfw_lab, ")"),
    x = "Dim 1", y = "Dim 2", colour = "Серия"
  ) +
  theme_cyr() +
  theme(legend.text = element_text(size = 8))

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

ggsave(file.path(out_dir, paste0("delta_mds_period_", tag_b, ".png")),
       p_mds_period, width = 12, height = 9, dpi = 150)
ggsave_pdf(file.path(out_dir, paste0("delta_mds_period_", tag_b, ".pdf")),
           p_mds_period, width = 12, height = 9)
ggsave(file.path(out_dir, paste0("delta_mds_year_", tag_b, ".png")),
       p_mds_year, width = 16, height = 12, dpi = 150)
ggsave_pdf(file.path(out_dir, paste0("delta_mds_year_", tag_b, ".pdf")),
           p_mds_year, width = 16, height = 12)
ggsave(file.path(out_dir, paste0("delta_mds_year_title_", tag_b, ".png")),
       p_mds_year_title, width = 18, height = 14, dpi = 150)
ggsave_pdf(file.path(out_dir, paste0("delta_mds_year_title_", tag_b, ".pdf")),
           p_mds_year_title, width = 18, height = 14)

message("Сохранено в ", out_dir)
