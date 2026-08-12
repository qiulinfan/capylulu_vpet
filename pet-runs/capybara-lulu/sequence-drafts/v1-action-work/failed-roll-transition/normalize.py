from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
SOURCE_STRIP = HERE / "imagegen-two-inbetweens-alpha.png"
PIPELINE_FRAMES = HERE / "pipeline-normalized-square"
OUTPUT = HERE / "normalized"

FRAME_SIZE = (192, 208)
PIPELINE_FRAME_SIZE = (176, 176)
FRAME_OFFSET = (8, 24)
ALPHA_THRESHOLD = 128
PIPELINE_PLUGIN = "game-studio@openai-curated"
PIPELINE_VERSION = "3fdeeb49"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hard_alpha(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    image.putdata(
        [
            (red, green, blue, 255) if alpha >= ALPHA_THRESHOLD else (0, 0, 0, 0)
            for red, green, blue, alpha in image.get_flattened_data()
        ]
    )
    return image


def main() -> None:
    inputs = sorted(PIPELINE_FRAMES.glob("*.png"))
    if len(inputs) != 2:
        raise SystemExit(f"Expected two sprite-pipeline frames, found {len(inputs)}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    for index, source_path in enumerate(inputs, start=1):
        source = Image.open(source_path).convert("RGBA")
        if source.size != PIPELINE_FRAME_SIZE:
            raise SystemExit(
                f"Unexpected sprite-pipeline frame size for {source_path}: {source.size}"
            )

        canvas = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
        canvas.alpha_composite(hard_alpha(source), FRAME_OFFSET)
        canvas = hard_alpha(canvas)
        bbox = canvas.getchannel("A").getbbox()
        if bbox is None or bbox[3] != 200:
            raise SystemExit(f"Lost bottom-center pet anchor for {source_path}: {bbox}")

        output_path = OUTPUT / f"failed-roll-transition-{index:02d}.png"
        canvas.save(output_path, optimize=True)
        records.append(
            {
                "source": str(source_path.relative_to(HERE)),
                "source_sha256": sha256(source_path),
                "output": str(output_path.relative_to(HERE)),
                "output_sha256": sha256(output_path),
                "alpha_bbox": list(bbox),
            }
        )

    manifest = {
        "source_strip": {
            "path": str(SOURCE_STRIP.relative_to(HERE)),
            "sha256": sha256(SOURCE_STRIP),
        },
        "normalizer": {
            "plugin": PIPELINE_PLUGIN,
            "version": PIPELINE_VERSION,
            "shared_square_size": list(PIPELINE_FRAME_SIZE),
            "pet_frame_size": list(FRAME_SIZE),
            "pet_frame_offset": list(FRAME_OFFSET),
            "alpha_threshold": ALPHA_THRESHOLD,
            "anchor": "bottom-center at x=96, ground y=200",
        },
        "frames": records,
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Adapted two shared-scale sprite-pipeline frames to 192x208")


if __name__ == "__main__":
    main()
