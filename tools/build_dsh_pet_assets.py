from __future__ import annotations

"""Build the compact CapyLulu sprite atlas + manifest for the DeepSeek Harness
web pet plugin.

Crops the five states the DSH pet uses from the shipped Codex adapter atlas
(pet-runs/capybara-lulu/final/spritesheet.webp), which already contains the
approved frame selections and the size-normalized running loop:

    row 0 idle    <- master idle  frames (1, 4, 6, 8, 10, 12) of the sleeping loop
    row 1 wave    <- master waving frames (1..4) pure-wave excerpt
    row 2 failed  <- master failed frames (1, 4, 6, 7, 8, 9, 10, 12) sleeping roll
    row 3 waiting <- master waiting frames (1..6)
    row 4 running <- master running frames (1, 6, 8, 10, 13, 15) normalized work loop

Outputs (under dsh-plugin/capylulu-pet/assets/):
    atlas.webp            lossless WebP atlas, 8 columns x 5 rows of 192x208 cells
    atlas.png             lossless PNG twin (fallback / diffing)
    manifest.json         cell size, per-state row/column/count/durations/meaning
    contact-sheet.png     labeled preview for the plugin README
"""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, features


ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "pet-runs" / "capybara-lulu"
MANIFEST_PATH = PET / "official-frames-v1-manifest.json"
FINAL_ATLAS = PET / "final" / "spritesheet.webp"
OUT_DIR = ROOT / "dsh-plugin" / "capylulu-pet" / "assets"

CELL = (192, 208)
COLUMNS = 8

# (dsh state, codex atlas row, master manifest state, selected master frame numbers)
# The running row carries the size-normalized work loop: the Codex adapter
# replaced the master frames with normalize_running_sequence output, so those
# cells do not byte-match the official master files (comparison is skipped
# via compare_source=False and the normalization report is cited instead).
ADAPTER = (
    ("idle", 0, "idle", (1, 4, 6, 8, 10, 12), "soft sleeping rest", True),
    ("wave", 3, "waving", (1, 2, 3, 4), "four-frame pure-wave greeting excerpt", True),
    ("failed", 5, "failed", (1, 4, 6, 7, 8, 9, 10, 12), "soft failure/rest sleeping roll", True),
    ("waiting", 6, "waiting", (1, 2, 3, 4, 5, 6), "healing unicorn-hug waiting loop", True),
    (
        "running",
        7,
        "running",
        (1, 6, 8, 10, 13, 15),
        "focused work loop: ink shrimp, page change, fresh sheet",
        False,
    ),
)


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


