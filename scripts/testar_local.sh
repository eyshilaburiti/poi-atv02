#!/usr/bin/env bash
# Testa as três aplicações na máquina local (seu notebook).
# Sobe as apps, faz uma requisição em cada uma, roda um teste de carga curto
# e salva os resultados em results/local/.  Uso:  bash scripts/testar_local.sh
set -e
cd "$(dirname "$0")/.."

echo ">> Subindo as aplicações..."
python3 apps/cpu_app.py --port 8001 & P1=$!
python3 apps/mem_app.py --port 8002 & P2=$!
python3 apps/io_app.py  --port 8003 & P3=$!
trap 'kill $P1 $P2 $P3 2>/dev/null; wait 2>/dev/null' EXIT
sleep 2

echo; echo ">> Teste funcional (uma requisição em cada app)"
echo -n "CPU-bound   : "; curl -s "http://localhost:8001/cpu?n=30000"; echo
echo -n "Memory-bound: "; curl -s "http://localhost:8002/mem?mb=64";   echo
echo -n "IO-bound    : "; curl -s "http://localhost:8003/io?kb=1024";  echo

echo; echo ">> Teste de carga curto em cada app (1 e 8 usuários, 10 s cada)"
OUT=results/local
rm -f $OUT/summary.csv
python3 loadtest/run_experiments.py --scenario local-cpu --descricao "CPU-bound no notebook" \
  --host http://localhost:8001 --path "/cpu?n=30000" --users 1 8 --duration 10 --cooldown 2 --out $OUT
python3 loadtest/run_experiments.py --scenario local-mem --descricao "Memory-bound no notebook" \
  --host http://localhost:8002 --path "/mem?mb=64&hold_ms=100" --users 1 8 --duration 10 --cooldown 2 --out $OUT
python3 loadtest/run_experiments.py --scenario local-io --descricao "IO-bound no notebook" \
  --host http://localhost:8003 --path "/io?kb=1024" --users 1 8 --duration 10 --cooldown 2 --out $OUT

echo; echo ">> Tudo certo! Resultados do teste local em $OUT/summary.csv"
