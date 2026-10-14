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
        print("Uso: python3 rodar_teste_completo_v2.py <cpu|mem> <cenario_2cpu_512mb|cenario_2cpu_1gb|...>")
        print()
        print("Exemplos (CPU):")
        print("  python3 rodar_teste_completo_v2.py cpu cenario_2cpu_512mb")
        print()
        print("Exemplos (MEMÓRIA - RAM variável, 2 CPUs fixos):")
        print("  python3 rodar_teste_completo_v2.py mem cenario_2cpu_512mb")
        print("  python3 rodar_teste_completo_v2.py mem cenario_2cpu_1gb")
        print("  python3 rodar_teste_completo_v2.py mem cenario_2cpu_2gb")
        print("  python3 rodar_teste_completo_v2.py mem cenario_2cpu_4gb")
        sys.exit(1)

    app_type = sys.argv[1].lower()
    cenario = sys.argv[2].lower()

    if app_type not in ["cpu", "mem"]:
        print("❌ Tipo de app inválido. Use 'cpu' ou 'mem'")
        sys.exit(1)

    if not cenario.startswith("cenario_"):
        print("❌ Cenário inválido. Use formato: cenario_2cpu_512mb, cenario_2cpu_1gb, etc")
        sys.exit(1)

    RESULTADOS_DIR = f"resultados/{cenario}"
    APP_NAME = "CPU-bound" if app_type == "cpu" else "Memory-bound"
    SCRIPT_NAME = "teste_stress.py" if app_type == "cpu" else "teste_stress_mem.py"

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
            f"{ssh_cmd} 'sync; echo 3 > /proc/sys/vm/drop_caches'",
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

    print("[2/5] Iniciando monitoramento da VM com vmstat...")
    print()

    try:
        ssh_cmd = f"sshpass -p {VM_PASSWORD} ssh {VM_USER}@{VM_IP}"
        subprocess.run(
            f"{ssh_cmd} 'pkill vmstat; sleep 1; vmstat 1 > /tmp/vmstat.log 2>&1 &'",
            shell=True,
            check=True,
            capture_output=True
        )
        print("✅ vmstat iniciado na VM")
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

    try:
        ssh_cmd = f"sshpass -p {VM_PASSWORD} scp {VM_USER}@{VM_IP}:/tmp/vmstat.log {RESULTADOS_DIR}/ 2>/dev/null"
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True)

        if result.returncode == 0:
            print(f"✅ vmstat.log copiado para {RESULTADOS_DIR}/")
        else:
            ssh_cmd = f"scp {VM_USER}@{VM_IP}:/tmp/vmstat.log {RESULTADOS_DIR}/"
            result = subprocess.run(ssh_cmd, shell=True, capture_output=True)
            if result.returncode == 0:
                print(f"✅ vmstat.log copiado para {RESULTADOS_DIR}/ (SSH key)")
            else:
                print(f"⚠️  Não consegui copiar vmstat.log da VM")
    except Exception as e:
        print(f"⚠️  Erro ao copiar: {e}")

    print()

    print("[5/5] Convertendo vmstat para CSV...")
    print()

    vmstat_log = f"{RESULTADOS_DIR}/vmstat.log"
    vmstat_csv = f"{RESULTADOS_DIR}/vmstat.csv"

    if os.path.exists(vmstat_log):
        try:
            result = subprocess.run(
                ["python3", "scripts/vmstat_to_csv.py", vmstat_log, vmstat_csv],
                check=True,
                capture_output=True,
                text=True
            )
            print(result.stdout)
            print(f"✅ Convertido: {vmstat_csv}")
        except Exception as e:
            print(f"⚠️  Erro ao converter vmstat: {e}")
    else:
        print(f"⚠️  Arquivo {vmstat_log} não encontrado")

    print()

    print("[6/6] Organizando resultados...")
    print()

    csv_file = f"teste_stress_mem.csv" if app_type == "mem" else "teste_stress.csv"
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
    print(f"  ✓ {RESULTADOS_DIR}/vmstat.csv         (métricas de VM)")
    print(f"  ✓ {RESULTADOS_DIR}/vmstat.log         (log bruto)")
    print()
    print("Próximos passos:")
    if app_type == "mem":
        print(f"  1. Repetir para os outros cenários de RAM:")
        print(f"     - python3 scripts/rodar_teste_completo_v2.py mem cenario_2cpu_1gb")
        print(f"     - python3 scripts/rodar_teste_completo_v2.py mem cenario_2cpu_2gb")
        print(f"     - python3 scripts/rodar_teste_completo_v2.py mem cenario_2cpu_4gb")
    else:
        print(f"  1. Repetir para os outros cenários de CPU:")
        print(f"     - python3 scripts/rodar_teste_completo_v2.py cpu cenario_2cpu_512mb")
        print(f"     - python3 scripts/rodar_teste_completo_v2.py cpu cenario_2cpu_1gb")
        print(f"     - python3 scripts/rodar_teste_completo_v2.py cpu cenario_2cpu_2gb")
        print(f"     - python3 scripts/rodar_teste_completo_v2.py cpu cenario_2cpu_4gb")
    print()

if __name__ == "__main__":
    main()
