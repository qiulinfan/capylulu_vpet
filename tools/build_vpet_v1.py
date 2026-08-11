from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, features


ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "pet-runs" / "capybara-lulu"
REQUEST = PET / "pet_request.json"
SCOPE = PET / "asset-scope.json"
FRAMES = PET / "official-frames-v1"
FINAL = PET / "final"
QA = PET / "qa"

CELL_W = 192
CELL_H = 208
COLS = 8
ROWS = 9
ATLAS_SIZE = (COLS * CELL_W, ROWS * CELL_H)
EXPECTED_STATES = [
    ("idle", 6),
    ("running-right", 8),
    ("running-left", 8),
    ("waving", 4),
    ("jumping", 5),
    ("failed", 8),
    ("waiting", 6),
    ("running", 6),
    ("review", 6),
]
EYE_REGIONS = ((55, 58, 90, 90), (105, 58, 140, 90))
DEFAULT_ACTION_FRAME_MS = 180
WAVING_FRAME_DURATIONS_MS = [140, 140, 140, 280]
EXPECTED_WAVING_BBOXES = [
    (34, 10, 158, 200),
    (26, 10, 166, 200),
    (22, 10, 169, 200),
    (25, 10, 167, 200),
]
EXPECTED_REUSED_WAVING_SHA256 = {
    "waving-03.png": "ad1ae7b765b28fd8f66009d0ea14fd288f0a6d1e076dd8006367dff29d701829",
    "waving-04.png": "7592d49c57b6bc6b4010d39fad51ccd6b087808e22e0a34bd6e25e151110a476",
}


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


def load_states() -> dict[str, list[Image.Image]]:
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    if (
        scope["formal_version"] != "v1"
        or scope["formal_frames"] != "official-frames-v1/"
        or scope["installable_package"] != "final/"
        or scope["runtime_states"] != [state for state, _ in EXPECTED_STATES]
        or scope["state_aliases"] != {"idle": "review"}
    ):
        raise ValueError("asset-scope.json no longer matches the formal V1 contract")
    request = json.loads(REQUEST.read_text(encoding="utf-8"))
    request_states = [(row["state"], row["frames"]) for row in request["rows"]]
    if request_states != EXPECTED_STATES:
        raise ValueError(f"Unexpected formal state contract: {request_states}")
    if request["atlas"] != {
        "columns": COLS,
        "rows": ROWS,
        "cell_width": CELL_W,
        "cell_height": CELL_H,
        "width": ATLAS_SIZE[0],
        "height": ATLAS_SIZE[1],
    }:
        raise ValueError("pet_request.json atlas contract changed")

    states: dict[str, list[Image.Image]] = {}
    for state, expected_count in EXPECTED_STATES:
        paths = sorted((FRAMES / state).glob(f"{state}-*.png"))
        if len(paths) != expected_count:
            raise ValueError(f"{state}: expected {expected_count} formal frames, found {len(paths)}")
        frames = [zero_transparent_rgb(Image.open(path)) for path in paths]
        if any(frame.size != (CELL_W, CELL_H) for frame in frames):
            raise ValueError(f"{state}: every frame must be {CELL_W}x{CELL_H}")
        states[state] = frames
    return states


def build_atlas(states: dict[str, list[Image.Image]]) -> Image.Image:
    atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
    for row, (state, _) in enumerate(EXPECTED_STATES):
        for column, frame in enumerate(states[state]):
            atlas.alpha_composite(frame, (column * CELL_W, row * CELL_H))
    return zero_transparent_rgb(atlas)


