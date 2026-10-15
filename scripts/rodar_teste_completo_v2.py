#!/usr/bin/env python3

import subprocess
import time
import os
import sys
from pathlib import Path

VM_IP = "192.168.10.14"
VM_USER = "osboxes"
VM_PASSWORD = "osboxes.org"

def main():
    if len(sys.argv) < 3:
        print("Uso: python3 rodar_teste_completo_v2.py <cpu|mem|io> <cenario_XcpuY>")
        print()
        print("Exemplos:")
        print("  python3 rodar_teste_completo_v2.py cpu cenario_2cpu_1gb")
        print("  python3 rodar_teste_completo_v2.py mem cenario_2cpu_512mb")
        print("  python3 rodar_teste_completo_v2.py io cenario_2cpu_1gb")
        sys.exit(1)

    app_type = sys.argv[1].lower()
    cenario = sys.argv[2].lower()

    if app_type not in ["cpu", "mem", "io"]:
        print("❌ Tipo de app inválido. Use 'cpu', 'mem' ou 'io'")
        sys.exit(1)

    if not cenario.startswith("cenario_"):
        print("❌ Cenário inválido. Use formato: cenario_2cpu_512mb, cenario_2cpu_1gb, etc")
        sys.exit(1)

    RESULTADOS_DIR = f"resultados/{app_type}/{cenario}"
    APP_NAMES = {"cpu": "CPU-bound", "mem": "Memory-bound", "io": "IO-bound"}
    SCRIPT_NAMES = {"cpu": "teste_stress.py", "mem": "teste_stress_mem.py", "io": "teste_stress_io.py"}
    APP_NAME = APP_NAMES[app_type]
    SCRIPT_NAME = SCRIPT_NAMES[app_type]

    print("="*70)
    print(f"TESTE COMPLETO - {APP_NAME.upper()}")
    print("="*70)
    print(f"Tipo de aplicação: {APP_NAME}")
    print(f"Cenário: {cenario}")
    print(f"VM: {VM_IP}")
    print(f"Diretório de resultados: {RESULTADOS_DIR}")
    print("="*70)
    print()

    Path(RESULTADOS_DIR).mkdir(parents=True, exist_ok=True)

    print("[1/5] Limpando cache da VM...")
    print()

    try:
        ssh_cmd = f"sshpass -p {VM_PASSWORD} ssh {VM_USER}@{VM_IP}"
        subprocess.run(
            f"{ssh_cmd} 'sync; echo osboxes.org | sudo -S sh -c \"echo 3 > /proc/sys/vm/drop_caches\"'",
            shell=True,
            check=True,
            capture_output=True
        )
        print("✅ Cache limpo")
        print()
    except Exception as e:
        print(f"⚠️  Aviso ao limpar cache: {e}")
        print("Continuando mesmo assim...")
        print()

    print("[2/5] Iniciando monitoramento da VM (vmstat + iostat)...")
    print()

    try:
        ssh_cmd = f"sshpass -p {VM_PASSWORD} ssh {VM_USER}@{VM_IP}"
        subprocess.run(
            f"{ssh_cmd} 'pkill vmstat; pkill iostat; sleep 1; vmstat 1 > /tmp/vmstat.log 2>&1 & iostat -dx 1 > /tmp/iostat.log 2>&1 &'",
            shell=True,
            check=True,
            capture_output=True
        )
        print("✅ vmstat e iostat iniciados na VM")
        print()
        time.sleep(2)
    except Exception as e:
        print(f"⚠️  Aviso ao iniciar vmstat: {e}")
        print("Continuando...")
        print()

    print(f"[3/5] Executando teste de stress ({APP_NAME})...")
    print()

    try:
        result = subprocess.run(
            ["python3", f"scripts/{SCRIPT_NAME}"],
            check=True,
            capture_output=False
        )
        print()
        print(f"✅ Teste de {APP_NAME} concluído")
        print()
    except Exception as e:
        print(f"❌ Erro ao rodar teste: {e}")
        sys.exit(1)

    print("[4/5] Copiando arquivos da VM...")
    print()

    for log_file in ["vmstat.log", "iostat.log"]:
        try:
            scp_cmd = f"sshpass -p {VM_PASSWORD} scp {VM_USER}@{VM_IP}:/tmp/{log_file} {RESULTADOS_DIR}/ 2>/dev/null"
            result = subprocess.run(scp_cmd, shell=True, capture_output=True)

            if result.returncode == 0:
                print(f"✅ {log_file} copiado para {RESULTADOS_DIR}/")
            else:
                print(f"⚠️  Não consegui copiar {log_file} da VM")
        except Exception as e:
            print(f"⚠️  Erro ao copiar {log_file}: {e}")

    print()

    print("[5/5] Convertendo logs para CSV...")
    print()

    vmstat_log = f"{RESULTADOS_DIR}/vmstat.log"
    vmstat_csv = f"{RESULTADOS_DIR}/vmstat.csv"

    if os.path.exists(vmstat_log):
        try:
            result = subprocess.run(
                ["python3", "scripts/vmstat_to_csv.py", vmstat_log, vmstat_csv],
                check=True, capture_output=True, text=True
            )
            print(result.stdout)
            print(f"✅ Convertido: {vmstat_csv}")
        except Exception as e:
            print(f"⚠️  Erro ao converter vmstat: {e}")
    else:
        print(f"⚠️  Arquivo {vmstat_log} não encontrado")

    iostat_log = f"{RESULTADOS_DIR}/iostat.log"
    iostat_csv = f"{RESULTADOS_DIR}/iostat.csv"

    if os.path.exists(iostat_log):
        try:
            result = subprocess.run(
                ["python3", "scripts/iostat_to_csv.py", iostat_log, iostat_csv],
                check=True, capture_output=True, text=True
            )
            print(result.stdout)
            print(f"✅ Convertido: {iostat_csv}")
        except Exception as e:
            print(f"⚠️  Erro ao converter iostat: {e}")
    else:
        print(f"⚠️  Arquivo {iostat_log} não encontrado")

    print()

    print("[6/6] Organizando resultados...")
    print()

    csv_names = {"cpu": "teste_stress.csv", "mem": "teste_stress_mem.csv", "io": "teste_stress_io.csv"}
    csv_file = csv_names[app_type]
    try:
        subprocess.run(
            ["cp", csv_file, f"{RESULTADOS_DIR}/{csv_file}"],
            check=True,
            capture_output=True
        )
        print(f"✅ {csv_file} copiado para {RESULTADOS_DIR}/")
    except Exception as e:
        print(f"⚠️  Erro ao copiar {csv_file}: {e}")

    print()

    print("="*70)
    print(f"✅ TESTE {APP_NAME.upper()} CONCLUÍDO!")
    print("="*70)
    print()
    print("Arquivos gerados:")
    print(f"  ✓ {RESULTADOS_DIR}/{csv_file}   (métricas de aplicação)")
    print(f"  ✓ {RESULTADOS_DIR}/vmstat.csv         (CPU/memória da VM)")
    print(f"  ✓ {RESULTADOS_DIR}/iostat.csv         (métricas de disco)")
    print(f"  ✓ {RESULTADOS_DIR}/vmstat.log         (log bruto vmstat)")
    print(f"  ✓ {RESULTADOS_DIR}/iostat.log         (log bruto iostat)")
    print()

if __name__ == "__main__":
    main()
