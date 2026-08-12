from __future__ import annotations

import math
from collections import deque
from pathlib import Path
from statistics import median

from PIL import Image


def connected_components(mask: bytearray, width: int, height: int) -> list[list[int]]:
    seen = bytearray(width * height)
    components: list[list[int]] = []
    neighbors = (
        (-1, -1), (0, -1), (1, -1),
        (-1, 0), (1, 0),
        (-1, 1), (0, 1), (1, 1),
    )
    for start, value in enumerate(mask):
        if not value or seen[start]:
            continue
        seen[start] = 1
        todo = deque((start,))
        component: list[int] = []
        while todo:
            index = todo.popleft()
            component.append(index)
            x, y = index % width, index // width
            for dx, dy in neighbors:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    continue
                neighbor = ny * width + nx
                if mask[neighbor] and not seen[neighbor]:
                    seen[neighbor] = 1
                    todo.append(neighbor)
        components.append(component)
    return sorted(components, key=len, reverse=True)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def pca_axes(
    points: list[tuple[float, float]],
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    xx = sum((x - cx) ** 2 for x, _ in points) / len(points)
    yy = sum((y - cy) ** 2 for _, y in points) / len(points)
    xy = sum((x - cx) * (y - cy) for x, y in points) / len(points)
    angle = 0.5 * math.atan2(2 * xy, xx - yy)
    ux, uy = math.cos(angle), math.sin(angle)
    if ux < 0:
        ux, uy = -ux, -uy
    return (cx, cy), (ux, uy), (-uy, ux)


def local(
    point: tuple[float, float],
    center: tuple[float, float],
    u_axis: tuple[float, float],
    v_axis: tuple[float, float],
) -> tuple[float, float]:
    dx, dy = point[0] - center[0], point[1] - center[1]
    return dx * u_axis[0] + dy * u_axis[1], dx * v_axis[0] + dy * v_axis[1]


def linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = (
        sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
        / denominator
        if denominator
        else 0
    )
    return slope, mean_y - slope * mean_x


def quadratic_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    count = float(len(xs))
    sx = sum(xs)
    sx2 = sum(x * x for x in xs)
    sx3 = sum(x * x * x for x in xs)
    sx4 = sum(x * x * x * x for x in xs)
    sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys, strict=True))
    sx2y = sum(x * x * y for x, y in zip(xs, ys, strict=True))
    matrix = [
        [sx4, sx3, sx2, sx2y],
        [sx3, sx2, sx, sxy],
        [sx2, sx, count, sy],
    ]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda row: abs(matrix[row][column]))
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        divisor = matrix[column][column]
        if abs(divisor) < 1e-9:
            return 0, *linear_fit(xs, ys)
        matrix[column] = [value / divisor for value in matrix[column]]
        for row in range(3):
            if row == column:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(matrix[row], matrix[column], strict=True)
            ]
    return matrix[0][3], matrix[1][3], matrix[2][3]


def interpolate_boundary(boundary: dict[int, float], u: float) -> float | None:
    lower = math.floor(u)
    upper = math.ceil(u)
    if lower in boundary and upper in boundary:
        if lower == upper:
            return boundary[lower]
        return boundary[lower] * (upper - u) + boundary[upper] * (u - lower)
    nearest = min(boundary, key=lambda key: abs(key - u))
    return boundary[nearest] if abs(nearest - u) <= 2 else None


def moving_median(values: list[float], radius: int = 2) -> list[float]:
    return [
        median(values[max(0, index - radius) : min(len(values), index + radius + 1)])
        for index in range(len(values))
    ]


def arc_sag(points: list[tuple[float, float]]) -> float:
    us = [u for u, _ in points]
    low, high = min(us), max(us)
    width = high - low
    left = [v for u, v in points if u <= low + 0.25 * width]
    middle = [v for u, v in points if low + 0.35 * width <= u <= low + 0.65 * width]
    right = [v for u, v in points if u >= high - 0.25 * width]
    if not left or not middle or not right:
        return 0
    return median(middle) - (median(left) + median(right)) / 2