def build() -> dict[str, object]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    states = manifest["states"]
    if not features.check("webp"):
        raise RuntimeError("Pillow was built without WebP support")
    if not FINAL_ATLAS.exists():
        raise FileNotFoundError(f"Codex adapter atlas missing: {FINAL_ATLAS}")

    atlas = Image.open(FINAL_ATLAS).convert("RGBA")
    if atlas.size != (COLUMNS * CELL[0], 9 * CELL[1]):
        raise ValueError(f"Unexpected Codex atlas size: {atlas.size}")

    rows: list[list[Image.Image]] = []
    manifest_states: dict[str, object] = {}
    for row_index, (dsh_state, codex_row, master_state, frame_numbers, meaning, compare) in enumerate(
        ADAPTER
    ):
        entry = states[master_state]
        master_frames = entry["frames"]
        master_durations = entry["frame_durations_ms"]
        frames: list[Image.Image] = []
        durations: list[int] = []
        for column_index, frame_number in enumerate(frame_numbers):
            cell = atlas.crop(
                (
                    column_index * CELL[0],
                    codex_row * CELL[1],
                    (column_index + 1) * CELL[0],
                    (codex_row + 1) * CELL[1],
                )
            )
            if compare:
                frame_path = PET / master_frames[frame_number - 1]
                if not frame_path.exists():
                    raise FileNotFoundError(f"{dsh_state}: missing master frame {frame_path}")
                expected = Image.open(frame_path).convert("RGBA")
                if expected.size != CELL:
                    raise ValueError(f"{dsh_state} frame {frame_number}: unexpected size {expected.size}")
                if cell.tobytes() != expected.tobytes():
                    raise ValueError(
                        f"{dsh_state} cell {frame_number} differs from official master frame"
                    )
            elif cell.getchannel("A").getbbox() is None:
                raise ValueError(f"{dsh_state} cell {frame_number}: fully transparent (normalized source)")
            frames.append(cell)
            durations.append(int(master_durations[frame_number - 1]))
        rows.append(frames)
        manifest_states[dsh_state] = {
            "row": row_index,
            "column": 0,
            "count": len(frames),
            "durations": durations,
            "meaning": meaning,
        }

    sheet = Image.new("RGBA", (COLUMNS * CELL[0], len(rows) * CELL[1]), (0, 0, 0, 0))
    for row_index, frames in enumerate(rows):
        for column_index, frame in enumerate(frames):
            sheet.alpha_composite(frame, (column_index * CELL[0], row_index * CELL[1]))
    sheet = zero_transparent_rgb(sheet)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "atlas.png").write_bytes(
        _encode_png(sheet)
    )
    (OUT_DIR / "atlas.webp").write_bytes(_encode_webp(sheet))
    write_contact_sheet(rows)

    webp = Image.open(OUT_DIR / "atlas.webp")
    if webp.size != sheet.size or webp.convert("RGBA").tobytes() != sheet.tobytes():
        raise ValueError("Lossless WebP must decode pixel-identically to the PNG atlas")

    bundle = {
        "id": "capybara-lulu",
        "displayName": "水豚噜噜",
        "cellSize": list(CELL),
        "columns": COLUMNS,
        "states": manifest_states,
        "source": {
            "codex_adapter_atlas": "pet-runs/capybara-lulu/final/spritesheet.webp",
            "selection": [
                {
                    "dsh_state": dsh_state,
                    "codex_row": codex_row,
                    "master_state": master_state,
                    "master_frame_numbers": list(frame_numbers),
                }
                for dsh_state, codex_row, master_state, frame_numbers, _, _ in ADAPTER
            ],
            "note": "cells cropped from the installed Codex adapter atlas; running cells carry the normalized work loop",
        },
        "atlas_sha256": sha256(OUT_DIR / "atlas.webp"),
        "png_sha256": sha256(OUT_DIR / "atlas.png"),
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Built DSH pet atlas: {sheet.width}x{sheet.height} "
        f"webp={ (OUT_DIR / 'atlas.webp').stat().st_size // 1024 }KiB "
        f"png={ (OUT_DIR / 'atlas.png').stat().st_size // 1024 }KiB"
    )
    return bundle


def _encode_png(image: Image.Image) -> bytes:
    import io

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _encode_webp(image: Image.Image) -> bytes:
    import io

    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", lossless=True, method=6, exact=True)
    return buffer.getvalue()


def write_contact_sheet(rows: list[list[Image.Image]]) -> None:
    thumb = (CELL[0] // 2, CELL[1] // 2)
    label_height = 20
    canvas = Image.new(
        "RGB",
        (COLUMNS * thumb[0], len(rows) * (thumb[1] + label_height)),
        (24, 24, 24),
    )
    draw = ImageDraw.Draw(canvas)
    for row_index, (row, (dsh_state, *_)) in enumerate(zip(rows, ADAPTER, strict=True)):
        top = row_index * (thumb[1] + label_height)
        draw.text((5, top + 4), f"{dsh_state} ({len(row)} frames)", fill=(255, 255, 255))
        for column_index in range(COLUMNS):
            x = column_index * thumb[0]
            y = top + label_height
            if column_index < len(row):
                thumb_image = row[column_index].resize(thumb, Image.Resampling.NEAREST)
                canvas.paste(thumb_image.convert("RGB"), (x, y))
                outline = (27, 198, 118)
            else:
                outline = (90, 90, 90)
            draw.rectangle(
                (x, y, x + thumb[0] - 1, y + thumb[1] - 1),
                outline=outline,
            )
    canvas.save(OUT_DIR / "contact-sheet.png", optimize=True)


if __name__ == "__main__":
    build()
