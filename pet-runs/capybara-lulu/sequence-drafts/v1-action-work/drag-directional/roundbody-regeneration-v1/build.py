from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw


PIPELINE = Path(__file__).resolve().parent
DRAG = PIPELINE.parent
PET = PIPELINE.parents[3]
SINGLE = DRAG / "single-frame-pipeline"

CELL_SIZE = (192, 208)
CELL_CENTER = (96, 104)
TARGET_ALPHA_AREA = 17_200
AREA_TOLERANCE = 0.05
FRAME_DURATIONS_MS = [120, 120, 120, 120, 120, 120, 120, 220]

GOLD_OPEN = SINGLE / "gold" / "gold-neutral-open-192x208.png"
GOLD_CLOSED = (
    PET
    / "sequence-drafts"
    / "v1-action-work"
    / "waving-success-windup"
    / "gold-normal-stand.png"
)
ALPHA = PIPELINE / "alpha"
NORMALIZED = PIPELINE / "normalized"
CLOSED = PIPELINE / "closed"
RIGHT = PIPELINE / "right"
LEFT = PIPELINE / "left"
VALIDATION = PIPELINE / "validation.json"


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


def gold_palette() -> Image.Image:
    gold = zero_transparent_rgb(Image.open(GOLD_OPEN))
    opaque_rgb = [
        (red, green, blue)
        for red, green, blue, alpha in gold.get_flattened_data()
        if alpha
    ]
    strip = Image.new("RGB", (len(opaque_rgb), 1))
    strip.putdata(opaque_rgb)
    return strip.quantize(colors=128, method=Image.Quantize.MEDIANCUT)


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
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame = zero_transparent_rgb(frame)
    frame.save(destination, optimize=True)
    return sum(1 for value in frame.getchannel("A").get_flattened_data() if value)


def white_components(image: Image.Image) -> list[tuple[int, tuple[int, int, int, int]]]:
    width, height = image.size
    remaining = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if (
            (pixel := image.getpixel((x, y)))[3]
            and min(pixel[:3]) >= 210
            and max(pixel[:3]) - min(pixel[:3]) <= 45
        )
    }
    components: list[tuple[int, tuple[int, int, int, int]]] = []
    while remaining:
        todo = [remaining.pop()]
        points: list[tuple[int, int]] = []
        while todo:
            point = todo.pop()
            points.append(point)
            x, y = point
            for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    todo.append(neighbor)
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        components.append((len(points), (min(xs), min(ys), max(xs) + 1, max(ys) + 1)))
    return components


def open_eye_candidates(image: Image.Image) -> list[tuple[int, tuple[int, int, int, int]]]:
    return [
        (area, bbox)
        for area, bbox in white_components(image)
        if area >= 60
        and bbox[1] < 100
        and 12 <= bbox[2] - bbox[0] <= 26
        and 14 <= bbox[3] - bbox[1] <= 30
    ]


def detect_open_eyes(image: Image.Image) -> list[tuple[int, int, int, int]]:
    candidates = open_eye_candidates(image)
    eyes = [bbox for _, bbox in sorted(candidates, reverse=True)[:2]]
    if len(eyes) != 2:
        raise ValueError(f"expected two open eyes, found {eyes}")
    return sorted(eyes)


def warm_mean(image: Image.Image) -> tuple[float, float, float]:
    colors = [
        (red, green, blue)
        for red, green, blue, alpha in image.get_flattened_data()
        if alpha and red > 140 and green > 70 and blue < 100
    ]
    if not colors:
        raise ValueError("frame has no warm Lulu palette pixels")
    return tuple(sum(color[channel] for color in colors) / len(colors) for channel in range(3))


def eye_template() -> Image.Image:
    closed = zero_transparent_rgb(Image.open(GOLD_CLOSED))
    crop = closed.crop((55, 72, 82, 88))
    mask = Image.new("L", crop.size, 0)
    mask.putdata(
        [
            255 if alpha and red < 110 and green < 110 and blue < 110 else 0
            for red, green, blue, alpha in crop.get_flattened_data()
        ]
    )
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("closed-eye gold template is empty")
    return mask.crop(bbox)


def inpaint_mask(image: Image.Image, mask: set[tuple[int, int]]) -> None:
    pixels = image.load()
    unfilled = set(mask)
    while unfilled:
        updates: list[tuple[tuple[int, int], tuple[int, int, int, int]]] = []
        for x, y in unfilled:
            colors = []
            for neighbor in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
                (x - 1, y - 1),
                (x + 1, y - 1),
                (x - 1, y + 1),
                (x + 1, y + 1),
            ):
                if neighbor not in unfilled:
                    color = pixels[neighbor[0], neighbor[1]]
                    if color[3] and color[0] >= 150 and color[1] >= 70:
                        colors.append(color)
            if colors:
                color = max(set(colors), key=colors.count)
                updates.append(((x, y), color))
        if not updates:
            raise ValueError("could not inpaint an eye region")
        for point, color in updates:
            pixels[point[0], point[1]] = color
            unfilled.remove(point)


