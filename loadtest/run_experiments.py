"""
Executa a bateria de testes de stress de UM cenário de provisionamento.

Para cada nível de demanda (nº de usuários concorrentes):
  1. gera carga contra a aplicação por --duration segundos (de FORA da VM);
  2. coleta as métricas de recursos medidas DENTRO da VM (endpoint /metrics);
  3. coleta as métricas do VirtualBox no host (VBoxManage metrics), se --vm for informado;
  4. grava uma linha com as métricas principais em resultados.jsonl.

Exemplo (no host do LCC, com a VM ligada e a porta 8001 redirecionada):
    python3 loadtest/run_experiments.py --scenario C1 --vm minha_vm
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loadgen import _OPENER, run_load  

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_json(url, timeout=10):
    with _OPENER.open(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def avg(vals):
    return round(sum(vals) / len(vals), 2) if vals else None


class VBoxMonitor(threading.Thread):
    """Coleta métricas da VM pelo lado do host com VBoxManage (opcional)."""

    METRICS = "CPU/Load/User,CPU/Load/Kernel,RAM/Usage/Used"

    def __init__(self, vm):
        super().__init__(daemon=True)
        self.vm = vm
        self.stop_evt = threading.Event()
        self.data = {"CPU/Load/User": [], "CPU/Load/Kernel": [], "RAM/Usage/Used": []}

    @staticmethod
    def available():
        return shutil.which("VBoxManage") is not None

    @classmethod
    def setup(cls, vm):
        subprocess.run(["VBoxManage", "metrics", "setup", "--period", "1",
                        "--samples", "1", vm, cls.METRICS],
                       capture_output=True, text=True, check=False)

    def run(self):
        while not self.stop_evt.is_set():
            out = subprocess.run(["VBoxManage", "metrics", "query", self.vm, self.METRICS],
                                 capture_output=True, text=True, check=False).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[1] in self.data:
                    raw = parts[2].replace("%", "").replace(",", ".")
                    try:
                        val = float(raw)
                    except ValueError:
                        continue
                    if parts[1] == "RAM/Usage/Used":
                        val = val / 1024  # kB -> MB
                    self.data[parts[1]].append(val)
            self.stop_evt.wait(1)


def main():
    ap = argparse.ArgumentParser(description="Teste de stress de um cenário")
    ap.add_argument("--scenario", required=True, help="nome do cenário, ex.: C1")
    ap.add_argument("--descricao", default="", help='ex.: "1 vCPU, 1 GB, 50%%"')
    ap.add_argument("--host", default="http://localhost:8001")
    ap.add_argument("--path", default="/cpu?n=30000")
    ap.add_argument("--users", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32])
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--cooldown", type=float, default=5)
    ap.add_argument("--vm", default=None, help="nome da VM no VirtualBox (opcional)")
    ap.add_argument("--out", default=os.path.join(ROOT, "results"))
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    out_path = os.path.join(a.out, "resultados.jsonl")

    try:
        health = get_json(a.host + "/health")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"ERRO: aplicação não respondeu em {a.host}/health ({e}).\n"
                 "Verifique se a VM está ligada, a app rodando e a porta redirecionada.")
    print(f"Aplicação: {health['app']} | CPUs na máquina: {health['ncpu']} | "
          f"RAM total: {health['mem_total_mb']:.0f} MB")

    use_vbox = bool(a.vm) and VBoxMonitor.available()
    if a.vm and not use_vbox:
        print("Aviso: VBoxManage não encontrado; seguindo só com métricas de dentro da VM.")
    if use_vbox:
        VBoxMonitor.setup(a.vm)

    url = a.host + a.path
    print("Aquecendo (5 s)...")
    run_load(url, 1, 5)

    for users in a.users:
        print(f"\n[{a.scenario}] {users} usuário(s) por {a.duration:.0f} s ...", flush=True)
        vbox = VBoxMonitor(a.vm) if use_vbox else None
        if vbox:
            vbox.start()
        res = run_load(url, users, a.duration)
        if vbox:
            vbox.stop_evt.set()
            vbox.join(timeout=5)

        try:
            samples = get_json(f"{a.host}/metrics?seconds={a.duration}")["samples"]
        except Exception:  # noqa: BLE001
            samples = []
        col = lambda k: [s[k] for s in samples]  # noqa: E731

        row = {
            "scenario": a.scenario, "descricao": a.descricao,
            "ncpu": health["ncpu"], "mem_total_mb": round(health["mem_total_mb"]),
            **{k: res[k] for k in ("users", "rps", "lat_mean_ms", "lat_p95_ms",
                                   "requests_ok", "error_pct")},
            "cpu_avg_pct": avg(col("cpu_pct")),
            "mem_used_avg_mb": avg(col("mem_used_mb")),
        }
        if vbox:
            cpu = [u + k for u, k in zip(vbox.data["CPU/Load/User"], vbox.data["CPU/Load/Kernel"])]
            row["vbox_cpu_avg_pct"] = avg(cpu)
            row["vbox_ram_avg_mb"] = avg(vbox.data["RAM/Usage/Used"])

        with open(out_path, "a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

        print(f"   vazão={res['rps']} req/s | latência média={res['lat_mean_ms']} ms | "
              f"p95={res['lat_p95_ms']} ms | erros={res['error_pct']}% | "
              f"CPU={row['cpu_avg_pct']}% | RAM={row['mem_used_avg_mb']} MB")
        time.sleep(a.cooldown)

    print(f"\nPronto! Resultados em {out_path}")


if __name__ == "__main__":
    main()
