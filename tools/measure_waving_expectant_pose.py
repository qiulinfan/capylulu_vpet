from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image

from build_action_gifs import rgba_rmse
from build_codex_pet import lulu_core_features
from process_waving_loop_transition import (
    WARM_FAMILIES,
    alpha_outline_features,
    median_rgb,
    warm_pixels,
)


def eye_features(frame: Image.Image) -> list[dict[str, object]]:
    rgba = frame.convert("RGBA")
    pixels = rgba.load()
    remaining: set[tuple[int, int]] = set()
    for y in range(40, 120):
        for x in range(20, rgba.width - 20):
            red, green, blue, alpha = pixels[x, y]
            neutral = max(red, green, blue) - min(red, green, blue) <= 80
            white_or_dark = min(red, green, blue) >= 150 or max(red, green, blue) <= 100
            if alpha >= 128 and neutral and white_or_dark:
                remaining.add((x, y))

    components: list[list[tuple[int, int]]] = []
    while remaining:
        pending = [remaining.pop()]
        component: list[tuple[int, int]] = []
        while pending:
            x, y = pending.pop()
            component.append((x, y))
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    pending.append(neighbor)
        if len(component) < 40:
            continue
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        width = max(xs) - min(xs) + 1
        height = max(ys) - min(ys) + 1
        if 10 <= width <= 35 and 10 <= height <= 35:
            components.append(component)

    if len(components) < 2:
        raise ValueError("Could not isolate two open eyes")
    selected = sorted(components, key=len, reverse=True)[:2]
    selected.sort(key=lambda component: sum(x for x, _ in component) / len(component))

    results: list[dict[str, object]] = []
    for component in selected:
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        left, top, right, bottom = min(xs), min(ys), max(xs) + 1, max(ys) + 1
        eye_center = ((left + right - 1) / 2, (top + bottom - 1) / 2)
        dark = [
            (x, y)
            for x, y in component
            if max(pixels[x, y][:3]) <= 100
        ]
        if not dark:
            raise ValueError("Eye component has no pupil")
        pupil_center = (
            sum(x for x, _ in dark) / len(dark),
            sum(y for _, y in dark) / len(dark),
        )
        results.append(
            {
                "bbox": [left, top, right, bottom],
                "geometric_center_px": list(eye_center),
                "pupil_center_px": list(pupil_center),
                "pupil_offset_from_eye_center_px": [
                    pupil_center[0] - eye_center[0],
                    pupil_center[1] - eye_center[1],
                ],
            }
        )
    return results


def maximum_pairwise_difference(values: list[float]) -> float:
    return max(values) - min(values)


def palette_medians(frames: list[Image.Image]) -> dict[str, tuple[int, int, int]]:
    values = warm_pixels(frames)
    return {
        family: median_rgb(family_values)
        for family, family_values in values.items()
    }


