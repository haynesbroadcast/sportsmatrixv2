#!/usr/bin/env bash
set -e
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git libjpeg-dev zlib1g-dev
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Base install complete."