def pixel_square_distance(
    left: list[tuple[int, int]],
    right: list[tuple[int, int]],
) -> tuple[float, tuple[tuple[int, int], tuple[int, int]]]:
    best = math.inf
    best_pair = (left[0], right[0])
    for left_x, left_y in left:
        for right_x, right_y in right:
            dx = max(abs(left_x - right_x) - 1, 0)
            dy = max(abs(left_y - right_y) - 1, 0)
            distance = dx * dx + dy * dy
            if distance < best:
                best = distance
                best_pair = ((left_x, left_y), (right_x, right_y))
                if best == 0:
                    return 0, best_pair
    return math.sqrt(best), best_pair


def raster_line(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    x0, y0 = start
    x1, y1 = end
    dx, step_x = abs(x1 - x0), 1 if x0 < x1 else -1
    dy, step_y = -abs(y1 - y0), 1 if y0 < y1 else -1
    error = dx + dy
    points = []
    while True:
        points.append((x0, y0))
        if (x0, y0) == (x1, y1):
            return points
        twice = 2 * error
        if twice >= dy:
            error += dy
            x0 += step_x
        if twice <= dx:
            error += dx
            y0 += step_y


def analyze(path: Path) -> dict[str, object]:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    pixels = list(image.get_flattened_data())
    orange = bytearray(
        red >= 230 and 105 <= green <= 165 and blue <= 40 and alpha >= 128
        for red, green, blue, alpha in pixels
    )
    orange_components = connected_components(orange, width, height)
    if not orange_components:
        raise ValueError(f"{path.name}: no orange component")
    muzzle_component = orange_components[0]
    muzzle_points = [(index % width, index // width) for index in muzzle_component]
    center, u_axis, v_axis = pca_axes(muzzle_points)
    muzzle_local = [local(point, center, u_axis, v_axis) for point in muzzle_points]
    muzzle_us = [u for u, _ in muzzle_local]
    u01 = percentile(muzzle_us, 0.01)
    u99 = percentile(muzzle_us, 0.99)
    width98 = u99 - u01
    samples: dict[int, list[float]] = {}
    for u, v in muzzle_local:
        samples.setdefault(round(u), []).append(v)
    boundary = {
        key: min(values)
        for key, values in samples.items()
        if len(values) >= 2 and u01 <= key <= u99
    }

    dark = bytearray(
        alpha >= 128 and red <= 85 and green <= 70 and blue <= 60
        for red, green, blue, alpha in pixels
    )
    candidates: list[dict[str, object]] = []
    for component in connected_components(dark, width, height):
        if not 18 <= len(component) <= 140:
            continue
        points = [(index % width, index // width) for index in component]
        projected = [local(point, center, u_axis, v_axis) for point in points]
        us = [u for u, _ in projected]
        vs = [v for _, v in projected]
        span_u = max(us) - min(us)
        span_v = max(vs) - min(vs)
        mean_u = sum(us) / len(us)
        mean_v = sum(vs) / len(vs)
        top = interpolate_boundary(boundary, mean_u)
        sag = arc_sag(projected)
        if (
            not 10 <= span_u <= 30
            or not 2 <= span_v <= 17
            or top is None
            or not -0.56 * width98 <= mean_v <= -0.12 * width98
            or sag < 0.75
        ):
            continue
        candidates.append(
            {
                "points": points,
                "local_points": projected,
                "area": len(component),
                "center": (
                    sum(x for x, _ in points) / len(points),
                    sum(y for _, y in points) / len(points),
                ),
                "local_center": (mean_u, mean_v),
                "span": (span_u, span_v),
                "sag": sag,
                "score": abs(mean_v + 0.37 * width98) + abs(span_u - 18) * 0.1,
            }
        )
    pairs = []
    for left in candidates:
        for right in candidates:
            left_u, left_v = left["local_center"]
            right_u, right_v = right["local_center"]
            separation = right_u - left_u
            if (
                left_u < -0.04 * width98
                and right_u > 0.04 * width98
                and 0.38 * width98 <= separation <= 0.78 * width98
                and abs(left_v - right_v) <= 0.18 * width98
            ):
                pairs.append(
                    (
                        left["score"] + right["score"] + abs(separation - 0.58 * width98),
                        left,
                        right,
                    )
                )
    if not pairs:
        raise ValueError(f"{path.name}: expected two closed-eye arcs")
    _, left_eye, right_eye = min(pairs, key=lambda item: item[0])
    eyes = [left_eye, right_eye]
    eye_separation = right_eye["local_center"][0] - left_eye["local_center"][0]
    square_projection = abs(v_axis[0]) + abs(v_axis[1])
    eye_results = []
    for eye in eyes:
        deltas = []
        for u, v in eye["local_points"]:
            top = interpolate_boundary(boundary, u)
            if top is not None:
                deltas.append(top - v)
        signed_clearance = min(deltas) - square_projection
        raster_clearance, closest_pair = pixel_square_distance(eye["points"], muzzle_points)
        gap_pixels = raster_line(*closest_pair)[1:-1]
        gap_skin = 0
        gap_background = 0
        gap_other = 0
        for x, y in gap_pixels:
            red, green, blue, alpha = pixels[y * width + x]
            if alpha < 128:
                gap_background += 1
            elif red >= 220 and green >= 166 and blue <= 60:
                gap_skin += 1
            else:
                gap_other += 1
        eye_results.append(
            {
                "center_xy": [round(value, 2) for value in eye["center"]],
                "center_uv": [round(value, 2) for value in eye["local_center"]],
                "area_px": eye["area"],
                "span_uv_px": [round(value, 2) for value in eye["span"]],
                "arc_sag_px": round(eye["sag"], 2),
                "skin_clearance_px": round(raster_clearance, 2),
                "signed_local_clearance_px": round(signed_clearance, 2),
                "gap_path_pixels": {
                    "skin": gap_skin,
                    "transparent_background": gap_background,
                    "other": gap_other,
                },
                "overlap_depth_px": round(max(0, -signed_clearance), 2),
                "touch_or_spill": raster_clearance <= 0 or signed_clearance <= 0,
            }
        )

    keys = sorted(boundary)
    values = moving_median([boundary[key] for key in keys])
    low = u01 + 0.1 * width98
    high = u99 - 0.1 * width98
    arch = [(float(key), value) for key, value in zip(keys, values, strict=True) if low <= key <= high]
    arch_u = [u for u, _ in arch]
    arch_v = [v for _, v in arch]
    qa, qb, qc = quadratic_fit(arch_u, arch_v)
    residuals = [v - (qa * u * u + qb * u + qc) for u, v in arch]
    rmse = math.sqrt(sum(value * value for value in residuals) / len(residuals))
    apex_u = -qb / (2 * qa) if qa > 1e-9 else math.inf
    half = width98 / 2
    left_shoulder = [v for u, v in arch if -0.38 * half <= u <= -0.14 * half]
    center_band = [v for u, v in arch if -0.08 * half <= u <= 0.08 * half]
    right_shoulder = [v for u, v in arch if 0.14 * half <= u <= 0.38 * half]
    notch = median(center_band) - max(min(left_shoulder), min(right_shoulder))
    second_area = len(orange_components[1]) if len(orange_components) > 1 else 0
    angle = math.degrees(math.atan2(u_axis[1], u_axis[0]))
    return {
        "file": path.name,
        "muzzle": {
            "area_px": len(muzzle_component),
            "head_local_angle_deg": round(angle, 2),
            "span_u_98_px": round(width98, 2),
            "second_orange_area_px": second_area,
            "dominance_ratio": round(len(muzzle_component) / max(second_area, 1), 2),
        },
        "eyes": eye_results,
        "eye_separation_u_px": round(eye_separation, 2),
        "top_arch": {
            "quadratic_curvature": round(qa, 5),
            "quadratic_apex_u_px": round(apex_u, 2),
            "fit_rmse_px": round(rmse, 2),
            "m_notch_px": round(notch, 2),
            "single_arch": (
                qa >= 0.0025
                and abs(apex_u) <= 0.18 * width98
                and rmse <= 1.25
                and notch <= 1.5
            ),
        },
    }
