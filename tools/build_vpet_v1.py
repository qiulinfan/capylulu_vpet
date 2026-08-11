from __future__ import annotations

import hashlib
import json
from collections import deque
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
DRAG_FRAME_DURATIONS_MS = [120, 120, 120, 120, 120, 120, 120, 220]
RUNNING_FRAME_DURATIONS_MS = [120, 120, 120, 120, 120, 220]
WAVING_FRAME_DURATIONS_MS = [140, 140, 140, 280]
DRAG_EYE_SPACING_MAX_DRIFT = 2.5
GOLD_EYE_SPACING = 51.715083798882674
EXPECTED_WAVING_BBOXES = [
    (34, 10, 158, 200),
    (26, 10, 166, 200),
    (22, 10, 169, 200),
    (25, 10, 167, 200),
]
EXPECTED_WAVING_SHA256 = {
    "waving-01.png": "4927bb779a107d6a357f0ae7fdfa73817a1bc350a45e9720e34bece0e04a11c6",
    "waving-02.png": "844c6bb342b2f4c0544da18d86154cd416a0fde9e85878a3d5811bfa284c5f70",
    "waving-03.png": "ad1ae7b765b28fd8f66009d0ea14fd288f0a6d1e076dd8006367dff29d701829",
    "waving-04.png": "7592d49c57b6bc6b4010d39fad51ccd6b087808e22e0a34bd6e25e151110a476",
}
EXPECTED_DRAG_RIGHT_SHA256 = {
    "running-right-01.png": "861deb3a6d5c693a56ca07c831078b5defe960cd72450d4dc96a124ad0cf7d42",
    "running-right-02.png": "88b516a44fc4ab6a9a5498eb724a86a71192fff4fbf5e4e72b87ff8967e6dc71",
    "running-right-03.png": "775e4cb5d17c1ba75192d5455afd67b8faab07cd9b682d6a7c9b45e82e04415a",
    "running-right-04.png": "f17c83affdbece6b846dce16e5cc4868f45435d76d4f401ef25d43eebe88d500",
    "running-right-05.png": "5c3b0384f81351778292bbebc3e11b355106d71df404a01e9c5e3926ec088d78",
    "running-right-06.png": "5f6c8fc44b30e1db36865eee653279bb534c33534e64a6c1e2cf9fa01901a464",
    "running-right-07.png": "3701c843f261ff80d81eff592bdf6ea1e81476828f773d8e061df5f11602562e",
    "running-right-08.png": "4c19d2715d46c0e9687ade0001912364fc98b324305d86b072de91982f35c91b",
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
        or scope["state_aliases"] != {"idle": "review", "running": "review"}
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


def alpha_components(image: Image.Image, threshold: int = 128) -> list[set[tuple[int, int]]]:
    alpha = image.getchannel("A")
    eligible = {
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if alpha.getpixel((x, y)) >= threshold
    }
    components: list[set[tuple[int, int]]] = []
    while eligible:
        start = eligible.pop()
        component = {start}
        queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for candidate in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if candidate in eligible:
                    eligible.remove(candidate)
                    component.add(candidate)
                    queue.append(candidate)
        components.append(component)
    return components


def find_open_eye_components(image: Image.Image) -> list[set[tuple[int, int]]]:
    """Locate full open-eye ovals while allowing the head to follow drag inertia."""
    source = image.convert("RGBA")
    mask = Image.new("RGBA", source.size, (0, 0, 0, 0))
    source_pixels = source.load()
    mask_pixels = mask.load()
    for y in range(45, 95):
        for x in range(30, 162):
            red, green, blue, alpha = source_pixels[x, y]
            if alpha > 128 and red + green + blue < 180:
                mask_pixels[x, y] = (0, 0, 0, 255)
    eye_components = []
    for component in alpha_components(mask):
        xs = [x for x, _ in component]
        ys = [y for _, y in component]
        if (
            len(component) >= 130
            and max(xs) - min(xs) + 1 >= 13
            and max(ys) - min(ys) + 1 >= 13
        ):
            eye_components.append(component)
    return sorted(eye_components, key=lambda component: sum(x for x, _ in component) / len(component))


def find_eye_centers(image: Image.Image) -> list[tuple[float, float]]:
    eye_components = find_open_eye_components(image)
    if len(eye_components) != 2:
        raise ValueError("Expected two full open-eye components in the V1 face band")
    centers = [
        (
            sum(x for x, _ in component) / len(component),
            sum(y for _, y in component) / len(component),
        )
        for component in eye_components
    ]
    return centers


def gif_durations(path: Path) -> list[int | None]:
    image = Image.open(path)
    durations = []
    for index in range(getattr(image, "n_frames", 1)):
        image.seek(index)
        durations.append(image.info.get("duration"))
    return durations


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
    for index, (running, review) in enumerate(
        zip(states["running"], states["review"], strict=True), start=1
    ):
        if running.tobytes() != review.tobytes():
            errors.append(f"running[{index}] must exactly reuse focused-listening review[{index}]")

    drag_right_sha256 = {}
    for filename, expected in EXPECTED_DRAG_RIGHT_SHA256.items():
        path = FRAMES / "running-right" / filename
        actual = sha256(path)
        drag_right_sha256[filename] = actual
        if actual != expected:
            errors.append(f"approved directional frame changed: {filename}")
    for index, (right, left) in enumerate(
        zip(states["running-right"], states["running-left"], strict=True), start=1
    ):
        mirrored = right.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if left.tobytes() != mirrored.tobytes():
            errors.append(f"running-left[{index}] must exactly mirror running-right[{index}]")
    if len({frame.tobytes() for frame in states["running-right"]}) != 8:
        errors.append("running-right must contain eight distinct drag poses")

    drag_eye_spacings: dict[str, list[float]] = {}
    drag_eye_spacing_drifts: dict[str, list[float]] = {}
    for state in ("running-right", "running-left"):
        spacings = []
        drifts = []
        for index, frame in enumerate(states[state], start=1):
            centers = find_eye_centers(frame)
            spacing = centers[1][0] - centers[0][0]
            drift = abs(spacing - GOLD_EYE_SPACING)
            spacings.append(spacing)
            drifts.append(drift)
            if drift > DRAG_EYE_SPACING_MAX_DRIFT:
                errors.append(
                    f"{state}[{index}] eye spacing drifted from V1 gold: "
                    f"{drift:.2f}px > {DRAG_EYE_SPACING_MAX_DRIFT:.2f}px"
                )
        drag_eye_spacings[state] = spacings
        drag_eye_spacing_drifts[state] = drifts

    drag_eye_states = {
        state: [
            (len(find_open_eye_components(frame)) == 2,) * 2
            for frame in states[state]
        ]
        for state in ("running-right", "running-left")
    }
    expected_drag_eye_states = [(True, True)] * 8
    for state, observed in drag_eye_states.items():
        if observed != expected_drag_eye_states:
            errors.append(f"{state} eyes must remain open together: {observed}")

    drag_bboxes = {
        state: [frame.getchannel("A").getbbox() for frame in states[state]]
        for state in ("running-right", "running-left")
    }
    for state, bboxes in drag_bboxes.items():
        for index, bbox in enumerate(bboxes, start=1):
            if bbox is None:
                errors.append(f"{state}[{index}] is empty")
                continue
            left, top, right, bottom = bbox
            if left < 18 or right > 174 or top < 4 or bottom > 200:
                errors.append(f"{state}[{index}] escaped the V1 drag envelope: {bbox}")
    drag_alpha_is_binary = all(
        alpha in (0, 255)
        for state in ("running-right", "running-left")
        for frame in states[state]
        for alpha in frame.getchannel("A").get_flattened_data()
    )
    if not drag_alpha_is_binary:
        errors.append("directional drag frames must retain the formal V1 hard alpha edge")

    waving_eye_states = [eye_states(frame) for frame in states["waving"]]
    expected_eye_states = [(False, False), (True, True), (True, True), (False, False)]
    if waving_eye_states != expected_eye_states:
        errors.append(f"waving eyes must blink together: {waving_eye_states}")

    for filename, expected_hash in EXPECTED_WAVING_SHA256.items():
        actual_hash = sha256(FRAMES / "waving" / filename)
        if actual_hash != expected_hash:
            errors.append(f"{filename} must remain byte-identical to its approved V1 action frame")

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

    expected_gif_durations = {
        "02-running-right.gif": DRAG_FRAME_DURATIONS_MS,
        "03-running-left.gif": DRAG_FRAME_DURATIONS_MS,
        "04-waving.gif": WAVING_FRAME_DURATIONS_MS,
        "08-running.gif": RUNNING_FRAME_DURATIONS_MS,
    }
    action_gif_durations = {}
    for filename, expected in expected_gif_durations.items():
        observed = gif_durations(QA / "action-gifs" / filename)
        action_gif_durations[filename] = observed
        if observed != expected:
            errors.append(f"{filename} QA timing differs from runtime: {observed}")

    return {
        "ok": not errors,
        "scope": "formal-v1",
        "format": "RGBA PNG + single-frame lossless WebP",
        "width": atlas.width,
        "height": atlas.height,
        "cell_size": [CELL_W, CELL_H],
        "errors": errors,
        "warnings": [],
        "state_aliases": {"idle": "review", "running": "review"},
        "directional_drag": {
            "semantics": {
                "running-right": "pointer/window dragged right; body and limbs trail left",
                "running-left": "exact horizontal mirror of running-right",
            },
            "source": "sequence-drafts/v1-action-work/drag-directional/right-drag-motion-v4-selected-alpha-hard.png",
            "frame_durations_ms": DRAG_FRAME_DURATIONS_MS,
            "gold_eye_spacing": GOLD_EYE_SPACING,
            "eye_spacings": drag_eye_spacings,
            "eye_spacing_drifts": drag_eye_spacing_drifts,
            "max_eye_spacing_drift": DRAG_EYE_SPACING_MAX_DRIFT,
            "eye_states": {
                state: [list(value) for value in values]
                for state, values in drag_eye_states.items()
            },
            "bboxes": drag_bboxes,
            "alpha_is_binary": drag_alpha_is_binary,
            "left_is_exact_mirror": not any(
                left.tobytes()
                != right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
                for right, left in zip(
                    states["running-right"], states["running-left"], strict=True
                )
            ),
        },
        "waving_eye_states": [list(state) for state in waving_eye_states],
        "waving_bboxes": waving_bboxes,
        "waving_alpha_is_binary": waving_alpha_is_binary,
        "waving_frame_durations_ms": WAVING_FRAME_DURATIONS_MS,
        "action_gif_durations_ms": action_gif_durations,
        "cells": cells,
        "sha256": {
            "spritesheet.png": sha256(FINAL / "spritesheet.png"),
            "spritesheet.webp": sha256(FINAL / "spritesheet.webp"),
            "running-right": drag_right_sha256,
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
        if state in ("running-right", "running-left"):
            durations = DRAG_FRAME_DURATIONS_MS
        elif state == "waving":
            durations = WAVING_FRAME_DURATIONS_MS
        elif state == "running":
            durations = RUNNING_FRAME_DURATIONS_MS
        else:
            durations = [DEFAULT_ACTION_FRAME_MS] * len(states[state])
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
