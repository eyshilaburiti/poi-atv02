#!/usr/bin/env python3

"""
Converte a saída de 'iostat -dx 1' para CSV.

Cada bloco do iostat (separado por linha em branco) contém métricas
de todos os dispositivos. Este script calcula a média de cada bloco
e gera uma linha por amostra temporal.

Colunas extraídas:
  - r/s: leituras por segundo
  - w/s: escritas por segundo
  - rkB/s: KB lidos por segundo
  - wkB/s: KB escritos por segundo
  - await: tempo médio de espera (ms) por requisição de I/O
  - %util: porcentagem de utilização do disco
"""

import sys
import csv
import re


def parse_iostat(input_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()

    samples = []
    current_block = []
    header_cols = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Device") or stripped.startswith("Dispositivo"):
            header_cols = stripped.split()
            current_block = []
            continue

        if not stripped:
            if current_block and header_cols:
                samples.append(aggregate_block(header_cols, current_block))
                current_block = []
            continue

        if header_cols and not stripped.startswith("Linux") and re.match(r'^[a-zA-Z]', stripped):
            dev = stripped.split()[0]
            if not dev.startswith("loop") and dev != "sr0":
                current_block.append(stripped)

    if current_block and header_cols:
        samples.append(aggregate_block(header_cols, current_block))

    return samples


def find_col(header_cols, candidates):
    for c in candidates:
        if c in header_cols:
            return header_cols.index(c)
    return None


def aggregate_block(header_cols, block_lines):
    idx_rs = find_col(header_cols, ["r/s"])
    idx_ws = find_col(header_cols, ["w/s"])
    idx_rkb = find_col(header_cols, ["rkB/s", "rMB/s"])
    idx_wkb = find_col(header_cols, ["wkB/s", "wMB/s"])
    idx_await = find_col(header_cols, ["await", "w_await"])
    idx_util = find_col(header_cols, ["%util"])

    rs_vals, ws_vals, rkb_vals, wkb_vals, await_vals, util_vals = [], [], [], [], [], []

    for line in block_lines:
        parts = line.split()
        try:
            if idx_rs is not None:
                rs_vals.append(float(parts[idx_rs]))
            if idx_ws is not None:
                ws_vals.append(float(parts[idx_ws]))
            if idx_rkb is not None:
                rkb_vals.append(float(parts[idx_rkb]))
            if idx_wkb is not None:
                wkb_vals.append(float(parts[idx_wkb]))
            if idx_await is not None:
                await_vals.append(float(parts[idx_await]))
            if idx_util is not None:
                util_vals.append(float(parts[idx_util]))
        except (IndexError, ValueError):
            continue

    def avg(vals):
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    return {
        "r_s": avg(rs_vals),
        "w_s": avg(ws_vals),
        "rkB_s": avg(rkb_vals),
        "wkB_s": avg(wkb_vals),
        "await_ms": avg(await_vals),
        "util_pct": avg(util_vals),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 iostat_to_csv.py <iostat.log> [output.csv]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "iostat.csv"

    try:
        samples = parse_iostat(input_file)
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo '{input_file}' não encontrado")
        sys.exit(1)

    fieldnames = ["r_s", "w_s", "rkB_s", "wkB_s", "await_ms", "util_pct"]

    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)

    print(f"✅ Convertido com sucesso!")
    print(f"   Entrada:  {input_file}")
    print(f"   Saída:    {output_file}")
    print(f"   Amostras: {len(samples)}")