def checker(size: tuple[int, int], square: int = 8) -> Image.Image:
    image = Image.new("RGBA", size, (238, 238, 238, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], square):
        for x in range(0, size[0], square):
            if (x // square + y // square) % 2:
                draw.rectangle((x, y, x + square - 1, y + square - 1), fill=(211, 211, 211, 255))
    return image


def make_contact_sheet(states: dict[str, list[Image.Image]]) -> None:
    thumb_w = CELL_W // 2
    thumb_h = CELL_H // 2
    label_h = 22
    canvas = Image.new("RGB", (COLS * thumb_w, ROWS * (thumb_h + label_h)), (18, 18, 18))
    draw = ImageDraw.Draw(canvas)
    for row, (state, count) in enumerate(EXPECTED_STATES):
        top = row * (thumb_h + label_h)
        draw.text((5, top + 4), f"row {row} {state}", fill=(255, 255, 255))
        draw.text((COLS * thumb_w - 56, top + 4), f"{count} frames", fill=(255, 255, 255))
        for column in range(COLS):
            x = column * thumb_w
            y = top + label_h
            cell = checker((thumb_w, thumb_h))
            if column < count:
                thumb = states[state][column].resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                cell.alpha_composite(thumb)
                border = (27, 198, 118)
            else:
                border = (220, 70, 70)
            canvas.paste(cell.convert("RGB"), (x, y))
            draw.rectangle((x, y, x + thumb_w - 1, y + thumb_h - 1), outline=border)
            draw.text((x + 4, y + 3), str(column), fill=(25, 25, 25))
    canvas.save(QA / "contact-sheet.png", optimize=True)


def make_idle_qa(frames: list[Image.Image]) -> None:
    durations = [600, 600, 600, 600, 600, 1120]
    frames[0].save(
        QA / "idle-sequence-preview.webp",
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        lossless=True,
        method=6,
        exact=True,
    )

    label_h = 24
    canvas = Image.new("RGBA", (len(frames) * CELL_W, CELL_H + label_h), (18, 18, 18, 255))
    draw = ImageDraw.Draw(canvas)
    for index, frame in enumerate(frames):
        x = index * CELL_W
        cell = checker((CELL_W, CELL_H), square=12)
        cell.alpha_composite(frame)
        canvas.alpha_composite(cell, (x, label_h))
        draw.text((x + 5, 5), f"{index + 1:02d} focused-listening", fill=(255, 255, 255, 255))
    canvas.convert("RGB").save(QA / "idle-sequence-contact-sheet.png", optimize=True)


def make_action_gif(path: Path, frames: list[Image.Image], durations: list[int]) -> None:
    if len(durations) != len(frames):
        raise ValueError(f"{path.name}: duration count must match frame count")
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )


def eye_states(frame: Image.Image) -> tuple[bool, bool]:
    result = []
    for left, top, right, bottom in EYE_REGIONS:
        white_pixels = 0
        for red, green, blue, alpha in frame.crop((left, top, right, bottom)).get_flattened_data():
            if alpha > 128 and red > 210 and green > 210 and blue > 210:
                white_pixels += 1
        result.append(white_pixels >= 40)
    return result[0], result[1]


