#!/usr/bin/env python3

import argparse
import base64
import io
import math
import os
import csv

import numpy as np
from PIL import Image, ImageDraw, ImageCms

import color_converter_2 as cc2


def srgb_oetf(linear_rgb: np.ndarray) -> np.ndarray:
    """
    Vectorized sRGB transfer curve.
    Equivalent to color_converter_2.linear_to_RGB(..., "srgb"),
    but applied to an entire image array at once.
    """
    linear_rgb = np.clip(linear_rgb, 0.0, 1.0)

    return np.where(
        linear_rgb <= 0.0031308,
        12.92 * linear_rgb,
        1.055 * np.power(linear_rgb, 1.0 / 2.4) - 0.055,
    )


def load_icc_profile_bytes(path: str | None) -> bytes | None:
    """
    Load ICC profile bytes.

    For sRGB, this is optional. If no path is provided, or if the file
    does not exist, the embedded PNG is saved without an ICC profile.
    Most browsers/viewers assume sRGB by default.
    """
    if not path:
        return None

    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        profile = ImageCms.ImageCmsProfile(f)
        return profile.tobytes()


def load_locus_with_wavelengths(path: str):
    """
    Load spectral locus CSV.

    Expected columns:
    wavelength, x, y

    color_converter_2.load_xy_polygon() already uses columns 1 and 2,
    so this mirrors that while also keeping wavelength values.
    """
    wavelengths = []
    xs = []
    ys = []

    with open(path, "r", newline="") as file:
        reader = csv.reader(file)
        next(reader)

        for row in reader:
            wavelengths.append(float(row[0]))
            xs.append(float(row[1]))
            ys.append(float(row[2]))

    return (
        np.array(wavelengths, dtype=float),
        np.array(xs, dtype=float),
        np.array(ys, dtype=float),
    )


def make_locus_mask(width, height, x_min, x_max, y_min, y_max, polygon):
    """
    Create an 8-bit mask of the CIE xy chromaticity locus.
    White = inside locus, black = outside.
    """
    def xy_to_pixel(x, y):
        px = (x - x_min) / (x_max - x_min) * (width - 1)
        py = (y_max - y) / (y_max - y_min) * (height - 1)
        return px, py

    pixel_polygon = [xy_to_pixel(x, y) for x, y in polygon]

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(pixel_polygon, fill=255)
    return mask


def generate_chromaticity_rgba(
    size: int = 1024,
    icc_profile_path: str | None = None,
    locus_path: str = "CIE_xy_locus.csv",
    x_min: float = 0.0,
    x_max: float = 0.8,
    y_min: float = 0.0,
    y_max: float = 0.9,
    supersample: int = 3,
):
    """
    Generate the chromaticity diagram as a Pillow RGBA image.

    The returned image:
    - uses sRGB-encoded RGB values;
    - has transparency outside the CIE xy locus;
    - uses D65 white-point compression for chromaticities outside sRGB;
    - scales each valid chromaticity to maximum brightness in linear sRGB.
    """
    scale = max(1, int(supersample))
    width = height = int(size) * scale

    polygon = cc2.load_xy_polygon(locus_path)

    xs = x_min + (np.arange(width) + 0.5) / width * (x_max - x_min)
    ys = y_max - (np.arange(height) + 0.5) / height * (y_max - y_min)
    X_grid, Y_grid_xy = np.meshgrid(xs, ys)

    x = X_grid
    y = Y_grid_xy

    safe_y = np.where(y > 0.0, y, 1.0)

    # xyY -> XYZ with Y = 1.
    XYZ = np.empty((height, width, 3), dtype=np.float64)
    XYZ[..., 0] = x / safe_y
    XYZ[..., 1] = 1.0
    XYZ[..., 2] = (1.0 - x - y) / safe_y

    # XYZ -> linear sRGB.
    M = cc2.RGB_to_XYZ_matrix(cc2.SRGB)
    M_inv = np.linalg.inv(M)
    rgb_linear = XYZ @ M_inv.T

    min_channel = np.min(rgb_linear, axis=-1)
    max_channel = np.max(rgb_linear, axis=-1)

    # Gamut-map colors outside sRGB toward D65 white at same Y.
    # With Y = 1, sRGB D65 white is linear RGB = (1, 1, 1).
    rgb_mapped = rgb_linear.copy()

    if np.any(min_channel < 0.0):
        negative = rgb_linear < 0.0
        denom = 1.0 - rgb_linear

        t_candidates = np.where(
            negative,
            -rgb_linear / np.where(denom != 0.0, denom, np.nan),
            0.0,
        )

        t = np.nanmax(t_candidates, axis=-1)
        t = np.clip(t, 0.0, 1.0)

        rgb_mapped = (1.0 - t[..., None]) * rgb_mapped + t[..., None]

    usable = max_channel > 0.0

    # Scale to maximum brightness in linear sRGB.
    max_after_mapping = np.max(rgb_mapped, axis=-1)
    valid_scale = usable & (max_after_mapping > 0.0)

    rgb_max = np.zeros_like(rgb_mapped)
    rgb_max[valid_scale] = rgb_mapped[valid_scale] / max_after_mapping[valid_scale, None]
    rgb_max = np.clip(rgb_max, 0.0, 1.0)

    # Apply sRGB transfer curve.
    rgb_encoded = srgb_oetf(rgb_max)
    rgb_u8 = np.round(rgb_encoded * 255.0).astype(np.uint8)

    # Transparent outside the CIE locus.
    mask = make_locus_mask(width, height, x_min, x_max, y_min, y_max, polygon)
    alpha = np.array(mask, dtype=np.uint8)

    rgba = np.dstack([rgb_u8, alpha])
    image = Image.fromarray(rgba, mode="RGBA")

    if scale > 1:
        image = image.resize((size, size), Image.Resampling.LANCZOS)

    icc_bytes = load_icc_profile_bytes(icc_profile_path)
    return image, icc_bytes


