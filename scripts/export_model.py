import argparse
import os
import sys

import torch


def convert_model(model_size: str, output_name: str) -> str:
    size_path = "yolo26m-combined" if model_size == "med" else "yolo26s-combined"
    model_path = os.path.join(os.getcwd(), f"models/trained/{size_path}/weights/best.pt")
    model = torch.load(model_path, weights_only=False, map_location="cpu")

    model = model["model"].float()
    model.eval()

    dummy_input = torch.randn(1, 3, 640, 640)

    try:
        output_path = os.path.join(os.getcwd(), f"models/onnx_converted/{size_path}/{output_name}.onnx")
        # Ensure output directory exists before exporting
        out_dir = os.path.dirname(output_path)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            input_names=["images"],
            output_names=["output"],
            opset_version=17,
        )

        # Switch to model path
        return f"Success! model saved at {output_path}"
    except Exception as e:
        return f"Error converting model: {e}"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Export a trained YOLO26 pothole model to ONNX.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "model_size",
        nargs="?",
        default="med",
        help="Model size: 'med' for yolo26m-combined, anything else (e.g. 'small'/'s') for yolo26s-combined.",
    )
    p.add_argument(
        "output_name",
        nargs="?",
        default="medium_model",
        help="Output ONNX filename without extension (saved under models/onnx_converted/<size_path>/).",
    )
    p.add_argument(
        "--model-size",
        dest="model_size_opt",
        default=None,
        help="Alternative flag for model size (overrides positional).",
    )
    p.add_argument(
        "--output-name",
        dest="output_name_opt",
        default=None,
        help="Alternative flag for output name (overrides positional).",
    )
    return p


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[1:]
    args = build_parser().parse_args(argv)
    # Flags take precedence over positionals if provided
    if args.model_size_opt is not None:
        args.model_size = args.model_size_opt
    if args.output_name_opt is not None:
        args.output_name = args.output_name_opt
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = convert_model(model_size=args.model_size, output_name=args.output_name)
    print(result)
    return 0 if result.startswith("Success") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))