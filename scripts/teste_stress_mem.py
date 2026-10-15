#!/usr/bin/env python3

import requests
import csv
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

VM_IP = "192.168.10.14"
VM_USER = "osboxes"
VM_PASSWORD = "osboxes.org"
PORT = 8002
RESULTADOS = "teste_stress_mem.csv"
TIMEOUT = 300
MB_FIXO = 128
HOLD_MS_FIXO = 200
INTERVALO_ENTRE_NIVEIS = 60  # segundos de pausa entre níveis
WARMUP_REQUISICOES = 3       # requisições de aquecimento antes do teste

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
print("STRESS TEST - MEMORY-BOUND (VARIANDO CONCORRÊNCIA)")
print("="*70)
print(f"VM: {VM_IP}:{PORT}")
print(f"Memória por requisição: {MB_FIXO} MB (fixo)")
print(f"Hold time: {HOLD_MS_FIXO} ms (fixo)")
print(f"Demandas (concorrência):")
for demanda, num_req in DEMANDAS.items():
    print(f"  - {demanda.upper()}: {num_req} requisições simultâneas")
print(f"Resultados: {RESULTADOS}")
print("="*70)
print()

def fazer_requisicao(mb, hold_ms):
    url = f"http://{VM_IP}:{PORT}/mem?mb={mb}&hold_ms={hold_ms}"
    try:
        start = time.time()
        response = requests.get(url, timeout=TIMEOUT)
        elapsed_ms = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            paginas = data.get('paginas_ocupadas', 0)
            return {
                'sucesso': True,
                'tempo_ms': elapsed_ms,
                'paginas': paginas,
                'erro': None
            }
        else:
            return {
                'sucesso': False,
                'tempo_ms': elapsed_ms,
                'paginas': 0,
                'erro': f"HTTP {response.status_code}"
            }
    except requests.exceptions.Timeout:
        return {
            'sucesso': False,
            'tempo_ms': TIMEOUT * 1000,
            'paginas': 0,
            'erro': 'TIMEOUT'
        }
    except Exception as e:
        return {
            'sucesso': False,
            'tempo_ms': 0,
            'paginas': 0,
            'erro': str(e)
        }

def executar_stress_test(mb, hold_ms, demanda_nome, num_requisicoes):
    print(f"  Demanda {demanda_nome.upper()}: {num_requisicoes} requisições simultâneas...", end="", flush=True)

    resultados = []
    start_total = time.time()

    with ThreadPoolExecutor(max_workers=num_requisicoes) as executor:
        futures = [executor.submit(fazer_requisicao, mb, hold_ms) for _ in range(num_requisicoes)]

        for future in as_completed(futures):
            resultados.append(future.result())

    tempo_total = time.time() - start_total

    sucesso = sum(1 for r in resultados if r['sucesso'])
    erro = num_requisicoes - sucesso
    tempos = [r['tempo_ms'] for r in resultados if r['sucesso']]
    paginas_list = [r['paginas'] for r in resultados if r['sucesso']]

    if tempos:
        tempo_medio = statistics.mean(tempos)
        tempo_p95 = statistics.quantiles(tempos, n=20)[18] if len(tempos) > 1 else tempos[0]
        tempo_p99 = statistics.quantiles(tempos, n=100)[98] if len(tempos) > 1 else tempos[0]
    else:
        tempo_medio = tempo_p95 = tempo_p99 = 0

    paginas_medio = statistics.mean(paginas_list) if paginas_list else 0
    req_por_segundo = num_requisicoes / tempo_total if tempo_total > 0 else 0

    print(f" ✓")
    print(f"    Tempo total: {tempo_total:.2f}s | Sucesso: {sucesso}/{num_requisicoes} | req/s: {req_por_segundo:.2f}")

    return {
        'mb': mb,
        'hold_ms': hold_ms,
        'demanda': demanda_nome,
        'num_requisicoes': num_requisicoes,
        'tempo_total_s': round(tempo_total, 2),
        'requisicoes_sucesso': sucesso,
        'requisicoes_erro': erro,
        'req_por_segundo': round(req_por_segundo, 2),
        'tempo_medio_ms': round(tempo_medio, 2),
        'tempo_p95_ms': round(tempo_p95, 2),
        'tempo_p99_ms': round(tempo_p99, 2),
        'paginas': int(paginas_medio),
        'timestamp': datetime.now().isoformat()
    }

def limpar_cache_vm():
    """Limpa page cache e swap residual na VM entre níveis de demanda."""
    import subprocess
    ssh_cmd = f"sshpass -p {VM_PASSWORD} ssh {VM_USER}@{VM_IP}"
    try:
        subprocess.run(
            f"{ssh_cmd} 'sync; echo {VM_PASSWORD} | sudo -S sh -c \"echo 3 > /proc/sys/vm/drop_caches\"'",
            shell=True, capture_output=True, timeout=15
        )
    except Exception:
        pass


def warmup():
    """Requisições de aquecimento para estabilizar a aplicação."""
    print(f"  Warmup: {WARMUP_REQUISICOES} requisições...", end="", flush=True)
    for _ in range(WARMUP_REQUISICOES):
        fazer_requisicao(MB_FIXO, HOLD_MS_FIXO)
    print(" ✓")


print(f"Iniciando stress test com memória FIXA em {MB_FIXO} MB...")
print("Variando apenas a concorrência (número de requisições simultâneas)")
print()

warmup()
print()

todos_resultados = []

print(f"Testando mb = {MB_FIXO}, hold_ms = {HOLD_MS_FIXO}")
for i, (demanda_nome, num_req) in enumerate(DEMANDAS.items()):
    if i > 0:
        print(f"  Limpando cache e aguardando {INTERVALO_ENTRE_NIVEIS}s...", flush=True)
        limpar_cache_vm()
        time.sleep(INTERVALO_ENTRE_NIVEIS)
    resultado = executar_stress_test(MB_FIXO, HOLD_MS_FIXO, demanda_nome, num_req)
    todos_resultados.append(resultado)

print()
print("="*70)

with open(RESULTADOS, 'w', newline='') as csvfile:
    fieldnames = [
        'mb', 'hold_ms', 'demanda', 'num_requisicoes', 'tempo_total_s',
        'requisicoes_sucesso', 'requisicoes_erro', 'req_por_segundo',
        'tempo_medio_ms', 'tempo_p95_ms', 'tempo_p99_ms',
        'paginas', 'timestamp'
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(todos_resultados)

print()
print("="*70)
print("✅ TESTES CONCLUÍDOS!")
print("="*70)
print()

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
