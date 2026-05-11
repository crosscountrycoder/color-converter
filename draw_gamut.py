#!/usr/bin/env python3

import re
import color_converter_2 as cc2


INPUT_SVG = "cie_xy_diagram.svg"
OUTPUT_SVG = "cie_xy_rec2020.svg"

# Must match the settings used to generate cie_xy_diagram.svg.
SIZE = 1024
LEFT_PAD = 100
TOP_PAD = 30

X_MIN = 0.0
X_MAX = 0.8
Y_MIN = 0.0
Y_MAX = 0.9


def x_to_svg(x: float) -> float:
    return LEFT_PAD + (x - X_MIN) / (X_MAX - X_MIN) * SIZE


def y_to_svg(y: float) -> float:
    return TOP_PAD + (Y_MAX - y) / (Y_MAX - Y_MIN) * SIZE


def xy_to_svg(point: tuple[float, float]) -> tuple[float, float]:
    x, y = point
    return x_to_svg(x), y_to_svg(y)


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def insert_before_closing_svg(svg_text: str, overlay: str) -> str:
    match = re.search(r"</svg>\s*$", svg_text, flags=re.IGNORECASE)

    if not match:
        raise ValueError("Could not find closing </svg> tag.")

    return svg_text[:match.start()] + overlay + "\n" + svg_text[match.start():]


def draw_shape_with_label(
    vertices: list[tuple[float, float]],
    label: str,
    label_location: tuple[float, float],
    stroke_color: str,
    stroke_width: float = 2.5,
    fill_color: str | None = None,
    fill_opacity: float = 0.04,
    label_color: str | None = None,
    label_font_size: int = 24,
    white_point: tuple[float, float] | None = None,
    white_point_label: str | None = None,
    white_point_label_location: tuple[float, float] | None = None,
) -> str:
    """
    Draw a labeled xy polygon on top of the CIE diagram.

    vertices:
        CIE xy vertices. Can be 3 points for RGB triangles or more points
        for irregular gamuts such as Pointer's gamut.

    label_location:
        Exact CIE xy coordinate for the shape label.

    white_point:
        Optional CIE xy coordinate for a white-point marker.

    white_point_label_location:
        Exact CIE xy coordinate for the white-point label.
    """

    if fill_color is None:
        fill_color = stroke_color

    if label_color is None:
        label_color = stroke_color

    points_svg = [xy_to_svg(p) for p in vertices]
    label_svg = xy_to_svg(label_location)

    points_str = " ".join(
        f"{x:.4f},{y:.4f}"
        for x, y in points_svg
    )

    safe_id = (
        label.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace("/", "-")
        .replace("(", "")
        .replace(")", "")
        .replace("'", "")
    )

    parts = []
    parts.append(f'<g id="{svg_escape(safe_id)}-overlay">')

    parts.append(
        f'  <polygon points="{points_str}" '
        f'fill="{svg_escape(fill_color)}" '
        f'fill-opacity="{fill_opacity}" '
        f'stroke="{svg_escape(stroke_color)}" '
        f'stroke-width="{stroke_width}" '
        f'stroke-linejoin="round"/>'
    )

    parts.append(
        f'  <text x="{label_svg[0]:.4f}" y="{label_svg[1]:.4f}" '
        f'text-anchor="middle" '
        f'dominant-baseline="middle" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{label_font_size}" '
        f'font-weight="bold" '
        f'fill="{svg_escape(label_color)}">{svg_escape(label)}</text>'
    )

    if white_point is not None:
        wx, wy = xy_to_svg(white_point)

        parts.append(
            f'  <circle cx="{wx:.4f}" cy="{wy:.4f}" '
            f'r="4.5" fill="black"/>'
        )

        if white_point_label is not None:
            if white_point_label_location is None:
                white_point_label_location = (
                    white_point[0] + 0.015,
                    white_point[1] + 0.015,
                )

            wlx, wly = xy_to_svg(white_point_label_location)

            parts.append(
                f'  <text x="{wlx:.4f}" y="{wly:.4f}" '
                f'text-anchor="start" '
                f'dominant-baseline="middle" '
                f'font-family="Arial, Helvetica, sans-serif" '
                f'font-size="{label_font_size}" '
                f'font-weight="bold" '
                f'fill="black">{svg_escape(white_point_label)}</text>'
            )

    parts.append("</g>")
    return "\n".join(parts)


def main():
    with open(INPUT_SVG, "r", encoding="utf-8") as f:
        svg_text = f.read()

    xr, yr, _ = cc2.XYZ_to_xyY(*cc2.spectral_to_XYZ(630, True))
    xg, yg, _ = cc2.XYZ_to_xyY(*cc2.spectral_to_XYZ(532, True))
    xb, yb, _ = cc2.XYZ_to_xyY(*cc2.spectral_to_XYZ(467, True))
    overlay_parts = []
    overlay_parts.append(
        draw_shape_with_label(
            vertices=[(xr, yr), (xg, yg), (xb, yb)],
            label="Rec2020",
            label_location=(0.2, 0.5),
            stroke_color="#000000",
            stroke_width=2.5,
            fill_opacity=0.0,
            label_font_size=24,
            white_point=cc2.D65,
            white_point_label="D65",
            white_point_label_location=(0.310, 0.345),
        )
    )

    overlay = "\n".join(overlay_parts)
    new_svg = insert_before_closing_svg(svg_text, overlay)

    with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
        f.write(new_svg)

    print(f"Wrote {OUTPUT_SVG}")


if __name__ == "__main__":
    main()