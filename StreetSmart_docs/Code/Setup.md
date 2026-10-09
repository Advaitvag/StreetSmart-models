---
type: code-doc
component: Environment setup
source: requirements.txt, .gitattributes
tags:
  - code
  - setup
---

# Setup

## Purpose

Getting a working Python/GPU environment and the data needed to train or evaluate.

## How it works

- **Python 3.12 venv** at `.venv/`. The system Python (3.14) is ahead of the available torch wheels, so any 3.12 interpreter is used to create the venv.
- `requirements.txt` pins `torch==2.10.0` / `torchvision==0.25.0` from the CUDA 12.8 wheel index (needed for RTX 50-series / Blackwell), plus `ultralytics==8.4.9` and `huggingface_hub[cli]`.
- Weights (`*.pt`, `*.pth`) and training plots are stored with **Git LFS**.
- Datasets are **not in git**. They are placed under `datasets/` locally. See [[Dataset_Builder]].

## Usage

```bash
git lfs install                 # once, before/after cloning
git clone https://github.com/Advaitvag/StreetSmart-models && cd StreetSmart-models

python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import torch; print(torch.cuda.is_available())"   # -> True
```

Data you need for each task:

| Task | Needs |
| --- | --- |
| Inference with trained weights | Only the repo (weights are in LFS) + some video |
| Reproduce held-out accuracy | `datasets/combined_dataset` and `datasets/_upload_PotholesCombined` |
| Rebuild the dataset | The seven upstream datasets under `datasets/` (layout in [[Dataset_Builder]]) |
| Night sweep | `datasets/combined_dataset/data.yaml` + the systemd units ([[Training]]) |

Every Python CLI resolves relative paths against the **repo root**, so it can be run from any working directory. The shell scripts default to `REPO=/home/ad/potholes`; override with `STREETSMART_REPO=...`.

## Related

- [[Overview]] · [[Training]] · [[Inference]]
