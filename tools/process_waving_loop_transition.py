from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from types import ModuleType

from PIL import Image

from build_action_gifs import load_action, load_manifest, zero_transparent_rgb


ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "pet-runs" / "capybara-lulu"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def save_frames(frames: list[Image.Image], directory: Path, prefix: str) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for master_number, frame in enumerate(frames, start=6):
        output = directory / f"{prefix}-{master_number:02d}.png"
        zero_transparent_rgb(frame).save(output)
        outputs.append(output)
    return outputs


def alpha_outline_features(frame: Image.Image) -> dict[str, object]:
    rgba = frame.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("Cannot measure a fully transparent sprite")
    left, top, right, bottom = bbox
    area = sum(alpha.get_flattened_data()) / 255
    width = right - left
    height = bottom - top
    support_band_top = max(top, bottom - 12)
    alpha_pixels = alpha.load()
    support_x = [
        x
        for y in range(support_band_top, bottom)
        for x in range(left, right)
        if alpha_pixels[x, y] >= 128
    ]
    support_center_x = (
        sum(support_x) / len(support_x)
        if support_x
        else (left + right) / 2
    )
    return {
        "area_px": area,
        "equivalent_diameter_px": 2 * math.sqrt(area / math.pi),
        "bbox": list(bbox),
        "bbox_width_px": width,
        "bbox_height_px": height,
        "bbox_geometric_mean_px": math.sqrt(width * height),
        "bbox_center_x_px": (left + right) / 2,
        "alpha_bottom_px": bottom,
        "support_band_top_px": support_band_top,
        "support_center_x_px": support_center_x,
    }


def binary_alpha(frame: Image.Image, threshold: int = 128) -> Image.Image:
    rgba = frame.convert("RGBA")
    alpha = rgba.getchannel("A").point(lambda value: 255 if value >= threshold else 0)
    rgba.putalpha(alpha)
    return zero_transparent_rgb(rgba)


