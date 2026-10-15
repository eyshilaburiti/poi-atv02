#!/bin/bash

VM_IP="192.168.10.14"
VM_USER="osboxes"
VM_PASSWORD="osboxes.org"

echo "Limpando cache da VM ($VM_IP)..."
echo

sshpass -p "$VM_PASSWORD" ssh "$VM_USER@$VM_IP" 'sync; echo 3 > /proc/sys/vm/drop_caches'

if [ $? -eq 0 ]; then
    echo "✅ Cache limpo com sucesso"
    echo
    echo "Verificando memória livre..."
    sshpass -p "$VM_PASSWORD" ssh "$VM_USER@$VM_IP" 'free -h'
else
    echo "❌ Erro ao limpar cache"
    exit 1
fi
