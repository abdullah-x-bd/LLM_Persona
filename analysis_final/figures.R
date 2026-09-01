suppressPackageStartupMessages({
  library(ggplot2)
  library(dplyr)
  library(tidyr)
  library(readr)
  library(scales)
  library(ggrepel)
  library(patchwork)
  library(svglite)
})

args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2)
indir <- args[1]
outdir <- args[2]
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)

required_files <- c(
  "cell_metrics.csv", "contrasts.csv", "outcome_effects.csv",
  "joint_metrics.csv", "pattern_distribution.csv",
  "age_reasoning_effects.csv", "probability_tail.csv"
)
missing_files <- required_files[!file.exists(file.path(indir, required_files))]
if (length(missing_files)) stop(paste("Missing aggregate inputs:", paste(missing_files, collapse = ", ")))

cell <- read_csv(file.path(indir, "cell_metrics.csv"), show_col_types = FALSE)
con <- read_csv(file.path(indir, "contrasts.csv"), show_col_types = FALSE)
oe <- read_csv(file.path(indir, "outcome_effects.csv"), show_col_types = FALSE)
joint <- read_csv(file.path(indir, "joint_metrics.csv"), show_col_types = FALSE)
patt <- read_csv(file.path(indir, "pattern_distribution.csv"), show_col_types = FALSE)
age <- read_csv(file.path(indir, "age_reasoning_effects.csv"), show_col_types = FALSE)
tails <- read_csv(file.path(indir, "probability_tail.csv"), show_col_types = FALSE)

required_cell <- c("cell", "method_class", "model", "individual_brier", "joint_tv")
if (!all(required_cell %in% names(cell))) stop("cell_metrics.csv is not the finalized canonical schema")

pal <- c(
  "Luna" = "#CC79A7",
  "Claude" = "#0072B2",
  "Qwen" = "#D55E00",
  "DeepSeek" = "#009E73",
  "Human" = "#222222",
  "Supervised" = "#6B7280"
)

base_theme <- theme_minimal(base_size = 10.5, base_family = "sans") +
  theme(
    plot.title = element_blank(),
    plot.subtitle = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(linewidth = 0.23, colour = "grey90"),
    axis.title = element_text(size = 9.5, colour = "grey20"),
    axis.text = element_text(size = 9, colour = "grey25"),
    legend.title = element_blank(),
    legend.text = element_text(size = 8.5),
    legend.position = "bottom",
    strip.text = element_text(face = "bold", size = 9),
    strip.background = element_blank(),
    plot.margin = margin(7, 11, 7, 7)
  )

savefig <- function(p, name, w = 7, h = 4.6) {
  ggsave(file.path(outdir, paste0(name, ".pdf")), p, width = w, height = h, device = cairo_pdf)
  ggsave(file.path(outdir, paste0(name, ".svg")), p, width = w, height = h, device = svglite)
  ggsave(file.path(outdir, paste0(name, ".png")), p, width = w, height = h, dpi = 600, bg = "white")
}

pretty_con <- c(
  luna_rich_minus_thin = "Luna",
  claude_rich_minus_thin = "Claude",
  qwen_medium_minus_off = "Qwen",
  deepseek_rich_high_minus_off = "DeepSeek"
)

# 1. Micro versus macro fidelity. Lower-left is improvement on both axes.
m1 <- con %>%
  filter(contrast %in% names(pretty_con), metric %in% c("individual_brier", "hard_prevalence_mae")) %>%
  select(contrast, metric, estimate) %>%
  pivot_wider(names_from = metric, values_from = estimate) %>%
  mutate(model = unname(pretty_con[contrast]), x = 100 * individual_brier, y = 100 * hard_prevalence_mae)
stopifnot(nrow(m1) == 4)

p1 <- ggplot(m1, aes(x, y, colour = model)) +
  annotate("rect", xmin = -Inf, xmax = 0, ymin = -Inf, ymax = 0, fill = "grey70", alpha = 0.08) +
  geom_hline(yintercept = 0, colour = "grey62", linewidth = 0.35) +
  geom_vline(xintercept = 0, colour = "grey62", linewidth = 0.35) +
  geom_point(size = 3.4) +
  geom_text_repel(aes(label = model), show.legend = FALSE, size = 3.25, box.padding = 0.45, seed = 41) +
  scale_colour_manual(values = pal) +
  labs(x = "Change in individual Brier (×100)", y = "Change in hard population MAE (pp)") +
  base_theme +
  theme(legend.position = "none")
savefig(p1, "fig01_micro_macro", 6.6, 4.5)

