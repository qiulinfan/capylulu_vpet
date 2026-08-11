from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps, features


DRAFT = Path(__file__).resolve().parent
PET = DRAFT.parents[1]
ROOT = PET.parents[1]
SOURCES = DRAFT / "sources"
BUILD = DRAFT / "build"
NORMALIZED = BUILD / "normalized"
LIBRARY = BUILD / "animation-library"
FINAL = DRAFT / "package-preview"
QA = DRAFT / "qa"

LIBRARY_SOURCE = SOURCES / "idle-library-gold-aligned-alpha.png"
LIBRARY_NEUTRAL_SOURCE = SOURCES / "idle-library-gold-aligned-neutral.png"
LIBRARY_GOLD_REFERENCE = SOURCES / "legacy-v1" / "running" / "running-01.png"

CELL_W = 192
CELL_H = 208
COLS = 8
ROWS = 11
ATLAS_SIZE = (COLS * CELL_W, ROWS * CELL_H)

LIBRARY_NEUTRAL_HEIGHT = 190
LIBRARY_NEUTRAL_WIDTH = 140
LIBRARY_GROUND_Y = 200
LIBRARY_ACTION_MAX_WIDTH = 176
LIBRARY_ACTION_MAX_HEIGHT = 196

STATE_ORDER = [
    ("idle", 6),
    ("running-right", 8),
    ("running-left", 8),
    ("waving", 4),
    ("jumping", 5),
    ("failed", 8),
    ("waiting", 6),
    ("running", 6),
    ("review", 6),
    ("gaze-00-to-07", 8),
    ("gaze-08-to-15", 8),
]

LIBRARY_ACTIONS = ["stretch", "sneeze", "kiss-shy", "warm-bath", "happy-snack"]

# These frames intentionally contain detached story elements.  Keep the checks
# close to the build so a future cleanup pass cannot silently erase them.
DETACHED_ELEMENT_CHECKS = {
    ("sneeze", 3): {"minimum_area": 1000, "minimum_components": 2},
    ("warm-bath", 3): {"minimum_area": 1000, "minimum_components": 2},
    ("warm-bath", 4): {"minimum_area": 20, "minimum_components": 5},
}
FACE_ANCHOR_REGION = (50, 55, 142, 90)
FACE_ANCHOR_MAX_DRIFT = 2.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_sheet(
    path: Path,
    rows: int,
    cols: int,
    y_boundaries: list[int] | None = None,
) -> list[list[Image.Image]]:
    sheet = Image.open(path).convert("RGBA")
    if y_boundaries is not None and (
        len(y_boundaries) != rows + 1
        or y_boundaries[0] != 0
        or y_boundaries[-1] != sheet.height
        or any(left >= right for left, right in zip(y_boundaries, y_boundaries[1:]))
    ):
        raise ValueError(f"Invalid sprite-sheet row boundaries: {y_boundaries}")
    result: list[list[Image.Image]] = []
    for row in range(rows):
        row_frames: list[Image.Image] = []
        y0 = y_boundaries[row] if y_boundaries is not None else round(row * sheet.height / rows)
        y1 = y_boundaries[row + 1] if y_boundaries is not None else round((row + 1) * sheet.height / rows)
        for col in range(cols):
            x0 = round(col * sheet.width / cols)
            x1 = round((col + 1) * sheet.width / cols)
            row_frames.append(sheet.crop((x0, y0, x1, y1)))
        result.append(row_frames)
    return result


def find_transparent_row_boundaries(
    path: Path,
    rows: int,
    search_radius: int = 32,
    alpha_threshold: int = 8,
) -> list[int]:
    """Recover action rows when an edited sheet drifts across nominal cuts."""
    sheet = Image.open(path).convert("RGBA")
    alpha = sheet.getchannel("A").point(lambda value: 255 if value > alpha_threshold else 0)
    boundaries = [0]
    for row in range(1, rows):
        nominal = round(row * sheet.height / rows)
        candidates = []
        for y in range(max(1, nominal - search_radius), min(sheet.height - 1, nominal + search_radius + 1)):
            if not alpha.crop((0, y, sheet.width, y + 1)).getbbox():
                candidates.append(y)
        if not candidates:
            raise ValueError(f"No transparent separator found near source row boundary {nominal}")
        boundaries.append(min(candidates, key=lambda y: abs(y - nominal)))
    boundaries.append(sheet.height)
    return boundaries


