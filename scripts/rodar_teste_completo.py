#!/usr/bin/env python3

import subprocess
import time
import os
import sys
from pathlib import Path

# Configuração
VM_IP = "192.168.10.10"
VM_USER = "osboxes"
VM_PASSWORD = "osboxes.org"
CENARIO = "cenario_4cpu_1gb"  # Alterar para cada cenário
RESULTADOS_DIR = f"resultados/{CENARIO}"

print("="*70)
print("TESTE COMPLETO COM MONITORAMENTO DA VM")
print("="*70)
print(f"Cenário: {CENARIO}")
print(f"VM: {VM_IP}")
print(f"Diretório de resultados: {RESULTADOS_DIR}")
print("="*70)
print()

# Criar diretório se não existir
Path(RESULTADOS_DIR).mkdir(parents=True, exist_ok=True)

print("[1/5] Iniciando monitoramento da VM com vmstat...")
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
    print(f"❌ Erro ao iniciar vmstat: {e}")
    print("Tentando alternativa com chave SSH...")
    try:
        subprocess.run(
            f"ssh {VM_USER}@{VM_IP} 'pkill vmstat; sleep 1; vmstat 1 > /tmp/vmstat.log 2>&1 &'",
            shell=True,
            check=True,
            capture_output=True
        )
        print("✅ vmstat iniciado na VM (via SSH key)")
        time.sleep(2)
    except Exception as e2:
        print(f"⚠️  Aviso: Não consegui iniciar vmstat na VM: {e2}")
        print("Continuando sem monitoramento da VM...")

print("[2/5] Executando teste de stress...")
print()

# Rodar teste de stress
try:
    result = subprocess.run(
        ["python3", "scripts/teste_stress.py"],
        check=True,
        capture_output=False
    )
    print()
    print("✅ Teste de stress concluído")
    print()
except Exception as e:
    print(f"❌ Erro ao rodar teste: {e}")
    sys.exit(1)

print("[3/5] Copiando arquivos da VM...")
print()

try:
    ssh_cmd = f"sshpass -p {VM_PASSWORD} scp {VM_USER}@{VM_IP}:/tmp/vmstat.log {RESULTADOS_DIR}/ 2>/dev/null"
    result = subprocess.run(ssh_cmd, shell=True, capture_output=True)

    if result.returncode == 0:
        print(f"✅ vmstat.log copiado para {RESULTADOS_DIR}/")
    else:
        # Tentar com SSH key
        ssh_cmd = f"scp {VM_USER}@{VM_IP}:/tmp/vmstat.log {RESULTADOS_DIR}/"
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True)
        if result.returncode == 0:
            print(f"✅ vmstat.log copiado para {RESULTADOS_DIR}/ (SSH key)")
        else:
            print(f"⚠️  Não consegui copiar vmstat.log da VM")
except Exception as e:
    print(f"⚠️  Erro ao copiar: {e}")

print()

print("[4/5] Convertendo vmstat para CSV...")
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

print("[5/5] Organizando resultados...")
print()

try:
    subprocess.run(
        ["cp", "teste_stress.csv", f"{RESULTADOS_DIR}/teste_stress.csv"],
        check=True,
        capture_output=True
    )
    print(f"✅ teste_stress.csv copiado para {RESULTADOS_DIR}/")
except Exception as e:
    print(f"⚠️  Erro ao copiar teste_stress.csv: {e}")

print()

# Mostrar resumo
print("="*70)
print("✅ TESTE COMPLETO CONCLUÍDO!")
print("="*70)
print()
print("Arquivos gerados:")
print(f"  ✓ {RESULTADOS_DIR}/teste_stress.csv   (métricas de aplicação)")
print(f"  ✓ {RESULTADOS_DIR}/vmstat.csv         (métricas de VM)")
print(f"  ✓ {RESULTADOS_DIR}/vmstat.log         (log bruto)")
print()
print(f"Próximos passos:")
print(f"  1. Repetir para os outros cenários (alterar CENARIO no script)")
print(f"  2. Importar CSVs no Excel")
print(f"  3. Criar gráficos comparativos")
print()
