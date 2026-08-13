from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image

from build_codex_pet import lulu_core_features
from process_waving_loop_transition import alpha_outline_features


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure CapyLulu's expectant waving pose and grounded loop seam."
    )
    parser.add_argument("--direct-gaze-reference", required=True)
    parser.add_argument("--neutral-reference", required=True)
    parser.add_argument("--frame-7", required=True)
    parser.add_argument("--frame-8", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    direct_reference = Image.open(args.direct_gaze_reference).convert("RGBA")
    neutral_reference = Image.open(args.neutral_reference).convert("RGBA")
    frame_7 = Image.open(args.frame_7).convert("RGBA")
    frame_8 = Image.open(args.frame_8).convert("RGBA")

    reference_eyes = eye_features(direct_reference)
    pose_eyes = eye_features(frame_7)
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

    outlines = {
        "frame_7": alpha_outline_features(frame_7),
        "frame_8": alpha_outline_features(frame_8),
        "neutral_reference": alpha_outline_features(neutral_reference),
    }
    support_centers = [
        float(outlines[key]["support_center_x_px"])
        for key in ("frame_7", "frame_8", "neutral_reference")
    ]
    core = lulu_core_features(frame_7)
    core_offset = float(core["centroid_x_px"]) - float(
        outlines["frame_7"]["support_center_x_px"]
    )
    edge_margins = {
        key: {
            "left": int(features["bbox"][0]),
            "top": int(features["bbox"][1]),
            "right": frame_7.width - int(features["bbox"][2]),
            "bottom": frame_7.height - int(features["bbox"][3]),
        }
        for key, features in outlines.items()
    }

    checks = {
        "direct_gaze_matches_reference_within_2px": max_gaze_delta <= 2,
        "body_has_subtle_screen_right_lean": 1 <= eye_line_angle <= 8,
        "core_is_right_of_ground_support_by_3_to_10px": 3 <= core_offset <= 10,
        "ground_support_stays_within_1px_through_seam": (
            maximum_pairwise_difference(support_centers) <= 1
        ),
        "grounded_frames_share_alpha_bottom": (
            int(outlines["frame_7"]["alpha_bottom_px"])
            == int(outlines["frame_8"]["alpha_bottom_px"])
            == int(outlines["neutral_reference"]["alpha_bottom_px"])
        ),
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
            "frame_7": str(Path(args.frame_7).resolve()),
            "frame_8": str(Path(args.frame_8).resolve()),
        },
        "checks": checks,
        "direct_gaze": {
            "reference_eyes": reference_eyes,
            "pose_eyes": pose_eyes,
            "pose_minus_reference_pupil_offsets_px": gaze_delta,
            "maximum_absolute_offset_delta_px": max_gaze_delta,
        },
        "lean": {
            "eye_center_line_angle_degrees_clockwise": eye_line_angle,
            "lulu_core_centroid_x_px": core["centroid_x_px"],
            "support_center_x_px": outlines["frame_7"]["support_center_x_px"],
            "core_centroid_minus_support_center_x_px": core_offset,
        },
        "loop_registration": {
            "support_centers_x_px": dict(
                zip(
                    ("frame_7", "frame_8", "neutral_reference"),
                    support_centers,
                    strict=True,
                )
            ),
            "maximum_pairwise_support_center_difference_px": (
                maximum_pairwise_difference(support_centers)
            ),
            "outlines": outlines,
            "edge_margins_px": edge_margins,
        },
    }
    output = Path(args.json_out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "report": str(output.resolve())}, indent=2))


if __name__ == "__main__":
    main()
