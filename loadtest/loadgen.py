"""
Gerador de carga simples (somente biblioteca padrão do Python).

Simula N usuários concorrentes fazendo requisições sem pausa durante D
segundos e mede vazão (req/s), latência (média, p50, p95, p99, máx) e erros.

Uso avulso:
    python3 loadtest/loadgen.py --url "http://localhost:8001/cpu?n=30000" --users 8 --duration 30
"""
import argparse
import json
import math
import threading
import time
import urllib.request

# Ignora proxies configurados no sistema (as requisições são para localhost).
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    idx = max(0, math.ceil(p / 100 * len(sorted_vals)) - 1)
    return sorted_vals[idx]


def run_load(url, users, duration, timeout=60):
    latencies = []
    errors = [0]
    lock = threading.Lock()
    start_evt = threading.Event()
    deadline = [0.0]

    def worker():
        local_lat, local_err = [], 0
        start_evt.wait()
        while time.perf_counter() < deadline[0]:
            t0 = time.perf_counter()
            ok = False
            try:
                with _OPENER.open(url, timeout=timeout) as r:
                    r.read()
                    ok = r.status == 200
            except Exception:  # noqa: BLE001 - qualquer falha conta como erro
                ok = False
            dt = time.perf_counter() - t0
            if ok:
                local_lat.append(dt)
            else:
                local_err += 1
                time.sleep(0.05)
        with lock:
            latencies.extend(local_lat)
            errors[0] += local_err

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(users)]
    for t in threads:
        t.start()
    t_start = time.perf_counter()
    deadline[0] = t_start + duration
    start_evt.set()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t_start

    lat = sorted(latencies)
    ok = len(lat)
    ms = lambda v: round(v * 1000, 2)  # noqa: E731
    return {
        "users": users,
        "duration_s": round(elapsed, 2),
        "requests_ok": ok,
        "errors": errors[0],
        "error_pct": round(100 * errors[0] / max(1, ok + errors[0]), 2),
        "rps": round(ok / elapsed, 2) if elapsed else 0.0,
        "lat_mean_ms": ms(sum(lat) / ok) if ok else 0.0,
        "lat_p50_ms": ms(percentile(lat, 50)),
        "lat_p95_ms": ms(percentile(lat, 95)),
        "lat_p99_ms": ms(percentile(lat, 99)),
        "lat_max_ms": ms(lat[-1]) if ok else 0.0,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gerador de carga HTTP")
    ap.add_argument("--url", required=True)
    ap.add_argument("--users", type=int, default=4)
    ap.add_argument("--duration", type=float, default=20)
    a = ap.parse_args()
    print(json.dumps(run_load(a.url, a.users, a.duration), indent=2))
