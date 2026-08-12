from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
CANVAS_SIZE = (192, 208)
MAX_CONTENT_SIZE = (180, 184)
BOTTOM_ANCHOR = 198

ACTIONS = {
    "looking-around": {
        "source": ROOT / "looking-around" / "contact-sheet-alpha-clean.png",
        "durations": [500, 420, 180, 500, 500, 650],
    },
}

WORKING_SOURCES = {
    "approved_prefix": ROOT / "working" / "contact-sheet-alpha.png",
    "painting_continuation": ROOT / "working" / "continuation-contact-sheet-alpha.png",
    "page_transition": ROOT / "working" / "page-transition-contact-sheet-alpha.png",
}
WORKING_DURATIONS = [
    180,
    180,
    180,
    180,
    180,
    300,
    180,
    180,
    180,
    500,
    180,
    180,
    180,
    220,
    300,
]
APPROVED_WORKING_PREFIX_SHA256 = [
    "f018a39570742a3b165d1bae4a4c235fce2d1edc4a7ffc06bae778966f5095e9",
    "21079fb6a49181d6850d2d3db2180f84c51dc9176aa5ab75627bdcc2a31d6a72",
    "a25db3896eb79d9fc7d3fa5c04179b40c201b5cfe0a4c2a02da47d12f56386aa",
    "21026a717333ae7809896b6eb94db25dc0155029fa30b48b181ea1a1ec135dfe",
    "78af68a42acdfe77152c81e37a8bd0789f6a2f7251c51eaf9bf6a1e46b7faa54",
    "30d18d6d1e85c4e528bcc60111a08aedd332019cfbd0630ea194d3bb8ea48ca0",
]


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


def connected_components(image: Image.Image) -> list[tuple[int, tuple[int, int, int, int]]]:
    alpha = image.getchannel("A")
    width, height = image.size
    pixels = alpha.load()
    seen = bytearray(width * height)
    components: list[tuple[int, tuple[int, int, int, int]]] = []

    for y in range(height):
        for x in range(width):
            index = y * width + x
            if seen[index] or pixels[x, y] == 0:
                continue
            queue = deque([(x, y)])
            seen[index] = 1
            size = 0
            left = right = x
            top = bottom = y
            while queue:
                current_x, current_y = queue.popleft()
                size += 1
                left = min(left, current_x)
                right = max(right, current_x)
                top = min(top, current_y)
                bottom = max(bottom, current_y)
                for neighbor_x, neighbor_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if not (0 <= neighbor_x < width and 0 <= neighbor_y < height):
                        continue
                    neighbor_index = neighbor_y * width + neighbor_x
                    if seen[neighbor_index] or pixels[neighbor_x, neighbor_y] == 0:
                        continue
                    seen[neighbor_index] = 1
                    queue.append((neighbor_x, neighbor_y))
            components.append((size, (left, top, right + 1, bottom + 1)))
    return components


