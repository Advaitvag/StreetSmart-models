#!/usr/bin/env python3
"""Build the combined pothole detection dataset from its upstream sources.

Merges eight YOLO-format pothole datasets into a single ``train`` / ``val``
split with one class (``0: pothole``). Segmentation polygons are converted to
axis-aligned boxes; multi-class sources are filtered down to their pothole
class.

Only the standard library is required. All paths are relative to
``--repo-root`` (default: the current directory).

Expected layout under ``--sources-dir`` (default ``<repo-root>/datasets``)::

    BharatPotHole/BharatPotHole/{train,valid,test}/{images,labels}
    HRP4K/{train,valid,test}/{images,labels}
    A Curated RGB Dataset for Real-Time Road Damage De/Data Y12 Final/{train,valid}/{images,labels}
    Pothole-detection-Yolov8/{train,valid,test}/{images,labels}
    dataset/{train,valid,test}/            (images and .txt labels co-located)
    PData/{images,labels}/                 (polygon segmentation labels)
    RDD_SPLIT/{train,val}/{images,labels}  (5 classes; class 3 == pothole)

Cincinnati 311 imagery is opt-in via ``--cincinnati`` and is NOT part of the
published dataset.

Example::

    python scripts/build_dataset.py                      # publishable build
    python scripts/build_dataset.py --cincinnati         # local training build
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

IMAGE_GLOBS = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")


class Builder:
    def __init__(self, out: Path, train_ratio: float, seed: int) -> None:
        self.out = out
        self.train_ratio = train_ratio
        self.rng = random.Random(seed)
        self.seed = seed
        self.stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"train": 0, "val": 0}
        )
        self.total = 0
        # stem -> source that first claimed it, for collision detection
        self._claimed: dict[str, str] = {}
        for split in ("train", "val"):
            (out / split / "images").mkdir(parents=True, exist_ok=True)
            (out / split / "labels").mkdir(parents=True, exist_ok=True)

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _find_image(img_dir: Path, stem: str) -> Path | None:
        for pattern in IMAGE_GLOBS:
            hit = next(iter(img_dir.glob(f"{stem}{pattern[1:]}")), None)
            if hit is not None:
                return hit
        # last resort: any extension
        hit = next(iter(img_dir.glob(f"{stem}.*")), None)
        return hit

    def _dest_stem(self, source: str, stem: str) -> str:
        """Return a unique stem, prefixing on cross-source collision."""
        owner = self._claimed.get(stem)
        if owner is None:
            self._claimed[stem] = source
            return stem
        if owner == source:
            return stem
        new_stem = f"{source}_{stem}"
        self._claimed.setdefault(new_stem, source)
        return new_stem

    def _emit(self, source: str, image: Path, lines: list[str], stem: str,
              split: str) -> None:
        dest_stem = self._dest_stem(source, stem)
        shutil.copy2(image, self.out / split / "images" / f"{dest_stem}{image.suffix}")
        (self.out / split / "labels" / f"{dest_stem}.txt").write_text(
            "\n".join(lines) + "\n"
        )
        self.stats[source][split] += 1
        self.total += 1

    def _split_for(self, index: int, count: int) -> str:
        return "train" if index < int(count * self.train_ratio) else "val"

    # -- ingest -------------------------------------------------------------

    def add_yolo_dir(self, source: str, img_dir: Path, lbl_dir: Path,
                     cls_map: dict[int, int] | None = None) -> None:
        """Add a plain YOLO-format directory, optionally remapping classes.

        ``cls_map`` maps *kept* source class ids to output class ids; any class
        not present as a key is dropped.
        """
        if not lbl_dir.is_dir() or not img_dir.is_dir():
            print(f"  {source}: skipped (missing {img_dir} or {lbl_dir})")
            return

        pairs: list[tuple[Path, list[str], str]] = []
        for lbl_file in sorted(lbl_dir.glob("*.txt")):
            image = self._find_image(img_dir, lbl_file.stem)
            if image is None:
                continue
            lines: list[str] = []
            for line in lbl_file.read_text().strip().splitlines():
                parts = line.split()
                if not parts:
                    continue
                cls = int(float(parts[0]))
                if cls_map is not None:
                    if cls not in cls_map:
                        continue
                    parts[0] = str(cls_map[cls])
                lines.append(" ".join(parts))
            if lines:
                pairs.append((image, lines, lbl_file.stem))

        self._ingest_pairs(source, pairs)

    def add_segmentation_dir(self, source: str, img_dir: Path,
                             lbl_dir: Path) -> None:
        """Add a polygon-segmentation dataset, converting polygons to boxes."""
        if not lbl_dir.is_dir() or not img_dir.is_dir():
            print(f"  {source}: skipped (missing {img_dir} or {lbl_dir})")
            return

        pairs: list[tuple[Path, list[str], str]] = []
        for lbl_file in sorted(lbl_dir.glob("*.txt")):
            image = self._find_image(img_dir, lbl_file.stem)
            if image is None:
                continue
            boxes: list[str] = []
            for line in lbl_file.read_text().strip().splitlines():
                parts = line.split()
                if len(parts) < 7:
                    continue
                coords = [float(x) for x in parts[1:]]
                xs, ys = coords[0::2], coords[1::2]
                cx = (min(xs) + max(xs)) / 2
                cy = (min(ys) + max(ys)) / 2
                bw = max(xs) - min(xs)
                bh = max(ys) - min(ys)
                boxes.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            if boxes:
                pairs.append((image, boxes, lbl_file.stem))

        self._ingest_pairs(source, pairs)

    def _ingest_pairs(self, source: str,
                      pairs: list[tuple[Path, list[str], str]]) -> None:
        self.rng.shuffle(pairs)
        for i, (image, lines, stem) in enumerate(pairs):
            self._emit(source, image, lines, stem, self._split_for(i, len(pairs)))
        s = self.stats[source]
        print(f"  {source}: {len(pairs)} images "
              f"({s['train']} train / {s['val']} val)")

    # -- outputs ------------------------------------------------------------

    def write_metadata(self, cincinnati_included: bool) -> None:
        (self.out / "data.yaml").write_text(
            "# Combined Pothole Detection Dataset\n"
            f"# Built {datetime.now(timezone.utc).isoformat()} "
            f"(seed={self.seed}, train_ratio={self.train_ratio})\n"
            "path: .\n"
            "train: train/images\n"
            "val: val/images\n\n"
            "nc: 1\n"
            "names:\n"
            "  0: pothole\n"
        )

        train_total = sum(s["train"] for s in self.stats.values())
        val_total = sum(s["val"] for s in self.stats.values())
        manifest = {
            "built": datetime.now(timezone.utc).isoformat(),
            "seed": self.seed,
            "train_ratio": self.train_ratio,
            "cincinnati_included": cincinnati_included,
            "totals": {
                "images": self.total,
                "train": train_total,
                "val": val_total,
            },
            "per_source": {
                name: dict(counts) for name, counts in sorted(self.stats.items())
            },
        }
        (self.out / "build_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        (self.out / "SOURCES.md").write_text(SOURCES_MD)

    def summary(self) -> None:
        print("\n" + "=" * 60)
        print(f"COMBINED DATASET: {self.total} images")
        for name, counts in sorted(self.stats.items()):
            t, v = counts["train"], counts["val"]
            print(f"  {name:<24s}: {t + v:>6} total  ({t} train / {v} val)")
        train_total = sum(s["train"] for s in self.stats.values())
        val_total = sum(s["val"] for s in self.stats.values())
        print(f"\n  TOTAL: {train_total} train / {val_total} val")


SOURCES_MD = """\
# Dataset sources & credits

