#!/usr/bin/env python3
"""Train an Ultralytics YOLO model on the combined pothole dataset.

Standalone replacement for the inline ``python -c`` blocks in
``queue_yolo26*.sh``. Only depends on the standard library and
``ultralytics``.

Examples
--------
Train YOLO26s with the defaults (50 epochs, imgsz 640, batch 16)::

    python train.py --model yolo26s.pt

Train YOLO26m with a smaller batch and a custom run name::

    python train.py --model yolo26m.pt --batch 8 --name yolo26m-combined

Pass an arbitrary extra Ultralytics argument straight through::

    python train.py --model yolo11n.pt --set cos_lr=true --set close_mosaic=15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo root = directory containing this file. Every default path is relative
# to it so the script works regardless of the current working directory.
REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = "datasets/combined_dataset/data.yaml"


def parse_extra(pairs: list[str]) -> dict[str, object]:
    """Turn ``["cos_lr=true", "lr0=0.01"]`` into a typed kwargs dict."""
    extra: dict[str, object] = {}
    for item in pairs:
        if "=" not in item:
            raise argparse.ArgumentTypeError(
                f"--set expects KEY=VALUE, got {item!r}"
            )
        key, _, raw = item.partition("=")
        key = key.strip()
        raw = raw.strip()
        lowered = raw.lower()
        value: object
        if lowered in {"true", "false"}:
            value = lowered == "true"
        elif lowered in {"none", "null"}:
            value = None
        else:
            try:
                value = int(raw)
            except ValueError:
                try:
                    value = float(raw)
                except ValueError:
                    value = raw
        extra[key] = value
    return extra


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--model",
        default="yolo26s.pt",
        help="Weights path or Ultralytics model name (default: yolo26s.pt).",
    )
    p.add_argument(
        "--data",
        default=DEFAULT_DATA,
        help=f"Dataset YAML, relative to repo root (default: {DEFAULT_DATA}).",
    )
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--patience", type=int, default=10)
    p.add_argument(
        "--device",
        default="0",
        help="CUDA device index, 'cpu', or comma list (default: 0).",
    )
    p.add_argument("--project", default="runs", help="Ultralytics project dir.")
    p.add_argument(
        "--name",
        default=None,
        help="Run name (default: '<model-stem>-<data-stem>').",
    )
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--seed", type=int, default=0)

    amp = p.add_mutually_exclusive_group()
    amp.add_argument("--amp", dest="amp", action="store_true", default=True)
    amp.add_argument("--no-amp", dest="amp", action="store_false")

    val = p.add_mutually_exclusive_group()
    val.add_argument("--val", dest="val", action="store_true", default=True)
    val.add_argument("--no-val", dest="val", action="store_false")

    p.add_argument(
        "--resume",
        action="store_true",
        help="Resume the last interrupted run for this project/name.",
    )
    p.add_argument(
        "--exist-ok",
        action="store_true",
        help="Reuse the run directory if it already exists.",
    )
    p.add_argument(
        "--set",
        dest="extra",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra kwarg forwarded to model.train(); repeatable.",
    )
    return p


def resolve_path(value: str) -> str:
    """Resolve a possibly-relative path against the repo root."""
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return str(path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    data_path = resolve_path(args.data)
    if not Path(data_path).exists():
        print(f"error: dataset YAML not found: {data_path}", file=sys.stderr)
        return 2

    model_arg = args.model
    if model_arg.endswith((".pt", ".yaml")) and Path(model_arg).exists():
        model_arg = str(Path(model_arg).resolve())

    data_stem = Path(data_path).parent.name or Path(data_path).stem
    run_name = args.name or f"{Path(args.model).stem}-{data_stem}"

    train_kwargs: dict[str, object] = {
        "data": data_path,
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "patience": args.patience,
        "device": args.device,
        "project": args.project,
        "name": run_name,
        "workers": args.workers,
        "seed": args.seed,
        "amp": args.amp,
        "resume": args.resume,
        "exist_ok": args.exist_ok,
    }
    train_kwargs.update(parse_extra(args.extra))

    try:
        from ultralytics import YOLO
    except ImportError:
        print(
            "error: ultralytics is not installed. Activate the project venv:\n"
            "  source .venv/bin/activate\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    print(f"model: {model_arg}")
    print("train config:")
    for key, value in train_kwargs.items():
        print(f"  {key}: {value}")

    model = YOLO(model_arg)
    try:
        model.train(**train_kwargs)
        if args.val:
            model.val()
    except Exception as exc:  # noqa: BLE001 - surface any training failure
        print(f"error: training failed: {exc}", file=sys.stderr)
        return 1

    save_dir = getattr(getattr(model, "trainer", None), "save_dir", None)
    if save_dir:
        print(f"done. results in: {save_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