def extract_poses(source: Image.Image, expected_count: int) -> list[Image.Image]:
    components = sorted(connected_components(source), reverse=True)[:expected_count]
    if (
        len(components) != expected_count
        or min(size for size, _ in components) < 10_000
    ):
        raise ValueError(f"Expected {expected_count} large, isolated pose components")
    ordered = sorted(
        components,
        key=lambda item: (
            ((item[1][1] + item[1][3]) // 2) // (source.height // 2),
            (item[1][0] + item[1][2]) // 2,
        ),
    )
    return [source.crop(bounds) for _, bounds in ordered]


def normalize_poses(poses: list[Image.Image]) -> list[Image.Image]:
    max_width = max(pose.width for pose in poses)
    max_height = max(pose.height for pose in poses)
    scale = min(MAX_CONTENT_SIZE[0] / max_width, MAX_CONTENT_SIZE[1] / max_height)
    normalized: list[Image.Image] = []
    for pose in poses:
        size = (
            max(1, round(pose.width * scale)),
            max(1, round(pose.height * scale)),
        )
        resized = pose.resize(size, Image.Resampling.LANCZOS)
        frame = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        position = (
            (CANVAS_SIZE[0] - resized.width) // 2,
            BOTTOM_ANCHOR - resized.height,
        )
        frame.alpha_composite(resized, position)
        normalized.append(zero_transparent_rgb(frame))
    return normalized


def write_gif(path: Path, frames: list[Image.Image], durations: list[int]) -> None:
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


def write_frames(action: str, frames: list[Image.Image]) -> list[Path]:
    frame_dir = ROOT / action / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    frame_paths: list[Path] = []
    for index, frame in enumerate(frames, start=1):
        frame_path = frame_dir / f"{action}-{index:02d}.png"
        frame.save(frame_path)
        frame_paths.append(frame_path)
    expected_paths = set(frame_paths)
    for stale_path in frame_dir.glob(f"{action}-*.png"):
        if stale_path not in expected_paths:
            stale_path.unlink()
    return frame_paths


def action_report(
    *,
    frames: list[Image.Image],
    frame_paths: list[Path],
    durations: list[int],
    gif_path: Path,
) -> dict[str, object]:
    return {
        "frames": [str(path.relative_to(ROOT)) for path in frame_paths],
        "frame_sha256": [sha256(path) for path in frame_paths],
        "frame_durations_ms": durations,
        "gif": str(gif_path.relative_to(ROOT)),
        "gif_sha256": sha256(gif_path),
        "alpha_areas": [
            sum(frame.getchannel("A").get_flattened_data()) / 255
            for frame in frames
        ],
    }


def build() -> dict[str, object]:
    report: dict[str, object] = {"ok": True, "canvas_size": list(CANVAS_SIZE), "actions": {}}

    approved_source = Image.open(WORKING_SOURCES["approved_prefix"]).convert("RGBA")
    continuation_source = Image.open(WORKING_SOURCES["painting_continuation"]).convert(
        "RGBA"
    )
    page_source = Image.open(WORKING_SOURCES["page_transition"]).convert("RGBA")

    approved_frames = normalize_poses(extract_poses(approved_source, 6))
    continuation_frames = normalize_poses(extract_poses(continuation_source, 6))
    page_frames = normalize_poses(extract_poses(page_source, 4))
    working_frames = (
        approved_frames
        + continuation_frames[:4]
        + page_frames
        + continuation_frames[5:]
    )
    if len(working_frames) != len(WORKING_DURATIONS):
        raise ValueError("Working frame and duration counts do not match")

    working_frame_paths = write_frames("working", working_frames)
    working_prefix_hashes = [sha256(path) for path in working_frame_paths[:6]]
    if working_prefix_hashes != APPROVED_WORKING_PREFIX_SHA256:
        raise ValueError("Approved working prefix changed")
    working_gif_path = ROOT / "working" / "working-extended-candidate.gif"
    write_gif(working_gif_path, working_frames, WORKING_DURATIONS)
    working_report = action_report(
        frames=working_frames,
        frame_paths=working_frame_paths,
        durations=WORKING_DURATIONS,
        gif_path=working_gif_path,
    )
    working_report.update(
        {
            "sources": {
                name: str(path.relative_to(ROOT)) for name, path in WORKING_SOURCES.items()
            },
            "source_sha256": {
                name: sha256(path) for name, path in WORKING_SOURCES.items()
            },
            "approved_prefix_frames": 6,
            "approved_prefix_unchanged": True,
            "assembly": [
                "approved-prefix:1-6",
                "painting-continuation:1-4",
                "page-transition:1-4",
                "painting-continuation:6",
            ],
        }
    )
    report["actions"]["working"] = working_report

    for action, config in ACTIONS.items():
        source_path = config["source"]
        durations = config["durations"]
        if not isinstance(source_path, Path) or not isinstance(durations, list):
            raise TypeError(f"Invalid configuration for {action}")
        source = Image.open(source_path).convert("RGBA")
        frames = normalize_poses(extract_poses(source, 6))
        output_dir = ROOT / action
        frame_paths = write_frames(action, frames)
        gif_path = output_dir / f"{action}-candidate.gif"
        write_gif(gif_path, frames, durations)
        item = action_report(
            frames=frames,
            frame_paths=frame_paths,
            durations=durations,
            gif_path=gif_path,
        )
        item.update({
            "source": str(source_path.relative_to(ROOT)),
            "source_sha256": sha256(source_path),
        })
        report["actions"][action] = item
    report_path = ROOT / "validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
