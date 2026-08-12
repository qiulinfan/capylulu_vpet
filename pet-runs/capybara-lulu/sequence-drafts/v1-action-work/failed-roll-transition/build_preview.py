from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
PET = HERE.parents[2]
FAILED = PET / "official-frames-v1" / "failed"
TRANSITIONS = HERE / "normalized"

TRANSITION_DURATIONS_MS = [180, 120, 120, 360, 120, 120]
FULL_DURATIONS_MS = [180, 180, 180, 180, 180, 120, 120, 360, 120, 120, 180, 180]


def load(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    image.putdata(
        [
            (red, green, blue, alpha) if alpha else (0, 0, 0, 0)
            for red, green, blue, alpha in image.get_flattened_data()
        ]
    )
    return image


def rgba_rmse(left: Image.Image, right: Image.Image) -> float:
    left_bytes = left.tobytes()
    right_bytes = right.tobytes()
    squared_error = sum((a - b) ** 2 for a, b in zip(left_bytes, right_bytes, strict=True))
    return math.sqrt(squared_error / len(left_bytes)) / 255


def save_gif(path: Path, frames: list[Image.Image], durations: list[int]) -> None:
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


def metrics(frames: list[Image.Image]) -> dict[str, object]:
    transitions = [
        rgba_rmse(left, right)
        for left, right in zip(frames, frames[1:], strict=False)
    ]
    return {
        "transition_rmse": transitions,
        "loop_seam_rmse": rgba_rmse(frames[-1], frames[0]),
        "max_transition_rmse": max(transitions),
    }


def main() -> None:
    prone = load(FAILED / "failed-05.png")
    side = load(FAILED / "failed-06.png")
    transition_a = load(TRANSITIONS / "failed-roll-transition-01.png")
    transition_b = load(TRANSITIONS / "failed-roll-transition-02.png")

    transition_frames = [prone, transition_a, transition_b, side, transition_b, transition_a]
    save_gif(HERE / "failed-roll-preview.gif", transition_frames, TRANSITION_DURATIONS_MS)

    full_paths = [FAILED / f"failed-{index:02d}.png" for index in range(1, 6)]
    full_frames = [load(path) for path in full_paths]
    full_frames.extend([transition_a, transition_b, side, transition_b, transition_a])
    full_frames.extend([load(FAILED / "failed-07.png"), load(FAILED / "failed-08.png")])
    save_gif(HERE / "failed-full-candidate.gif", full_frames, FULL_DURATIONS_MS)

    report = {
        "transition_preview": {
            "sequence": ["prone", "transition-a", "transition-b", "side", "transition-b", "transition-a"],
            "frame_durations_ms": TRANSITION_DURATIONS_MS,
            **metrics(transition_frames),
        },
        "full_candidate": {
            "frame_count": len(full_frames),
            "frame_durations_ms": FULL_DURATIONS_MS,
            "cycle_duration_ms": sum(FULL_DURATIONS_MS),
            **metrics(full_frames),
        },
    }
    (HERE / "preview-validation.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
