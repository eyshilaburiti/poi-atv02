#!/usr/bin/env Rscript

library(tidyverse)
library(ggplot2)

for (pkg in c("tidyverse", "ggplot2")) {
  if (!require(pkg, character.only = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org/")
    library(pkg, character.only = TRUE)
  }
}

cat("\n📊 Gerando gráficos de stress testing...\n\n")

cores <- c(
  "1 CPU / 1GB" = "#E74C3C",
  "2 CPU / 1GB" = "#F39C12",
  "3 CPU / 1GB" = "#27AE60",
  "4 CPU / 1GB" = "#3498DB"
)

dados <- data.frame()

cenarios_map <- list(
  "cenario_1cpu_1gb" = "1 CPU / 1GB",
  "cenario_2cpu_1gb" = "2 CPU / 1GB",
  "cenario_3cpu_1gb" = "3 CPU / 1GB",
  "cenario_4cpu_1gb" = "4 CPU / 1GB"
)

for (dir_name in names(cenarios_map)) {
  path <- file.path("resultados", dir_name, "teste_stress.csv")
  if (file.exists(path)) {
    df <- read.csv(path)
    df$config <- cenarios_map[[dir_name]]
    dados <- rbind(dados, df)
    cat("✓", dir_name, "\n")
  } else {
    cat("✗", dir_name, "não encontrado\n")
  }
}

vmstat_dados <- data.frame()

for (dir_name in names(cenarios_map)) {
  path <- file.path("resultados", dir_name, "vmstat.csv")
  if (file.exists(path)) {
    df_vmstat <- read.csv(path, skip = 2, header = FALSE)
    colnames(df_vmstat) <- c("cpu_user", "cpu_system", "cpu_idle", "memory_free", "buffer", "cache")
    df_vmstat <- df_vmstat %>%
      filter(!is.na(as.numeric(cpu_user)))

    df_vmstat$cpu_user <- as.numeric(df_vmstat$cpu_user)
    df_vmstat$cpu_system <- as.numeric(df_vmstat$cpu_system)
    df_vmstat$cpu_idle <- as.numeric(df_vmstat$cpu_idle)
    df_vmstat$memory_free <- as.numeric(df_vmstat$memory_free)

    df_vmstat <- df_vmstat %>% filter(!is.na(cpu_user))

    demandas_teste <- sort(unique(dados$num_requisicoes))
    n_demandas <- length(demandas_teste)

    chunk_size <- nrow(df_vmstat) %/% n_demandas

    for (i in seq_along(demandas_teste)) {
      start_idx <- (i - 1) * chunk_size + 1
      end_idx <- if (i == n_demandas) nrow(df_vmstat) else i * chunk_size

      chunk <- df_vmstat[start_idx:end_idx, ]

      if (nrow(chunk) > 0) {
        vm_row <- data.frame(
          config = cenarios_map[[dir_name]],
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
  vmstat_dados$config <- factor(vmstat_dados$config, levels = c("1 CPU / 1GB", "2 CPU / 1GB", "3 CPU / 1GB", "4 CPU / 1GB"))
}

if (nrow(dados) == 0) {
  cat("❌ Nenhum dado carregado!\n")
  quit(status = 1)
}

dados$config <- factor(dados$config, levels = c("1 CPU / 1GB", "2 CPU / 1GB", "3 CPU / 1GB", "4 CPU / 1GB"))
dir.create("resultados/graficos", showWarnings = FALSE)

cat("Gerando gráficos...\n\n")

# Gráfico 1: Latência vs Demanda
cat("  • Latência vs Demanda...")
breaks_x <- sort(unique(dados$num_requisicoes))
p1 <- ggplot(dados, aes(x = num_requisicoes, y = tempo_medio_ms, color = config, group = config)) +
  geom_line(linewidth = 1) +
  geom_point(size = 3) +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  labs(
    title = "Latência Média vs Demanda",
    x = "Requisições Simultâneas",
    y = "Latência Média (ms)",
    color = "Configuração"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    legend.position = "bottom"
  )
ggsave("resultados/graficos/01_latencia_vs_demanda.png", p1, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

# Gráfico 2: Throughput vs Demanda
cat("  • Throughput vs Demanda...")
p2 <- ggplot(dados, aes(x = num_requisicoes, y = req_por_segundo, color = config, group = config)) +
  geom_line(linewidth = 1) +
  geom_point(size = 3) +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  labs(
    title = "Throughput vs Demanda",
    x = "Requisições Simultâneas",
    y = "Requisições por Segundo",
    color = "Configuração"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    legend.position = "bottom"
  )
ggsave("resultados/graficos/02_throughput_vs_demanda.png", p2, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

# Gráfico 3: Percentis
cat("  • Percentis de Latência...")
dados_long <- dados %>%
  select(config, num_requisicoes, tempo_medio_ms, tempo_p95_ms, tempo_p99_ms) %>%
  pivot_longer(
    cols = c(tempo_medio_ms, tempo_p95_ms, tempo_p99_ms),
    names_to = "metrica",
    values_to = "latencia"
  ) %>%
  mutate(metrica = factor(metrica,
                          levels = c("tempo_medio_ms", "tempo_p95_ms", "tempo_p99_ms"),
                          labels = c("Média", "P95", "P99")))

p3 <- ggplot(dados_long, aes(x = num_requisicoes, y = latencia, fill = metrica)) +
  geom_bar(stat = "identity", position = "dodge", alpha = 0.8) +
  facet_wrap(~config, nrow = 2) +
  scale_x_continuous(breaks = breaks_x) +
  labs(
    title = "Distribuição de Latência (Média, P95, P99)",
    x = "Requisições Simultâneas",
    y = "Latência (ms)",
    fill = "Métrica"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    legend.position = "bottom",
    axis.text.x = element_text(angle = 45, hjust = 1)
  )
ggsave("resultados/graficos/03_percentis_latencia.png", p3, width = 12, height = 8, dpi = 300)
cat(" ✓\n")

# Gráfico 4: Degradação
cat("  • Taxa de Degradação...")
dados_deg <- dados %>%
  group_by(config) %>%
  mutate(baseline = first(tempo_medio_ms), degradacao = tempo_medio_ms / baseline) %>%
  ungroup()

p4 <- ggplot(dados_deg, aes(x = num_requisicoes, y = degradacao, color = config, group = config)) +
  geom_line(linewidth = 1) +
  geom_point(size = 3) +
  geom_hline(yintercept = 1, linetype = "dashed", color = "gray50") +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  labs(
    title = "Taxa de Degradação de Latência",
    x = "Requisições Simultâneas",
    y = "Degradação (relativo ao baseline)",
    color = "Configuração"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    legend.position = "bottom"
  )
ggsave("resultados/graficos/04_degradacao_latencia.png", p4, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

# Gráfico 5: CPU Usuário vs Demanda
cat("  • CPU Usuário vs Demanda...")
p5 <- ggplot(vmstat_dados, aes(x = num_requisicoes, y = cpu_user, color = config, group = config)) +
  geom_line(linewidth = 1) +
  geom_point(size = 3) +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  ylim(0, 105) +
  labs(
    title = "CPU Usuário vs Demanda",
    x = "Requisições Simultâneas",
    y = "CPU Usuário (%)",
    color = "Configuração"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    legend.position = "bottom"
  )
ggsave("resultados/graficos/05_cpu_usuario_vs_demanda.png", p5, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

# Gráfico 6: CPU Total (User + System) vs Demanda
cat("  • CPU Total vs Demanda...")
vmstat_dados$cpu_total <- vmstat_dados$cpu_user + vmstat_dados$cpu_system

p6 <- ggplot(vmstat_dados, aes(x = num_requisicoes, y = cpu_total, color = config, group = config)) +
  geom_line(linewidth = 1) +
  geom_point(size = 3) +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  ylim(0, 105) +
  labs(
    title = "CPU Total vs Demanda",
    x = "Requisições Simultâneas",
    y = "CPU Total (%)",
    color = "Configuração"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    legend.position = "bottom"
  )
ggsave("resultados/graficos/06_cpu_total_vs_demanda.png", p6, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

# Gráfico 7: Memória Livre vs Demanda
cat("  • Memória Livre vs Demanda...")
p7 <- ggplot(vmstat_dados, aes(x = num_requisicoes, y = memory_free / 1024, color = config, group = config)) +
  geom_line(linewidth = 1) +
  geom_point(size = 3) +
  scale_color_manual(values = cores) +
  scale_x_continuous(breaks = breaks_x) +
  labs(
    title = "Memória Livre vs Demanda",
    x = "Requisições Simultâneas",
    y = "Memória Livre (MB)",
    color = "Configuração"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    legend.position = "bottom"
  )
ggsave("resultados/graficos/07_memoria_livre_vs_demanda.png", p7, width = 10, height = 6, dpi = 300)
cat(" ✓\n")

cat("\n✅ Gráficos gerados em: resultados/graficos/\n\n")
cat("Arquivos:\n")
cat("  - 01_latencia_vs_demanda.png\n")
cat("  - 02_throughput_vs_demanda.png\n")
cat("  - 03_percentis_latencia.png\n")
cat("  - 04_degradacao_latencia.png\n")
cat("  - 05_cpu_usuario_vs_demanda.png\n")
cat("  - 06_cpu_total_vs_demanda.png\n")
cat("  - 07_memoria_livre_vs_demanda.png\n\n")
