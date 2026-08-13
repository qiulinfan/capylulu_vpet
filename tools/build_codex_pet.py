from __future__ import annotations

import argparse
import colorsys
import json
import math
import os
import shutil
import statistics
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, features

from build_action_gifs import (
    build as build_action_gifs,
    load_action,
    load_manifest,
    sha256,
    write_gif,
    zero_transparent_rgb,
)


ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "pet-runs" / "capybara-lulu"
MANIFEST = PET / "official-frames-v1-manifest.json"
FINAL = PET / "final"
CONTACT_SHEET = PET / "qa" / "codex-adapter-contact-sheet.png"
WORKING_PREVIEW = PET / "qa" / "codex-working-preview.gif"
WORKING_FULL_PREVIEW = PET / "qa" / "codex-working-normalized-full-preview.gif"
WORKING_FULL_CONTACT_SHEET = (
    PET / "qa" / "codex-working-normalized-full-contact-sheet.png"
)
WORKING_SCALE_REPORT = PET / "qa" / "working-scale-feature-report.json"
WORKING_VISUAL_QA = PET / "qa" / "working-scale-feature-visual-qa.json"

PET_ID = "capybara-lulu"
CELL_SIZE = (192, 208)
ATLAS_COLUMNS = 8
ATLAS_ROWS = 9
ATLAS_SIZE = (ATLAS_COLUMNS * CELL_SIZE[0], ATLAS_ROWS * CELL_SIZE[1])
SPRITE_VERSION_NUMBER = 1
CODEX_APP_VERSION = "26.803.41515"
CODEX_REQUIRED_FRAMES_BY_ROW = [6, 8, 8, 4, 5, 8, 6, 6, 6]
WORKING_REFERENCE_STATES = ("running-right", "running-left", "waving", "review")
WORKING_RUNTIME_FRAME_NUMBERS = (1, 6, 8, 10, 13, 15)


@dataclass(frozen=True)
class AdapterRow:
    runtime_state: str
    master_state: str
    master_frame_numbers: tuple[int, ...]
    note: str


