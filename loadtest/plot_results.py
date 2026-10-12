"""
Gera os gráficos comparativos entre cenários a partir de results/resultados.jsonl
e uma tabela em Markdown (results/tabela.md) para colar no relatório.

Requer matplotlib:  sudo apt install -y python3-matplotlib
Uso:               python3 loadtest/plot_results.py
"""
import json
import os
import sys
from collections import OrderedDict

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("matplotlib não encontrado. Instale com:  sudo apt install -y python3-matplotlib")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
OUTDIR = os.path.join(RESULTS, "graficos")

# Paleta categórica (ordem fixa) + marcador diferente por cenário,
# para não depender só da cor.
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MARKERS = ["o", "s", "^", "D", "v", "P"]

CHARTS = [
    ("rps", "Vazão (requisições/s)", "1_vazao_rps.png"),
    ("lat_mean_ms", "Tempo de resposta médio (ms)", "2_latencia_media.png"),
    ("lat_p95_ms", "Tempo de resposta p95 (ms)", "3_latencia_p95.png"),
    ("cpu_avg_pct", "Uso médio de CPU da VM (%)", "4_cpu_vm.png"),
    ("mem_used_avg_mb", "Memória usada na VM (MB)", "5_memoria_vm.png"),
    ("error_pct", "Requisições com erro (%)", "6_erros.png"),
]


def load(path):
    data = OrderedDict()
    with open(path) as f:
        for row in map(json.loads, filter(str.strip, f)):
            data.setdefault(row["scenario"], []).append(row)
    for rows in data.values():
        rows.sort(key=lambda r: int(r["users"]))
    return data


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def label(scn, rows):
    d = rows[0].get("descricao") or f"{rows[0]['ncpu']} vCPU, {rows[0]['mem_total_mb']} MB"
    return f"{scn} ({d})"


def style(ax, ylabel):
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Usuários concorrentes (demanda)")
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#e3e2dc", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#9a998f")
    ax.tick_params(colors="#55544c")
    ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_ylim(bottom=0)


def plot_metric(ax, data, key, ylabel):
    users_all = set()
    for i, (scn, rows) in enumerate(data.items()):
        pts = [(int(r["users"]), num(r.get(key))) for r in rows if num(r.get(key)) is not None]
        if not pts:
            continue
        xs, ys = zip(*pts)
        users_all.update(xs)
        ax.plot(xs, ys, color=COLORS[i % len(COLORS)], marker=MARKERS[i % len(MARKERS)],
                markersize=6, linewidth=2, label=label(scn, rows))
    style(ax, ylabel)
    if users_all:
        ax.set_xticks(sorted(users_all))


def main():
    path = os.path.join(RESULTS, sys.argv[1] if len(sys.argv) > 1 else "resultados.jsonl")
    if not os.path.exists(path):
        sys.exit(f"Arquivo {path} não encontrado. Rode os experimentos primeiro.")
    data = load(path)
    os.makedirs(OUTDIR, exist_ok=True)
    plt.rcParams.update({"font.size": 10})

    for key, ylabel, fname in CHARTS:
        fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
        plot_metric(ax, data, key, ylabel)
        ax.set_title(f"{ylabel} × demanda", loc="left", fontsize=12, color="#1f1e1b")
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(os.path.join(OUTDIR, fname))
        plt.close(fig)

    # Painel 2x2 com as quatro métricas principais (bom para o relatório)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), dpi=150)
    for ax, (key, ylabel, _) in zip(axes.flat, [CHARTS[0], CHARTS[2], CHARTS[3], CHARTS[4]]):
        plot_metric(ax, data, key, ylabel)
        ax.set_title(ylabel, loc="left", fontsize=11, color="#1f1e1b")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=min(4, len(labels)), frameon=False)
    fig.suptitle("Demanda × provisionamento × desempenho (app CPU-bound)", x=0.01, ha="left",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    fig.savefig(os.path.join(OUTDIR, "0_painel_comparativo.png"))
    plt.close(fig)

    # Tabela Markdown
    cols = [("Cenário", "scenario"), ("vCPU", "ncpu"), ("RAM (MB)", "mem_total_mb"),
            ("Usuários", "users"), ("Vazão (req/s)", "rps"), ("Lat. média (ms)", "lat_mean_ms"),
            ("Lat. p95 (ms)", "lat_p95_ms"), ("Erros (%)", "error_pct"),
            ("CPU VM (%)", "cpu_avg_pct"), ("RAM VM (MB)", "mem_used_avg_mb")]
    lines = ["| " + " | ".join(c for c, _ in cols) + " |",
             "|" + "---|" * len(cols)]
    for rows in data.values():
        for r in rows:
            lines.append("| " + " | ".join(str(r.get(k, "")) for _, k in cols) + " |")
    with open(os.path.join(RESULTS, "tabela.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Gráficos salvos em {OUTDIR}")
    print(f"Tabela salva em {os.path.join(RESULTS, 'tabela.md')}")


if __name__ == "__main__":
    main()
