#!/usr/bin/env Rscript

for (pkg in c("tidyverse", "ggplot2")) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org/")
    library(pkg, character.only = TRUE)
  }
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  cat("Uso: Rscript gerar_graficos.R <diretorio>\n")
  cat("Exemplo: Rscript gerar_graficos.R resultados/cpu\n")
  cat("         Rscript gerar_graficos.R resultados/mem\n")
  quit(status = 1)
}

base_dir <- args[1]
if (!dir.exists(base_dir)) {
  cat("Diretório não encontrado:", base_dir, "\n")
  quit(status = 1)
}

subdirs <- list.dirs(base_dir, recursive = FALSE, full.names = FALSE)
subdirs <- subdirs[grepl("^cenario_", subdirs)]

if (length(subdirs) == 0) {
  cat("Nenhum subdiretório cenario_* encontrado em", base_dir, "\n")
  quit(status = 1)
}

cat("\n📊 Gerando gráficos de stress testing...\n")
cat("Diretório:", base_dir, "\n")
cat("Cenários:", paste(subdirs, collapse = ", "), "\n\n")

# --- Detectar tipo de experimento pelos nomes dos cenários ---

cpus_variam <- length(unique(str_extract(subdirs, "\\d+cpu"))) > 1
rams_variam <- length(unique(str_extract(subdirs, "\\d+[gm]b"))) > 1

if (cpus_variam && !rams_variam) {
  tipo <- "cpu"
  recurso_label <- "CPU"
} else if (rams_variam && !cpus_variam) {
  tipo <- "mem"
  recurso_label <- "RAM"
} else {
  tipo <- "misto"
  recurso_label <- "Config"
}

cat("Recurso variável detectado:", recurso_label, "\n\n")

# --- Gerar label legível para cada cenário ---

gerar_label <- function(dir_name) {
  cpus <- str_extract(dir_name, "\\d+(?=cpu)")
  ram <- str_extract(dir_name, "\\d+[gm]b")
  if (is.na(ram)) ram <- "??"
  ram <- toupper(ram)
  paste0(cpus, " CPU / ", ram)
}

labels <- sapply(subdirs, gerar_label)

# --- Paleta de cores (até 6 cenários) ---

paleta_base <- c("#E74C3C", "#F39C12", "#27AE60", "#3498DB", "#9B59B6", "#1ABC9C")
cores <- setNames(paleta_base[seq_along(labels)], labels)

# --- Detectar nome do CSV de stress ---

primeiro_dir <- file.path(base_dir, subdirs[1])
csvs <- list.files(primeiro_dir, pattern = "teste_stress.*\\.csv$")
csvs <- csvs[csvs != "vmstat.csv"]
if (length(csvs) == 0) {
  cat("Nenhum CSV de stress encontrado em", primeiro_dir, "\n")
  quit(status = 1)
}
csv_stress_name <- csvs[1]
cat("CSV de stress:", csv_stress_name, "\n\n")

# --- Carregar dados de stress ---

dados <- data.frame()

for (dir_name in subdirs) {
  path <- file.path(base_dir, dir_name, csv_stress_name)
  if (file.exists(path)) {
    df <- read.csv(path)
    df$config <- gerar_label(dir_name)
    dados <- rbind(dados, df)
    cat("  ✓", dir_name, "\n")
  } else {
    cat("  ✗", dir_name, "- CSV não encontrado\n")
  }
}

if (nrow(dados) == 0) {
  cat("Nenhum dado carregado!\n")
  quit(status = 1)
}

# --- Ordenar configs de forma natural (por recurso variável) ---

ordem <- labels[order(as.numeric(str_extract(
  if (tipo == "cpu") subdirs else subdirs,
  if (tipo == "cpu") "\\d+(?=cpu)" else "\\d+(?=[gm]b)"
)))]
dados$config <- factor(dados$config, levels = ordem)