def input_image(path: str) -> Image.Image:
    with Image.open(path) as opened:
        return opened.convert("RGBA")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Measure CapyLulu's direct-gaze expectant poses, warm palette, "
            "ground registration, and loop seam."
        )
    )
    parser.add_argument("--direct-gaze-reference", required=True)
    parser.add_argument("--neutral-reference", required=True)
    parser.add_argument(
        "--palette-reference",
        action="append",
        required=True,
        help="Approved frame used to establish the gold warm-color medians; repeatable.",
    )
    parser.add_argument(
        "--expectant-frame",
        action="append",
        required=True,
        help="Open-eye low-clasp expectant pose; repeat for every held pose.",
    )
    parser.add_argument("--loop-tail-frame", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()
    if len(args.expectant_frame) < 3:
        raise ValueError("Provide at least three expectant frames for the held pose")

    direct_reference = input_image(args.direct_gaze_reference)
    neutral_reference = input_image(args.neutral_reference)
    palette_references = [input_image(path) for path in args.palette_reference]
    expectant_frames = [input_image(path) for path in args.expectant_frame]
    loop_tail = input_image(args.loop_tail_frame)

    reference_eyes = eye_features(direct_reference)
    reference_outline = alpha_outline_features(direct_reference)
    reference_eye_center_y_from_top = (
        sum(float(eye["geometric_center_px"][1]) for eye in reference_eyes) / 2
        - float(reference_outline["bbox"][1])
    )
    gold_palette = palette_medians(palette_references)
    pose_reports: list[dict[str, object]] = []

    for path, pose in zip(args.expectant_frame, expectant_frames, strict=True):
        pose_eyes = eye_features(pose)
        eye_line_dx = (
            float(pose_eyes[1]["geometric_center_px"][0])
            - float(pose_eyes[0]["geometric_center_px"][0])
        )
        eye_line_dy = (
            float(pose_eyes[1]["geometric_center_px"][1])
            - float(pose_eyes[0]["geometric_center_px"][1])
        )
        eye_line_angle = math.degrees(math.atan2(eye_line_dy, eye_line_dx))
        gaze_delta = [
            [
                float(pose_eyes[index]["pupil_offset_from_eye_center_px"][axis])
                - float(reference_eyes[index]["pupil_offset_from_eye_center_px"][axis])
                for axis in range(2)
            ]
            for index in range(2)
        ]
        max_gaze_delta = max(abs(value) for pair in gaze_delta for value in pair)
        outline = alpha_outline_features(pose)
        pose_eye_center_y_from_top = (
            sum(float(eye["geometric_center_px"][1]) for eye in pose_eyes) / 2
            - float(outline["bbox"][1])
        )
        eye_vertical_delta = (
            pose_eye_center_y_from_top - reference_eye_center_y_from_top
        )
        core = lulu_core_features(pose)
        core_offset = float(core["centroid_x_px"]) - float(
            outline["support_center_x_px"]
        )
        pose_palette = palette_medians([pose])
        palette_distances = {
            family: math.dist(pose_palette[family], gold_palette[family])
            for family in WARM_FAMILIES
        }
        pose_reports.append(
            {
                "path": str(Path(path).resolve()),
                "eyes": pose_eyes,
                "pose_minus_reference_pupil_offsets_px": gaze_delta,
                "maximum_absolute_gaze_offset_delta_px": max_gaze_delta,
                "eye_center_line_angle_degrees_clockwise": eye_line_angle,
                "eye_center_y_from_alpha_top_px": pose_eye_center_y_from_top,
                "eye_center_y_delta_from_direct_reference_px": eye_vertical_delta,
                "lulu_core_centroid_x_px": core["centroid_x_px"],
                "support_center_x_px": outline["support_center_x_px"],
                "core_centroid_minus_support_center_x_px": core_offset,
                "warm_palette_median_rgb": {
                    family: list(value) for family, value in pose_palette.items()
                },
                "warm_palette_distance_to_gold": palette_distances,
                "outline": outline,
                "checks": {
                    "direct_gaze_within_3px_of_reference": max_gaze_delta <= 3,
                    "eyes_not_lowered_on_face": abs(eye_vertical_delta) <= 6,
                    "head_has_4_to_12_degree_screen_right_lean": (
                        4 <= eye_line_angle <= 12
                    ),
                    "core_is_right_of_support_by_2_5_to_12px": (
                        2.5 <= core_offset <= 12
                    ),
                    "warm_palette_within_3_rgb_units": all(
                        distance <= 3 for distance in palette_distances.values()
                    ),
                },
            }
        )

    outlines = {
        **{
            f"expectant_{index}": report["outline"]
            for index, report in enumerate(pose_reports, start=1)
        },
        "loop_tail": alpha_outline_features(loop_tail),
        "neutral_reference": alpha_outline_features(neutral_reference),
    }
    support_centers = [
        float(features["support_center_x_px"])
        for features in outlines.values()
    ]
    edge_margins = {}
    outline_images = [*expectant_frames, loop_tail, neutral_reference]
    for (key, features), image in zip(
        outlines.items(),
        outline_images,
        strict=True,
    ):
        edge_margins[key] = {
            "left": int(features["bbox"][0]),
            "top": int(features["bbox"][1]),
            "right": image.width - int(features["bbox"][2]),
            "bottom": image.height - int(features["bbox"][3]),
        }
    seam_rmse = rgba_rmse(loop_tail, neutral_reference)

    checks = {
        "all_expectant_pose_checks_pass": all(
            all(bool(value) for value in report["checks"].values())
            for report in pose_reports
        ),
        "ground_support_stays_within_2px_through_hold_and_seam": (
            maximum_pairwise_difference(support_centers) <= 2
        ),
        "grounded_frames_share_alpha_bottom": len(
            {int(features["alpha_bottom_px"]) for features in outlines.values()}
        )
        == 1,
        "loop_tail_to_neutral_rmse_at_most_0_19": seam_rmse <= 0.19,
        "no_sprite_touches_cell_edge": all(
            margin > 0
            for margins in edge_margins.values()
            for margin in margins.values()
        ),
    }
    report = {
        "ok": all(checks.values()),
        "coordinate_system": "origin top-left; x increases screen-right; y increases down",
        "inputs": {
            "direct_gaze_reference": str(Path(args.direct_gaze_reference).resolve()),
            "neutral_reference": str(Path(args.neutral_reference).resolve()),
            "palette_references": [
                str(Path(path).resolve()) for path in args.palette_reference
            ],
            "expectant_frames": [
                str(Path(path).resolve()) for path in args.expectant_frame
            ],
            "loop_tail_frame": str(Path(args.loop_tail_frame).resolve()),
        },
        "checks": checks,
        "direct_gaze": {
            "reference_eyes": reference_eyes,
            "reference_eye_center_y_from_alpha_top_px": (
                reference_eye_center_y_from_top
            ),
        },
        "gold_warm_palette_median_rgb": {
            family: list(value) for family, value in gold_palette.items()
        },
        "expectant_poses": pose_reports,
        "loop_registration": {
            "support_centers_x_px": dict(zip(outlines, support_centers, strict=True)),
            "maximum_pairwise_support_center_difference_px": (
                maximum_pairwise_difference(support_centers)
            ),
            "loop_tail_to_neutral_rgba_rmse": seam_rmse,
            "outlines": outlines,
            "edge_margins_px": edge_margins,
        },
        "semantic_visual_gate": {
            "required": True,
            "reason": (
                "Automated geometry cannot reliably distinguish a low gentle "
                "paw clasp from a high V-shaped self-hug or infer emotional intent."
            ),
            "must_confirm": [
                "paws clasp low above the shorts waistband in frames 8-10",
                "pose reads attentive and ready, not shy or downcast",
                "frame 12 is one small motion step from neutral frame 1",
            ],
        },
    }
    output = Path(args.json_out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "report": str(output.resolve())}, indent=2))


if __name__ == "__main__":
    main()
