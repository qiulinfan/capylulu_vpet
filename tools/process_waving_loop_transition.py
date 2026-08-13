from __future__ import annotations

import argparse
import colorsys
import hashlib
import importlib.util
import json
import math
import os
import statistics
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


def save_frames(
    frames: list[Image.Image],
    directory: Path,
    prefix: str,
    *,
    start_frame: int = 6,
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for master_number, frame in enumerate(frames, start=start_frame):
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
    *,
    start_frame: int = 6,
    anchor_frame_numbers: list[int] | None = None,
) -> tuple[list[Image.Image], dict[str, object]]:
    if len(frames) != len(anchors):
        raise ValueError("Every continuation frame needs one semantic size anchor")
    if anchor_frame_numbers is None:
        anchor_frame_numbers = [5] + [1] * (len(frames) - 1)
    if len(anchor_frame_numbers) != len(frames):
        raise ValueError("Every continuation frame needs one anchor frame number")

    target_center_x = 96
    target_bottom = 200
    top_margin = 5
    side_margin = 5
    normalized: list[Image.Image] = []
    frame_reports: list[dict[str, object]] = []

    for index, (frame, anchor) in enumerate(zip(frames, anchors, strict=True)):
        master_number = start_frame + index
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
        if index == 0:
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
                "anchor_master_frame_number": anchor_frame_numbers[index],
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
            f"frame_{start_frame}": (
                f"approved waving frame {anchor_frame_numbers[0]} follow-through"
            ),
            f"frames_{start_frame + 1}_{start_frame + len(frames) - 1}": (
                f"approved waving frame {anchor_frame_numbers[-1]} compact neutral stance"
            ),
        },
        "registration": {
            "initial_bbox_center_x_px": target_center_x,
            "horizontal_anchor_policy": {
                f"frame_{start_frame}": (
                    "bbox center because the follow-through may remain airborne"
                ),
                f"frames_{start_frame + 1}_{start_frame + len(frames) - 1}": (
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
        "new_master_frame_numbers": list(
            range(start_frame, start_frame + len(frames))
        ),
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


WARM_FAMILIES = {
    "yellow_skin": {
        "hue_min": 38.0,
        "hue_max": 60.0,
        "saturation_min": 0.45,
        "value_min": 0.45,
    },
    "orange_accents": {
        "hue_min": 15.0,
        "hue_max": 38.0,
        "saturation_min": 0.55,
        "value_min": 0.45,
    },
}


def warm_family(rgb: tuple[int, int, int]) -> str | None:
    red, green, blue = rgb
    hue, saturation, value = colorsys.rgb_to_hsv(
        red / 255,
        green / 255,
        blue / 255,
    )
    hue *= 360
    for family, limits in WARM_FAMILIES.items():
        if (
            float(limits["hue_min"]) <= hue < float(limits["hue_max"])
            and saturation >= float(limits["saturation_min"])
            and value >= float(limits["value_min"])
        ):
            return family
    return None


def warm_pixels(
    frames: list[Image.Image],
) -> dict[str, list[tuple[int, int, int]]]:
    values: dict[str, list[tuple[int, int, int]]] = {
        family: [] for family in WARM_FAMILIES
    }
    for frame in frames:
        for red, green, blue, alpha in frame.convert("RGBA").get_flattened_data():
            if alpha < 128:
                continue
            rgb = (red, green, blue)
            family = warm_family(rgb)
            if family is not None:
                values[family].append(rgb)
    return values


def median_rgb(values: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    if not values:
        raise ValueError("Cannot calculate a warm-palette median without pixels")
    return tuple(
        round(statistics.median(pixel[channel] for pixel in values))
        for channel in range(3)
    )


def lock_warm_palette(
    frames: list[Image.Image],
    reference_frames: list[Image.Image],
    *,
    start_frame: int,
) -> tuple[list[Image.Image], dict[str, object]]:
    reference_values = warm_pixels(reference_frames)
    targets = {
        family: median_rgb(values)
        for family, values in reference_values.items()
    }
    outputs: list[Image.Image] = []
    frame_reports: list[dict[str, object]] = []

    for master_number, frame in enumerate(frames, start=start_frame):
        source_values = warm_pixels([frame])
        before = {
            family: median_rgb(values)
            for family, values in source_values.items()
        }
        deltas = {
            family: tuple(
                targets[family][channel] - before[family][channel]
                for channel in range(3)
            )
            for family in WARM_FAMILIES
        }
        shifted_pixels: list[tuple[int, int, int, int]] = []
        for red, green, blue, alpha in frame.convert("RGBA").get_flattened_data():
            family = warm_family((red, green, blue)) if alpha >= 128 else None
            if family is None:
                shifted_pixels.append((red, green, blue, alpha))
                continue
            delta = deltas[family]
            shifted_pixels.append(
                (
                    max(0, min(255, red + delta[0])),
                    max(0, min(255, green + delta[1])),
                    max(0, min(255, blue + delta[2])),
                    alpha,
                )
            )
        output = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        output.putdata(shifted_pixels)
        output = zero_transparent_rgb(output)
        after_values = warm_pixels([output])
        after = {
            family: median_rgb(values)
            for family, values in after_values.items()
        }
        deviations = {
            family: math.dist(after[family], targets[family])
            for family in WARM_FAMILIES
        }
        outputs.append(output)
        frame_reports.append(
            {
                "master_frame_number": master_number,
                "before_median_rgb": {
                    family: list(value) for family, value in before.items()
                },
                "applied_rgb_delta": {
                    family: list(value) for family, value in deltas.items()
                },
                "after_median_rgb": {
                    family: list(value) for family, value in after.items()
                },
                "distance_to_gold_median": deviations,
            }
        )

    max_deviation = max(
        float(distance)
        for frame_report in frame_reports
        for distance in frame_report["distance_to_gold_median"].values()
    )
    report = {
        "method": "per-frame warm-family median RGB alignment",
        "reference_master_frame_numbers": list(range(1, len(reference_frames) + 1)),
        "gold_median_rgb": {
            family: list(value) for family, value in targets.items()
        },
        "family_classifiers_hsv": WARM_FAMILIES,
        "frames": frame_reports,
        "max_distance_to_gold_median": max_deviation,
        "gate_max_distance": 3.0,
        "gate_pass": max_deviation <= 3.0,
    }
    if not report["gate_pass"]:
        raise ValueError(
            "Warm-palette lock did not converge within the 3-RGB-unit gate"
        )
    return outputs, report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract, despill, and scientifically size-match a continuation "
            "strip for CapyLulu waving."
        )
    )
    parser.add_argument("input_strip")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--chroma-key", default="#FF00FF")
    parser.add_argument("--key-threshold", type=float, default=96.0)
    parser.add_argument("--frame-count", type=int, default=3)
    parser.add_argument("--frame-start", type=int, default=6)
    parser.add_argument(
        "--lock-warm-palette",
        action="store_true",
        help="Align yellow skin and orange accents to approved waving frames 1-5.",
    )
    args = parser.parse_args()
    if args.frame_count <= 0:
        raise ValueError("--frame-count must be positive")
    if args.frame_start <= 0:
        raise ValueError("--frame-start must be positive")

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
    extracted_frames = extractor.extract_stable_slot_frames(keyed, args.frame_count)
    extracted_paths = save_frames(
        extracted_frames,
        output_root / "extracted",
        "waving",
        start_frame=args.frame_start,
    )

    despilled_frames: list[Image.Image] = []
    despill_reports: list[dict[str, object]] = []
    for master_number, frame in enumerate(
        extracted_frames,
        start=args.frame_start,
    ):
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
        start_frame=args.frame_start,
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
        [waving_frames[4]] + [waving_frames[0]] * (args.frame_count - 1),
        start_frame=args.frame_start,
        anchor_frame_numbers=[5] + [1] * (args.frame_count - 1),
    )
    if args.lock_warm_palette:
        normalized_frames, palette_report = lock_warm_palette(
            normalized_frames,
            waving_frames[:5],
            start_frame=args.frame_start,
        )
    else:
        palette_report = {"enabled": False}

    normalized_paths = save_frames(
        normalized_frames,
        output_root / "normalized",
        "waving",
        start_frame=args.frame_start,
    )
    report = {
        "ok": True,
        "input_strip": str(input_path),
        "input_sha256": sha256(input_path),
        "frame_count": args.frame_count,
        "master_frame_numbers": list(
            range(args.frame_start, args.frame_start + args.frame_count)
        ),
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
        "warm_palette_lock": palette_report,
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