# 2. Model-specific reasoning effects. All plotted values are percentage-point-like changes,
# except Brier, which is multiplied by 100 for comparable visual scale.
r2 <- con %>%
  filter(
    contrast %in% c("qwen_medium_minus_off", "deepseek_rich_high_minus_off"),
    metric %in% c("individual_brier", "hard_accuracy", "probability_prevalence_mae", "hard_prevalence_mae")
  ) %>%
  mutate(
    model = if_else(grepl("qwen", contrast), "Qwen", "DeepSeek"),
    metric = recode(
      metric,
      individual_brier = "Brier ×100",
      hard_accuracy = "Accuracy (pp)",
      probability_prevalence_mae = "Probability MAE (pp)",
      hard_prevalence_mae = "Hard MAE (pp)"
    ),
    estimate = 100 * estimate,
    ci_low = 100 * ci_low,
    ci_high = 100 * ci_high
  )
stopifnot(nrow(r2) == 8)

p2 <- ggplot(r2, aes(estimate, model, colour = model)) +
  geom_vline(xintercept = 0, colour = "grey58", linewidth = 0.35) +
  geom_errorbarh(aes(xmin = ci_low, xmax = ci_high), height = 0.14, linewidth = 0.62) +
  geom_point(size = 2.7) +
  facet_wrap(~metric, scales = "free_x", nrow = 1) +
  scale_colour_manual(values = pal) +
  labs(x = "Reasoning effect", y = NULL) +
  base_theme +
  theme(legend.position = "none", panel.spacing = unit(1.05, "lines"))
savefig(p2, "fig02_reasoning_reversal", 9.2, 3.1)

# 3. DeepSeek 2x2 factorial. Direct labels replace the legend.
f3 <- cell %>%
  filter(cell %in% c("deepseek_thin_off", "deepseek_thin_high", "deepseek_rich_off", "deepseek_rich_high")) %>%
  mutate(
    persona = if_else(grepl("thin", cell), "Thin", "Rich"),
    reasoning = if_else(grepl("high", cell), "High", "Off")
  ) %>%
  select(persona, reasoning, individual_brier, hard_prevalence_mae) %>%
  pivot_longer(c(individual_brier, hard_prevalence_mae), names_to = "metric", values_to = "value") %>%
  mutate(
    metric = recode(individual_brier = "Brier", hard_prevalence_mae = "Hard population MAE", .x = metric),
    value = if_else(metric == "Hard population MAE", 100 * value, value),
    reasoning = factor(reasoning, levels = c("Off", "High"))
  )
stopifnot(nrow(f3) == 8)

p3 <- ggplot(f3, aes(reasoning, value, group = persona, colour = persona)) +
  geom_line(linewidth = 0.9) +
  geom_point(size = 2.7) +
  geom_text(
    data = f3 %>% filter(reasoning == "High"),
    aes(label = persona), hjust = -0.18, size = 3.05, show.legend = FALSE
  ) +
  facet_wrap(~metric, scales = "free_y", nrow = 1) +
  scale_colour_manual(values = c(Thin = "#7A6FF0", Rich = pal[["DeepSeek"]])) +
  scale_x_discrete(expand = expansion(mult = c(0.06, 0.24))) +
  labs(x = NULL, y = NULL) +
  base_theme +
  theme(legend.position = "none")
savefig(p3, "fig03_deepseek_factorial", 7.4, 3.55)

# 4. Age-specific reasoning effects. Direct labels at the oldest group avoid a legend.
ag <- age %>%
  filter(metric == "probability_prevalence_mae") %>%
  mutate(
    age_group = factor(age_group, levels = c("15-24", "25-34", "35-44", "45-59", "60+")),
    estimate = 100 * estimate,
    ci_low = 100 * ci_low,
    ci_high = 100 * ci_high
  )

p4 <- ggplot(ag, aes(age_group, estimate, group = model, colour = model)) +
  geom_hline(yintercept = 0, colour = "grey58", linewidth = 0.35) +
  geom_ribbon(aes(ymin = ci_low, ymax = ci_high, fill = model), alpha = 0.08, colour = NA) +
  geom_line(linewidth = 0.85) +
  geom_point(size = 2.25) +
  geom_text_repel(
    data = ag %>% filter(age_group == "60+"),
    aes(label = model), direction = "y", hjust = 0, nudge_x = 0.25,
    show.legend = FALSE, size = 3, seed = 42
  ) +
  scale_colour_manual(values = pal) +
  scale_fill_manual(values = pal) +
  scale_x_discrete(expand = expansion(mult = c(0.04, 0.18))) +
  labs(x = "Age", y = "Reasoning effect on population MAE (pp)") +
  base_theme +
  theme(legend.position = "none")
