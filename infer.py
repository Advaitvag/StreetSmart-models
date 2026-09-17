#!/usr/bin/env python3
"""Run inference with YOLO models on test videos or images.

Standalone inference CLI matching the style of ``train.py``. Only depends
on the standard library and ``ultralytics`` (with optional ``ffmpeg`` for
fast MP4 re-encoding).

Examples
--------
Run all night-trained models on default test videos::

    python infer.py

Run a specific model on the test videos::

    python infer.py --models runs/night-yolo26m/weights/best.pt

Run with a higher confidence threshold and custom output directory::

    python infer.py --models night --conf 0.4 --project runs/inference_c40

Pass arbitrary extra Ultralytics predict arguments straight through::

    python infer.py --set line_width=2 --set show_labels=true
"""

from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Repo root = directory containing this file. Every default path is relative
# to it so the script works regardless of the current working directory.
REPO_ROOT = Path(__file__).resolve().parent

DEFAULT_NIGHT_MODELS = [
    "runs/night-yolo11s/weights/best.pt",
    "runs/night-yolo26s/weights/best.pt",
    "runs/night-yolo26m/weights/best.pt",
    "runs/night-yolo11m/weights/best.pt",
]

DEFAULT_TEST_SOURCES = [
    "datasets/test_videos/*.mp4",
]


def parse_extra(pairs: list[str]) -> dict[str, object]:
    """Turn ``["line_width=2", "show_labels=true"]`` into a typed kwargs dict."""
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