This dataset is an **aggregate of independently-licensed source datasets**.
Each source keeps its own license (table below). In particular the `dataset/`
(Chitholian) portion is **ODbL v1.0**, and its share-alike terms continue to
apply to that portion. The split layout, `data.yaml`, `build_manifest.json`
and `build_dataset.py` added by this project are released under
**CC BY-SA 4.0**. When redistributing, comply with every source license for
the corresponding images and labels.

| Source | Attribution | License |
| --- | --- | --- |
| Roboflow "Pothole" raw (`dataset/`) | Atikur Rahman Chitholian | ODbL v1.0 |
| Roboflow "Potholes Detection" (`Pothole-detection-Yolov8/`) | Roboflow Universe `project-ssayl` | CC BY 4.0 |
| PothRGBD (`PData/`) | Yurdakul & Taşdemir, 2025 — *An Enhanced YOLOv8 Model for Real-Time and Accurate Pothole Detection and Measurement* (arXiv:2505.04207) | MIT |
| RDD2022 (`RDD_SPLIT/`, class `D40` pothole only) | Arya et al. — Road Damage Detection Challenge | CC BY-SA 4.0 |
| BharatPotHole | BharatPotHole authors | CC BY 4.0 |
| A Curated RGB Dataset for Real-Time Road Damage Detection | dataset authors (Mendeley Data) | CC BY 4.0 |
| HRP4K | HRP4K authors | CC BY-SA 4.0 (upstream license not stated; assumed) |
| Cincinnati 311 pothole imagery | City of Cincinnati / CAGIS | Not redistributed — excluded from the published dataset |

