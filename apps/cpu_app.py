"""
Aplicação 1: CPU-bound (porta 8001)

    GET /cpu?n=30000
    conta quantos números primos existem entre 2 e n.

Só faz contas, sem usar memória ou disco, então o limite é o processador.
"""
import os
from concurrent.futures import ProcessPoolExecutor

from common import iniciar_app, limitar


def eh_primo(numero):
    divisor = 2
    while divisor * divisor <= numero:
        if numero % divisor == 0:
            return False
        divisor += 1
    return True


def contar_primos(n):
    return sum(1 for numero in range(2, n + 1) if eh_primo(numero))


def main():
    # Um processo por CPU, pois threads em Python não calculam em paralelo (GIL)
    num_processos = os.cpu_count() or 1
    pool = ProcessPoolExecutor(max_workers=num_processos)

    def rota_cpu(params):
        n = limitar(int(params.get("n", 30000)), 10, 2_000_000)
        primos = pool.submit(contar_primos, n).result()
        return {"n": n, "primos": primos, "processos": num_processos}

    iniciar_app(
        nome="cpu-bound",
        porta_padrao=8001,
        rotas={"/cpu": rota_cpu},
        descricao="CPU-bound: conta números primos até n",
        ao_encerrar=lambda: pool.shutdown(wait=False, cancel_futures=True),
    )


if __name__ == "__main__":
    main()
