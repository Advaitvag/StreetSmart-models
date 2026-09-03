#!/bin/bash
# Queue YOLO26s training — waits for YOLOv8s to finish first

echo "Waiting for YOLOv8s training to complete..."
while pgrep -f "combined_pothole" > /dev/null 2>&1; do
    sleep 30
done

echo "YOLOv8s done! Starting YOLO26s..."

cd /home/ad/potholes
PYTHONPATH="" /home/ad/miniconda3/envs/comfy/bin/python3 -c "
import os, sys
os.environ.pop('PYTHONPATH', None)
sys.path.insert(0, '/home/ad/miniconda3/envs/comfy/lib/python3.12/site-packages')
from ultralytics import YOLO

model = YOLO('yolo26s.pt')
print(f'YOLO26s loaded. Classes: {model.names}')

model.train(
    data='datasets/combined_dataset/data.yaml',
    epochs=50,
    imgsz=640,
    batch=16,
    patience=10,
    device=0,
    project='runs',
    name='combined_yolo26s',
    exist_ok=True,
    workers=2,
    amp=True,
)
print('YOLO26s DONE')
" 2>&1