savefig(p4, "fig04_age_gradient", 7, 4.15)

# 5. Joint-population fingerprint. The left glyph encodes the six yes/no outcomes;
# the right heatmap shows each pattern's weighted population share.
usecells <- c("human", "qwen_off", "qwen_medium", "deepseek_rich_off", "deepseek_rich_high")
cell_names <- c(
  human = "Human",
  qwen_off = "Qwen off",
  qwen_medium = "Qwen medium",
  deepseek_rich_off = "DeepSeek off",
  deepseek_rich_high = "DeepSeek high"
)

top_patterns <- patt %>%
  filter(cell == "human") %>%
  arrange(desc(share)) %>%
  slice_head(n = 10) %>%
  pull(pattern)
top_patterns <- unique(c("110111", "110110", top_patterns))
top_patterns <- top_patterns[seq_len(min(10, length(top_patterns)))]
pattern_rank <- paste0("P", seq_along(top_patterns))
names(pattern_rank) <- top_patterns

pattern_bits <- tibble(pattern = top_patterns, rank = unname(pattern_rank[top_patterns])) %>%
  rowwise() %>%
  mutate(bits = list(as.integer(strsplit(pattern, "")[[1]]))) %>%
  ungroup() %>%
  unnest_wider(bits, names_sep = "") %>%
  rename(Mob = bits1, `Mob 3m` = bits2, Comp = bits3, Net = bits4, `Net 3m` = bits5, Copy = bits6) %>%
  pivot_longer(c(Mob, `Mob 3m`, Comp, Net, `Net 3m`, Copy), names_to = "outcome", values_to = "yes") %>%
  mutate(
    rank = factor(rank, levels = rev(unname(pattern_rank[top_patterns]))),
    outcome = factor(outcome, levels = c("Mob", "Mob 3m", "Comp", "Net", "Net 3m", "Copy"))
  )

shares <- patt %>%
  filter(cell %in% usecells, pattern %in% top_patterns) %>%
  mutate(
    rank = factor(unname(pattern_rank[pattern]), levels = rev(unname(pattern_rank[top_patterns]))),
    cell = factor(unname(cell_names[cell]), levels = unname(cell_names))
  )

p5a <- ggplot(pattern_bits, aes(outcome, rank, fill = factor(yes))) +
  geom_tile(colour = "white", linewidth = 0.48) +
  scale_fill_manual(values = c(`0` = "grey96", `1` = "grey20")) +
  labs(x = NULL, y = NULL) +
  base_theme +
  theme(
    legend.position = "none", panel.grid = element_blank(),
    axis.text.x = element_text(size = 7.5, angle = 45, hjust = 1),
    axis.text.y = element_text(size = 8)
  )

p5b <- ggplot(shares, aes(cell, rank, fill = share)) +
  geom_tile(colour = "white", linewidth = 0.48) +
  geom_text(aes(label = if_else(share >= 0.025, percent(share, accuracy = 1), "")), size = 2.55) +
  scale_fill_gradient(low = "grey97", high = "grey20") +
  labs(x = NULL, y = NULL) +
  base_theme +
  theme(
    legend.position = "none", panel.grid = element_blank(), axis.text.y = element_blank(),
    axis.text.x = element_text(size = 7.8, angle = 28, hjust = 1)
  )

p5 <- p5a + p5b + plot_layout(widths = c(1.05, 1.35))
savefig(p5, "fig05_population_fingerprint", 8.2, 4.9)

# 6. Individual-versus-joint fidelity landscape. No join is required in the finalized schema,
# avoiding the duplicate joint_tv column that caused the previous workflow failure.
c6 <- cell %>%
  filter(!is.na(individual_brier), !is.na(joint_tv)) %>%
  mutate(
    label = case_when(
      cell == "luna_thin" ~ "Luna thin",
      cell == "luna_rich" ~ "Luna rich",
      cell == "claude_thin" ~ "Claude thin",
      cell == "claude_rich" ~ "Claude rich",
      cell == "qwen_off" ~ "Qwen off",
      cell == "qwen_medium" ~ "Qwen medium",
      cell == "deepseek_rich_off" ~ "DeepSeek off",
      cell == "deepseek_rich_high" ~ "DeepSeek high",
      cell == "baseline_weighted_prevalence" ~ "Prevalence",
      cell == "baseline_logistic" ~ "Logistic",
      cell == "baseline_regularized_logistic" ~ "Logistic",
      cell == "baseline_gradient_boosting" ~ "Gradient boost",
      cell == "baseline_random_forest" ~ "Random forest",
      TRUE ~ NA_character_
    ),
    family = if_else(method_class == "LLM", "LLM", "Supervised")
  ) %>%
  filter(!is.na(label))

