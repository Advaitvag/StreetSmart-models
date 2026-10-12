---
type: code-doc
component: Backend pipeline (Go + ONNX)
source: branch origin/backend_pipeline → backend/, scripts/export_model.py
tags:
  - code
  - backend
---

# Backend Pipeline

> [!info] Branch / status
> This code is on **`origin/backend_pipeline`** and is not merged into `main`. It is an early scaffold (latest commit: "WIP: scaffold Detector and model loader constructor"). The full design (PostgreSQL/PostGIS, ingestion, REST API, Supabase Storage) is in [[D1_Detailed_Design]].

## Purpose

The server side of StreetSmart. It will:

- run the trained detector on uploaded drive footage with ONNX Runtime from Go
- match detections to GPS (see [[Android_Capture_App]])
- store and serve them through a Gin REST API

## How it works (current code)

| File | State |
| --- | --- |
| `scripts/export_model.py` | Loads `models/trained/yolo26m-combined/weights/best.pt` (`model_size` = `med`, the default) or `yolo26s-combined` (any other value). Usage: `export_model.py [med\|small] [output_name]` or `--model-size` / `--output-name`. Exports the raw `model["model"]` with `torch.onnx.export` (input `images` 1×3×640×640, output `output`, opset 17) to `models/onnx_converted/<model>/<name>.onnx`. |
| `backend/cmd/server/main.go` | Gin server on `:8080` with only `GET /health → {"status":"ok"}`. |
| `backend/cmd/inference-test/main.go` | Harness for testing the ONNX runtime setup (Linux/Windows). |
| `backend/internal/inference/inference.go` | `Detector` wrapping `onnxruntime_go.AdvancedSession`. `NewDetector` is a stub that returns `nil, nil`. |

## Usage

```bash
git switch backend_pipeline   # or: git worktree add ../ss-backend origin/backend_pipeline
.venv/bin/python scripts/export_model.py med medium_model   # → models/onnx_converted/yolo26m-combined/medium_model.onnx
cd backend && go run ./cmd/server   # → curl localhost:8080/health
```

> [!warning] Export the better model
> `export_model.py` hard-codes the **50-epoch** `models/trained/yolo26m-combined` weights, which score mAP50-95 0.398 on the held-out set. `runs/night-yolo26m/weights/best.pt` scores **0.567**. Point the exporter at the night model, or copy it into `models/trained/`. See [[Models_and_Accuracy]].
>
> Ultralytics' own exporter, `YOLO(path).export(format="onnx", opset=17)`, is an alternative to raw `torch.onnx.export`. It handles fusing and the output head layout that the Go side will have to decode.

## Related

- [[Models_and_Accuracy]] · [[Android_Capture_App]] · [[Overview]]
