#!/usr/bin/env python3

import sys
import csv

if len(sys.argv) < 2:
    print("Uso: python3 vmstat_to_csv.py <vmstat.log> [output.csv]")
    print("Exemplo: python3 vmstat_to_csv.py vmstat.log vmstat_metrics.csv")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2] if len(sys.argv) > 2 else "vmstat_metrics.csv"

try:
    with open(input_file, 'r') as f:
        lines = f.readlines()
except FileNotFoundError:
    print(f"❌ Erro: Arquivo '{input_file}' não encontrado")
    sys.exit(1)

data_lines = [l.strip() for l in lines if l.strip()]
if data_lines and 'r  b' in data_lines[0]:
    data_lines = data_lines[1:]

with open(output_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['cpu_user(%)', 'cpu_system(%)', 'cpu_idle(%)', 'memory_free(KB)', 'buffer(KB)', 'cache(KB)'])

    for i, line in enumerate(data_lines):
        parts = line.split()
        if len(parts) >= 16:
            try:
                cpu_user = parts[12]
                cpu_system = parts[13]
                cpu_idle = parts[14]
                memory_free = parts[3]
                buffer = parts[4]
                cache = parts[5]
                writer.writerow([cpu_user, cpu_system, cpu_idle, memory_free, buffer, cache])
            except Exception as e:
                print(f"⚠️  Linha {i} ignorada: {e}")
                pass

print(f"✅ Convertido com sucesso!")
print(f"   Entrada:  {input_file}")
print(f"   Saída:    {output_file}")
print(f"   Linhas:   {len(data_lines)} dados coletados")