def image_to_data_uri_png(image: Image.Image, icc_bytes: bytes | None) -> str:
    """
    Convert a Pillow image to a base64 PNG data URI.

    If icc_bytes is None, no ICC profile is embedded.
    For sRGB output, that is usually acceptable.
    """
    bio = io.BytesIO()

    if icc_bytes is None:
        image.save(bio, format="PNG")
    else:
        image.save(bio, format="PNG", icc_profile=icc_bytes)

    encoded = base64.b64encode(bio.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def frange(start: float, stop: float, step: float):
    """
    Inclusive floating-point range.
    """
    n0 = int(math.ceil((start - 1e-12) / step))
    n1 = int(math.floor((stop + 1e-12) / step))

    for n in range(n0, n1 + 1):
        yield round(n * step, 10)


def is_major_tick(value: float, label_step: float) -> bool:
    return abs((value / label_step) - round(value / label_step)) < 1e-9


def fmt_tick(value: float) -> str:
    """
    Format tick labels cleanly.
    """
    if abs(value) < 5e-12:
        value = 0.0

    s = f"{value:.1f}"

    if s == "-0.0":
        s = "0.0"

    return s


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )


def wavelength_label_offset(wavelength_nm: int, font_size: int):
    """
    Small label offsets so wavelength labels sit close to their corresponding dots.

    These are SVG-pixel offsets, not xy-coordinate offsets.
    Positive dx moves right. Positive dy moves down.
    """
    label_size = max(12, round(font_size * 0.75))

    if wavelength_nm <= 460:
        return -0.8 * label_size, 0.8 * label_size

    if wavelength_nm <= 500:
        return -1.0 * label_size, 0.4 * label_size

    if wavelength_nm <= 540:
        return 0.25 * label_size, -0.35 * label_size

    if wavelength_nm <= 580:
        return 0.5 * label_size, -0.35 * label_size

    if wavelength_nm <= 620:
        return 0.9 * label_size, 0.0 * label_size

    return 0.8 * label_size, -0.25 * label_size


def add_locus_outline_dots_and_labels(
    parts: list[str],
    locus_path: str,
    x_to_svg,
    y_to_svg,
    font_size: int,
):
    """
    Add:
    - dark-blue outline around the CIE locus;
    - dots every 5 nm from 460-620 nm;
    - labels every 20 nm from 460-620 nm;
    - dots every 10 nm from 400-450 and 630-700 nm;
    - labels at 400 and 700 nm.
    """
    wavelengths, xs, ys = load_locus_with_wavelengths(locus_path)

    # Full locus outline, including the line of purples by closing the polygon.
    outline_points = []

    for x, y in zip(xs, ys):
        outline_points.append(f"{x_to_svg(x):.4f},{y_to_svg(y):.4f}")

    # Close the locus outline.
    if outline_points:
        outline_points.append(outline_points[0])

    parts.append(
        f'<polyline points="{" ".join(outline_points)}" '
        f'class="locus-outline"/>'
    )

    # Dot wavelength ranges.
    dot_wavelengths = []

    dot_wavelengths.extend(range(400, 451, 10))
    dot_wavelengths.extend(range(460, 621, 5))
    dot_wavelengths.extend(range(630, 701, 10))

    # Avoid duplicates if ranges are changed later.
    dot_wavelengths = sorted(set(dot_wavelengths))

    for wl in dot_wavelengths:
        x = float(np.interp(wl, wavelengths, xs))
        y = float(np.interp(wl, wavelengths, ys))

        parts.append(
            f'<circle cx="{x_to_svg(x):.4f}" cy="{y_to_svg(y):.4f}" '
            f'r="3.2" class="locus-dot"/>'
        )

    # Label wavelength ranges.
    label_wavelengths = [400]
    label_wavelengths.extend(range(460, 621, 20))
    label_wavelengths.append(700)

    label_wavelengths = sorted(set(label_wavelengths))

    for wl in label_wavelengths:
        x = float(np.interp(wl, wavelengths, xs))
        y = float(np.interp(wl, wavelengths, ys))

        sx = x_to_svg(x)
        sy = y_to_svg(y)

        dx, dy = wavelength_label_offset(wl, font_size)

        parts.append(
            f'<text x="{sx + dx:.4f}" y="{sy + dy:.4f}" '
            f'text-anchor="middle" '
            f'class="wavelength-label">{wl}</text>'
        )