def close_both_eyes(source: Path, destination: Path) -> None:
    image = zero_transparent_rgb(Image.open(source))
    eyes = detect_open_eyes(image)
    centers = [((left + right) / 2, (top + bottom) / 2) for left, top, right, bottom in eyes]
    angle = math.degrees(
        math.atan2(centers[1][1] - centers[0][1], centers[1][0] - centers[0][0])
    )
    template = eye_template()

    for (left, top, right, bottom), (center_x, center_y) in zip(eyes, centers, strict=True):
        expanded = (left - 4, top - 4, right + 4, bottom + 4)
        erase = Image.new("L", CELL_SIZE, 0)
        ImageDraw.Draw(erase).ellipse(expanded, fill=255)
        mask = {
            (x, y)
            for y in range(max(0, expanded[1]), min(CELL_SIZE[1], expanded[3] + 1))
            for x in range(max(0, expanded[0]), min(CELL_SIZE[0], expanded[2] + 1))
            if erase.getpixel((x, y))
        }
        inpaint_mask(image, mask)

        target_width = max(14, right - left - 1)
        target_height = max(6, round(template.height * target_width / template.width))
        arc = template.resize((target_width, target_height), Image.Resampling.NEAREST)
        arc = arc.rotate(-angle, resample=Image.Resampling.NEAREST, expand=True, fillcolor=0)
        dark = Image.new("RGBA", arc.size, (47, 30, 5, 255))
        position = (
            round(center_x - arc.width / 2),
            round(center_y + 2 - arc.height / 2),
        )
        eye_layer = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
        eye_layer.paste(dark, position, arc)
        image.alpha_composite(eye_layer)

    destination.parent.mkdir(parents=True, exist_ok=True)
    zero_transparent_rgb(image).save(destination, optimize=True)


def shift_frame(source: Path, destination: Path, dy: int) -> None:
    image = zero_transparent_rgb(Image.open(source))
    shifted = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    shifted.alpha_composite(image, (0, dy))
    zero_transparent_rgb(shifted).save(destination, optimize=True)


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


def build() -> dict[str, object]:
    for directory in (NORMALIZED, CLOSED, RIGHT, LEFT):
        directory.mkdir(parents=True, exist_ok=True)

    palette = gold_palette()
    areas: dict[str, int] = {}
    for frame_number in range(2, 7):
        source = ALPHA / f"f{frame_number:02d}-alpha.png"
        destination = NORMALIZED / f"f{frame_number:02d}.png"
        areas[f"f{frame_number:02d}"] = normalize_generated(source, destination, palette)

    open_frames = [
        GOLD_OPEN,
        NORMALIZED / "f02.png",
        NORMALIZED / "f03.png",
        NORMALIZED / "f04.png",
        NORMALIZED / "f05.png",
        NORMALIZED / "f06.png",
        GOLD_OPEN,
        GOLD_OPEN,
    ]
    selected = []
    for index, source in enumerate(open_frames, start=1):
        destination = CLOSED / f"f{index:02d}.png"
        close_both_eyes(source, destination)
        selected.append(destination)
    f07_shifted = CLOSED / "f07-shifted.png"
    shift_frame(selected[6], f07_shifted, dy=-1)
    selected[6] = f07_shifted

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

    save_gif(PIPELINE / "right-preview.gif", right_frames)
    save_gif(PIPELINE / "left-preview.gif", left_frames)

    contact = Image.new("RGBA", (CELL_SIZE[0] * 8, CELL_SIZE[1] + 20), (18, 18, 18, 255))
    draw = ImageDraw.Draw(contact)
    for index, frame in enumerate(right_frames):
        x = index * CELL_SIZE[0]
        cell = checker()
        cell.alpha_composite(frame)
        contact.alpha_composite(cell, (x, 20))
        draw.text((x + 4, 4), f"F{index + 1}", fill=(255, 255, 255, 255))
    contact.convert("RGB").save(PIPELINE / "right-contact-sheet.png", optimize=True)

    errors: list[str] = []
    gold_hash = sha256(GOLD_OPEN)
    first_hash = sha256(RIGHT / "running-right-01.png")
    if sha256(RIGHT / "running-right-08.png") != first_hash:
        errors.append("F8 does not return exactly to the closed-eye F1")
    for name, area in areas.items():
        deviation = abs(area - TARGET_ALPHA_AREA) / TARGET_ALPHA_AREA
        if deviation > AREA_TOLERANCE:
            errors.append(f"{name} alpha area drifted by {deviation:.3%}")
    for right, left in zip(right_frames, left_frames, strict=True):
        if left.tobytes() != right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes():
            errors.append("left frame is not an exact mirror of right frame")
            break
    for index, frame in enumerate(right_frames, start=1):
        if len(open_eye_candidates(frame)) >= 2:
            errors.append(f"F{index} still contains two open eyes")
    anchor_warm_mean = warm_mean(right_frames[0])
    warm_means = [warm_mean(frame) for frame in right_frames]
    for index, mean in enumerate(warm_means, start=1):
        if max(abs(value - anchor) for value, anchor in zip(mean, anchor_warm_mean, strict=True)) > 6:
            errors.append(f"F{index} warm palette mean drifted from F1: {mean}")

    validation = {
        "ok": not errors,
        "status": "superseded-source",
        "superseded_by": "../six-gold-rerun-v2/",
        "identity_frame": str(GOLD_OPEN.relative_to(PET)),
        "identity_frame_sha256": gold_hash,
        "frame_durations_ms": FRAME_DURATIONS_MS,
        "target_alpha_area": TARGET_ALPHA_AREA,
        "generated_frame_alpha_areas": areas,
        "eye_policy": "both eyes synchronized closed in all eight frames",
        "recovery_bob_frame": 7,
        "exact_return_frames": [8],
        "palette_policy": "all generated frames share one 128-color palette derived from exact F1",
        "warm_palette_mean_rgb": [list(mean) for mean in warm_means],
        "warm_palette_max_channel_drift": 6,
        "left_policy": "exact pixel mirror of right",
        "errors": errors,
    }
    VALIDATION.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if errors:
        raise SystemExit("\n".join(errors))
    return validation


if __name__ == "__main__":
    result = build()
    print(f"Round-body directional candidate: {'OK' if result['ok'] else 'FAILED'}")
