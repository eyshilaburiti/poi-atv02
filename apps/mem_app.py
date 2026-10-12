"""
Aplicação 2: Memory-bound (porta 8002)

    GET /mem?mb=64&hold_ms=100
    reserva `mb` megabytes, preenche, faz uma cópia, mantém os dados
    por `hold_ms` milissegundos e libera.

Cada requisição ocupa cerca de 2×N MB, então o limite é a quantidade de memória.
"""
import time

from common import iniciar_app, limitar

TAMANHO_PAGINA = 4096 # o sistema operacional gerencia a RAM em páginas de 4 KB


def rota_mem(params):
    mb = limitar(int(params.get("mb", 64)), 1, 512)
    hold_ms = limitar(int(params.get("hold_ms", 100)), 0, 5000)

    # Reserva o bloco de memória.
    bloco = bytearray(mb * 1024 * 1024)
    for posicao in range(0, len(bloco), TAMANHO_PAGINA):
        bloco[posicao] = 1          
    copia = bytes(bloco)           
    time.sleep(hold_ms / 1000)     

    paginas = copia.count(1)
    del bloco, copia
    return {"mb": mb, "hold_ms": hold_ms, "paginas_ocupadas": paginas}


if __name__ == "__main__":
    iniciar_app(
        nome="memory-bound",
        porta_padrao=8002,
        rotas={"/mem": rota_mem},
        descricao="Memory-bound: ocupa e copia N MB de RAM",
    )
