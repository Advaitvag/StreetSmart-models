# Code Documentation

Notes on the codebase: architecture, setup, scripts, models, and the Android app. They describe `main` @ `b85d457` plus the `android-capture-app` and `origin/backend_pipeline` branches, as of 2026-10-08.

| Note | What it covers |
| --- | --- |
| [Overview](Overview.md) | What the repo is, the data → train → infer flow, layout, branches, stack |
| [Setup](Setup.md) | venv, CUDA, Git LFS, which data each task needs |
| [Dataset Builder](Dataset_Builder.md) | `scripts/build_dataset.py`, sources, the two datasets on disk |
| [Training](Training.md) | `train.py`, the night sweep + systemd timers, Cincinnati-free fine-tuning, run history |
| [Inference](Inference.md) | `infer.py` |
| [Models and Accuracy](Models_and_Accuracy.md) | Model registry and **the accuracy numbers to report** (Cincinnati-free held-out set) |
| [Android Capture App](Android_Capture_App.md) | StreetSmart Capture: video + GPS recording, session format, architecture |
| [Backend Pipeline](Backend_Pipeline.md) | Go/Gin + ONNX Runtime scaffold, model export |
| [Known Issues](Known_Issues.md) | Inconsistencies and gotchas found while documenting |

> [!important] Reporting accuracy
> Use only the held-out, Cincinnati-free numbers in [Models and Accuracy](Models_and_Accuracy.md). Best model: `runs/night-yolo26m` with **mAP50 0.808 / mAP50-95 0.567**. Cincinnati 311 labels may be inaccurate, and the logged training metrics either include them or overlap the training data.

Create a new note here and insert [the code doc template](../Templates/Code_Doc.md) with **Templates: Insert template**.