def is_magenta(pixel: tuple[int, int, int, int]) -> bool:
    red, green, blue, alpha = pixel
    return alpha > 0 and red > 145 and blue > 115 and green < 105


def clean_magenta_fringe(image: Image.Image) -> Image.Image:
    """Replace the final chroma fringe with the nearest opaque subject color."""
    source = image.convert("RGBA")
    pixels = source.load()
    replacements: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    for y in range(source.height):
        for x in range(source.width):
            if not is_magenta(pixels[x, y]):
                continue
            replacement = None
            for radius in range(1, 6):
                candidates = []
                for yy in range(max(0, y - radius), min(source.height, y + radius + 1)):
                    for xx in range(max(0, x - radius), min(source.width, x + radius + 1)):
                        candidate = pixels[xx, yy]
                        if candidate[3] >= 220 and not is_magenta(candidate):
                            candidates.append(candidate)
                if candidates:
                    replacement = min(candidates, key=lambda p: p[0] + p[1] + p[2])
                    break
            replacements[(x, y)] = replacement or (61, 25, 8, pixels[x, y][3])
    for (x, y), replacement in replacements.items():
        pixels[x, y] = replacement
    return source


def alpha_components(image: Image.Image, threshold: int = 8) -> list[set[tuple[int, int]]]:
    alpha = image.getchannel("A")
    eligible = {
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if alpha.getpixel((x, y)) > threshold
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


def find_eye_centers(image: Image.Image) -> list[tuple[float, float]]:
    """Locate the two dark eye components inside the canonical face band."""
    source = image.convert("RGBA")
    mask = Image.new("RGBA", source.size, (0, 0, 0, 0))
    source_pixels = source.load()
    mask_pixels = mask.load()
    left, top, right, bottom = FACE_ANCHOR_REGION
    for y in range(top, bottom):
        for x in range(left, right):
            red, green, blue, alpha = source_pixels[x, y]
            if alpha > 128 and red + green + blue < 180:
                mask_pixels[x, y] = (0, 0, 0, 255)
    eye_components = sorted(
        (component for component in alpha_components(mask) if len(component) >= 50),
        key=len,
        reverse=True,
    )[:2]
    if len(eye_components) != 2:
        raise ValueError("Expected two dark eye components in the canonical face band")
    centers = [
        (
            sum(x for x, _ in component) / len(component),
            sum(y for _, y in component) / len(component),
        )
        for component in eye_components
    ]
    return sorted(centers)


def remove_grid_bleed(image: Image.Image) -> Image.Image:
    """Drop small disconnected fragments that crossed an AI storyboard cell boundary."""
    output = image.convert("RGBA")
    pixels = output.load()
    for component in alpha_components(output):
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        touches_edge = min(xs) <= 2 or max(xs) >= output.width - 3 or min(ys) <= 2 or max(ys) >= output.height - 3
        is_boundary_sliver = max(ys) < 28 or min(ys) > output.height - 28
        if len(component) < 1500 and (touches_edge or is_boundary_sliver):
            for x, y in component:
                pixels[x, y] = (0, 0, 0, 0)
    return output


def alpha_bbox(image: Image.Image, threshold: int = 8) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A").point(lambda value: 255 if value > threshold else 0)
    return alpha.getbbox()


def normalize_sequence(
    frames: list[Image.Image],
    max_width: int = 168,
    max_height: int = 184,
    ground_y: int = 199,
) -> list[Image.Image]:
    cleaned = [remove_grid_bleed(clean_magenta_fringe(frame)) for frame in frames]
    boxes = [alpha_bbox(frame) for frame in cleaned]
    if any(box is None for box in boxes):
        raise ValueError("Every source frame must contain visible pixels")
    visible_boxes = [box for box in boxes if box is not None]
    widest = max(box[2] - box[0] for box in visible_boxes)
    tallest = max(box[3] - box[1] for box in visible_boxes)
    scale = min(max_width / widest, max_height / tallest)

    normalized: list[Image.Image] = []
    for frame, box in zip(cleaned, visible_boxes, strict=True):
        crop = frame.crop(box)
        width = max(1, round(crop.width * scale))
        height = max(1, round(crop.height * scale))
        resized = crop.resize((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
        x = (CELL_W - width) // 2
        y = ground_y - height
        canvas.alpha_composite(resized, (x, y))
        normalized.append(zero_transparent_rgb(canvas))
    return normalized


def harden_alpha(image: Image.Image, threshold: int = 128) -> Image.Image:
    """Match the V1 sprites' fully opaque or fully transparent pixel edges."""
    output = image.convert("RGBA")
    output.putalpha(output.getchannel("A").point(lambda value: 255 if value >= threshold else 0))
    return zero_transparent_rgb(output)


def align_alpha_bottom(image: Image.Image, ground_y: int) -> Image.Image:
    box = alpha_bbox(image)
    if box is None or box[3] == ground_y:
        return image
    aligned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    aligned.alpha_composite(image, (0, ground_y - box[3]))
    return zero_transparent_rgb(aligned)


def normalize_library_sequence(
    frames: list[Image.Image],
    neutral_height: int = LIBRARY_NEUTRAL_HEIGHT,
    ground_y: int = LIBRARY_GROUND_Y,
    max_width: int = LIBRARY_ACTION_MAX_WIDTH,
    max_height: int = LIBRARY_ACTION_MAX_HEIGHT,
) -> list[Image.Image]:
    """Normalize optional actions against the relaxed V1 body anchor.

    The generic normalizer sizes an entire sequence from its widest frame. That
    makes Lulu shrink when a stretch pose or detached sneeze particle is wide.
    Library actions instead share a scale derived from their relaxed first and
    last frames. Only an individual action frame that exceeds the V1 safety box
    is compressed on that axis, leaving the body scale stable through the loop.
    """
    # Transparent row separators already isolate the gold-aligned source. Keep
    # detached action elements such as airborne fruit, spray, and water drops.
    cleaned = [frame.convert("RGBA") for frame in frames]
    boxes = [alpha_bbox(frame) for frame in cleaned]
    if any(box is None for box in boxes):
        raise ValueError("Every library source frame must contain visible pixels")
    visible_boxes = [box for box in boxes if box is not None]
    anchor_heights = [
        visible_boxes[index][3] - visible_boxes[index][1]
        for index in (0, len(visible_boxes) - 1)
    ]
    anchor_height = sum(anchor_heights) / len(anchor_heights)
    scale = neutral_height / anchor_height

    normalized: list[Image.Image] = []
    for frame, box in zip(cleaned, visible_boxes, strict=True):
        crop = frame.crop(box)
        scaled_width = max(1, round(crop.width * scale))
        scaled_height = max(1, round(crop.height * scale))
        width = min(scaled_width, max_width)
        height = min(scaled_height, max_height)
        resized = crop.resize((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
        x = (CELL_W - width) // 2
        y = ground_y - height
        canvas.alpha_composite(resized, (x, y))
        normalized.append(align_alpha_bottom(harden_alpha(canvas), ground_y))
    return normalized


def fit_library_neutral_anchor(frame: Image.Image) -> Image.Image:
    """Fit the shared relaxed pose to the exact V1 runtime bounding box."""
    box = alpha_bbox(frame)
    if box is None:
        raise ValueError("Library neutral anchor must contain visible pixels")
    crop = frame.crop(box).resize(
        (LIBRARY_NEUTRAL_WIDTH, LIBRARY_NEUTRAL_HEIGHT),
        Image.Resampling.NEAREST,
    )
    canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    x = (CELL_W - LIBRARY_NEUTRAL_WIDTH) // 2
    y = LIBRARY_GROUND_Y - LIBRARY_NEUTRAL_HEIGHT
    canvas.alpha_composite(crop, (x, y))
    return harden_alpha(canvas)


def zero_transparent_rgb(image: Image.Image) -> Image.Image:
    output = image.convert("RGBA")
    data = []
    for red, green, blue, alpha in output.get_flattened_data():
        if alpha == 0:
            data.append((0, 0, 0, 0))
        else:
            data.append((red, green, blue, alpha))
    output.putdata(data)
    return output


def load_existing_sequence(folder: str, count: int) -> list[Image.Image]:
    directory = SOURCES / "legacy-v1" / folder
    return [Image.open(directory / f"{folder}-{index:02d}.png").convert("RGBA") for index in range(1, count + 1)]


def shift_frame(frame: Image.Image, dy: int) -> Image.Image:
    shifted = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    shifted.alpha_composite(frame, (0, dy))
    return shifted


def dark_components(frame: Image.Image) -> list[set[tuple[int, int]]]:
    pixels = frame.load()
    eligible = set()
    for y in range(24, 116):
        for x in range(24, CELL_W - 24):
            red, green, blue, alpha = pixels[x, y]
            if alpha > 220 and red < 72 and green < 72 and blue < 72:
                eligible.add((x, y))
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
        if 24 <= len(component) <= 600:
            components.append(component)
    return components


def make_gaze_frames(anchor: Image.Image) -> list[Image.Image]:
    components = []
    for component in dark_components(anchor):
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        center = (sum(xs) / len(xs), sum(ys) / len(ys))
        if len(component) > 120 and 65 < center[1] < 98 and 38 < center[0] < 154:
            components.append(component)
    components = sorted(components, key=lambda component: sum(x for x, _ in component) / len(component))[:2]
    if len(components) != 2:
        return [anchor.copy() for _ in range(16)]

    directions = [
        (0, -2), (1, -2), (2, -2), (2, -1), (2, 0), (2, 1), (2, 2), (1, 2),
        (0, 2), (-1, 2), (-2, 2), (-2, 1), (-2, 0), (-2, -1), (-2, -2), (-1, -2),
    ]
    frames: list[Image.Image] = []
    for dx, dy in directions:
        frame = anchor.copy()
        pixels = frame.load()
        for component in components:
            xs = [point[0] for point in component]
            ys = [point[1] for point in component]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            for y in range(max(0, min_y - 1), min(CELL_H, max_y + 2)):
                for x in range(max(0, min_x - 1), min(CELL_W, max_x + 2)):
                    pixels[x, y] = (245, 249, 246, 255)
            for x, y in component:
                target_x = min(max(x + dx, 0), CELL_W - 1)
                target_y = min(max(y + dy, 0), CELL_H - 1)
                pixels[target_x, target_y] = (25, 24, 20, 255)
            highlight_x = min(max(max_x + dx - 2, 0), CELL_W - 2)
            highlight_y = min(max(min_y + dy + 2, 0), CELL_H - 2)
            for oy in range(2):
                for ox in range(2):
                    pixels[highlight_x + ox, highlight_y + oy] = (255, 255, 255, 255)
        frames.append(frame)
    return frames


def save_sequence(name: str, frames: list[Image.Image], target_root: Path) -> None:
    directory = target_root / name
    directory.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames, start=1):
        frame.save(directory / f"{name}-{index:02d}.png", optimize=True)


def make_preview(path: Path, frames: list[Image.Image], duration: int = 220) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=[duration] * len(frames),
        loop=0,
        lossless=True,
        method=6,
        exact=True,
    )


def checker(size: tuple[int, int], square: int = 12) -> Image.Image:
    image = Image.new("RGBA", size, (238, 238, 238, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], square):
        for x in range(0, size[0], square):
            if (x // square + y // square) % 2:
                draw.rectangle((x, y, x + square - 1, y + square - 1), fill=(211, 211, 211, 255))
    return image


def make_contact_sheet(states: dict[str, list[Image.Image]], path: Path) -> None:
    label_height = 24
    canvas = Image.new("RGBA", (ATLAS_SIZE[0], ROWS * (CELL_H + label_height)), (18, 18, 18, 255))
    draw = ImageDraw.Draw(canvas)
    for row, (state, used_count) in enumerate(STATE_ORDER):
        top = row * (CELL_H + label_height)
        draw.text((7, top + 5), f"row {row}: {state} ({used_count} frames)", fill=(255, 255, 255, 255))
        frames = states[state]
        for column in range(COLS):
            x = column * CELL_W
            y = top + label_height
            cell = checker((CELL_W, CELL_H))
            if column < len(frames):
                cell.alpha_composite(frames[column])
                border = (27, 198, 118, 255)
            else:
                border = (220, 70, 70, 255)
            canvas.alpha_composite(cell, (x, y))
            draw.rectangle((x, y, x + CELL_W - 1, y + CELL_H - 1), outline=border, width=1)
            draw.text((x + 5, y + 4), str(column), fill=(25, 25, 25, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(path, optimize=True)


def make_library_sheet(library: dict[str, list[Image.Image]], path: Path) -> None:
    label_height = 24
    width = 6 * CELL_W
    height = len(LIBRARY_ACTIONS) * (CELL_H + label_height)
    canvas = Image.new("RGBA", (width, height), (18, 18, 18, 255))
    draw = ImageDraw.Draw(canvas)
    for row, action in enumerate(LIBRARY_ACTIONS):
        top = row * (CELL_H + label_height)
        draw.text((7, top + 5), action, fill=(255, 255, 255, 255))
        for column, frame in enumerate(library[action]):
            x = column * CELL_W
            y = top + label_height
            cell = checker((CELL_W, CELL_H))
            cell.alpha_composite(frame)
            canvas.alpha_composite(cell, (x, y))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(path, optimize=True)


def build() -> None:
    for output in (BUILD, FINAL, QA):
        if not output.resolve().is_relative_to(DRAFT.resolve()):
            raise ValueError(f"Draft build attempted to escape the draft box: {output}")
    for directory in (NORMALIZED, LIBRARY, FINAL, QA / "state-previews", QA / "library-previews"):
        directory.mkdir(parents=True, exist_ok=True)

    waddle_sheet = split_sheet(SOURCES / "waddle-right-alpha.png", 1, 8)
    status_sheet = split_sheet(SOURCES / "status-actions-alpha.png", 4, 8)
    library_row_boundaries = find_transparent_row_boundaries(LIBRARY_SOURCE, 5)
    library_sheet = split_sheet(LIBRARY_SOURCE, 5, 6, y_boundaries=library_row_boundaries)

    waddle_right = normalize_sequence(waddle_sheet[0], max_width=172, max_height=176)
    waddle_left = [ImageOps.mirror(frame) for frame in waddle_right]

    idle_library = {
        action: normalize_library_sequence(frames)
        for action, frames in zip(LIBRARY_ACTIONS, library_sheet, strict=True)
    }
    neutral_anchor = fit_library_neutral_anchor(Image.open(LIBRARY_NEUTRAL_SOURCE).convert("RGBA"))
    for frames in idle_library.values():
        frames[0] = neutral_anchor.copy()
        frames[-1] = neutral_anchor.copy()

    failed = normalize_sequence(status_sheet[0], max_width=168, max_height=184)
    waiting_all = normalize_sequence(status_sheet[1], max_width=168, max_height=184)
    working_all = normalize_sequence(status_sheet[2], max_width=190, max_height=192)
    success_all = normalize_sequence(status_sheet[3], max_width=168, max_height=184)
    waiting = [waiting_all[index] for index in (0, 1, 2, 3, 5, 7)]
    working = [working_all[index] for index in (0, 1, 2, 3, 5, 7)]
    success = [success_all[index] for index in (0, 1, 2, 3, 5, 7)]

    waving = normalize_sequence(load_existing_sequence("waving", 4), max_width=168, max_height=184)
    jumping_base = normalize_sequence(load_existing_sequence("jumping", 5), max_width=168, max_height=180)
    jumping = [shift_frame(frame, offset) for frame, offset in zip(jumping_base, (0, -4, -12, -5, 0), strict=True)]

    gaze = make_gaze_frames(idle_library["stretch"][0])
    states = {
        "idle": idle_library["stretch"],
        "running-right": waddle_right,
        "running-left": waddle_left,
        "waving": waving,
        "jumping": jumping,
        "failed": failed,
        "waiting": waiting,
        "running": working,
        "review": success,
        "gaze-00-to-07": gaze[:8],
        "gaze-08-to-15": gaze[8:],
    }

    for state, frames in states.items():
        save_sequence(state, frames, NORMALIZED)
        make_preview(QA / "state-previews" / f"{state}.webp", frames)
    for action, frames in idle_library.items():
        save_sequence(action, frames, LIBRARY)
        make_preview(QA / "library-previews" / f"{action}.webp", frames, duration=280)

    atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
    for row, (state, _) in enumerate(STATE_ORDER):
        for column, frame in enumerate(states[state]):
            atlas.alpha_composite(frame, (column * CELL_W, row * CELL_H))
    atlas = zero_transparent_rgb(atlas)
    atlas.save(FINAL / "spritesheet.png", optimize=True)
    atlas.save(FINAL / "spritesheet.webp", format="WEBP", lossless=True, method=6, exact=True)

    pet_manifest = {
        "status": "draft",
        "installable": False,
        "id": "capybara-lulu-v2",
        "displayName": "水豚噜噜 · 连贯版",
        "description": "A coherent, gentle CapyLulu Codex pet with real waddling, themed status reactions, and 16-direction gaze.",
        "spriteVersionNumber": 2,
        "spritesheetPath": "spritesheet.webp",
    }
    (FINAL / "pet.draft.json").write_text(
        json.dumps(pet_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    make_contact_sheet(states, QA / "contact-sheet.png")
    make_library_sheet(idle_library, QA / "animation-library.png")

    cells = []
    errors = []
    warnings = []
    detached_element_components = []
    gold_reference = Image.open(LIBRARY_GOLD_REFERENCE).convert("RGBA")
    gold_box = alpha_bbox(gold_reference)
    neutral_box = alpha_bbox(neutral_anchor)
    if gold_box is None:
        errors.append("V1 gold reference is empty")
    if neutral_box is None:
        errors.append("gold-aligned neutral anchor is empty")
    else:
        neutral_width = neutral_box[2] - neutral_box[0]
        neutral_height = neutral_box[3] - neutral_box[1]
        if (
            neutral_width != LIBRARY_NEUTRAL_WIDTH
            or neutral_height != LIBRARY_NEUTRAL_HEIGHT
            or neutral_box[3] != LIBRARY_GROUND_Y
        ):
            errors.append(
                "gold-aligned neutral anchor must be "
                f"{LIBRARY_NEUTRAL_WIDTH}x{LIBRARY_NEUTRAL_HEIGHT} on ground line "
                f"{LIBRARY_GROUND_Y}: {neutral_box}"
            )
    if gold_box is not None and neutral_box is not None and neutral_box != gold_box:
        errors.append(f"neutral bbox must match V1 gold bbox {gold_box}: {neutral_box}")
    gold_eye_centers = find_eye_centers(gold_reference)
    neutral_eye_centers = find_eye_centers(neutral_anchor)
    eye_center_drifts = [
        ((neutral_x - gold_x) ** 2 + (neutral_y - gold_y) ** 2) ** 0.5
        for (gold_x, gold_y), (neutral_x, neutral_y) in zip(
            gold_eye_centers,
            neutral_eye_centers,
            strict=True,
        )
    ]
    if any(drift > FACE_ANCHOR_MAX_DRIFT for drift in eye_center_drifts):
        errors.append(
            "neutral eye centers drift too far from V1 gold: "
            f"{eye_center_drifts} > {FACE_ANCHOR_MAX_DRIFT}"
        )
    for action, frames in idle_library.items():
        if frames[0].tobytes() != neutral_anchor.tobytes() or frames[-1].tobytes() != neutral_anchor.tobytes():
            errors.append(f"{action} must share the canonical neutral first and last frame")
        if any(set(frame.getchannel("A").get_flattened_data()) - {0, 255} for frame in frames):
            errors.append(f"{action} contains soft alpha pixels")
        if any((box := alpha_bbox(frame)) is None or box[3] != LIBRARY_GROUND_Y for frame in frames):
            errors.append(f"{action} does not consistently land on ground line {LIBRARY_GROUND_Y}")
    for (action, frame_index), check in DETACHED_ELEMENT_CHECKS.items():
        component_areas = sorted(
            (len(component) for component in alpha_components(idle_library[action][frame_index])),
            reverse=True,
        )
        significant_count = sum(area >= check["minimum_area"] for area in component_areas)
        detached_element_components.append(
            {
                "action": action,
                "frame": frame_index + 1,
                "minimum_area": check["minimum_area"],
                "minimum_components": check["minimum_components"],
                "significant_components": significant_count,
                "component_areas": component_areas,
            }
        )
        if significant_count < check["minimum_components"]:
            errors.append(
                f"{action}[{frame_index}] lost detached action elements: "
                f"expected at least {check['minimum_components']} components with area "
                f">= {check['minimum_area']}, found {significant_count}"
            )
    if len({frame.tobytes() for frame in gaze}) != 16:
        errors.append("16-direction gaze generation produced duplicate frames")
    for row, (state, used_count) in enumerate(STATE_ORDER):
        for column in range(COLS):
            cell = atlas.crop((column * CELL_W, row * CELL_H, (column + 1) * CELL_W, (row + 1) * CELL_H))
            bbox = alpha_bbox(cell)
            used = column < used_count
            if used and bbox is None:
                errors.append(f"{state}[{column}] is empty")
            if not used and bbox is not None:
                errors.append(f"{state}[{column}] should be transparent")
            if bbox is not None:
                left, top, right, bottom = bbox
                if left < 8 or right > CELL_W - 8 or top < 4 or bottom > CELL_H - 4:
                    warnings.append(f"{state}[{column}] approaches the cell safety edge: {bbox}")
            cells.append({"state": state, "row": row, "column": column, "used": used, "bbox": bbox})

    validation = {
        "ok": not errors,
        "status": "draft",
        "installable": False,
        "release_input": False,
        "sprite_version": 2,
        "format": "RGBA PNG + lossless WebP",
        "width": atlas.width,
        "height": atlas.height,
        "cell_size": [CELL_W, CELL_H],
        "errors": errors,
        "warnings": sorted(set(warnings)),
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
        "gold_alignment": {
            "reference": str(LIBRARY_GOLD_REFERENCE.relative_to(ROOT)),
            "reference_sha256": sha256(LIBRARY_GOLD_REFERENCE),
            "reference_bbox": gold_box,
            "reference_eye_centers": gold_eye_centers,
            "library_source_sha256": sha256(LIBRARY_SOURCE),
            "neutral_source_sha256": sha256(LIBRARY_NEUTRAL_SOURCE),
            "neutral_bbox": neutral_box,
            "neutral_eye_centers": neutral_eye_centers,
            "eye_center_drifts": eye_center_drifts,
            "max_eye_center_drift": FACE_ANCHOR_MAX_DRIFT,
            "neutral_width": LIBRARY_NEUTRAL_WIDTH,
            "neutral_height": LIBRARY_NEUTRAL_HEIGHT,
            "ground_y": LIBRARY_GROUND_Y,
            "max_action_width": LIBRARY_ACTION_MAX_WIDTH,
            "max_action_height": LIBRARY_ACTION_MAX_HEIGHT,
        },
        "detached_element_components": detached_element_components,
    }
    (FINAL / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    build_manifest = {
        "schema": 1,
        "status": "draft",
        "installable": False,
        "release_input": False,
        "atlas": {"columns": COLS, "rows": ROWS, "cell": [CELL_W, CELL_H], "sprite_version": 2},
        "sources": {
            "waddle": "sources/waddle-right-alpha.png",
            "status_actions": "sources/status-actions-alpha.png",
            "idle_library": str(LIBRARY_SOURCE.relative_to(PET)),
            "idle_library_neutral": str(LIBRARY_NEUTRAL_SOURCE.relative_to(PET)),
            "idle_library_original": "sources/idle-library-alpha.png",
            "gold_reference": str(LIBRARY_GOLD_REFERENCE.relative_to(PET)),
            "legacy_waving": "sources/legacy-v1/waving/",
            "legacy_jumping": "sources/legacy-v1/jumping/",
        },
        "states": {state: {"row": row, "frames": count} for row, (state, count) in enumerate(STATE_ORDER)},
        "animation_library": {action: 6 for action in LIBRARY_ACTIONS},
        "gold_alignment": {
            "reference_sha256": sha256(LIBRARY_GOLD_REFERENCE),
            "reference_bbox": gold_box,
            "reference_eye_centers": gold_eye_centers,
            "library_source_sha256": sha256(LIBRARY_SOURCE),
            "neutral_source_sha256": sha256(LIBRARY_NEUTRAL_SOURCE),
            "neutral_bbox": neutral_box,
            "neutral_eye_centers": neutral_eye_centers,
            "eye_center_drifts": eye_center_drifts,
            "max_eye_center_drift": FACE_ANCHOR_MAX_DRIFT,
            "neutral_width": LIBRARY_NEUTRAL_WIDTH,
            "neutral_height": LIBRARY_NEUTRAL_HEIGHT,
            "ground_y": LIBRARY_GROUND_Y,
            "max_action_width": LIBRARY_ACTION_MAX_WIDTH,
            "max_action_height": LIBRARY_ACTION_MAX_HEIGHT,
            "shared_neutral_frames": [0, 5],
            "source_row_boundaries": library_row_boundaries,
        },
        "continuity_rules": [
            "Every native state begins near the relaxed standing anchor.",
            "Every native state ends near the relaxed standing anchor before Codex returns to idle.",
            "The fruit follows body motion with mild inertia and returns to center.",
            "All standing actions share a fixed ground line and action-level scale.",
            "Props appear only inside theme-relevant state stories and are put away before the final frame.",
        ],
    }
    (BUILD / "manifest.json").write_text(json.dumps(build_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Built draft preview {FINAL.relative_to(ROOT)}")
    print(f"Atlas: {atlas.width}x{atlas.height}, spriteVersionNumber=2")
    print(f"Validation: {'OK' if not errors else 'FAILED'} ({len(errors)} errors, {len(set(warnings))} warnings)")


if __name__ == "__main__":
    build()
