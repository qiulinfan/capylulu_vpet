from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from face_geometry import (
    analyze,
    connected_components,
    interpolate_boundary,
    local,
    pca_axes,
    percentile,
)


PIPELINE = Path(__file__).resolve().parent
NORMALIZED = PIPELINE / "normalized"
ORANGE = (250, 129, 6, 255)


def muzzle_geometry(image: Image.Image):
    width, height = image.size
    pixels = list(image.get_flattened_data())
    mask = bytearray(
        red >= 230 and 105 <= green <= 165 and blue <= 40 and alpha >= 128
        for red, green, blue, alpha in pixels
    )
    component = connected_components(mask, width, height)[0]
    points = [(index % width, index // width) for index in component]
    center, u_axis, v_axis = pca_axes(points)
    projected = [local(point, center, u_axis, v_axis) for point in points]
    us = [u for u, _ in projected]
    u01 = percentile(us, 0.01)
    u99 = percentile(us, 0.99)
    samples: dict[int, list[float]] = {}
    for u, v in projected:
        samples.setdefault(round(u), []).append(v)
    boundary = {
        key: min(values)
        for key, values in samples.items()
        if len(values) >= 2 and u01 <= key <= u99
    }
    return center, u_axis, v_axis, boundary


def assert_selected_frames() -> None:
    for frame_number in range(1, 7):
        result = analyze(NORMALIZED / f"f{frame_number:02d}.png")
        assert result["top_arch"]["single_arch"]
        assert 42 <= result["eye_separation_u_px"] <= 60
        for eye in result["eyes"]:
            assert eye["skin_clearance_px"] >= 7
            assert eye["signed_local_clearance_px"] >= 7
            assert eye["gap_path_pixels"]["skin"] >= 7
            assert not eye["gap_path_pixels"]["transparent_background"]
            assert not eye["gap_path_pixels"]["other"]
            assert not eye["touch_or_spill"]


def spill_control(destination: Path) -> None:
    source = NORMALIZED / "f03.png"
    image = Image.open(source).convert("RGBA")
    center, u_axis, v_axis, boundary = muzzle_geometry(image)
    eye_u, eye_v = analyze(source)["eyes"][0]["center_uv"]
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            u, v = local((x, y), center, u_axis, v_axis)
            top = interpolate_boundary(boundary, u)
            if top is None or abs(u - eye_u) > 10 or not eye_v - 3 <= v <= top + 1:
                continue
            red, green, blue, alpha = pixels[x, y]
            if not (alpha >= 128 and red <= 85 and green <= 70 and blue <= 60):
                pixels[x, y] = ORANGE
    image.save(destination)


def m_shape_control(destination: Path) -> None:
    source = NORMALIZED / "f03.png"
    image = Image.open(source).convert("RGBA")
    center, u_axis, v_axis, boundary = muzzle_geometry(image)
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            u, v = local((x, y), center, u_axis, v_axis)
            top = interpolate_boundary(boundary, u)
            if top is None or min(abs(u + 16), abs(u - 16)) > 5 or not top - 7 <= v <= top + 1:
                continue
            red, green, blue, alpha = pixels[x, y]
            if alpha >= 128 and not (red <= 85 and green <= 70 and blue <= 60):
                pixels[x, y] = ORANGE
    image.save(destination)


def main() -> None:
    assert_selected_frames()
    with tempfile.TemporaryDirectory(prefix="lulu-face-geometry-") as temporary:
        root = Path(temporary)
        spill_path = root / "spill.png"
        m_shape_path = root / "m-shape.png"
        spill_control(spill_path)
        m_shape_control(m_shape_path)
        spill = analyze(spill_path)
        assert any(eye["touch_or_spill"] for eye in spill["eyes"])
        assert any(eye["skin_clearance_px"] == 0 for eye in spill["eyes"])
        m_shape = analyze(m_shape_path)
        assert not m_shape["top_arch"]["single_arch"]
        assert m_shape["top_arch"]["m_notch_px"] > 1.5
    print("PASS: six selected faces plus spill and M-shape negative controls")


if __name__ == "__main__":
    main()