frontier <- c6 %>%
  arrange(individual_brier, joint_tv) %>%
  mutate(best_so_far = cummin(joint_tv)) %>%
  filter(joint_tv <= best_so_far + 1e-12)

p6 <- ggplot(c6, aes(individual_brier, joint_tv)) +
  geom_path(data = frontier, aes(group = 1), colour = "grey72", linewidth = 0.55) +
  geom_point(aes(shape = family), size = 3.1, colour = "grey20", fill = "white", stroke = 0.9) +
  geom_text_repel(aes(label = label), size = 2.95, box.padding = 0.38, seed = 43) +
  scale_shape_manual(values = c(LLM = 16, Supervised = 22)) +
  labs(x = "Individual Brier", y = "Joint TV distance", shape = NULL) +
  base_theme
savefig(p6, "fig06_fidelity_landscape", 7.2, 5)

# 7. DeepSeek confidence-tail trade-off.
d7 <- cell %>%
  filter(cell %in% c("deepseek_rich_off", "deepseek_rich_high")) %>%
  select(cell, individual_brier, log_loss) %>%
  left_join(tails, by = "cell") %>%
  mutate(condition = factor(if_else(grepl("high", cell), "High", "Off"), levels = c("Off", "High"))) %>%
  select(condition, individual_brier, log_loss, wrong_extreme_share) %>%
  pivot_longer(-condition, names_to = "metric", values_to = "value") %>%
  mutate(
    metric = recode(metric, individual_brier = "Brier", log_loss = "Log loss", wrong_extreme_share = "Wrong extreme (%)"),
    value = if_else(metric == "Wrong extreme (%)", 100 * value, value)
  )

p7 <- ggplot(d7, aes(condition, value, group = 1)) +
  geom_line(colour = "grey70", linewidth = 0.75) +
  geom_point(size = 2.8, colour = pal[["DeepSeek"]]) +
  facet_wrap(~metric, scales = "free_y", nrow = 1) +
  labs(x = NULL, y = NULL) +
  base_theme +
  theme(legend.position = "none")
savefig(p7, "fig07_overconfidence", 7.6, 3.15)

# 8. Outcome-level reasoning effects.
h8 <- oe %>%
  filter(
    contrast %in% c("qwen_medium_minus_off", "deepseek_rich_high_minus_off"),
    metric %in% c("brier", "probability_prevalence_abs_error", "hard_prevalence_abs_error")
  ) %>%
  mutate(
    model = if_else(grepl("qwen", contrast), "Qwen", "DeepSeek"),
    metric = recode(metric, brier = "Brier", probability_prevalence_abs_error = "Prob. MAE", hard_prevalence_abs_error = "Hard MAE"),
    effect = 100 * effect,
    outcome = recode(
      outcome,
      mobile_ability = "Mobile", mobile_3m = "Mobile 3m", computer_ability = "Computer",
      internet_ability = "Internet", internet_3m = "Internet 3m", copy_paste = "Copy/paste"
    )
  )

max_abs <- max(abs(h8$effect), na.rm = TRUE)
p8 <- ggplot(h8, aes(metric, outcome, fill = effect)) +
  geom_tile(colour = "white", linewidth = 0.52) +
  geom_text(aes(label = sprintf("%+.1f", effect)), size = 2.65) +
  facet_wrap(~model, nrow = 1) +
  scale_fill_gradient2(low = "#009E73", mid = "white", high = "#D55E00", midpoint = 0, limits = c(-max_abs, max_abs)) +
  labs(x = NULL, y = NULL) +
  base_theme +
  theme(legend.position = "none", panel.grid = element_blank())
savefig(p8, "fig08_outcome_effects", 7.6, 4.5)

figure_index <- c(
  "fig01_micro_macro",
  "fig02_reasoning_reversal",
  "fig03_deepseek_factorial",
  "fig04_age_gradient",
  "fig05_population_fingerprint",
  "fig06_fidelity_landscape",
  "fig07_overconfidence",
  "fig08_outcome_effects"
)
writeLines(figure_index, file.path(outdir, "FIGURE_INDEX.txt"))

for (name in figure_index) {
  for (ext in c("pdf", "svg", "png")) {
    path <- file.path(outdir, paste0(name, ".", ext))
    if (!file.exists(path) || file.info(path)$size <= 1000) stop(paste("Figure output missing or unexpectedly small:", path))
  }
}
cat("FINAL_R_FIGURE_SUITE_PASS\n")
