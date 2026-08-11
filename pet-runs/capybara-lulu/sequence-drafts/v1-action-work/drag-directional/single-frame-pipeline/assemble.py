from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


PIPELINE = Path(__file__).resolve().parent
PET = PIPELINE.parents[3]
CELL_SIZE = (192, 208)
SUBJECT_HEIGHT = 190
FRAME_DURATIONS_MS = [120, 120, 120, 120, 120, 120, 120, 220]

GOLD_OPEN = PIPELINE / "gold" / "gold-neutral-open-192x208.png"
GOLD_CLOSED = (
    PET
    / "sequence-drafts"
    / "v1-action-work"
    / "waving-success-windup"
    / "gold-normal-stand.png"
)
F06_SOURCE = PIPELINE / "inbetweens" / "f06" / "source-magenta-recovery-v2.png"
F06_ALPHA = PIPELINE / "inbetweens" / "f06" / "source-alpha-recovery-v2.png"
F06_GENERATED_NORMALIZED = (
    PIPELINE / "inbetweens" / "f06" / "normalized-recovery-v2-192x208.png"
)
F06_POSE_GUIDE = PIPELINE / "inbetweens" / "f06" / "pose-guide-recovery-v3.png"
F06_SELECTED_SOURCE = (
    PIPELINE / "inbetweens" / "f06" / "source-magenta-poseguided-v3-corrected.png"
)
F06_SELECTED_ALPHA = (
    PIPELINE / "inbetweens" / "f06" / "source-alpha-poseguided-v3.png"
)
F06_NORMALIZED_RAW = (
    PIPELINE / "inbetweens" / "f06" / "normalized-poseguided-v3-raw-192x208.png"
)
F06_NORMALIZED = (
    PIPELINE / "inbetweens" / "f06" / "normalized-poseguided-v3-selected-192x208.png"
)
F03_SELECTED = PIPELINE / "keyframes" / "f03" / "normalized-corrected-192x208.png"
F07_SELECTED = (
    PIPELINE / "keyframes" / "f07" / "normalized-gold-blink-selected-192x208.png"
)
F08_SELECTED = (
    PIPELINE / "keyframes" / "f08" / "normalized-gold-settle-selected-192x208.png"
)
OUTPUT = PIPELINE / "assembled-v4"


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


def remove_magenta_background(source: Path, destination: Path) -> None:
    """Create a binary-alpha sprite without soft despill or recoloring Lulu."""
    image = Image.open(source).convert("RGB")
    pixels = []
    for red, green, blue in image.get_flattened_data():
        is_magenta = (
            red >= 145
            and blue >= 135
            and red >= green * 1.7
            and blue >= green * 1.7
            and abs(red - blue) <= 90
        )
        pixels.append((0, 0, 0, 0) if is_magenta else (red, green, blue, 255))
    output = Image.new("RGBA", image.size, (0, 0, 0, 0))
    output.putdata(pixels)
    destination.parent.mkdir(parents=True, exist_ok=True)
    zero_transparent_rgb(output).save(destination, optimize=True)


