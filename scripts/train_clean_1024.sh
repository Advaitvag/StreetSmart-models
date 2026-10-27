#!/usr/bin/env bash
# Clean YOLO26m at 1024 px with a regularized recipe.
#
# Why (see StreetSmart_docs/Code/Training.md): clean200-yolo26m overfit (val
# loss bottomed near epoch 40, best.pt at 67) and lost most of its mAP on the
# small-pothole sources. The two 4K sources (HRP4K, dataset-generic) have
# potholes around 0.05% of the frame, about 10 px at 640.
#
#   * 1024 px: those potholes are about 2.5x larger in pixels;
#   * 80 epochs + cosine LR instead of 200 linear;
#   * scale 0.9 (zoom 0.1-1.9x) and mixup 0.1 against overfitting;
#   * batch 4 to fit 1024 px in 8 GB; Ultralytics accumulates to nbs 64.
#
# Everything else is train_clean.sh: same clean split, COCO start, resume on
# re-run, Ctrl-C checkpoints, final test score -> runs/<name>/test_metrics.json
# (night-yolo26m compared at the 640 px it was trained at).
#
#     nohup scripts/train_clean_1024.sh >>runs/streetsmart_clean1024.out 2>&1 &

export STREETSMART_MODEL="${STREETSMART_MODEL:-yolo26m}"
export STREETSMART_NAME="${STREETSMART_NAME:-clean1024-$STREETSMART_MODEL}"
export STREETSMART_IMGSZ="${STREETSMART_IMGSZ:-1024}"
export STREETSMART_EPOCHS="${STREETSMART_EPOCHS:-80}"
export STREETSMART_BATCH="${STREETSMART_BATCH:-4}"
export STREETSMART_HYP="${STREETSMART_HYP:-cos_lr=true scale=0.9 mixup=0.1}"

exec "$(dirname "$0")/train_clean.sh"
