"""
Aplicação 3: IO-bound (porta 8003)

    GET /io?kb=1024
    grava, lê e apaga um arquivo de N KB.

Passa a maior parte do tempo esperando o disco, então o limite é o disco, não a CPU.
"""
import os
import uuid

from common import iniciar_app, limitar

PASTA = "/tmp/poi_io"
os.makedirs(PASTA, exist_ok=True)


def rota_io(params):
    kb = limitar(int(params.get("kb", 1024)), 1, 100 * 1024)
    dados = b"x" * (kb * 1024)
    caminho = os.path.join(PASTA, f"{uuid.uuid4().hex}.bin")

    with open(caminho, "wb") as arquivo:
        arquivo.write(dados)
        arquivo.flush()
        os.fsync(arquivo.fileno())  # espera o disco confirmar a gravação

    with open(caminho, "rb") as arquivo:
        lidos = len(arquivo.read())

    os.remove(caminho)
    return {"kb": kb, "bytes_gravados": len(dados), "bytes_lidos": lidos}


if __name__ == "__main__":
    iniciar_app(
        nome="io-bound",
        porta_padrao=8003,
        rotas={"/io": rota_io},
        descricao="IO-bound: grava (fsync), lê e apaga um arquivo de N KB",
    )