ADAPTER_ROWS = (
    AdapterRow(
        "idle",
        "idle",
        (1, 4, 6, 8, 10, 12),
        "six key poses selected from the complete twelve-frame sleeping loop",
    ),
    AdapterRow("running-right", "running-right", tuple(range(1, 9)), "exact master action"),
    AdapterRow("running-left", "running-left", tuple(range(1, 9)), "exact master action"),
    AdapterRow("waving", "waving", tuple(range(1, 5)), "exact master action"),
    AdapterRow(
        "jumping",
        "waving",
        (1, 2, 3, 4, 1),
        "Codex-required hover row derived from the approved waving replacement",
    ),
    AdapterRow(
        "failed",
        "failed",
        (1, 4, 6, 7, 8, 9, 10, 12),
        "symmetric eight-pose selection from the same sleeping loop used by idle",
    ),
    AdapterRow("waiting", "waiting", tuple(range(1, 7)), "exact master action"),
    AdapterRow(
        "running",
        "working",
        (1, 6, 8, 10, 13, 15),
        "Codex task-running state mapped to the approved work cycle: blank page, marks, finished shrimp, page change, reset",
    ),
    AdapterRow("review", "review", tuple(range(1, 7)), "exact master action"),
)


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def checker(size: tuple[int, int], square: int = 8) -> Image.Image:
    image = Image.new("RGBA", size, (238, 238, 238, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], square):
        for x in range(0, size[0], square):
            if (x // square + y // square) % 2:
                draw.rectangle(
                    (x, y, x + square - 1, y + square - 1),
                    fill=(211, 211, 211, 255),
                )
    return image


def lulu_palette_components(frame: Image.Image) -> list[list[tuple[int, int]]]:
    """Return Lulu-colored 4-connected components, largest first."""
    rgba = frame.convert("RGBA")
    remaining: set[tuple[int, int]] = set()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = rgba.getpixel((x, y))
            if alpha < 16:
                continue
            hue, saturation, value = colorsys.rgb_to_hsv(
                red / 255,
                green / 255,
                blue / 255,
            )
            orange_or_yellow = (
                0.025 <= hue <= 0.19 and saturation >= 0.43 and value >= 0.35
            )
            leaf_green = (
                0.20 <= hue <= 0.48 and saturation >= 0.38 and value >= 0.20
            )
            if orange_or_yellow or leaf_green:
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
        components.append(component)
    if not components:
        raise ValueError("Could not isolate Lulu's palette component")
    return sorted(components, key=len, reverse=True)


def component_bbox(component: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    xs = [point[0] for point in component]
    ys = [point[1] for point in component]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def lulu_core_features(frame: Image.Image) -> dict[str, object]:
    """Measure Lulu's anatomical core independently of painting props."""
    core = lulu_palette_components(frame)[0]
    left, top, right, bottom = component_bbox(core)
    xs = [point[0] for point in core]
    ys = [point[1] for point in core]
    area = len(core)
    width = right - left
    height = bottom - top
    return {
        "area_px": area,
        "equivalent_diameter_px": 2 * math.sqrt(area / math.pi),
        "bbox": [left, top, right, bottom],
        "bbox_width_px": width,
        "bbox_height_px": height,
        "bbox_geometric_mean_px": math.sqrt(width * height),
        "centroid_x_px": sum(xs) / area,
        "centroid_y_px": sum(ys) / area,
    }


def lulu_semantic_contour(frame: Image.Image) -> dict[str, object]:
    """Bound the core plus detached orange paws/limbs, excluding pale props."""
    components = lulu_palette_components(frame)
    core = components[0]
    core_bbox = component_bbox(core)
    included = [core]
    included_metadata = [
        {"area_px": len(core), "bbox": list(core_bbox), "role": "anatomical-core"}
    ]
    for component in components[1:]:
        bbox = component_bbox(component)
        if len(component) >= 80 and bbox[1] < core_bbox[3] and bbox[3] <= core_bbox[3] + 2:
            included.append(component)
            included_metadata.append(
                {"area_px": len(component), "bbox": list(bbox), "role": "detached-limb"}
            )
    points = [point for component in included for point in component]
    bbox = component_bbox(points)
    return {
        "bbox": list(bbox),
        "component_count": len(included),
        "components": included_metadata,
    }


def median_feature_summary(frames: list[Image.Image]) -> dict[str, float]:
    features_by_frame = [lulu_core_features(frame) for frame in frames]
    return {
        key: statistics.median(float(features[key]) for features in features_by_frame)
        for key in (
            "area_px",
            "equivalent_diameter_px",
            "bbox_geometric_mean_px",
            "centroid_x_px",
        )
    } | {
        "alpha_bottom_px": statistics.median(
            frame.getchannel("A").getbbox()[3] for frame in frames
        )
    }


def normalize_working_sequence(
    working_frames: list[Image.Image],
    reference_frames: dict[str, list[Image.Image]],
) -> tuple[list[Image.Image], dict[str, object]]:
    """Equalize Lulu per frame while scaling the complete working composition."""
    reference_state_medians = {
        state: median_feature_summary(reference_frames[state])
        for state in WORKING_REFERENCE_STATES
    }
    target_equivalent_diameter = statistics.median(
        summary["equivalent_diameter_px"]
        for summary in reference_state_medians.values()
    )
    target_bbox_geometric_mean = statistics.median(
        summary["bbox_geometric_mean_px"]
        for summary in reference_state_medians.values()
    )
    target_centroid_x = statistics.median(
        summary["centroid_x_px"] for summary in reference_state_medians.values()
    )
    target_alpha_bottom = round(
        statistics.median(
            summary["alpha_bottom_px"] for summary in reference_state_medians.values()
        )
    )

    normalized_frames: list[Image.Image] = []
    frame_reports: list[dict[str, object]] = []
    contour_source_padding = 2
    contour_output_margin = 2
    source_measurements: list[dict[str, object]] = []
    for frame_number, frame in enumerate(working_frames, start=1):
        source_features = lulu_core_features(frame)
        source_contour = lulu_semantic_contour(frame)
        diameter_scale = target_equivalent_diameter / float(
            source_features["equivalent_diameter_px"]
        )
        bbox_scale = target_bbox_geometric_mean / float(
            source_features["bbox_geometric_mean_px"]
        )
        requested_scale = math.sqrt(diameter_scale * bbox_scale)
        contour_left, _, contour_right, _ = source_contour["bbox"]
        padded_contour_width = (
            contour_right - contour_left + 2 * contour_source_padding
        )
        contour_fit_scale = (
            frame.width - 2 * contour_output_margin - 1
        ) / padded_contour_width
        alpha_bbox = frame.getchannel("A").getbbox()
        if alpha_bbox is None:
            raise ValueError(f"Working frame {frame_number} is fully transparent")
        source_measurements.append(
            {
                "frame_number": frame_number,
                "frame": frame,
                "source_features": source_features,
                "source_contour": source_contour,
                "diameter_scale": diameter_scale,
                "bbox_scale": bbox_scale,
                "requested_scale": requested_scale,
                "contour_fit_scale": contour_fit_scale,
                "alpha_bbox": alpha_bbox,
            }
        )

    common_safe_target_ratio = min(
        1.0,
        min(
            float(measurement["contour_fit_scale"])
            / float(measurement["requested_scale"])
            for measurement in source_measurements
        ),
    )
    for measurement in source_measurements:
        frame_number = int(measurement["frame_number"])
        frame = measurement["frame"]
        source_features = measurement["source_features"]
        source_contour = measurement["source_contour"]
        diameter_scale = float(measurement["diameter_scale"])
        bbox_scale = float(measurement["bbox_scale"])
        requested_scale = float(measurement["requested_scale"])
        contour_fit_scale = float(measurement["contour_fit_scale"])
        alpha_bbox = measurement["alpha_bbox"]
        scale = requested_scale * common_safe_target_ratio
        contour_left, _, contour_right, _ = source_contour["bbox"]

        requested_offset_x = round(
            target_centroid_x - scale * float(source_features["centroid_x_px"])
        )
        minimum_offset_x = math.ceil(
            contour_output_margin
            - scale * (contour_left - contour_source_padding)
        )
        maximum_offset_x = math.floor(
            frame.width
            - contour_output_margin
            - scale * (contour_right + contour_source_padding)
        )
        if minimum_offset_x > maximum_offset_x:
            raise ValueError(
                f"Working frame {frame_number}: contour fit rounding escaped its cell"
            )
        offset = (
            min(max(requested_offset_x, minimum_offset_x), maximum_offset_x),
            round(target_alpha_bottom - scale * alpha_bbox[3]),
        )
        scaled = frame.resize(
            (round(frame.width * scale), round(frame.height * scale)),
            Image.Resampling.NEAREST,
        )

        def composite_at(position: tuple[int, int]) -> Image.Image:
            canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            canvas.alpha_composite(scaled, position)
            return zero_transparent_rgb(canvas)

        output = composite_at(offset)
        output_features = lulu_core_features(output)
        output_contour = lulu_semantic_contour(output)
        fused_size_ratio = math.sqrt(
            (
                float(output_features["equivalent_diameter_px"])
                / target_equivalent_diameter
            )
            * (
                float(output_features["bbox_geometric_mean_px"])
                / target_bbox_geometric_mean
            )
        )
        output_alpha = output.getchannel("A")
        edge_counts = {
            "top": sum(1 for x in range(output.width) if output_alpha.getpixel((x, 0))),
            "right": sum(
                1
                for y in range(output.height)
                if output_alpha.getpixel((output.width - 1, y))
            ),
            "bottom": sum(
                1
                for x in range(output.width)
                if output_alpha.getpixel((x, output.height - 1))
            ),
            "left": sum(1 for y in range(output.height) if output_alpha.getpixel((0, y))),
        }
        normalized_frames.append(output)
        frame_reports.append(
            {
                "frame_number": frame_number,
                "selected_for_codex_runtime": frame_number
                in WORKING_RUNTIME_FRAME_NUMBERS,
                "source_lulu": source_features,
                "source_lulu_semantic_contour": source_contour,
                "diameter_scale": diameter_scale,
                "bbox_scale": bbox_scale,
                "requested_feature_scale": requested_scale,
                "contour_fit_scale": contour_fit_scale,
                "common_safe_target_ratio": common_safe_target_ratio,
                "contour_fit_constraint_active": common_safe_target_ratio < 1,
                "applied_scale": scale,
                "offset_px": list(offset),
                "horizontal_safety_shift_px": offset[0] - requested_offset_x,
                "output_lulu": output_features,
                "output_lulu_semantic_contour": output_contour,
                "output_fused_size_ratio": fused_size_ratio,
                "output_alpha_bbox": output_alpha.getbbox(),
                "output_alpha_edge_pixels": edge_counts,
            }
        )

    report: dict[str, object] = {
        "method": (
            "per-frame-lulu-silhouette-feature-normalization-with-semantic-"
            "contour-fit"
        ),
        "segmentation": {
            "alpha_min": 16,
            "orange_yellow_hsv": {
                "hue": [0.025, 0.19],
                "saturation_min": 0.43,
                "value_min": 0.35,
            },
            "leaf_green_hsv": {
                "hue": [0.20, 0.48],
                "saturation_min": 0.38,
                "value_min": 0.20,
            },
            "component": "largest 4-connected palette component",
            "semantic_contour": (
                "anatomical core plus detached palette components of at least "
                "80 pixels above the core baseline"
            ),
            "excluded_props": ["paper", "ink dish", "brush", "black ink"],
        },
        "reference_states": list(WORKING_REFERENCE_STATES),
        "reference_weighting": "equal state weight via median of state medians",
        "reference_state_medians": reference_state_medians,
        "targets": {
            "equivalent_diameter_px": target_equivalent_diameter,
            "bbox_geometric_mean_px": target_bbox_geometric_mean,
            "lulu_centroid_x_px": target_centroid_x,
            "composition_alpha_bottom_px": target_alpha_bottom,
        },
        "scale_formula": (
            "sqrt((target_equivalent_diameter / source_equivalent_diameter) * "
            "(target_bbox_geometric_mean / source_bbox_geometric_mean))"
        ),
        "contour_fit_constraint": {
            "source_outline_padding_px": contour_source_padding,
            "output_margin_px": contour_output_margin,
            "common_safe_target_ratio": common_safe_target_ratio,
            "rule": (
                "common_safe_target_ratio = min(contour_fit_scale / "
                "requested_feature_scale) across all frames; applied_scale = "
                "requested_feature_scale * common_safe_target_ratio"
            ),
            "temporal_policy": (
                "one shared feasible target ratio preserves the normalized Lulu "
                "size across the complete fifteen-frame loop"
            ),
        },
        "transform_scope": ["Lulu", "paper", "ink dish", "brush"],
        "resampling": "nearest-neighbor",
        "source_master_modified": False,
        "runtime_master_frame_numbers": list(WORKING_RUNTIME_FRAME_NUMBERS),
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
    return normalized_frames, report


def load_adapter_rows() -> tuple[
    list[list[Image.Image]],
    list[list[Path]],
    dict[str, dict[str, object]],
    list[Image.Image],
    list[int],
    dict[str, object],
]:
    states, _ = load_manifest()
    loaded: dict[str, tuple[list[Image.Image], list[Path], list[int]]] = {}
    for row in ADAPTER_ROWS:
        if row.master_state in loaded:
            continue
        entry = states.get(row.master_state)
        if not isinstance(entry, dict):
            raise ValueError(f"Missing master action: {row.master_state}")
        frames, paths, durations = load_action(row.master_state, entry)
        loaded[row.master_state] = (frames, paths, durations)

    idle_frames = loaded["idle"][0]
    failed_frames = loaded["failed"][0]
    if len(idle_frames) != len(failed_frames) or any(
        idle.tobytes() != failed.tobytes()
        for idle, failed in zip(idle_frames, failed_frames, strict=True)
    ):
        raise ValueError("Idle must exactly alias the complete failed sleeping loop")

    working_frames, _, working_durations = loaded["working"]
    normalized_working_frames, normalization_report = normalize_working_sequence(
        working_frames,
        {state: loaded[state][0] for state in WORKING_REFERENCE_STATES},
    )

    selected_frames: list[list[Image.Image]] = []
    selected_paths: list[list[Path]] = []
    row_report: dict[str, dict[str, object]] = {}
    for row_index, row in enumerate(ADAPTER_ROWS):
        frames, paths, _ = loaded[row.master_state]
        indices = [number - 1 for number in row.master_frame_numbers]
        if any(index < 0 or index >= len(frames) for index in indices):
            raise ValueError(f"{row.runtime_state}: adapter selection escaped master frames")
        selected = [frames[index].copy() for index in indices]
        transform: dict[str, object] | None = None
        if row.runtime_state == "running" and row.master_state == "working":
            selected = [normalized_working_frames[index].copy() for index in indices]
            transform = normalization_report
        selected_frames.append(selected)
        selected_paths.append([paths[index] for index in indices])
        row_report[row.runtime_state] = {
            "row_index": row_index,
            "master_state": row.master_state,
            "master_frame_numbers": list(row.master_frame_numbers),
            "source_frames": [str(paths[index].relative_to(ROOT)) for index in indices],
            "source_frame_sha256": [sha256(paths[index]) for index in indices],
            "note": row.note,
            "adapter_transform": transform,
        }
    return (
        selected_frames,
        selected_paths,
        row_report,
        normalized_working_frames,
        working_durations,
        normalization_report,
    )


def build_atlas(rows: list[list[Image.Image]]) -> Image.Image:
    atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
    for row_index, frames in enumerate(rows):
        for column_index, frame in enumerate(frames):
            atlas.alpha_composite(
                frame,
                (column_index * CELL_SIZE[0], row_index * CELL_SIZE[1]),
            )
    return zero_transparent_rgb(atlas)


def write_contact_sheet(rows: list[list[Image.Image]]) -> None:
    thumb_size = (CELL_SIZE[0] // 2, CELL_SIZE[1] // 2)
    label_height = 20
    canvas = Image.new(
        "RGB",
        (ATLAS_COLUMNS * thumb_size[0], ATLAS_ROWS * (thumb_size[1] + label_height)),
        (24, 24, 24),
    )
    draw = ImageDraw.Draw(canvas)
    for row_index, (row, frames) in enumerate(zip(ADAPTER_ROWS, rows, strict=True)):
        top = row_index * (thumb_size[1] + label_height)
        draw.text(
            (5, top + 4),
            f"row {row_index}: {row.runtime_state} <- {row.master_state}",
            fill=(255, 255, 255),
        )
        for column_index in range(ATLAS_COLUMNS):
            x = column_index * thumb_size[0]
            y = top + label_height
            cell = checker(thumb_size)
            if column_index < len(frames):
                thumb = frames[column_index].resize(thumb_size, Image.Resampling.NEAREST)
                cell.alpha_composite(thumb)
                border = (27, 198, 118)
            else:
                border = (90, 90, 90)
            canvas.paste(cell.convert("RGB"), (x, y))
            draw.rectangle(
                (x, y, x + thumb_size[0] - 1, y + thumb_size[1] - 1),
                outline=border,
            )
    CONTACT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(CONTACT_SHEET, optimize=True)


def write_working_full_contact_sheet(frames: list[Image.Image]) -> None:
    columns = 5
    rows = math.ceil(len(frames) / columns)
    label_height = 20
    canvas = Image.new(
        "RGB",
        (columns * CELL_SIZE[0], rows * (CELL_SIZE[1] + label_height)),
        (24, 24, 24),
    )
    draw = ImageDraw.Draw(canvas)
    for index, frame in enumerate(frames):
        column = index % columns
        row = index // columns
        x = column * CELL_SIZE[0]
        y = row * (CELL_SIZE[1] + label_height)
        draw.text((x + 5, y + 4), f"working {index + 1:02d}", fill=(255, 255, 255))
        cell = checker(CELL_SIZE)
        cell.alpha_composite(frame)
        canvas.paste(cell.convert("RGB"), (x, y + label_height))
        draw.rectangle(
            (x, y + label_height, x + CELL_SIZE[0] - 1, y + label_height + CELL_SIZE[1] - 1),
            outline=(27, 198, 118),
        )
    WORKING_FULL_CONTACT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(WORKING_FULL_CONTACT_SHEET, optimize=True)


def write_adapter_previews(
    rows: list[list[Image.Image]],
    normalized_working_frames: list[Image.Image],
    working_durations: list[int],
    normalization_report: dict[str, object],
) -> None:
    working_row = next(
        index for index, row in enumerate(ADAPTER_ROWS) if row.runtime_state == "running"
    )
    write_gif(WORKING_PREVIEW, rows[working_row], [120, 120, 120, 120, 120, 220])
    write_gif(WORKING_FULL_PREVIEW, normalized_working_frames, working_durations)
    write_working_full_contact_sheet(normalized_working_frames)
    WORKING_SCALE_REPORT.write_text(
        json.dumps(normalization_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def install_package() -> dict[str, object]:
    target = codex_home() / "pets" / PET_ID
    target.mkdir(parents=True, exist_ok=True)
    installed_files: dict[str, str] = {}
    for filename in ("pet.json", "spritesheet.webp"):
        source = FINAL / filename
        destination = target / filename
        shutil.copy2(source, destination)
        if source.read_bytes() != destination.read_bytes():
            raise ValueError(f"Installed file differs from package: {filename}")
        installed_files[filename] = sha256(destination)
    return {
        "status": "installed",
        "directory": str(target),
        "avatar_id": f"custom:{PET_ID}",
        "files": installed_files,
    }


def validate_atlas(
    atlas: Image.Image,
    rows: list[list[Image.Image]],
) -> list[dict[str, object]]:
    cells: list[dict[str, object]] = []
    for row_index, frames in enumerate(rows):
        for column_index in range(ATLAS_COLUMNS):
            bounds = (
                column_index * CELL_SIZE[0],
                row_index * CELL_SIZE[1],
                (column_index + 1) * CELL_SIZE[0],
                (row_index + 1) * CELL_SIZE[1],
            )
            cell = atlas.crop(bounds)
            used = column_index < len(frames)
            if used and cell.tobytes() != frames[column_index].tobytes():
                raise ValueError(
                    f"Atlas cell differs from source: row={row_index}, column={column_index}"
                )
            if not used and cell.getchannel("A").getbbox() is not None:
                raise ValueError(
                    f"Unused atlas cell is not transparent: row={row_index}, column={column_index}"
                )
            cells.append(
                {
                    "row": row_index,
                    "column": column_index,
                    "runtime_state": ADAPTER_ROWS[row_index].runtime_state,
                    "used": used,
                    "bbox": cell.getchannel("A").getbbox(),
                }
            )
    return cells


def build(*, install: bool) -> dict[str, object]:
    master_validation = build_action_gifs()
    if not master_validation["ok"]:
        raise ValueError("Animation-master validation failed")
    observed_counts = [len(row.master_frame_numbers) for row in ADAPTER_ROWS]
    if observed_counts != CODEX_REQUIRED_FRAMES_BY_ROW:
        raise ValueError(
            f"Codex V1 row contract changed: {observed_counts} != {CODEX_REQUIRED_FRAMES_BY_ROW}"
        )

    (
        rows,
        _,
        row_report,
        normalized_working_frames,
        working_durations,
        normalization_report,
    ) = load_adapter_rows()
    atlas = build_atlas(rows)
    if atlas.size != ATLAS_SIZE:
        raise ValueError(f"Unexpected atlas size: {atlas.size}")

    FINAL.mkdir(parents=True, exist_ok=True)
    atlas.save(FINAL / "spritesheet.png", optimize=True)
    atlas.save(
        FINAL / "spritesheet.webp",
        format="WEBP",
        lossless=True,
        method=6,
        exact=True,
    )
    pet_json = {
        "id": PET_ID,
        "displayName": "水豚噜噜",
        "description": "会画水墨小虾、休息时香香睡觉的橙子水豚桌面伙伴。",
        "spriteVersionNumber": SPRITE_VERSION_NUMBER,
        "spritesheetPath": "spritesheet.webp",
    }
    (FINAL / "pet.json").write_text(
        json.dumps(pet_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_contact_sheet(rows)
    write_adapter_previews(
        rows,
        normalized_working_frames,
        working_durations,
        normalization_report,
    )
    cells = validate_atlas(atlas, rows)

    webp = Image.open(FINAL / "spritesheet.webp")
    if getattr(webp, "n_frames", 1) != 1:
        raise ValueError("Codex spritesheet WebP must be a single-frame atlas")
    if webp.size != ATLAS_SIZE or webp.convert("RGBA").tobytes() != atlas.tobytes():
        raise ValueError("Lossless WebP must decode pixel-identically to the PNG atlas")

    installation = install_package() if install else {"status": "not-requested"}
    validation = {
        "ok": True,
        "scope": "codex-custom-pet-adapter",
        "errors": [],
        "warnings": [],
        "application_contract": {
            "source": "locally installed Codex app bundle",
            "bundle_id": "com.openai.codex",
            "app_version": CODEX_APP_VERSION,
            "sprite_version_number": SPRITE_VERSION_NUMBER,
            "width": ATLAS_SIZE[0],
            "height": ATLAS_SIZE[1],
            "cell_size": list(CELL_SIZE),
            "columns": ATLAS_COLUMNS,
            "rows": ATLAS_ROWS,
            "required_frames_by_row": CODEX_REQUIRED_FRAMES_BY_ROW,
        },
        "runtime_state_mapping": row_report,
        "master_aliases": {"idle": "failed"},
        "adapter_aliases": {
            "idle": "failed sleeping artwork",
            "jumping": "waving",
            "running": "working",
        },
        "cells": cells,
        "installation": installation,
        "artifacts": {
            "pet.json": sha256(FINAL / "pet.json"),
            "spritesheet.png": sha256(FINAL / "spritesheet.png"),
            "spritesheet.webp": sha256(FINAL / "spritesheet.webp"),
            "contact_sheet": sha256(CONTACT_SHEET),
            "working_preview": sha256(WORKING_PREVIEW),
            "working_full_preview": sha256(WORKING_FULL_PREVIEW),
            "working_full_contact_sheet": sha256(WORKING_FULL_CONTACT_SHEET),
            "working_scale_report": sha256(WORKING_SCALE_REPORT),
            "working_visual_qa": sha256(WORKING_VISUAL_QA),
            "source_manifest": sha256(MANIFEST),
        },
        "toolchain": {
            "pillow": Image.__version__,
            "webp": bool(features.check("webp")),
            "webp_version": features.version_module("webp"),
        },
    }
    validation_path = FINAL / "validation.json"
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if install:
        receipt = {
            "ok": True,
            **installation,
            "validation_sha256": sha256(validation_path),
        }
        (FINAL / "install-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"Built Codex pet atlas: {atlas.width}x{atlas.height}")
    print("Validation: OK (0 errors)")
    if install:
        print(f"Installed Codex pet: {installation['directory']}")
    return validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the CapyLulu Codex pet adapter")
    parser.add_argument(
        "--install",
        action="store_true",
        help="copy pet.json and spritesheet.webp into the local Codex pets directory",
    )
    args = parser.parse_args()
    build(install=args.install)


if __name__ == "__main__":
    main()
