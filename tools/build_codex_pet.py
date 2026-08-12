from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, features

from build_action_gifs import (
    build as build_action_gifs,
    load_action,
    load_manifest,
    sha256,
    zero_transparent_rgb,
)


ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "pet-runs" / "capybara-lulu"
MANIFEST = PET / "official-frames-v1-manifest.json"
FINAL = PET / "final"
CONTACT_SHEET = PET / "qa" / "codex-adapter-contact-sheet.png"

PET_ID = "capybara-lulu"
CELL_SIZE = (192, 208)
ATLAS_COLUMNS = 8
ATLAS_ROWS = 9
ATLAS_SIZE = (ATLAS_COLUMNS * CELL_SIZE[0], ATLAS_ROWS * CELL_SIZE[1])
SPRITE_VERSION_NUMBER = 1
CODEX_APP_VERSION = "26.803.41515"
CODEX_REQUIRED_FRAMES_BY_ROW = [6, 8, 8, 4, 5, 8, 6, 6, 6]


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


def load_adapter_rows() -> tuple[
    list[list[Image.Image]], list[list[Path]], dict[str, dict[str, object]]
]:
    states, _ = load_manifest()
    loaded: dict[str, tuple[list[Image.Image], list[Path]]] = {}
    for row in ADAPTER_ROWS:
        if row.master_state in loaded:
            continue
        entry = states.get(row.master_state)
        if not isinstance(entry, dict):
            raise ValueError(f"Missing master action: {row.master_state}")
        frames, paths, _ = load_action(row.master_state, entry)
        loaded[row.master_state] = (frames, paths)

    idle_frames = loaded["idle"][0]
    failed_frames = loaded["failed"][0]
    if len(idle_frames) != len(failed_frames) or any(
        idle.tobytes() != failed.tobytes()
        for idle, failed in zip(idle_frames, failed_frames, strict=True)
    ):
        raise ValueError("Idle must exactly alias the complete failed sleeping loop")

    selected_frames: list[list[Image.Image]] = []
    selected_paths: list[list[Path]] = []
    row_report: dict[str, dict[str, object]] = {}
    for row_index, row in enumerate(ADAPTER_ROWS):
        frames, paths = loaded[row.master_state]
        indices = [number - 1 for number in row.master_frame_numbers]
        if any(index < 0 or index >= len(frames) for index in indices):
            raise ValueError(f"{row.runtime_state}: adapter selection escaped master frames")
        selected_frames.append([frames[index].copy() for index in indices])
        selected_paths.append([paths[index] for index in indices])
        row_report[row.runtime_state] = {
            "row_index": row_index,
            "master_state": row.master_state,
            "master_frame_numbers": list(row.master_frame_numbers),
            "source_frames": [str(paths[index].relative_to(ROOT)) for index in indices],
            "source_frame_sha256": [sha256(paths[index]) for index in indices],
            "note": row.note,
        }
    return selected_frames, selected_paths, row_report


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

    rows, _, row_report = load_adapter_rows()
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
