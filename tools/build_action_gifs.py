from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "pet-runs" / "capybara-lulu"
MANIFEST = PET / "official-frames-v1-manifest.json"
OUTPUT = PET / "qa" / "action-gifs"
VALIDATION = OUTPUT / "validation.json"

EXPECTED_SIZE = (192, 208)
RETIRED_ACTION = "jumping"


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


def rgba_rmse(left: Image.Image, right: Image.Image) -> float:
    left_bytes = left.convert("RGBA").tobytes()
    right_bytes = right.convert("RGBA").tobytes()
    if len(left_bytes) != len(right_bytes):
        raise ValueError("Cannot compare animation frames with different sizes")
    squared_error = sum((a - b) ** 2 for a, b in zip(left_bytes, right_bytes, strict=True))
    return math.sqrt(squared_error / len(left_bytes)) / 255


def load_manifest() -> tuple[dict[str, object], list[str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    action_order = manifest.get("action_order")
    states = manifest.get("states")
    if not isinstance(action_order, list) or not action_order:
        raise ValueError("Manifest action_order must be a non-empty list")
    if not all(isinstance(state, str) and state for state in action_order):
        raise ValueError("Every action_order entry must be a state name")
    if len(action_order) != len(set(action_order)):
        raise ValueError("Manifest action_order must not contain duplicates")
    if RETIRED_ACTION in action_order:
        raise ValueError(f"Retired action remains active: {RETIRED_ACTION}")
    if not isinstance(states, dict):
        raise ValueError("Manifest states must be an object")
    missing = [state for state in action_order if state not in states]
    if missing:
        raise ValueError(f"Active actions are missing manifest entries: {missing}")
    return states, action_order


def load_action(
    state: str,
    entry: dict[str, object],
) -> tuple[list[Image.Image], list[Path], list[int]]:
    frame_values = entry.get("frames")
    duration_values = entry.get("frame_durations_ms")
    if not isinstance(frame_values, list) or not frame_values:
        raise ValueError(f"{state}: frames must be a non-empty list")
    if not isinstance(duration_values, list) or len(duration_values) != len(frame_values):
        raise ValueError(f"{state}: frame_durations_ms must match frames")
    if not all(isinstance(duration, int) and duration > 0 for duration in duration_values):
        raise ValueError(f"{state}: frame durations must be positive integers")

    frame_paths: list[Path] = []
    frames: list[Image.Image] = []
    for value in frame_values:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{state}: every frame path must be a string")
        path = (PET / value).resolve()
        if not path.is_relative_to(PET.resolve()):
            raise ValueError(f"{state}: frame escaped the pet workspace: {value}")
        if not path.is_file():
            raise FileNotFoundError(path)
        frame = zero_transparent_rgb(Image.open(path))
        if frame.size != EXPECTED_SIZE:
            raise ValueError(f"{state}: {path.name} must be {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]}")
        frame_paths.append(path)
        frames.append(frame)

    expected_gold_hashes = entry.get("frame_sha256")
    if entry.get("quality") == "gold":
        if not isinstance(expected_gold_hashes, dict):
            raise ValueError(f"{state}: gold action must lock every source-frame hash")
        observed_names = {path.name for path in frame_paths}
        if set(expected_gold_hashes) != observed_names:
            raise ValueError(f"{state}: gold hash keys do not match its frames")
        for path in frame_paths:
            expected = expected_gold_hashes[path.name]
            actual = sha256(path)
            if expected != actual:
                raise ValueError(f"{state}: gold frame changed: {path.name}")

    return frames, frame_paths, duration_values


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


def inspect_gif(path: Path) -> tuple[int, list[int | None], int | None, list[Image.Image]]:
    image = Image.open(path)
    frame_count = getattr(image, "n_frames", 1)
    loop = image.info.get("loop")
    durations: list[int | None] = []
    decoded_frames: list[Image.Image] = []
    for index in range(frame_count):
        image.seek(index)
        durations.append(image.info.get("duration"))
        decoded_frames.append(image.convert("RGBA").copy())
    return frame_count, durations, loop, decoded_frames


def build() -> dict[str, object]:
    states, action_order = load_manifest()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if VALIDATION.exists():
        VALIDATION.unlink()
    expected_names = {
        f"{index:02d}-{state}.gif"
        for index, state in enumerate(action_order, start=1)
    }
    for stale in OUTPUT.glob("*.gif"):
        if stale.name not in expected_names:
            stale.unlink()

    errors: list[str] = []
    actions: dict[str, object] = {}
    loaded_frames: dict[str, list[Image.Image]] = {}
    for index, state in enumerate(action_order, start=1):
        entry = states[state]
        if not isinstance(entry, dict):
            raise ValueError(f"{state}: manifest entry must be an object")
        frames, frame_paths, expected_durations = load_action(state, entry)
        loaded_frames[state] = frames
        output = OUTPUT / f"{index:02d}-{state}.gif"
        write_gif(output, frames, expected_durations)

        frame_count, observed_durations, loop, decoded_frames = inspect_gif(output)
        if frame_count != len(frames):
            errors.append(f"{state}: expected {len(frames)} GIF frames, found {frame_count}")
        if observed_durations != expected_durations:
            errors.append(
                f"{state}: GIF durations changed: {observed_durations} != {expected_durations}"
            )
        if loop != 0:
            errors.append(f"{state}: GIF must loop forever, observed loop={loop}")
        held_pose_frame = entry.get("held_pose_frame")
        if held_pose_frame is not None:
            if (
                not isinstance(held_pose_frame, int)
                or isinstance(held_pose_frame, bool)
                or not 1 <= held_pose_frame <= len(expected_durations)
            ):
                errors.append(f"{state}: held_pose_frame is invalid: {held_pose_frame}")
            else:
                held_duration = expected_durations[held_pose_frame - 1]
                other_durations = [
                    duration
                    for frame_index, duration in enumerate(expected_durations, start=1)
                    if frame_index != held_pose_frame
                ]
                if not other_durations or held_duration <= max(other_durations):
                    errors.append(
                        f"{state}: held pose {held_pose_frame} must be longer than every other frame"
                    )

        reversible_pairs = entry.get("reversible_transition_pairs")
        if reversible_pairs is not None:
            if not isinstance(reversible_pairs, list) or not reversible_pairs:
                errors.append(f"{state}: reversible_transition_pairs must be a non-empty list")
            else:
                for pair in reversible_pairs:
                    if (
                        not isinstance(pair, list)
                        or len(pair) != 2
                        or not all(
                            isinstance(frame_index, int)
                            and not isinstance(frame_index, bool)
                            and 1 <= frame_index <= len(frames)
                            for frame_index in pair
                        )
                    ):
                        errors.append(f"{state}: invalid reversible transition pair: {pair}")
                        continue
                    forward_index, reverse_index = pair
                    if frames[forward_index - 1].tobytes() != frames[reverse_index - 1].tobytes():
                        errors.append(
                            f"{state}: reversible transition frames differ: "
                            f"{forward_index} != {reverse_index}"
                        )

        transitions = [
            rgba_rmse(left, right)
            for left, right in zip(decoded_frames, decoded_frames[1:], strict=False)
        ]
        seam = rgba_rmse(decoded_frames[-1], decoded_frames[0])
        actions[state] = {
            "gif": str(output.relative_to(ROOT)),
            "gif_sha256": sha256(output),
            "source_frames": [str(path.relative_to(ROOT)) for path in frame_paths],
            "source_frame_sha256": [sha256(path) for path in frame_paths],
            "frame_count": frame_count,
            "frame_durations_ms": observed_durations,
            "cycle_duration_ms": sum(duration for duration in observed_durations if duration),
            "loop": loop,
            "transition_rmse": transitions,
            "loop_seam_rmse": seam,
            "reversible_transition_pairs": entry.get("reversible_transition_pairs", []),
            "quality": entry.get("quality", "candidate"),
        }

    for state in action_order:
        entry = states[state]
        alias_of = entry.get("alias_of")
        if alias_of is not None:
            if not isinstance(alias_of, str) or alias_of not in loaded_frames:
                errors.append(f"{state}: invalid alias target: {alias_of}")
            else:
                frames = loaded_frames[state]
                target_frames = loaded_frames[alias_of]
                if len(frames) != len(target_frames) or any(
                    frame.tobytes() != target.tobytes()
                    for frame, target in zip(frames, target_frames, strict=False)
                ):
                    errors.append(f"{state}: frames no longer exactly alias {alias_of}")

        mirror_of = entry.get("mirror_of")
        if mirror_of is not None:
            if not isinstance(mirror_of, str) or mirror_of not in loaded_frames:
                errors.append(f"{state}: invalid mirror target: {mirror_of}")
            else:
                frames = loaded_frames[state]
                target_frames = loaded_frames[mirror_of]
                if len(frames) != len(target_frames) or any(
                    frame.tobytes()
                    != target.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
                    for frame, target in zip(frames, target_frames, strict=False)
                ):
                    errors.append(f"{state}: frames no longer exactly mirror {mirror_of}")

    retired_gifs = sorted(path.name for path in OUTPUT.glob(f"*{RETIRED_ACTION}*.gif"))
    if retired_gifs:
        errors.append(f"Retired action GIFs remain: {retired_gifs}")
    observed_names = {path.name for path in OUTPUT.glob("*.gif")}
    if observed_names != expected_names:
        errors.append(
            "Action GIF directory differs from the active manifest: "
            f"observed={sorted(observed_names)}, expected={sorted(expected_names)}"
        )

    validation = {
        "ok": not errors,
        "scope": "independent-action-gifs",
        "frame_size": list(EXPECTED_SIZE),
        "action_order": action_order,
        "retired_actions": [RETIRED_ACTION],
        "errors": errors,
        "actions": actions,
        "toolchain": {"pillow": Image.__version__},
    }
    VALIDATION.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Built {len(action_order)} independent action GIFs")
    print(f"Validation: {'OK' if validation['ok'] else 'FAILED'} ({len(errors)} errors)")
    if errors:
        raise SystemExit(1)
    return validation


if __name__ == "__main__":
    build()