# --- Carregar dados de vmstat ---

vmstat_dados <- data.frame()

for (dir_name in subdirs) {
  path <- file.path(base_dir, dir_name, "vmstat.csv")
  if (file.exists(path)) {
    df_vmstat <- read.csv(path, skip = 2, header = FALSE)
    colnames(df_vmstat) <- c("cpu_user", "cpu_system", "cpu_idle", "memory_free", "buffer", "cache")
    df_vmstat <- df_vmstat %>%
      mutate(across(everything(), as.numeric)) %>%
      filter(!is.na(cpu_user))

    demandas_teste <- sort(unique(dados$num_requisicoes))
    n_demandas <- length(demandas_teste)
    chunk_size <- nrow(df_vmstat) %/% n_demandas

    for (i in seq_along(demandas_teste)) {
      start_idx <- (i - 1) * chunk_size + 1
      end_idx <- if (i == n_demandas) nrow(df_vmstat) else i * chunk_size
      chunk <- df_vmstat[start_idx:end_idx, ]

      if (nrow(chunk) > 0) {
        vm_row <- data.frame(
          config = gerar_label(dir_name),
          num_requisicoes = demandas_teste[i],
          cpu_user = mean(chunk$cpu_user, na.rm = TRUE),
          cpu_system = mean(chunk$cpu_system, na.rm = TRUE),
          cpu_idle = mean(chunk$cpu_idle, na.rm = TRUE),
          memory_free = mean(chunk$memory_free, na.rm = TRUE)
        )
        vmstat_dados <- rbind(vmstat_dados, vm_row)
      }
    }
  }
}

if (nrow(vmstat_dados) > 0) {
  vmstat_dados$config <- factor(vmstat_dados$config, levels = ordem)
}

# --- Diretório de saída ---

out_dir <- file.path(base_dir, "graficos")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

breaks_x <- sort(unique(dados$num_requisicoes))

cat("\nGerando gráficos...\n\n")

# 1. Latência vs Demanda
cat("  • Latência vs Demanda...")
p1 <- ggplot(dados, aes(x = num_requisicoes, y = tempo_medio_ms, color = config, group = config)) +
  geom_line(linewidth = 1) + geom_point(size = 3) +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  labs(title = "Latência Média vs Demanda", x = "Requisições Simultâneas",
       y = "Latência Média (ms)", color = recurso_label) +
  theme_minimal() +
  theme(plot.title = element_text(size = 14, face = "bold"), legend.position = "bottom")