def validate(states: dict[str, list[Image.Image]], atlas: Image.Image) -> dict[str, object]:
    errors: list[str] = []
    cells = []
    for index, (idle, review) in enumerate(zip(states["idle"], states["review"], strict=True), start=1):
        if idle.tobytes() != review.tobytes():
            errors.append(f"idle[{index}] must exactly reuse focused-listening review[{index}]")

    waving_eye_states = [eye_states(frame) for frame in states["waving"]]
    expected_eye_states = [(False, False), (True, True), (True, True), (False, False)]
    if waving_eye_states != expected_eye_states:
        errors.append(f"waving eyes must blink together: {waving_eye_states}")

    normal_stand = zero_transparent_rgb(Image.open(FRAMES / "running" / "running-04.png"))
    if states["waving"][0].tobytes() != normal_stand.tobytes():
        errors.append("waving[1] must exactly reuse the formal V1 normal standing pose")

    gold_open_face = zero_transparent_rgb(Image.open(FRAMES / "running" / "running-05.png"))
    if states["waving"][1].crop((0, 0, CELL_W, 120)).tobytes() != gold_open_face.crop(
        (0, 0, CELL_W, 120)
    ).tobytes():
        errors.append("waving[2] must retain the exact formal V1 upper head and face")

    for filename, expected_hash in EXPECTED_REUSED_WAVING_SHA256.items():
        actual_hash = sha256(FRAMES / "waving" / filename)
        if actual_hash != expected_hash:
            errors.append(f"{filename} must remain byte-identical to its approved no-windup peak")

    waving_bboxes = [frame.getchannel("A").getbbox() for frame in states["waving"]]
    if waving_bboxes != EXPECTED_WAVING_BBOXES:
        errors.append(f"waving pose anchors drifted: {waving_bboxes}")
    waving_alpha_is_binary = all(
        alpha in (0, 255)
        for frame in states["waving"]
        for alpha in frame.getchannel("A").get_flattened_data()
    )
    if not waving_alpha_is_binary:
        errors.append("waving frames must retain the formal V1 hard alpha edge")

    for row, (state, used_count) in enumerate(EXPECTED_STATES):
        for column in range(COLS):
            cell = atlas.crop(
                (column * CELL_W, row * CELL_H, (column + 1) * CELL_W, (row + 1) * CELL_H)
            )
            bbox = cell.getchannel("A").getbbox()
            if column < used_count:
                if cell.tobytes() != states[state][column].tobytes():
                    errors.append(f"atlas {state}[{column}] differs from its formal frame")
            elif bbox is not None:
                errors.append(f"atlas {state}[{column}] must be transparent")
            cells.append(
                {
                    "state": state,
                    "row": row,
                    "column": column,
                    "used": column < used_count,
                    "bbox": bbox,
                }
            )

    webp = Image.open(FINAL / "spritesheet.webp")
    if getattr(webp, "n_frames", 1) != 1:
        errors.append("formal spritesheet.webp must be a single-frame lossless atlas")
    if webp.convert("RGBA").tobytes() != atlas.tobytes():
        errors.append("formal PNG and lossless WebP must decode pixel-identically")

    waving_gif = Image.open(QA / "action-gifs" / "04-waving.gif")
    gif_durations = []
    for index in range(getattr(waving_gif, "n_frames", 1)):
        waving_gif.seek(index)
        gif_durations.append(waving_gif.info.get("duration"))
    if gif_durations != WAVING_FRAME_DURATIONS_MS:
        errors.append(f"waving QA GIF timing differs from runtime: {gif_durations}")

    return {
        "ok": not errors,
        "scope": "formal-v1",
        "format": "RGBA PNG + single-frame lossless WebP",
        "width": atlas.width,
        "height": atlas.height,
        "cell_size": [CELL_W, CELL_H],
        "errors": errors,
        "warnings": [],
        "idle_reuses": "review",
        "waving_eye_states": [list(state) for state in waving_eye_states],
        "waving_bboxes": waving_bboxes,
        "waving_alpha_is_binary": waving_alpha_is_binary,
        "waving_frame_durations_ms": WAVING_FRAME_DURATIONS_MS,
        "cells": cells,
        "sha256": {
            "spritesheet.png": sha256(FINAL / "spritesheet.png"),
            "spritesheet.webp": sha256(FINAL / "spritesheet.webp"),
        },
        "toolchain": {
            "pillow": Image.__version__,
            "webp": bool(features.check("webp")),
            "webp_version": features.version_module("webp"),
        },
    }


def build() -> None:
    FINAL.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    states = load_states()
    atlas = build_atlas(states)
    atlas.save(FINAL / "spritesheet.png", optimize=True)
    atlas.save(FINAL / "spritesheet.webp", format="WEBP", lossless=True, method=6, exact=True)
    make_contact_sheet(states)
    make_idle_qa(states["idle"])
    for index, (state, _) in enumerate(EXPECTED_STATES, start=1):
        durations = (
            WAVING_FRAME_DURATIONS_MS
            if state == "waving"
            else [DEFAULT_ACTION_FRAME_MS] * len(states[state])
        )
        make_action_gif(
            QA / "action-gifs" / f"{index:02d}-{state}.gif",
            states[state],
            durations,
        )
    validation = validate(states, atlas)
    (FINAL / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Built formal V1 atlas: {atlas.width}x{atlas.height}")
    print(f"Validation: {'OK' if validation['ok'] else 'FAILED'} ({len(validation['errors'])} errors)")
    if not validation["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    build()