def normalize(source: Path, destination: Path, top: int) -> None:
    image = zero_transparent_rgb(Image.open(source))
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"empty source: {source}")
    sprite = image.crop(bbox)
    width = round(sprite.width * SUBJECT_HEIGHT / sprite.height)
    sprite = sprite.resize((width, SUBJECT_HEIGHT), Image.Resampling.NEAREST)
    if width > CELL_SIZE[0]:
        raise ValueError(f"normalized sprite is too wide: {width}px")
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    frame.alpha_composite(sprite, ((CELL_SIZE[0] - width) // 2, top))
    destination.parent.mkdir(parents=True, exist_ok=True)
    zero_transparent_rgb(frame).save(destination, optimize=True)


def shift(source: Path, destination: Path, dy: int) -> None:
    image = zero_transparent_rgb(Image.open(source))
    if image.size != CELL_SIZE:
        raise ValueError(f"gold frame must be {CELL_SIZE}: {source}")
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    frame.alpha_composite(image, (0, dy))
    destination.parent.mkdir(parents=True, exist_ok=True)
    zero_transparent_rgb(frame).save(destination, optimize=True)


def widen_subject(source: Path, destination: Path, factor: float) -> None:
    """Restore gold horizontal mass after pose transfer without changing height."""
    image = zero_transparent_rgb(Image.open(source))
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"empty source: {source}")
    left, top, right, bottom = bbox
    sprite = image.crop(bbox)
    sprite = sprite.resize(
        (round(sprite.width * factor), sprite.height),
        Image.Resampling.NEAREST,
    )
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    frame.alpha_composite(sprite, ((CELL_SIZE[0] - sprite.width) // 2, top))
    destination.parent.mkdir(parents=True, exist_ok=True)
    zero_transparent_rgb(frame).save(destination, optimize=True)


def make_gold_blink(destination: Path, dy: int) -> None:
    """Close both eyes together while retaining the open gold's body and mouth."""
    opened = zero_transparent_rgb(Image.open(GOLD_OPEN))
    closed = zero_transparent_rgb(Image.open(GOLD_CLOSED))
    opened_pixels = opened.load()
    closed_pixels = closed.load()
    for box in ((52, 58, 93, 90), (101, 58, 142, 90)):
        left, top, right, bottom = box
        for y in range(top, bottom):
            for x in range(left, right):
                source = opened_pixels[x, y]
                replacement = closed_pixels[x, y]
                if max(abs(source[channel] - replacement[channel]) for channel in range(4)) >= 8:
                    opened_pixels[x, y] = replacement
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    frame.alpha_composite(opened, (0, dy))
    destination.parent.mkdir(parents=True, exist_ok=True)
    zero_transparent_rgb(frame).save(destination, optimize=True)


def make_gold_recovery(destination: Path, angle: float = -12.0) -> None:
    """Rigidly ease the exact open gold toward upright without rescaling it."""
    gold = zero_transparent_rgb(Image.open(GOLD_OPEN))
    bbox = gold.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("open gold is empty")
    sprite = gold.crop(bbox).rotate(
        angle,
        resample=Image.Resampling.NEAREST,
        expand=True,
        fillcolor=(0, 0, 0, 0),
    )
    rotated_bbox = sprite.getchannel("A").getbbox()
    if rotated_bbox is None:
        raise ValueError("rotated open gold is empty")
    sprite = zero_transparent_rgb(sprite.crop(rotated_bbox))
    if sprite.width > CELL_SIZE[0] or sprite.height > CELL_SIZE[1]:
        raise ValueError(f"rotated gold does not fit the runtime cell: {sprite.size}")
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    left = (CELL_SIZE[0] - sprite.width) // 2
    top = round(103 - sprite.height / 2)
    frame.alpha_composite(sprite, (left, top))
    destination.parent.mkdir(parents=True, exist_ok=True)
    zero_transparent_rgb(frame).save(destination, optimize=True)


def rotate_frame_rigid(source: Path, destination: Path, angle: float) -> None:
    """Make a one-frame pose guide without changing the source sprite's scale."""
    image = zero_transparent_rgb(Image.open(source))
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"pose guide source is empty: {source}")
    sprite = image.crop(bbox).rotate(
        angle,
        resample=Image.Resampling.NEAREST,
        expand=True,
        fillcolor=(0, 0, 0, 0),
    )
    bbox = sprite.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"rotated pose guide is empty: {source}")
    sprite = zero_transparent_rgb(sprite.crop(bbox))
    frame = Image.new("RGBA", CELL_SIZE, (0, 0, 0, 0))
    frame.alpha_composite(
        sprite,
        ((CELL_SIZE[0] - sprite.width) // 2, round(103 - sprite.height / 2)),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    zero_transparent_rgb(frame).save(destination, optimize=True)


def checker() -> Image.Image:
    image = Image.new("RGBA", CELL_SIZE, (238, 238, 238, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, CELL_SIZE[1], 8):
        for x in range(0, CELL_SIZE[0], 8):
            if (x // 8 + y // 8) % 2:
                draw.rectangle((x, y, x + 7, y + 7), fill=(211, 211, 211, 255))
    return image


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


def build() -> None:
    rotate_frame_rigid(F06_GENERATED_NORMALIZED, F06_POSE_GUIDE, angle=8.0)
    remove_magenta_background(F06_SELECTED_SOURCE, F06_SELECTED_ALPHA)
    normalize(F06_SELECTED_ALPHA, F06_NORMALIZED_RAW, top=6)
    widen_subject(F06_NORMALIZED_RAW, F06_NORMALIZED, factor=1.10)
    # The gold-corrected F3 key supplies the approved dangling-limb silhouette;
    # a rigid ease toward upright makes the final selected recovery in-between.
    rotate_frame_rigid(F03_SELECTED, F06_NORMALIZED, angle=10.0)
    make_gold_blink(F07_SELECTED, dy=-2)
    shift(GOLD_OPEN, F08_SELECTED, dy=-1)

    selected = [
        GOLD_OPEN,
        PIPELINE / "inbetweens" / "f02" / "normalized-rotated-selected-192x208.png",
        PIPELINE / "keyframes" / "f03" / "normalized-corrected-192x208.png",
        PIPELINE / "inbetweens" / "f04" / "normalized-192x208.png",
        PIPELINE / "keyframes" / "f05" / "normalized-corrected-192x208.png",
        F06_NORMALIZED,
        F07_SELECTED,
        F08_SELECTED,
    ]
    right_dir = OUTPUT / "right"
    left_dir = OUTPUT / "left"
    right_dir.mkdir(parents=True, exist_ok=True)
    left_dir.mkdir(parents=True, exist_ok=True)

    right_frames = []
    left_frames = []
    for index, source in enumerate(selected, start=1):
        right = zero_transparent_rgb(Image.open(source))
        if right.size != CELL_SIZE:
            raise ValueError(f"selected frame must be {CELL_SIZE}: {source}")
        if set(right.getchannel("A").get_flattened_data()) - {0, 255}:
            raise ValueError(f"selected frame must use binary alpha: {source}")
        right_path = right_dir / f"running-right-{index:02d}.png"
        left_path = left_dir / f"running-left-{index:02d}.png"
        left = zero_transparent_rgb(right.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        right.save(right_path, optimize=True)
        left.save(left_path, optimize=True)
        right_frames.append(right)
        left_frames.append(left)

    save_gif(OUTPUT / "right-preview.gif", right_frames)
    save_gif(OUTPUT / "left-preview.gif", left_frames)

    strip = Image.new("RGBA", (CELL_SIZE[0] * 8, CELL_SIZE[1]), (0, 0, 0, 0))
    contact = Image.new("RGBA", (CELL_SIZE[0] * 8, CELL_SIZE[1] + 20), (18, 18, 18, 255))
    draw = ImageDraw.Draw(contact)
    for index, frame in enumerate(right_frames):
        x = index * CELL_SIZE[0]
        strip.alpha_composite(frame, (x, 0))
        cell = checker()
        cell.alpha_composite(frame)
        contact.alpha_composite(cell, (x, 20))
        draw.text((x + 4, 4), f"F{index + 1}", fill=(255, 255, 255, 255))
    zero_transparent_rgb(strip).save(OUTPUT / "right-spritesheet-strip.png", optimize=True)
    contact.convert("RGB").save(OUTPUT / "right-contact-sheet.png", optimize=True)

    manifest = {
        "status": "draft-candidate",
        "workflow": [
            "one canonical gold sprite",
            "individual action keyframes",
            "individual in-between frames",
            "deterministic alpha, normalization, mirror, and assembly",
        ],
        "gold_sprite": str(GOLD_OPEN.relative_to(PET)),
        "selected_sources": [str(path.relative_to(PET)) for path in selected],
        "frame_durations_ms": FRAME_DURATIONS_MS,
        "blink_frame": 7,
        "sha256": {
            path.name: sha256(path)
            for path in sorted(right_dir.glob("running-right-*.png"))
        },
    }
    (OUTPUT / "assembly.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
