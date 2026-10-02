#!/bin/bash
set -e
cd "$(dirname "$0")"
sudo apt update && sudo apt install -y python3 python3-venv python3-pip curl
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
B=https://raw.githubusercontent.com/vladmandic/face-api/master
curl -fL -o static/face-api.js $B/dist/face-api.js
for f in tiny_face_detector_model face_landmark_68_model face_recognition_model; do
  curl -fL -o static/models/$f-weights_manifest.json $B/model/$f-weights_manifest.json
  curl -fL -o static/models/$f.bin $B/model/$f.bin
done
echo "SETUP SELESAI. Jalankan: ./run.sh"
