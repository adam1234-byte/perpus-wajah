#!/bin/bash
set -e
cd "$(dirname "$0")"
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
echo "SETUP SELESAI. Jalankan: ./run.sh"