Cincinnati imagery is used only for the maintainer's local training runs
(`build_dataset.py --cincinnati`) and is never uploaded.
"""


def build(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    sources = Path(args.sources_dir) if args.sources_dir else repo_root / "datasets"
    sources = sources if sources.is_absolute() else repo_root / sources
    out = Path(args.out) if args.out else sources / "combined_dataset"
    out = out if out.is_absolute() else repo_root / out

    if out.exists() and any(out.iterdir()) and not args.force:
        print(f"error: {out} exists and is not empty (use --force).")
        return 1

    b = Builder(out, args.train_ratio, args.seed)

    curated = sources / "A Curated RGB Dataset for Real-Time Road Damage De" / "Data Y12 Final"

    # 1. BharatPotHole
    for split in ("train", "valid", "test"):
        base = sources / "BharatPotHole" / "BharatPotHole" / split
        b.add_yolo_dir("BharatPotHole", base / "images", base / "labels")

    # 2. HRP4K
    for split in ("train", "valid", "test"):
        base = sources / "HRP4K" / split
        b.add_yolo_dir("HRP4K", base / "images", base / "labels")

    # 3. Curated RGB — source class 1 == pothole -> 0
    for split in ("train", "valid"):
        base = curated / split
        b.add_yolo_dir("CuratedRGB", base / "images", base / "labels",
                       cls_map={1: 0})

    # 4. Roboflow "Potholes Detection"
    for split in ("train", "valid", "test"):
        base = sources / "Pothole-detection-Yolov8" / split
        b.add_yolo_dir("Roboflow-YOLOv8", base / "images", base / "labels")

    # 5. generic GoPro "dataset" — images and labels co-located per split
    for split in ("train", "valid", "test"):
        base = sources / "dataset" / split
        b.add_yolo_dir("dataset-generic", base, base)

    # 6. PData / PothRGBD — polygon segmentation -> bbox
    b.add_segmentation_dir("PData", sources / "PData" / "images",
                           sources / "PData" / "labels")

    # 7. RDD2022 — keep class 3 (D40 pothole), remap to 0
    for split in ("train", "val"):
        base = sources / "RDD_SPLIT" / split
        b.add_yolo_dir("RDD", base / "images", base / "labels", cls_map={3: 0})

    # 8. Cincinnati (opt-in only)
    if args.cincinnati:
        img_root = Path(args.cincinnati_images)
        img_root = img_root if img_root.is_absolute() else repo_root / img_root
        lbl_root = Path(args.cincinnati_labels)
        lbl_root = lbl_root if lbl_root.is_absolute() else repo_root / lbl_root
        index: dict[str, Path] = {}
        for pattern in IMAGE_GLOBS:
            for f in img_root.glob(f"**/{pattern}"):
                if f.stat().st_size > 5000:
                    index.setdefault(f.stem, f)
        pairs: list[tuple[Path, list[str], str]] = []
        for lbl in sorted(lbl_root.glob("*.txt")):
            text = lbl.read_text().strip()
            if text and lbl.stem in index:
                pairs.append((index[lbl.stem], text.splitlines(), lbl.stem))
        b._ingest_pairs("Cincinnati", pairs)

    b.summary()
    b.write_metadata(cincinnati_included=bool(args.cincinnati))
    print(f"\nwrote data.yaml, build_manifest.json, SOURCES.md -> {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--repo-root", default=".",
                   help="Project root; all other paths resolve against it.")
    p.add_argument("--sources-dir", default=None,
                   help="Directory holding the upstream datasets "
                        "(default: <repo-root>/datasets).")
    p.add_argument("--out", default=None,
                   help="Output dataset directory "
                        "(default: <sources-dir>/combined_dataset).")
    p.add_argument("--cincinnati-images", default="cincinnati",
                   help="Cincinnati image root (default: cincinnati).")
    p.add_argument("--cincinnati-labels", default="labels",
                   help="Cincinnati label root (default: labels).")
    p.add_argument("--cincinnati", action="store_true",
                   help="Include Cincinnati 311 pairs (NOT for the published "
                        "dataset).")
    p.add_argument("--train-ratio", type=float, default=0.85)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--force", action="store_true",
                   help="Write into a non-empty output directory.")
    return p


if __name__ == "__main__":
    raise SystemExit(build(build_parser().parse_args()))