ggsave(file.path(out_dir, "01_latencia_vs_demanda.png"), p1, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

# 2. Throughput vs Demanda
cat("  • Throughput vs Demanda...")
p2 <- ggplot(dados, aes(x = num_requisicoes, y = req_por_segundo, color = config, group = config)) +
  geom_line(linewidth = 1) + geom_point(size = 3) +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  labs(title = "Throughput vs Demanda", x = "Requisições Simultâneas",
       y = "Requisições por Segundo", color = recurso_label) +
  theme_minimal() +
  theme(plot.title = element_text(size = 14, face = "bold"), legend.position = "bottom")
ggsave(file.path(out_dir, "02_throughput_vs_demanda.png"), p2, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

# 3. Percentis de Latência
cat("  • Percentis de Latência...")
dados_long <- dados %>%
  select(config, num_requisicoes, tempo_medio_ms, tempo_p95_ms, tempo_p99_ms) %>%
  pivot_longer(cols = c(tempo_medio_ms, tempo_p95_ms, tempo_p99_ms),
               names_to = "metrica", values_to = "latencia") %>%
  mutate(metrica = factor(metrica,
    levels = c("tempo_medio_ms", "tempo_p95_ms", "tempo_p99_ms"),
    labels = c("Média", "P95", "P99")))

p3 <- ggplot(dados_long, aes(x = num_requisicoes, y = latencia, fill = metrica)) +
  geom_bar(stat = "identity", position = "dodge", alpha = 0.8) +
  facet_wrap(~config, nrow = 2) +
  scale_x_continuous(breaks = breaks_x) +
  labs(title = "Distribuição de Latência (Média, P95, P99)", x = "Requisições Simultâneas",
       y = "Latência (ms)", fill = "Métrica") +
  theme_minimal() +
  theme(plot.title = element_text(size = 14, face = "bold"), legend.position = "bottom",
        axis.text.x = element_text(angle = 45, hjust = 1))
ggsave(file.path(out_dir, "03_percentis_latencia.png"), p3, width = 12, height = 8, dpi = 300)
cat(" ✓\n")

# 4. Degradação
cat("  • Taxa de Degradação...")
dados_deg <- dados %>%
  group_by(config) %>%
  mutate(baseline = first(tempo_medio_ms), degradacao = tempo_medio_ms / baseline) %>%
  ungroup()

p4 <- ggplot(dados_deg, aes(x = num_requisicoes, y = degradacao, color = config, group = config)) +
  geom_line(linewidth = 1) + geom_point(size = 3) +
  geom_hline(yintercept = 1, linetype = "dashed", color = "gray50") +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  labs(title = "Taxa de Degradação de Latência", x = "Requisições Simultâneas",
       y = "Degradação (relativo ao baseline)", color = recurso_label) +
  theme_minimal() +
  theme(plot.title = element_text(size = 14, face = "bold"), legend.position = "bottom")
ggsave(file.path(out_dir, "04_degradacao_latencia.png"), p4, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

# 5. CPU Usuário vs Demanda
if (nrow(vmstat_dados) > 0) {
  cat("  • CPU Usuário vs Demanda...")
  p5 <- ggplot(vmstat_dados, aes(x = num_requisicoes, y = cpu_user, color = config, group = config)) +
    geom_line(linewidth = 1) + geom_point(size = 3) +
    scale_color_manual(values = cores) +
    scale_x_continuous(breaks = breaks_x) +
    ylim(0, 105) +
    labs(title = "CPU Usuário vs Demanda", x = "Requisições Simultâneas",
         y = "CPU Usuário (%)", color = recurso_label) +
    theme_minimal() +
    theme(plot.title = element_text(size = 14, face = "bold"), legend.position = "bottom")
  ggsave(file.path(out_dir, "05_cpu_usuario_vs_demanda.png"), p5, width = 10, height = 6, dpi = 300)
  cat(" ✓\n")

  # 6. CPU Total vs Demanda
  cat("  • CPU Total vs Demanda...")
  vmstat_dados$cpu_total <- vmstat_dados$cpu_user + vmstat_dados$cpu_system

  p6 <- ggplot(vmstat_dados, aes(x = num_requisicoes, y = cpu_total, color = config, group = config)) +
    geom_line(linewidth = 1) + geom_point(size = 3) +
    scale_color_manual(values = cores) +
    scale_x_continuous(breaks = breaks_x) +
    ylim(0, 105) +
    labs(title = "CPU Total vs Demanda", x = "Requisições Simultâneas",
         y = "CPU Total (%)", color = recurso_label) +
    theme_minimal() +
    theme(plot.title = element_text(size = 14, face = "bold"), legend.position = "bottom")
  ggsave(file.path(out_dir, "06_cpu_total_vs_demanda.png"), p6, width = 10, height = 6, dpi = 300)
  cat(" ✓\n")

  # 7. Memória Livre vs Demanda
  cat("  • Memória Livre vs Demanda...")
  p7 <- ggplot(vmstat_dados, aes(x = num_requisicoes, y = memory_free / 1024, color = config, group = config)) +
    geom_line(linewidth = 1) + geom_point(size = 3) +
    scale_color_manual(values = cores) +
    scale_x_continuous(breaks = breaks_x) +
    labs(title = "Memória Livre vs Demanda", x = "Requisições Simultâneas",
         y = "Memória Livre (MB)", color = recurso_label) +
    theme_minimal() +
    theme(plot.title = element_text(size = 14, face = "bold"), legend.position = "bottom")
  ggsave(file.path(out_dir, "07_memoria_livre_vs_demanda.png"), p7, width = 10, height = 6, dpi = 300)
  cat(" ✓\n")
} else {
  cat("  ⚠ Sem dados de vmstat, pulando gráficos 5-7\n")
}

# --- Carregar dados de iostat ---

iostat_dados <- data.frame()

for (dir_name in subdirs) {
  path <- file.path(base_dir, dir_name, "iostat.csv")
  if (file.exists(path)) {
    df_io <- read.csv(path)
    df_io <- df_io %>% mutate(across(everything(), as.numeric)) %>% filter(!is.na(w_s))

    demandas_teste <- sort(unique(dados$num_requisicoes))
    n_demandas <- length(demandas_teste)
    chunk_size <- nrow(df_io) %/% n_demandas

    for (i in seq_along(demandas_teste)) {
      start_idx <- (i - 1) * chunk_size + 1
      end_idx <- if (i == n_demandas) nrow(df_io) else i * chunk_size
      chunk <- df_io[start_idx:end_idx, ]

      if (nrow(chunk) > 0) {
        io_row <- data.frame(
          config = gerar_label(dir_name),
          num_requisicoes = demandas_teste[i],
          r_s = mean(chunk$r_s, na.rm = TRUE),
          w_s = mean(chunk$w_s, na.rm = TRUE),
          rkB_s = mean(chunk$rkB_s, na.rm = TRUE),
          wkB_s = mean(chunk$wkB_s, na.rm = TRUE),
          await_ms = mean(chunk$await_ms, na.rm = TRUE),
          util_pct = mean(chunk$util_pct, na.rm = TRUE)
        )
        iostat_dados <- rbind(iostat_dados, io_row)
      }
    }
  }
}

if (nrow(iostat_dados) > 0) {
  iostat_dados$config <- factor(iostat_dados$config, levels = ordem)
  iostat_dados$iops <- iostat_dados$r_s + iostat_dados$w_s
  iostat_dados$throughput_kb <- iostat_dados$rkB_s + iostat_dados$wkB_s

  # 8. Gráfico de facetas: IOPS, Await, Utilização
  cat("  • Métricas de Disco (facetas)...")
  io_facet <- iostat_dados %>%
    select(config, num_requisicoes, iops, await_ms, util_pct) %>%
    pivot_longer(cols = c(iops, await_ms, util_pct),
                 names_to = "metrica", values_to = "valor") %>%
    mutate(metrica = factor(metrica,
      levels = c("iops", "await_ms", "util_pct"),
      labels = c("IOPS (leitura + escrita)", "Await (ms)", "Utilização (%)")))

  p8 <- ggplot(io_facet, aes(x = num_requisicoes, y = valor, color = config, group = config)) +
    geom_line(linewidth = 1) + geom_point(size = 2.5) +
    scale_color_manual(values = cores) +
    scale_x_continuous(breaks = breaks_x) +
    facet_wrap(~metrica, ncol = 1, scales = "free_y") +
    labs(title = "Métricas de Disco vs Demanda", x = "Requisições Simultâneas",
         y = NULL, color = recurso_label) +
    theme_minimal() +
    theme(plot.title = element_text(size = 14, face = "bold"), legend.position = "bottom",
          strip.text = element_text(size = 11, face = "bold"))
  ggsave(file.path(out_dir, "08_metricas_disco_vs_demanda.png"), p8, width = 10, height = 12, dpi = 300)
  cat(" ✓\n")
} else {
  cat("  ⚠ Sem dados de iostat, pulando gráfico de disco\n")
}

cat("\n✅ Gráficos gerados em:", out_dir, "\n\n")