def resolve_path(value: str | Path) -> Path:
    """Resolve a possibly-relative path against the repo root."""
    path = Path(value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def expand_sources(patterns: list[str]) -> list[Path]:
    """Resolve source files and glob patterns in order, eliminating duplicates."""
    resolved: list[Path] = []
    seen: set[Path] = set()

    for item in patterns:
        path = resolve_path(item)
        if any(char in item for char in ["*", "?", "["]):
            matched = [Path(p) for p in glob.glob(str(path))]
            matched.sort()
            for m in matched:
                if m.is_file() and m not in seen:
                    resolved.append(m)
                    seen.add(m)
        elif path.is_file():
            if path not in seen:
                resolved.append(path)
                seen.add(path)
        elif path.is_dir():
            for m in sorted(path.iterdir()):
                if m.is_file() and m not in seen:
                    resolved.append(m)
                    seen.add(m)
        else:
            print(f"warning: source not found: {item}", file=sys.stderr)

    return resolved


def expand_models(model_args: list[str]) -> list[Path]:
    """Resolve model weights, expanding the 'night' preset if specified."""
    resolved: list[Path] = []
    seen: set[Path] = set()

    for item in model_args:
        if item.lower() in {"night", "all-night", "default"}:
            for rel in DEFAULT_NIGHT_MODELS:
                p = resolve_path(rel)
                if p.exists() and p not in seen:
                    resolved.append(p)
                    seen.add(p)
                elif not p.exists():
                    print(f"warning: night model weights missing: {p}", file=sys.stderr)
        else:
            p = resolve_path(item)
            if p.exists() and p not in seen:
                resolved.append(p)
                seen.add(p)
            else:
                print(f"warning: model weights not found: {item}", file=sys.stderr)

    return resolved


def convert_avi_to_mp4(avi_path: Path) -> Path | None:
    """Re-encode an MJPG AVI to H.264 MP4 using ffmpeg (NVENC if available)."""
    if not shutil.which("ffmpeg"):
        return None

    mp4_path = avi_path.with_suffix(".mp4")
    # Try GPU nvenc first for blistering speed, then CPU libx264 fallback
    encoders = [
        ["ffmpeg", "-y", "-i", str(avi_path), "-c:v", "h264_nvenc", "-cq", "24", "-preset", "p4", "-pix_fmt", "yuv420p", str(mp4_path)],
        ["ffmpeg", "-y", "-i", str(avi_path), "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(mp4_path)],
    ]

    for cmd in encoders:
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            avi_path.unlink(missing_ok=True)
            return mp4_path
        except Exception:
            continue

    print(f"warning: ffmpeg MP4 conversion failed for {avi_path.name}", file=sys.stderr)
    return None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--models",
        nargs="+",
        default=["night"],
        help="Weights paths, run names, or 'night' for all night-trained models (default: night).",
    )
    p.add_argument(
        "--source",
        nargs="+",
        default=DEFAULT_TEST_SOURCES,
        help="Input video/image paths or glob patterns (default: datasets/test_videos/*.mp4).",
    )
    p.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25).")
    p.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold (default: 0.45).")
    p.add_argument("--imgsz", type=int, default=640, help="Inference image size (default: 640).")
    p.add_argument(
        "--device",
        default="0",
        help="CUDA device index, 'cpu', or comma list (default: 0).",
    )
    p.add_argument(
        "--project",
        default="runs/inference",
        help="Base directory for saving inference results (default: runs/inference).",
    )
    p.add_argument(
        "--name",
        default=None,
        help="Custom run name/subfolder (default: model run directory stem).",
    )
    p.add_argument(
        "--save-txt",
        action="store_true",
        help="Save results as *.txt labels.",
    )
    p.add_argument(
        "--save-conf",
        action="store_true",
        help="Include confidence scores in saved labels.",
    )

    save_vid = p.add_mutually_exclusive_group()
    save_vid.add_argument(
        "--save-vid",
        dest="save_vid",
        action="store_true",
        default=True,
        help="Save annotated detection videos/images (default: True).",
    )
    save_vid.add_argument("--no-save-vid", dest="save_vid", action="store_false")

    mp4 = p.add_mutually_exclusive_group()
    mp4.add_argument(
        "--mp4",
        dest="convert_mp4",
        action="store_true",
        default=True,
        help="Convert output AVI videos to MP4 using ffmpeg (default: True).",
    )
    mp4.add_argument("--no-mp4", dest="convert_mp4", action="store_false")

    stream = p.add_mutually_exclusive_group()
    stream.add_argument(
        "--stream",
        dest="stream",
        action="store_true",
        default=True,
        help="Stream frames generator to keep memory usage minimal (default: True).",
    )
    stream.add_argument("--no-stream", dest="stream", action="store_false")

    p.add_argument(
        "--set",
        dest="extra",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra kwarg forwarded to model.predict(); repeatable.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    models = expand_models(args.models)
    if not models:
        print("error: no valid model weights found", file=sys.stderr)
        return 2

    sources = expand_sources(args.source)
    if not sources:
        print("error: no valid input sources found", file=sys.stderr)
        return 2

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

    project_dir = resolve_path(args.project)
    project_dir.mkdir(parents=True, exist_ok=True)

    extra_kwargs = parse_extra(args.extra)

    print("=" * 70)
    print("StreetSmart Inference")
    print("=" * 70)
    print(f"Models ({len(models)}):")
    for m in models:
        print(f"  - {m.relative_to(REPO_ROOT) if m.is_relative_to(REPO_ROOT) else m}")
    print(f"Sources ({len(sources)}):")
    for s in sources:
        print(f"  - {s.relative_to(REPO_ROOT) if s.is_relative_to(REPO_ROOT) else s}")
    print(f"Config: conf={args.conf}, iou={args.iou}, imgsz={args.imgsz}, device={args.device}")
    print(f"Output: {project_dir.relative_to(REPO_ROOT) if project_dir.is_relative_to(REPO_ROOT) else project_dir}")
    print("=" * 70)

    summary_records: list[dict[str, object]] = []

    for model_path in models:
        # Determine a recognizable subfolder name (e.g., night-yolo26m)
        if args.name:
            run_name = args.name
        elif model_path.parent.name == "weights":
            run_name = model_path.parent.parent.name
        else:
            run_name = model_path.stem

        print(f"\n>>> Loading model: {run_name} ({model_path.name})")
        model = YOLO(str(model_path))

        for src in sources:
            src_name = src.name
            print(f"\n--- Running inference on: {src_name} ---")
            t0 = time.time()

            predict_kwargs: dict[str, object] = {
                "source": str(src),
                "conf": args.conf,
                "iou": args.iou,
                "imgsz": args.imgsz,
                "device": args.device,
                "project": str(project_dir),
                "name": run_name,
                "exist_ok": True,
                "save": args.save_vid,
                "save_txt": args.save_txt,
                "save_conf": args.save_conf,
                "stream": args.stream,
                "verbose": True,
            }
            predict_kwargs.update(extra_kwargs)

            total_frames = 0
            total_detections = 0

            try:
                results_gen = model.predict(**predict_kwargs)
                if args.stream:
                    for r in results_gen:
                        total_frames += 1
                        total_detections += len(r.boxes)
                else:
                    results_list = list(results_gen)
                    total_frames = len(results_list)
                    for r in results_list:
                        total_detections += len(r.boxes)
            except Exception as exc:
                print(f"error: inference failed for {src_name}: {exc}", file=sys.stderr)
                continue

            elapsed = time.time() - t0
            fps = total_frames / elapsed if elapsed > 0 else 0.0

            # Target output path check
            target_dir = project_dir / run_name
            saved_file: Path | None = None

            # Look for written video / output
            avi_candidates = list(target_dir.glob(f"{src.stem}*.avi"))
            mp4_candidates = list(target_dir.glob(f"{src.stem}*.mp4"))

            if args.convert_mp4 and avi_candidates:
                for avi in avi_candidates:
                    print(f"Converting {avi.name} to MP4 (H.264)...")
                    mp4_out = convert_avi_to_mp4(avi)
                    if mp4_out:
                        saved_file = mp4_out
            elif mp4_candidates:
                saved_file = mp4_candidates[0]
            elif avi_candidates:
                saved_file = avi_candidates[0]

            print(
                f"Finished {src_name} in {elapsed:.1f}s ({fps:.1f} fps) | "
                f"Frames: {total_frames} | Potholes detected: {total_detections}"
            )
            if saved_file:
                rel = saved_file.relative_to(REPO_ROOT) if saved_file.is_relative_to(REPO_ROOT) else saved_file
                print(f"Saved: {rel}")

            summary_records.append({
                "model": run_name,
                "source": src_name,
                "frames": total_frames,
                "detections": total_detections,
                "fps": round(fps, 1),
                "elapsed_s": round(elapsed, 1),
                "output": str(saved_file.relative_to(REPO_ROOT) if saved_file and saved_file.is_relative_to(REPO_ROOT) else saved_file),
            })

    print("\n" + "=" * 70)
    print("Inference Summary")
    print("=" * 70)
    print(f"{'Model':<16} {'Source Video':<42} {'Frames':<8} {'Detections':<12} {'FPS':<6} {'Time(s)'}")
    print("-" * 90)
    for rec in summary_records:
        src_abbr = rec["source"] if len(str(rec["source"])) <= 40 else str(rec["source"])[:37] + "..."
        print(
            f"{str(rec['model']):<16} {src_abbr:<42} {str(rec['frames']):<8} "
            f"{str(rec['detections']):<12} {str(rec['fps']):<6} {str(rec['elapsed_s'])}"
        )
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