def normalize_by_outline(
    frames: list[Image.Image],
    anchors: list[Image.Image],
) -> tuple[list[Image.Image], dict[str, object]]:
    if len(frames) != len(anchors):
        raise ValueError("Every continuation frame needs one semantic size anchor")

    target_center_x = 96
    target_bottom = 200
    top_margin = 5
    side_margin = 5
    normalized: list[Image.Image] = []
    frame_reports: list[dict[str, object]] = []

    for master_number, (frame, anchor) in enumerate(zip(frames, anchors, strict=True), start=6):
        source = alpha_outline_features(frame)
        target = alpha_outline_features(anchor)
        diameter_scale = float(target["equivalent_diameter_px"]) / float(
            source["equivalent_diameter_px"]
        )
        bbox_scale = float(target["bbox_geometric_mean_px"]) / float(
            source["bbox_geometric_mean_px"]
        )
        requested_scale = math.sqrt(diameter_scale * bbox_scale)
        source_width = int(source["bbox_width_px"])
        source_height = int(source["bbox_height_px"])
        vertical_fit_scale = (target_bottom - top_margin) / source_height
        horizontal_fit_scale = (frame.width - 2 * side_margin) / source_width
        applied_scale = min(requested_scale, vertical_fit_scale, horizontal_fit_scale)

        left, top, right, bottom = source["bbox"]
        sprite = frame.crop((left, top, right, bottom))
        scaled_size = (
            max(1, round(sprite.width * applied_scale)),
            max(1, round(sprite.height * applied_scale)),
        )
        sprite = sprite.resize(scaled_size, Image.Resampling.NEAREST)
        output = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        offset = (
            round(target_center_x - scaled_size[0] / 2),
            target_bottom - scaled_size[1],
        )
        output.alpha_composite(sprite, offset)
        output = binary_alpha(output)
        registered = alpha_outline_features(output)
        if master_number == 6:
            horizontal_anchor = "bbox-center-for-airborne-follow-through"
            horizontal_shift = round(
                target_center_x - float(registered["bbox_center_x_px"])
            )
        else:
            horizontal_anchor = "bottom-support-center-for-grounded-pose"
            horizontal_shift = round(
                float(target["support_center_x_px"])
                - float(registered["support_center_x_px"])
            )
        registration_shift = (
            horizontal_shift,
            target_bottom - int(registered["alpha_bottom_px"]),
        )
        if registration_shift != (0, 0):
            shifted = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            shifted.alpha_composite(output, registration_shift)
            output = zero_transparent_rgb(shifted)
        output_features = alpha_outline_features(output)
        output_fused_size_ratio = math.sqrt(
            (
                float(output_features["equivalent_diameter_px"])
                / float(target["equivalent_diameter_px"])
            )
            * (
                float(output_features["bbox_geometric_mean_px"])
                / float(target["bbox_geometric_mean_px"])
            )
        )
        normalized.append(output)
        frame_reports.append(
            {
                "master_frame_number": master_number,
                "anchor_master_frame_number": 5 if master_number == 6 else 1,
                "source_outline": source,
                "target_outline": target,
                "diameter_scale": diameter_scale,
                "bbox_scale": bbox_scale,
                "requested_feature_scale": requested_scale,
                "vertical_fit_scale": vertical_fit_scale,
                "horizontal_fit_scale": horizontal_fit_scale,
                "applied_scale": applied_scale,
                "vertical_fit_constraint_active": applied_scale < requested_scale,
                "offset_px": list(offset),
                "post_binary_registration_shift_px": list(registration_shift),
                "horizontal_registration_anchor": horizontal_anchor,
                "output_outline": output_features,
                "output_fused_size_ratio": output_fused_size_ratio,
            }
        )

    report = {
        "method": "semantic-anchor-alpha-outline-feature-normalization",
        "feature_formula": (
            "sqrt((target equivalent diameter / source equivalent diameter) * "
            "(target bbox geometric mean / source bbox geometric mean))"
        ),
        "semantic_anchors": {
            "frame_6": "approved waving frame 5 follow-through",
            "frames_7_8": "approved waving frame 1 compact neutral stance",
        },
        "registration": {
            "initial_bbox_center_x_px": target_center_x,
            "horizontal_anchor_policy": {
                "frame_6": "bbox center because one foot remains airborne",
                "frames_7_8": (
                    "semantic anchor frame's alpha centroid within the bottom "
                    "12-pixel support band because both feet are grounded"
                ),
            },
            "alpha_bottom_px": target_bottom,
            "minimum_top_margin_px": top_margin,
            "minimum_side_margin_px": side_margin,
        },
        "resampling": "nearest-neighbor",
        "alpha_policy": "binary alpha at threshold 128 after despill and scaling",
        "source_master_modified": False,
        "new_master_frame_numbers": [6, 7, 8],
        "frames": frame_reports,
        "applied_scale_range": [
            min(float(frame["applied_scale"]) for frame in frame_reports),
            max(float(frame["applied_scale"]) for frame in frame_reports),
        ],
        "output_fused_size_ratio_range": [
            min(float(frame["output_fused_size_ratio"]) for frame in frame_reports),
            max(float(frame["output_fused_size_ratio"]) for frame in frame_reports),
        ],
        "output_fused_size_max_deviation": max(
            abs(float(frame["output_fused_size_ratio"]) - 1)
            for frame in frame_reports
        ),
    }
    return normalized, report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract, despill, and scientifically size-match a three-pose "
            "continuation strip for CapyLulu waving frames 6-8."
        )
    )
    parser.add_argument("input_strip")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--chroma-key", default="#FF00FF")
    parser.add_argument("--key-threshold", type=float, default=96.0)
    args = parser.parse_args()

    input_path = Path(args.input_strip).expanduser().resolve()
    output_root = Path(args.output_dir).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    skill_scripts = codex_home() / "skills" / "hatch-pet" / "scripts"
    extractor = load_module(
        "hatch_pet_extract_strip_frames",
        skill_scripts / "extract_strip_frames.py",
    )
    despiller = load_module(
        "hatch_pet_despill_chroma_edges",
        skill_scripts / "despill_chroma_edges.py",
    )
    chroma_key = extractor.parse_hex_color(args.chroma_key)

    with Image.open(input_path) as opened:
        keyed = extractor.remove_chroma_background(
            opened,
            chroma_key,
            args.key_threshold,
        )
    extracted_frames = extractor.extract_stable_slot_frames(keyed, 3)
    extracted_paths = save_frames(extracted_frames, output_root / "extracted", "waving")

    despilled_frames: list[Image.Image] = []
    despill_reports: list[dict[str, object]] = []
    for master_number, frame in enumerate(extracted_frames, start=6):
        cleaned, report = despiller.decontaminate_image(
            frame,
            chroma_key=chroma_key,
        )
        despilled_frames.append(cleaned)
        despill_reports.append({"master_frame_number": master_number, **report})
    despilled_paths = save_frames(
        despilled_frames,
        output_root / "despilled",
        "waving",
    )

    states, _ = load_manifest()
    waving_entry = states["waving"]
    if not isinstance(waving_entry, dict):
        raise ValueError("Waving reference state is malformed")
    waving_frames = load_action("waving", waving_entry)[0]
    if len(waving_frames) < 5:
        raise ValueError("Waving must contain approved frames 1-5 before extension")
    normalized_frames, feature_report = normalize_by_outline(
        despilled_frames,
        [waving_frames[4], waving_frames[0], waving_frames[0]],
    )

    normalized_paths = save_frames(
        normalized_frames,
        output_root / "normalized",
        "waving",
    )
    report = {
        "ok": True,
        "input_strip": str(input_path),
        "input_sha256": sha256(input_path),
        "frame_count": 3,
        "master_frame_numbers": [6, 7, 8],
        "extraction": {
            "method": "hatch-pet extract_stable_slot_frames",
            "chroma_key": args.chroma_key.upper(),
            "key_threshold": args.key_threshold,
            "outputs": [str(path) for path in extracted_paths],
        },
        "despill": {
            "method": "hatch-pet edge-local-chroma-spill-suppression",
            "outputs": [str(path) for path in despilled_paths],
            "frames": despill_reports,
        },
        "feature_normalization": feature_report,
        "outputs": [
            {
                "path": str(path),
                "sha256": sha256(path),
                "size": list(Image.open(path).size),
            }
            for path in normalized_paths
        ],
    }
    report_path = output_root / "processing-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
