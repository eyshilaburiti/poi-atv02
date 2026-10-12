"""
Código compartilhado pelas apps
Rotas comuns: /health (CPUs e RAM da máquina) e /metrics?seconds=N (medições dos últimos N s).
"""
import argparse
import json
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def ler_tempos_de_cpu():
    # user, nice, system, idle, iowait, irq, softirq, steal
    with open("/proc/stat") as f:
        return [int(x) for x in f.readline().split()[1:9]]


def ler_memoria_mb():
    info = {}
    with open("/proc/meminfo") as f:
        for linha in f:
            nome, valor = linha.split(":")
            info[nome] = int(valor.split()[0]) / 1024
    usada = info["MemTotal"] - info["MemAvailable"]
    swap = info["SwapTotal"] - info["SwapFree"]
    return info["MemTotal"], usada, swap


class MonitorDeRecursos(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.medicoes = []
        self.trava = threading.Lock()

    def run(self):
        anterior = ler_tempos_de_cpu()
        while True:
            time.sleep(1)
            atual = ler_tempos_de_cpu()
            delta = [a - b for a, b in zip(atual, anterior)]
            anterior = atual
            total = sum(delta) or 1
            ocioso = delta[3] + delta[4]

            mem_total, mem_usada, swap = ler_memoria_mb()
            medicao = {
                "t": time.time(),
                "cpu_pct": round(100 * (total - ocioso) / total, 2),
                "iowait_pct": round(100 * delta[4] / total, 2),   # CPU esperando o disco
                "steal_pct": round(100 * delta[7] / total, 2),    # CPU retirada pelo hipervisor
                "mem_used_mb": round(mem_usada, 1),
                "mem_total_mb": round(mem_total, 1),
                "swap_used_mb": round(swap, 1),
            }
            with self.trava:
                self.medicoes = (self.medicoes + [medicao])[-3600:]

    def ultimos(self, segundos):
        limite = time.time() - segundos
        with self.trava:
            return [m for m in self.medicoes if m["t"] >= limite]


def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def iniciar_app(nome, porta_padrao, rotas, descricao, ao_encerrar=None):
    parser = argparse.ArgumentParser(description=descricao)
    parser.add_argument("--host", default="0.0.0.0")  # 0.0.0.0 = aceita acesso de fora (VM)
    parser.add_argument("--port", type=int, default=porta_padrao)
    args = parser.parse_args()

    monitor = MonitorDeRecursos()
    monitor.start()

    class Tratador(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def responder(self, codigo, dados):
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            url = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(url.query).items()}

            if url.path in ("/", "/health"):
                mem_total, mem_usada, _ = ler_memoria_mb()
                self.responder(200, {"app": nome, "descricao": descricao,
                                     "ncpu": os.cpu_count(),
                                     "mem_total_mb": round(mem_total, 1),
                                     "mem_used_mb": round(mem_usada, 1)})
            elif url.path == "/metrics":
                segundos = float(params.get("seconds", 60))
                self.responder(200, {"app": nome, "samples": monitor.ultimos(segundos)})
            elif url.path in rotas:
                inicio = time.perf_counter()
                try:
                    resultado = rotas[url.path](params)
                except ValueError:
                    self.responder(400, {"erro": "parâmetro inválido"})
                    return
                resultado["tempo_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
                self.responder(200, resultado)
            else:
                self.responder(404, {"erro": "rota não encontrada", "rotas": list(rotas)})

    class Servidor(ThreadingHTTPServer):  # uma thread por requisição
        daemon_threads = True
        allow_reuse_address = True
        request_queue_size = 256

    servidor = Servidor((args.host, args.port), Tratador)

    def parar(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, parar)  # encerra limpo com kill/systemctl stop

    print(f"[{nome}] rodando em http://{args.host}:{args.port} "
          f"(CPUs: {os.cpu_count()})", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{nome}] encerrada.", flush=True)
    finally:
        servidor.server_close()
        if ao_encerrar:
            ao_encerrar()
