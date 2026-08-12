from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from face_geometry import analyze


PIPELINE = Path(__file__).resolve().parent
DRAG = PIPELINE.parent
PET = PIPELINE.parents[3]
ROOT = PET.parents[1]
OFFICIAL = PET / "official-frames-v1"
MANIFEST = PET / "official-frames-v1-manifest.json"
OUTPUT_ROOT = Path(os.environ.get("LULU_DIRECTIONAL_BUILD_ROOT", PIPELINE)).resolve()

CELL_SIZE = (192, 208)
CELL_CENTER = (96, 104)
TARGET_ALPHA_AREA = 17_600
AREA_TOLERANCE = 0.05
FRAME_DURATIONS_MS = [120, 120, 120, 120, 120, 120, 120, 220]
GOLD_ACTIONS = ("idle", "waving", "failed", "waiting", "running", "review")

ALPHA = PIPELINE / "alpha"
SOURCE_SHEET = PIPELINE / "sources" / "six-frame-contact-sheet-magenta.png"
ALPHA_SHEET = ALPHA / "six-frame-contact-sheet-alpha.png"
CHROMA_RECEIPT = ALPHA / "chroma-removal-receipt.json"
EXTRACTED = OUTPUT_ROOT / "extracted-alpha"
BASE_NORMALIZED = OUTPUT_ROOT / "base-normalized"
NORMALIZED = OUTPUT_ROOT / "normalized"
RIGHT = OUTPUT_ROOT / "right"
LEFT = OUTPUT_ROOT / "left"
VALIDATION = OUTPUT_ROOT / "validation.json"
POSE_TARGET_ANGLES_DEG = [0, 8, 16, 22, 26, 13]
# Recovery deliberately reuses the newly redrawn early-lag silhouette at a
# steeper angle. This balances the peak-to-recovery and recovery-to-neutral
# transitions without introducing a seventh character drawing.
FRAME_SOURCE_CELLS = [1, 2, 3, 4, 5, 2]
PALETTE_GROUP_QUOTAS = (16, 8, 16, 88)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zero_transparent_rgb(image: Image.Image) -> Image.Image:
    output = image.convert("RGBA")
    output.putdata(
        [
            (red, green, blue, alpha) if alpha else (0, 0, 0, 0)
            for red, green, blue, alpha in output.get_flattened_data()
        ]
    )
    return output


def gold_paths() -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    states = manifest["states"]
    paths: list[Path] = []
    for action in GOLD_ACTIONS:
        entry = states.get(action)
        if not isinstance(entry, dict) or entry.get("quality") != "gold":
            raise ValueError(f"{action} is not a manifest-locked gold action")
        frame_values = entry.get("frames")
        expected_hashes = entry.get("frame_sha256")
        if not isinstance(frame_values, list) or not isinstance(expected_hashes, dict):
            raise ValueError(f"{action} lacks frames or hash locks")
        action_paths = [(PET / value).resolve() for value in frame_values]
        observed_names = {path.name for path in action_paths}
        if set(expected_hashes) != observed_names:
            raise ValueError(f"{action} gold hash keys do not match its frames")
        for path in action_paths:
            if not path.is_relative_to(PET.resolve()) or not path.is_file():
                raise ValueError(f"invalid gold frame: {path}")
            if sha256(path) != expected_hashes[path.name]:
                raise ValueError(f"gold frame changed: {path}")
        seen: set[Path] = set()
        for path in action_paths:
            if path not in seen:
                paths.append(path)
                seen.add(path)
    return paths


