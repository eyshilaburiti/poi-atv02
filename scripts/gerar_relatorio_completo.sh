#!/bin/bash

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Gerando Gráficos de Stress Testing                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if ! command -v Rscript &> /dev/null; then
    echo "❌ R não está instalado!"
    echo "   Ubuntu: sudo apt install -y r-base"
    echo "   macOS: brew install r"
    exit 1
fi

Rscript scripts/gerar_graficos.R
