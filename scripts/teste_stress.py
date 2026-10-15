#!/usr/bin/env python3

import requests
import csv
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Configuração
VM_IP = "192.168.10.14"
PORT = 8001
RESULTADOS = "teste_stress.csv"
TIMEOUT = 300  # 5 minutos por requisição
N_FIXO = 100_000  # Valor de n FIXO

DEMANDAS = {
    "nivel_1": 5,
    "nivel_2": 35,
    "nivel_3": 65,
    "nivel_4": 100,
    "nivel_5": 135,
    "nivel_6": 170,
    "nivel_7": 200,
}

print("="*70)
print("STRESS TEST - VARIANDO CONCORRÊNCIA")
print("="*70)
print(f"VM: {VM_IP}:{PORT}")
print(f"Valor de n (FIXO): {N_FIXO:,}")
print(f"Demandas (concorrência):")
for demanda, num_req in DEMANDAS.items():
    print(f"  - {demanda.upper()}: {num_req} requisições simultâneas")
print(f"Resultados: {RESULTADOS}")
print("="*70)
print()

def fazer_requisicao(n):
    url = f"http://{VM_IP}:{PORT}/cpu?n={n}"
    try:
        start = time.time()
        response = requests.get(url, timeout=TIMEOUT)
        elapsed_ms = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            primos = data.get('primos', 0)
            return {
                'sucesso': True,
                'tempo_ms': elapsed_ms,
                'primos': primos,
                'erro': None
            }
        else:
            return {
                'sucesso': False,
                'tempo_ms': elapsed_ms,
                'primos': 0,
                'erro': f"HTTP {response.status_code}"
            }
    except requests.exceptions.Timeout:
        return {
            'sucesso': False,
            'tempo_ms': TIMEOUT * 1000,
            'primos': 0,
            'erro': 'TIMEOUT'
        }
    except Exception as e:
        return {
            'sucesso': False,
            'tempo_ms': 0,
            'primos': 0,
            'erro': str(e)
        }

def executar_stress_test(n, demanda_nome, num_requisicoes):
    print(f"  Demanda {demanda_nome.upper()}: {num_requisicoes} requisições simultâneas...", end="", flush=True)

    resultados = []
    start_total = time.time()

    with ThreadPoolExecutor(max_workers=num_requisicoes) as executor:
        futures = [executor.submit(fazer_requisicao, n) for _ in range(num_requisicoes)]

        for future in as_completed(futures):
            resultados.append(future.result())

    tempo_total = time.time() - start_total

    # Calcular estatísticas
    sucesso = sum(1 for r in resultados if r['sucesso'])
    erro = num_requisicoes - sucesso
    tempos = [r['tempo_ms'] for r in resultados if r['sucesso']]
    primos_list = [r['primos'] for r in resultados if r['sucesso']]

    if tempos:
        tempo_medio = statistics.mean(tempos)
        tempo_p95 = statistics.quantiles(tempos, n=20)[18] if len(tempos) > 1 else tempos[0]
        tempo_p99 = statistics.quantiles(tempos, n=100)[98] if len(tempos) > 1 else tempos[0]
    else:
        tempo_medio = tempo_p95 = tempo_p99 = 0

    primos_medio = statistics.mean(primos_list) if primos_list else 0
    req_por_segundo = num_requisicoes / tempo_total if tempo_total > 0 else 0

    print(f" ✓")
    print(f"    Tempo total: {tempo_total:.2f}s | Sucesso: {sucesso}/{num_requisicoes} | req/s: {req_por_segundo:.2f}")

    return {
        'n': n,
        'demanda': demanda_nome,
        'num_requisicoes': num_requisicoes,
        'tempo_total_s': round(tempo_total, 2),
        'requisicoes_sucesso': sucesso,
        'requisicoes_erro': erro,
        'req_por_segundo': round(req_por_segundo, 2),
        'tempo_medio_ms': round(tempo_medio, 2),
        'tempo_p95_ms': round(tempo_p95, 2),
        'tempo_p99_ms': round(tempo_p99, 2),
        'primos': int(primos_medio),
        'timestamp': datetime.now().isoformat()
    }

print(f"Iniciando stress test com n FIXO em {N_FIXO:,}...")
print()

todos_resultados = []

print(f"Testando n = {N_FIXO:,}")
for demanda_nome, num_req in DEMANDAS.items():
    resultado = executar_stress_test(N_FIXO, demanda_nome, num_req)
    todos_resultados.append(resultado)

print()
print("="*70)

with open(RESULTADOS, 'w', newline='') as csvfile:
    fieldnames = [
        'n', 'demanda', 'num_requisicoes', 'tempo_total_s',
        'requisicoes_sucesso', 'requisicoes_erro', 'req_por_segundo',
        'tempo_medio_ms', 'tempo_p95_ms', 'tempo_p99_ms',
        'primos', 'timestamp'
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(todos_resultados)

print()
print("="*70)
print("✅ TESTES CONCLUÍDOS!")
print("="*70)
print()

# Exibir resumo
print("RESUMO DOS RESULTADOS:")
print("-"*80)
print(f"{'Demanda':>8} | {'Req Simultâneas':>15} | {'Tempo Total':>12} | {'Req/s':>8} | {'Tempo Médio':>12} | {'Sucesso':>8}")
print("-"*80)

for r in todos_resultados:
    print(f"{r['demanda']:>8} | {r['num_requisicoes']:>15} | {r['tempo_total_s']:>10.2f}s | {r['req_por_segundo']:>8.2f} | {r['tempo_medio_ms']:>10.2f}ms | {r['requisicoes_sucesso']}/{r['num_requisicoes']:>5}")

print("-"*80)
print()
print(f"Arquivo salvo: {RESULTADOS}")
print()