def generate_cie_xy_svg(
    output_path: str,
    size: int = 1024,
    icc_profile_path: str | None = None,
    locus_path: str = "CIE_xy_locus.csv",
    x_min: float = 0.0,
    x_max: float = 0.8,
    y_min: float = 0.0,
    y_max: float = 0.9,
    supersample: int = 3,
    left_pad: int = 100,
    right_pad: int = 30,
    top_pad: int = 30,
    bottom_pad: int = 90,
    grid_step: float = 0.05,
    label_step: float = 0.1,
    font_size: int = 28,
):
    """
    Generate an SVG file containing:
    - embedded sRGB PNG chromaticity layer;
    - white background;
    - vector gridlines every grid_step, overlaid on top of the raster layer;
    - vector labels every label_step;
    - dark-blue spectral locus outline;
    - wavelength dots and labels;
    - customizable padding.
    """

    chroma_img, icc_bytes = generate_chromaticity_rgba(
        size=size,
        icc_profile_path=icc_profile_path,
        locus_path=locus_path,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        supersample=supersample,
    )

    png_data_uri = image_to_data_uri_png(chroma_img, icc_bytes)

    plot_w = size
    plot_h = size
    svg_w = left_pad + plot_w + right_pad
    svg_h = top_pad + plot_h + bottom_pad

    def x_to_svg(x):
        return left_pad + (x - x_min) / (x_max - x_min) * plot_w

    def y_to_svg(y):
        return top_pad + (y_max - y) / (y_max - y_min) * plot_h

    parts = []

    parts.append('<?xml version="1.0" encoding="UTF-8" standalone="no"?>')
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}">'
    )

    parts.append(f'''
<defs>
<style>
.grid-major {{
    stroke: #000000;
    stroke-width: 0.75;
    stroke-opacity: 1.0;
}}

.grid-minor {{
    stroke: #000000;
    stroke-width: 0.5;
    stroke-opacity: 1.0;
}}

.axis-border {{
    stroke: #000000;
    stroke-width: 1.5;
    stroke-opacity: 1.0;
    fill: none;
}}

.tick-label {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: {font_size}px;
    fill: #000000;
}}

.axis-label {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: {font_size + 2}px;
    fill: #000000;
    font-weight: bold;
}}

.locus-outline {{
    fill: none;
    stroke: #003366;
    stroke-width: 1.35;
    stroke-linejoin: round;
    stroke-linecap: round;
}}

.locus-dot {{
    fill: #003366;
    stroke: none;
}}

.wavelength-label {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: {max(10, round(font_size * 0.625))}px;
    fill: #003366;
    font-weight: bold;
}}
</style>
</defs>
''')

    # White background behind everything.
    parts.append(
        f'<rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="white"/>'
    )

    # White plot background behind transparent parts of the raster layer.
    parts.append(
        f'<rect x="{left_pad}" y="{top_pad}" '
        f'width="{plot_w}" height="{plot_h}" '
        f'fill="white"/>'
    )

    # Embedded PNG chromaticity layer.
    parts.append(
        f'<image x="{left_pad}" y="{top_pad}" '
        f'width="{plot_w}" height="{plot_h}" '
        f'preserveAspectRatio="none" '
        f'xlink:href="{png_data_uri}"/>'
    )

    # Gridlines on top of the raster layer.
    for xv in frange(x_min, x_max, grid_step):
        cls = "grid-major" if is_major_tick(xv, label_step) else "grid-minor"
        x_svg = x_to_svg(xv)

        parts.append(
            f'<line x1="{x_svg:.4f}" y1="{top_pad}" '
            f'x2="{x_svg:.4f}" y2="{top_pad + plot_h}" '
            f'class="{cls}"/>'
        )

    for yv in frange(y_min, y_max, grid_step):
        cls = "grid-major" if is_major_tick(yv, label_step) else "grid-minor"
        y_svg = y_to_svg(yv)

        parts.append(
            f'<line x1="{left_pad}" y1="{y_svg:.4f}" '
            f'x2="{left_pad + plot_w}" y2="{y_svg:.4f}" '
            f'class="{cls}"/>'
        )

    # Locus outline, wavelength dots, and wavelength labels.
    # These are drawn after the grid so they remain visible.
    add_locus_outline_dots_and_labels(
        parts=parts,
        locus_path=locus_path,
        x_to_svg=x_to_svg,
        y_to_svg=y_to_svg,
        font_size=font_size,
    )

    # Border around plot, also over the raster layer.
    parts.append(
        f'<rect x="{left_pad}" y="{top_pad}" '
        f'width="{plot_w}" height="{plot_h}" '
        f'class="axis-border"/>'
    )

    # X labels every label_step.
    for xv in frange(x_min, x_max, label_step):
        x_svg = x_to_svg(xv)
        label = svg_escape(fmt_tick(xv))

        parts.append(
            f'<text x="{x_svg:.4f}" '
            f'y="{top_pad + plot_h + font_size + 12}" '
            f'text-anchor="middle" '
            f'class="tick-label">{label}</text>'
        )

    # Y labels every label_step.
    for yv in frange(y_min, y_max, label_step):
        y_svg = y_to_svg(yv)
        label = svg_escape(fmt_tick(yv))

        parts.append(
            f'<text x="{left_pad - 12}" '
            f'y="{y_svg + font_size / 3:.4f}" '
            f'text-anchor="end" '
            f'class="tick-label">{label}</text>'
        )

    # Axis labels.
    parts.append(
        f'<text x="{left_pad + plot_w / 2:.4f}" '
        f'y="{svg_h - 18}" '
        f'text-anchor="middle" '
        f'class="axis-label">x</text>'
    )

    y_axis_x = max(20, left_pad - font_size * 2.5)

    parts.append(
        f'<text x="{y_axis_x:.4f}" '
        f'y="{top_pad + plot_h / 2:.4f}" '
        f'text-anchor="middle" '
        f'class="axis-label" '
        f'transform="rotate(-90 {y_axis_x:.4f} {top_pad + plot_h / 2:.4f})">y</text>'
    )

    parts.append('</svg>')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def main():
    parser = argparse.ArgumentParser(
        description="Generate an sRGB SVG of the CIE 1931 xy chromaticity diagram with padding, gridlines, and labels."
    )

    parser.add_argument(
        "-o", "--output",
        default="cie_xy_diagram.svg",
        help="Output SVG path. Default: cie_xy_diagram.svg",
    )

    parser.add_argument(
        "-s", "--size",
        type=int,
        default=1024,
        help="Plot area size in pixels before padding. Default: 1024",
    )

    parser.add_argument(
        "--icc",
        default=None,
        help=(
            "Optional path to an sRGB ICC profile. "
            "If omitted, the embedded PNG is saved without ICC because sRGB is normally assumed."
        ),
    )

    parser.add_argument(
        "--locus",
        default="CIE_xy_locus.csv",
        help="Path to CIE xy locus CSV. Default: CIE_xy_locus.csv",
    )

    parser.add_argument("--x-min", type=float, default=0.0)
    parser.add_argument("--x-max", type=float, default=0.8)
    parser.add_argument("--y-min", type=float, default=0.0)
    parser.add_argument("--y-max", type=float, default=0.9)

    parser.add_argument(
        "--supersample",
        type=int,
        default=3,
        help="Supersampling factor for the embedded chromaticity PNG. Default: 3",
    )

    parser.add_argument("--left-pad", type=int, default=100)
    parser.add_argument("--right-pad", type=int, default=30)
    parser.add_argument("--top-pad", type=int, default=30)
    parser.add_argument("--bottom-pad", type=int, default=90)

    parser.add_argument("--grid-step", type=float, default=0.05)
    parser.add_argument("--label-step", type=float, default=0.1)

    parser.add_argument(
        "--font-size",
        type=int,
        default=28,
        help="Tick label font size. Default: 28",
    )

    args = parser.parse_args()

    generate_cie_xy_svg(
        output_path=args.output,
        size=args.size,
        icc_profile_path=args.icc,
        locus_path=args.locus,
        x_min=args.x_min,
        x_max=args.x_max,
        y_min=args.y_min,
        y_max=args.y_max,
        supersample=args.supersample,
        left_pad=args.left_pad,
        right_pad=args.right_pad,
        top_pad=args.top_pad,
        bottom_pad=args.bottom_pad,
        grid_step=args.grid_step,
        label_step=args.label_step,
        font_size=args.font_size,
    )


if __name__ == "__main__":
    main()