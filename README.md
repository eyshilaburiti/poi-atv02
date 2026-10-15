# Demanda, Provisionamento e Desempenho

A atividade mostra, por meio de experimentos, como a demanda e o provisionamento de recursos de uma máquina virtual afetam o desempenho de aplicações com perfis computacionais diferentes.

## Aplicações

São três backends HTTP em Python 3, feitos só com a biblioteca padrão. Eles compartilham o módulo [apps/common.py](apps/common.py), que fornece o servidor multithreaded e as rotas `/health` e `/metrics`.

| App | Porta | Rota | O que faz |
|-----|-------|------|-----------|
| [cpu_app.py](apps/cpu_app.py) | 8001 | `GET /cpu?n=100000` | Conta os números primos até `n` |
| [mem_app.py](apps/mem_app.py) | 8002 | `GET /mem?mb=64&hold_ms=100` | Aloca e copia `mb` MB de RAM e os mantém por `hold_ms` ms |
| [io_app.py](apps/io_app.py) | 8003 | `GET /io?kb=1024` | Grava o arquivo com `fsync`, lê de volta e apaga |

## Experimentos

Na VM (VirtualBox com Ubuntu Server), cada aplicação foi testada sob 4 cenários de provisionamento, com 7 níveis de requisições simultâneas em cada um. A carga é gerada da máquina hospedeira, e o `vmstat` e o `iostat` registram o uso de recursos dentro da VM.

- **CPU-bound:** 1 a 4 CPUs, com 1 GB de RAM (5 a 200 requisições)
- **Memory-bound:** 512 MB a 4 GB de RAM, com 2 CPUs (5 a 200 requisições, 128 MB cada)
- **IO-bound:** dois conjuntos de 4 cenários, um variando CPU e outro variando RAM (5 a 500 requisições, arquivos de 10 MB)


## Estrutura

- `apps/`: as três aplicações
- `scripts/`: testes de stress, automação, conversão dos logs (`vmstat_to_csv.py`, `iostat_to_csv.py`) e gráficos em R
- `resultados/<app>/cenario_*`: CSVs e logs brutos de cada cenário, com os gráficos em `graficos/`

## Conclusões

Cada perfil de aplicação tem um recurso que limita o desempenho. A aplicação CPU-bound ganha vazão com mais CPUs (de 4,5 para 13 req/s), mas cada CPU a mais rende menos que a anterior. A aplicação Memory-bound entra em swap com 1 GB ou menos de RAM, e a partir de 2 GB o gargalo passa a ser a CPU. A aplicação IO-bound continua limitada pelo disco, mesmo com mais CPU ou RAM.