def verify_chroma_receipt() -> dict[str, object]:
    receipt = json.loads(CHROMA_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("source_sha256") != sha256(SOURCE_SHEET):
        raise ValueError("chroma receipt does not match the selected source sheet")
    if receipt.get("alpha_sha256") != sha256(ALPHA_SHEET):
        raise ValueError("chroma receipt does not match the selected alpha sheet")
    if receipt.get("tool") != "imagegen/remove_chroma_key.py":
        raise ValueError("unsupported chroma-removal receipt")
    return receipt


def gold_palette() -> Image.Image:
    groups: list[list[tuple[int, int, int]]] = [[], [], [], []]
    for path in gold_paths():
        gold = zero_transparent_rgb(Image.open(path))
        for red, green, blue, alpha in gold.get_flattened_data():
            if not alpha:
                continue
            color = (red, green, blue)
            if green >= red * 1.15 and green >= blue * 1.4:
                groups[0].append(color)
            elif min(color) >= 180 and max(color) - min(color) <= 60:
                groups[1].append(color)
            elif max(color) < 120:
                groups[2].append(color)
            else:
                groups[3].append(color)

    colors: list[tuple[int, int, int]] = []
    for group, quota in zip(groups, PALETTE_GROUP_QUOTAS, strict=True):
        strip = Image.new("RGB", (len(group), 1))
        strip.putdata(group)
        quantized = strip.quantize(colors=quota, method=Image.Quantize.MEDIANCUT)
        raw_palette = quantized.getpalette()
        for index in sorted(set(quantized.get_flattened_data())):
            colors.append(tuple(raw_palette[index * 3 : index * 3 + 3]))
    if len(colors) != 128:
        raise ValueError(f"expected 128 stratified gold colors, found {len(colors)}")
    palette = Image.new("P", (1, 1))
    flat = [channel for color in colors for channel in color]
    palette.putpalette(flat + [0] * (768 - len(flat)))
    return palette


def extract_contact_sheet() -> list[Path]:
    sheet = zero_transparent_rgb(Image.open(ALPHA_SHEET))
    width, height = sheet.size
    x_edges = (0, width // 3, 2 * width // 3, width)
    y_edges = (0, height // 2, height)
    paths: list[Path] = []
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    for row in range(2):
        for column in range(3):
            frame_number = row * 3 + column + 1
            crop = sheet.crop(
                (
                    x_edges[column],
                    y_edges[row],
                    x_edges[column + 1],
                    y_edges[row + 1],
                )
            )
            destination = EXTRACTED / f"f{frame_number:02d}-alpha.png"
            zero_transparent_rgb(crop).save(destination, optimize=True)
            paths.append(destination)
    return paths


def normalize_generated(source: Path, destination: Path, palette: Image.Image) -> int:
    image = zero_transparent_rgb(Image.open(source))
    alpha = image.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError(f"empty generated frame: {source}")

    image.putalpha(alpha)
    sprite = zero_transparent_rgb(image.crop(bbox))
    source_area = sum(1 for value in sprite.getchannel("A").get_flattened_data() if value)
    scale = math.sqrt(TARGET_ALPHA_AREA / source_area)
    width = round(sprite.width * scale)
    height = round(sprite.height * scale)
    if width > CELL_SIZE[0] or height > CELL_SIZE[1]:
        raise ValueError(f"normalized frame would not fit: {source.name} -> {width}x{height}")

    sprite = sprite.resize((width, height), Image.Resampling.NEAREST)
    sprite_alpha = sprite.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    quantized_rgb = sprite.convert("RGB").quantize(
        palette=palette,
        dither=Image.Dither.NONE,
    ).convert("RGB")
    quantized = quantized_rgb.convert("RGBA")
    quantized.putalpha(sprite_alpha)

    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    left = CELL_CENTER[0] - width // 2
    top = CELL_CENTER[1] - height // 2
    frame.alpha_composite(quantized, (left, top))
    frame = zero_transparent_rgb(frame)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.save(destination, optimize=True)
    return sum(1 for value in frame.getchannel("A").get_flattened_data() if value)


def shift_frame(source: Path, destination: Path, dy: int) -> None:
    image = zero_transparent_rgb(Image.open(source))
    shifted = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    shifted.alpha_composite(image, (0, dy))
    zero_transparent_rgb(shifted).save(destination, optimize=True)


def rotate_complete_sprite(source: Path, destination: Path, degrees_clockwise: float) -> int:
    image = zero_transparent_rgb(Image.open(source))
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"empty normalized frame: {source}")
    sprite = image.crop(bbox).rotate(
        -degrees_clockwise,
        resample=Image.Resampling.NEAREST,
        expand=True,
        fillcolor=(0, 0, 0, 0),
    )
    rotated_bbox = sprite.getchannel("A").getbbox()
    if rotated_bbox is None:
        raise ValueError(f"empty rotated frame: {source}")
    sprite = zero_transparent_rgb(sprite.crop(rotated_bbox))
    area = sum(1 for value in sprite.getchannel("A").get_flattened_data() if value)
    scale = math.sqrt(TARGET_ALPHA_AREA / area)
    width = round(sprite.width * scale)
    height = round(sprite.height * scale)
    if width > CELL_SIZE[0] or height > CELL_SIZE[1]:
        raise ValueError(f"pose-aligned frame would not fit: {source.name} -> {width}x{height}")
    sprite = sprite.resize((width, height), Image.Resampling.NEAREST)
    alpha = sprite.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    sprite.putalpha(alpha)
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    frame.alpha_composite(sprite, (CELL_CENTER[0] - width // 2, CELL_CENTER[1] - height // 2))
    frame = zero_transparent_rgb(frame)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.save(destination, optimize=True)
    return sum(1 for value in frame.getchannel("A").get_flattened_data() if value)


def save_gif(path: Path, frames: list[Image.Image]) -> None:
    frames[0].save(
        path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DURATIONS_MS,
        loop=0,
        disposal=2,
        optimize=False,
    )


def checker() -> Image.Image:
    image = Image.new("RGBA", CELL_SIZE, (238, 238, 238, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, CELL_SIZE[1], 8):
        for x in range(0, CELL_SIZE[0], 8):
            if (x // 8 + y // 8) % 2:
                draw.rectangle((x, y, x + 7, y + 7), fill=(211, 211, 211, 255))
    return image


def translated_up_one(source: Image.Image, candidate: Image.Image) -> bool:
    expected = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    expected.alpha_composite(source, (0, -1))
    return zero_transparent_rgb(expected).tobytes() == candidate.tobytes()


def touches_canvas_edge(image: Image.Image) -> bool:
    alpha = image.getchannel("A")
    width, height = image.size
    return any(
        alpha.getpixel(point)
        for point in (
            *((x, 0) for x in range(width)),
            *((x, height - 1) for x in range(width)),
            *((0, y) for y in range(height)),
            *((width - 1, y) for y in range(height)),
        )
    )


def remove_stale_pngs(directory: Path, expected_names: set[str]) -> None:
    for path in directory.glob("*.png"):
        if path.name not in expected_names:
            path.unlink()


def alpha_iou(left: Image.Image, right: Image.Image) -> float:
    left_alpha = left.getchannel("A").get_flattened_data()
    right_alpha = right.getchannel("A").get_flattened_data()
    intersection = sum(bool(a) and bool(b) for a, b in zip(left_alpha, right_alpha, strict=True))
    union = sum(bool(a) or bool(b) for a, b in zip(left_alpha, right_alpha, strict=True))
    return intersection / union


def face_geometry_errors(frame_number: int, result: dict[str, object]) -> list[str]:
    errors: list[str] = []
    muzzle = result["muzzle"]
    eyes = result["eyes"]
    arch = result["top_arch"]
    if not 2_500 <= muzzle["area_px"] <= 5_000:
        errors.append(f"F{frame_number} muzzle component area is invalid")
    if muzzle["dominance_ratio"] < 4:
        errors.append(f"F{frame_number} muzzle is not the dominant orange component")
    if abs(muzzle["head_local_angle_deg"] - POSE_TARGET_ANGLES_DEG[frame_number - 1]) > 1.5:
        errors.append(f"F{frame_number} pose angle missed its target")
    if not 42 <= result["eye_separation_u_px"] <= 60:
        errors.append(f"F{frame_number} eye separation drifted")
    if not arch["single_arch"]:
        errors.append(f"F{frame_number} muzzle top is not a single arch")
    for eye_index, eye in enumerate(eyes, start=1):
        if eye["arc_sag_px"] < 1:
            errors.append(f"F{frame_number} eye {eye_index} is not a closed arc")
        if eye["skin_clearance_px"] < 7 or eye["signed_local_clearance_px"] < 7:
            errors.append(f"F{frame_number} eye {eye_index} has less than 7px muzzle clearance")
        gap = eye["gap_path_pixels"]
        if gap["skin"] < 7 or gap["transparent_background"] or gap["other"]:
            errors.append(f"F{frame_number} eye {eye_index} lacks a clean skin-only muzzle gap")
        if eye["touch_or_spill"]:
            errors.append(f"F{frame_number} muzzle touches or spills into eye {eye_index}")
    return errors


def build() -> dict[str, object]:
    if VALIDATION.exists():
        VALIDATION.unlink()
    for directory in (EXTRACTED, BASE_NORMALIZED, NORMALIZED, RIGHT, LEFT):
        directory.mkdir(parents=True, exist_ok=True)
    remove_stale_pngs(EXTRACTED, {f"f{number:02d}-alpha.png" for number in range(1, 7)})
    remove_stale_pngs(BASE_NORMALIZED, {f"cell{number:02d}.png" for number in range(1, 7)})
    remove_stale_pngs(NORMALIZED, {f"f{number:02d}.png" for number in range(1, 9)})
    remove_stale_pngs(RIGHT, {f"running-right-{number:02d}.png" for number in range(1, 9)})
    remove_stale_pngs(LEFT, {f"running-left-{number:02d}.png" for number in range(1, 9)})

    chroma_receipt = verify_chroma_receipt()
    palette = gold_palette()
    areas: dict[str, int] = {}
    selected: list[Path] = []
    face_geometry: dict[str, object] = {}
    base_frames: dict[int, Path] = {}
    for cell_number, source in enumerate(extract_contact_sheet(), start=1):
        base = BASE_NORMALIZED / f"cell{cell_number:02d}.png"
        normalize_generated(source, base, palette)
        base_frames[cell_number] = base
    for frame_number, source_cell in enumerate(FRAME_SOURCE_CELLS, start=1):
        base = base_frames[source_cell]
        base_geometry = analyze(base)
        target = POSE_TARGET_ANGLES_DEG[frame_number - 1]
        observed = base_geometry["muzzle"]["head_local_angle_deg"]
        destination = NORMALIZED / f"f{frame_number:02d}.png"
        areas[f"f{frame_number:02d}"] = rotate_complete_sprite(
            base,
            destination,
            degrees_clockwise=target - observed,
        )
        selected.append(destination)
        face_geometry[f"f{frame_number:02d}"] = analyze(destination)

    f07 = NORMALIZED / "f07.png"
    f08 = NORMALIZED / "f08.png"
    shift_frame(selected[0], f07, dy=-1)
    zero_transparent_rgb(Image.open(selected[0])).save(f08, optimize=True)
    selected.extend((f07, f08))

    right_frames: list[Image.Image] = []
    left_frames: list[Image.Image] = []
    for index, source in enumerate(selected, start=1):
        right = zero_transparent_rgb(Image.open(source))
        if right.size != CELL_SIZE:
            raise ValueError(f"selected frame must be {CELL_SIZE}: {source}")
        if set(right.getchannel("A").get_flattened_data()) - {0, 255}:
            raise ValueError(f"selected frame must use binary alpha: {source}")
        left = zero_transparent_rgb(right.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        right_path = RIGHT / f"running-right-{index:02d}.png"
        left_path = LEFT / f"running-left-{index:02d}.png"
        right.save(right_path, optimize=True)
        left.save(left_path, optimize=True)
        right_frames.append(right)
        left_frames.append(left)

    save_gif(OUTPUT_ROOT / "right-preview.gif", right_frames)
    save_gif(OUTPUT_ROOT / "left-preview.gif", left_frames)

    contact = Image.new("RGBA", (CELL_SIZE[0] * 4, CELL_SIZE[1] * 2 + 40), (18, 18, 18, 255))
    draw = ImageDraw.Draw(contact)
    for index, frame in enumerate(right_frames):
        column = index % 4
        row = index // 4
        x = column * CELL_SIZE[0]
        y = row * (CELL_SIZE[1] + 20)
        cell = checker()
        cell.alpha_composite(frame)
        contact.alpha_composite(cell, (x, y + 20))
        draw.text((x + 4, y + 4), f"F{index + 1}", fill=(255, 255, 255, 255))
    contact.convert("RGB").save(OUTPUT_ROOT / "right-contact-sheet.png", optimize=True)

    errors: list[str] = []
    for name, area in areas.items():
        deviation = abs(area - TARGET_ALPHA_AREA) / TARGET_ALPHA_AREA
        if deviation > AREA_TOLERANCE:
            errors.append(f"{name} alpha area drifted by {deviation:.3%}")
    if right_frames[7].tobytes() != right_frames[0].tobytes():
        errors.append("F8 does not return exactly to F1")
    if not translated_up_one(right_frames[0], right_frames[6]):
        errors.append("F7 is not an exact one-pixel upward translation of F1")
    for right, left in zip(right_frames, left_frames, strict=True):
        if left.tobytes() != right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes():
            errors.append("left frame is not an exact mirror of right frame")
            break
    for index, frame in enumerate(right_frames, start=1):
        if touches_canvas_edge(frame):
            errors.append(f"F{index} touches the canvas edge")
    for frame_number in range(1, 7):
        errors.extend(face_geometry_errors(frame_number, face_geometry[f"f{frame_number:02d}"]))

    transition_iou = [
        alpha_iou(left, right)
        for left, right in zip(right_frames, right_frames[1:], strict=False)
    ]
    iou_ranges = (
        (0.78, 0.89),
        (0.78, 0.89),
        (0.80, 0.91),
        (0.86, 0.94),
        (0.70, 0.82),
        (0.70, 0.82),
        (0.97, 0.99),
    )
    for transition, value, allowed in zip(range(1, 8), transition_iou, iou_ranges, strict=True):
        if not allowed[0] <= value <= allowed[1]:
            errors.append(
                f"F{transition}->F{transition + 1} alpha IoU {value:.3f} "
                f"outside {allowed[0]:.2f}..{allowed[1]:.2f}"
            )
    if abs(transition_iou[4] - transition_iou[5]) > 0.05:
        errors.append("peak-to-recovery and recovery-to-neutral motion are unbalanced")

    validation = {
        "ok": not errors,
        "status": "active-master-candidate-source",
        "build_sha256": sha256(Path(__file__).resolve()),
        "face_geometry_sha256": sha256(PIPELINE / "face_geometry.py"),
        "manifest_sha256": sha256(MANIFEST),
        "generation_policy": "F1-F6 are one full six-frame rerun; no old drag frame or local pixel patch is used",
        "source_sheet": str(SOURCE_SHEET.relative_to(PET)),
        "source_sheet_sha256": sha256(SOURCE_SHEET),
        "alpha_sheet": str(ALPHA_SHEET.relative_to(PET)),
        "alpha_sheet_sha256": sha256(ALPHA_SHEET),
        "chroma_removal_receipt": chroma_receipt,
        "identity_authority_actions": list(GOLD_ACTIONS),
        "identity_authority_sha256": {
            str(path.relative_to(PET)): sha256(path) for path in gold_paths()
        },
        "frame_durations_ms": FRAME_DURATIONS_MS,
        "target_alpha_area": TARGET_ALPHA_AREA,
        "alpha_area_tolerance_ratio": AREA_TOLERANCE,
        "generated_frame_alpha_areas": areas,
        "pose_target_angles_deg": POSE_TARGET_ANGLES_DEG,
        "source_sheet_frame_map": FRAME_SOURCE_CELLS,
        "face_geometry": face_geometry,
        "transition_alpha_iou": transition_iou,
        "eye_policy": "both eyes synchronized closed in all eight frames",
        "face_geometry_contract": {
            "muzzle_eye_clearance_px": ">= 7 in head-local coordinates, with at least 7 intervening yellow skin pixels",
            "muzzle_topology": "single central arch; no M-shaped peaks or orange incursion into either eye",
            "mouth": "small closed dark smile; no tongue or teeth",
            "review": "machine geometry only; manual mouth/shorts review is separately hash-bound in visual-review.json",
        },
        "shorts_geometry_contract": {
            "front": "flat with exactly two leg openings and an upward background gap",
            "forbidden": ["center seam", "oval pouch", "third lobe", "crotch bulge"],
            "review": "manual review is separately hash-bound in visual-review.json",
        },
        "recovery_bob_frame": 7,
        "exact_return_frames": [8],
        "palette_policy": "one hue-stratified 128-color palette derived from all six gold actions, with explicit green/neutral/dark/warm quotas",
        "left_policy": "exact pixel mirror of right",
        "output_sha256": {
            "right_frames": {
                path.name: sha256(path) for path in sorted(RIGHT.glob("*.png"))
            },
            "left_frames": {
                path.name: sha256(path) for path in sorted(LEFT.glob("*.png"))
            },
            "artifacts": {
                name: sha256(OUTPUT_ROOT / name)
                for name in (
                    "right-preview.gif",
                    "left-preview.gif",
                    "right-contact-sheet.png",
                )
            },
        },
        "errors": errors,
    }
    VALIDATION.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("\n".join(errors))
    return validation


def staged_build() -> None:
    final_validation = PIPELINE / "validation.json"
    if final_validation.exists():
        final_validation.unlink()
    output_names = (
        "extracted-alpha",
        "base-normalized",
        "normalized",
        "right",
        "left",
        "right-preview.gif",
        "left-preview.gif",
        "right-contact-sheet.png",
        "validation.json",
    )
    with tempfile.TemporaryDirectory(
        prefix="six-gold-rerun-build-", dir=PIPELINE
    ) as temporary:
        temporary_root = Path(temporary)
        staging = temporary_root / "staging"
        backup = temporary_root / "backup"
        failed = temporary_root / "failed"
        staging.mkdir()
        backup.mkdir()
        failed.mkdir()
        environment = os.environ.copy()
        environment["LULU_DIRECTIONAL_BUILD_ROOT"] = str(staging)
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--staged-worker"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        for name in output_names:
            if not (staging / name).exists():
                raise ValueError(f"staged build omitted {name}")

        committed: list[tuple[Path, Path, bool]] = []
        try:
            for name in output_names:
                target = PIPELINE / name
                saved = backup / name
                existed = target.exists()
                if existed:
                    target.rename(saved)
                try:
                    (staging / name).rename(target)
                except BaseException:
                    if existed:
                        saved.rename(target)
                    raise
                committed.append((target, saved, existed))
        except BaseException:
            for target, saved, existed in reversed(committed):
                if target.exists():
                    target.rename(failed / target.name)
                if existed:
                    saved.rename(target)
            raise
    print("Committed complete staged lineage build: OK")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--staged-worker":
        result = build()
        print(f"Six-gold directional rerun: {'OK' if result['ok'] else 'FAILED'}")
    elif len(sys.argv) == 1:
        staged_build()
    else:
        raise SystemExit("usage: build.py [--staged-worker]")
