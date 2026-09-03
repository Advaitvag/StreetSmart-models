#!/bin/bash
echo "Waiting for YOLO26s to finish..."
while pgrep -f "combined_yolo26s" > /dev/null 2>&1; do sleep 30; done

echo "Starting YOLO26m training..."

cd /home/ad/potholes
rm -rf runs/combined_yolo26m 2>/dev/null

PYTHONPATH="" /home/ad/miniconda3/envs/comfy/bin/python3 -c "
import os, sys
os.environ.pop('PYTHONPATH', None)
sys.path.insert(0, '/home/ad/miniconda3/envs/comfy/lib/python3.12/site-packages')
from ultralytics import YOLO

model = YOLO('yolo26m.pt')
print('YOLO26m loaded')

model.train(
    data='datasets/combined_dataset/data.yaml',
    epochs=50,
    imgsz=640,
    batch=8,
    patience=10,
    device=0,
    project='runs',
    name='combined_yolo26m',
    exist_ok=True,
    workers=2,
    amp=True,
)
print('YOLO26m DONE')
" 2>&1
