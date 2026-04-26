import sys
import csv
from math import sqrt

Point = tuple[float, float]

SRGB_RED = (0.64, 0.33)
SRGB_GREEN = (0.3, 0.6)
SRGB_BLUE = (0.15, 0.06)
SRGB_WHITE = (0.3127, 0.3290)

def clamp(x: float, lo: float = 0.0, hi: float = 1.0):
    return max(lo, min(x, hi))

def RGB_to_XYZ(R: int, G: int, B: int) -> tuple[float, float, float]:
    """Converts sRGB color values in [0, 255] range to CIE XYZ color space."""
    r = (R / 3294.6) if R <= 10 else ((R/255 + 0.055)/1.055)**2.4
    g = (G / 3294.6) if G <= 10 else ((G/255 + 0.055)/1.055)**2.4
    b = (B / 3294.6) if B <= 10 else ((B/255 + 0.055)/1.055)**2.4
    X = 0.4124564*r + 0.3575761*g + 0.1804375*b
    Y = 0.2126729*r + 0.7151522*g + 0.0721750*b
    Z = 0.0193339*r + 0.1191920*g + 0.9503041*b
    return X, Y, Z

def XYZ_to_xyY(X: float, Y: float, Z: float) -> tuple[float, float, float]:
    s = X + Y + Z
    if s == 0:
        return 1/3, 1/3, 0
    x = X / s
    y = Y / s
    return x, y, Y

def xyY_to_XYZ(x: float, y: float, Y: float) -> tuple[float, float, float]:
    if y == 0:
        return 0.0, 0.0, 0.0
    X = x * Y / y
    Z = (1.0 - x - y) * Y / y
    return X, Y, Z

def move_into_sRGB(x: float, y: float) -> tuple[float, float, bool]:
    """If the xy chromaticity coordinate is outside the sRGB gamut, this function moves the color towards the D65 white point
    until it is within the sRGB gamut If it is inside the gamut, the output values are the same as the input.
    The boolean is true if the point is inside the sRGB gamut, or false if it is not."""

    def point_in_triangle(p: Point, a: Point, b: Point, c: Point) -> bool:
        """Returns True if p is inside or on the boundary of triangle abc."""
        v0 = (c[0] - a[0], c[1] - a[1])
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (p[0] - a[0], p[1] - a[1])
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if den == 0.0:
            return False
        u = (v2[0] * v1[1] - v1[0] * v2[1]) / den
        v = (v0[0] * v2[1] - v2[0] * v0[1]) / den
        return u >= 0.0 and v >= 0.0 and (u + v) <= 1.0
    
    def segment_intersection(p1: Point, p2: Point, q1: Point, q2: Point) -> Point | None:
        """Intersection of segments p1->p2 and q1->q2, or None if they do not intersect."""
        rx, ry = p2[0] - p1[0], p2[1] - p1[1]
        sx, sy = q2[0] - q1[0], q2[1] - q1[1]
        denom = rx * sy - ry * sx
        if abs(denom) < 1e-12:
            return None
        qpx, qpy = q1[0] - p1[0], q1[1] - p1[1]
        t = (qpx * sy - qpy * sx) / denom
        u = (qpx * ry - qpy * rx) / denom
        return (p1[0] + t * rx, p1[1] + t * ry) if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0 else None
    
    if point_in_triangle((x, y), SRGB_RED, SRGB_GREEN, SRGB_BLUE):
        return x, y, True
    edges = [(SRGB_RED, SRGB_GREEN), (SRGB_GREEN, SRGB_BLUE), (SRGB_BLUE, SRGB_RED)]
    for a, c in edges:
        i = segment_intersection(SRGB_WHITE, (x, y), a, c)
        if i is not None:
            return i[0], i[1], False
    return SRGB_WHITE[0], SRGB_WHITE[1], False


def XYZ_to_RGB(X: float, Y: float, Z: float) -> tuple[int, int, int, bool, bool]:
    """Converts CIE xyz chromaticity coordinates to sRGB.
    If the color lies outside the sRGB gamut, it is shifted towards sRGB's D65 white point."""
    r = 3.2404542 * X + (-1.5371385) * Y + (-0.4985314) * Z
    g = -0.9692660 * X +  1.8760108 * Y +  0.0415560 * Z
    b = 0.0556434 * X + (-0.2040259) * Y +  1.0572252 * Z
    hi = max(r, g, b)
    lo = min(r, g, b)
    max_bright = hi > 1.001
    in_gamut = lo >= 0.0
    if max_bright:
        if in_gamut:
            r /= hi
            g /= hi
            b /= hi
        else:
            r = (r - lo) / (hi - lo)
            g = (g - lo) / (hi - lo)
            b = (b - lo) / (hi - lo)
    elif not in_gamut:
        r = (r - lo) * hi / (hi - lo)
        g = (g - lo) * hi / (hi - lo)
        b = (b - lo) * hi / (hi - lo)
    R = 12.92 * r if r <= 0.0031308 else 1.055 * (r ** (1 / 2.4)) - 0.055
    G = 12.92 * g if g <= 0.0031308 else 1.055 * (g ** (1 / 2.4)) - 0.055
    B = 12.92 * b if b <= 0.0031308 else 1.055 * (b ** (1 / 2.4)) - 0.055
    return round(clamp(R)*255), round(clamp(G)*255), round(clamp(B)*255), in_gamut, max_bright

def max_Y(x: float, y: float) -> float:
    if y <= 0.0:
        return 0.0
    X = x / y
    Z = (1.0 - x - y) / y
    kr = 3.2404542 * X - 1.5371385 - 0.4985314 * Z
    kg = -0.9692660 * X + 1.8760108 + 0.0415560 * Z
    kb = 0.0556434 * X - 0.2040259 + 1.0572252 * Z
    return min(1.0 / abs(kr), 1.0 / abs(kg), 1.0 / abs(kb))

def temp_to_xyY(t: float, daylight: bool = False) -> tuple[float, float, float]:
    """Converts color temp to CIE color coordinates. Formulas from:
    https://web.archive.org/web/20190303161843/http://pdfs.semanticscholar.org/cc7f/c2e67601ccb1a8fec048c9b78a4224c34d26.pdf
    by Bongsoon Kang et al., extended below 1600 K as needed. It is most accurate above 1600 K.
    If daylight is set to true, it provides a value in the daylight locus, rather than the color of a blackbody. The
    daylight locus is slightly above (greener than) the Planckian or blackbody locus. Note that the daylight option
    breaks down when t < 3000."""
    if daylight:
        if t < 7000:
            x = -4607000000/t**3 + 2967800/t**2 + 99.11/t + 0.244063
        else:
            x = -2006400000/t**3 + 1901800/t**2 + 247.48/t + 0.23704
        y = -3*x**2 + 2.87*x - 0.275
    else:
        if t < 4000:
            x = -266123900/t**3 - 234358/t**2 + 877.6956/t + 0.17991
            if t < 2222:
                y = -1.1063814*x**3 - 1.3481102*x**2 + 2.18555832*x - 0.20219683
            else:
                y = -0.9549476*x**3 - 1.37418593*x**2 + 2.09137015*x - 0.16748867
        else:
            x = -3025846900/t**3 + 2107037.9/t**2 + 222.6347/t + 0.24039
            y = 3.081758*x**3 - 5.8733867*x**2 + 3.75112997*x - 0.37001483
    x1, y1, _ = move_into_sRGB(x, y)
    Y = max_Y(x1, y1)
    return x, y, Y

def xy_to_uv(x: float, y: float) -> tuple[float, float]:
    """Converts CIE 1931 xy coordinates to the CIE 1960 UCS or uv color system."""
    u = (4*x) / (-2*x + 12*y + 3)
    v = (6*y) / (-2*x + 12*y + 3)
    return u, v

def xy_to_cct_duv(x: float, y: float) -> tuple[float, float]:
    """Calculates correlated color temperature and Duv of an illuminant given its CIE xy coordinates. Return value is
    (cct, Duv)

    Correlated color temperature measures how blue or orange a light source is, higher color temperature means the light is
    more blue. The color #ffffff in sRGB has a CCT of about 6500 K.
    Duv measures how green or purple a light is. A positive Duv means the light is greener than a blackbody of the same CCT,
    while a negative Duv means the light is more purple than that blackbody."""
    u, v = xy_to_uv(x, y)
    best_t = None
    best_dist = float("inf")
    best_u = best_v = 0.0
    for t in range(1000, 50001, 5):
        xb, yb, _ = temp_to_xyY(t)
        ub, vb = xy_to_uv(xb, yb)
        d = (u-ub)**2 + (v-vb)**2
        if d <= best_dist:
            best_dist = d
            best_t = t
            best_u = ub
            best_v = vb
    if best_t == 50000:
        for t in range(51000, 1000001, 1000):
            xb, yb, _ = temp_to_xyY(t)
            ub, vb = xy_to_uv(xb, yb)
            d = (u-ub)**2 + (v-vb)**2
            if d <= best_dist:
                best_dist = d
                best_t = t
                best_u = ub
                best_v = vb
    dist = sqrt(best_dist)
    sign = 1 if (best_u - u) + (v - best_v) > 0 else -1
    return float(best_t), sign * dist

def rgb_to_cct_duv(R: int, G: int, B: int) -> tuple[float, float]:
    """Converts sRGB values to correlated color temperature and DUV."""
    X, Y, Z = RGB_to_XYZ(R, G, B)
    x, y, _ = XYZ_to_xyY(X, Y, Z)
    return xy_to_cct_duv(x, y)

def print_color_patch(r, g, b, width=15, height=4) -> None:
    """Prints a color patch with the given RGB value."""
    for _ in range(height):
        print(f"\033[48;2;{r};{g};{b}m" + " " * width + "\033[0m")

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Syntax:")
        print("python3 color_converter.py rgb <R> <G> <B>")
        print("python3 color_converter.py hex <hexcode> (example: ffe6d0, do not include #)")
        print("python3 color_converter.py xyy <x> <y> [Y] (Y defaults to 1 if not specified)")
        print("python3 color_converter.py xyz <x> <y> <z>")
        print("python3 color_converter.py temp <T> [daylight] \033[3m(use the word 'daylight' to indicate daylight rather than black body)")
        exit(1)
    arg1 = sys.argv[1].lower()
    if arg1 == "rgb":
        r = int(sys.argv[2])
        g = int(sys.argv[3])
        b = int(sys.argv[4])
        i = True
        br = False
        X, Y, Z = RGB_to_XYZ(r, g, b)
        x, y, _ = XYZ_to_xyY(X, Y, Z) # capital Y is the same in both
    elif arg1 == "hex":
        s = sys.argv[2]
        color = int(s, 16)
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        i = True
        br = False
        X, Y, Z = RGB_to_XYZ(r, g, b)
        x, y, _ = XYZ_to_xyY(X, Y, Z) # capital Y is the same in both
    elif arg1 == "xyy":
        x = float(sys.argv[2])
        y = float(sys.argv[3])
        Y = max_Y(x, y) if len(sys.argv) == 4 else float(sys.argv[4])
        X, _, Z = xyY_to_XYZ(x, y, Y)
        r, g, b, i, br = XYZ_to_RGB(X, Y, Z)
    elif arg1 == "xyz":
        X = float(sys.argv[2])
        Y = float(sys.argv[3])
        Z = float(sys.argv[4])
        x, y, _ = XYZ_to_xyY(X, Y, Z)
        r, g, b, i, br = XYZ_to_RGB(X, Y, Z)
    elif arg1 == "temp":
        t = float(sys.argv[2])
        d = len(sys.argv) == 4 and sys.argv[3].lower() == "daylight"
        x, y, Y = temp_to_xyY(t, d)
        X, _, Z = xyY_to_XYZ(x, y, Y)
        r, g, b, i, br = XYZ_to_RGB(X, Y, Z)
    print_color_patch(r, g, b)
    cct, duv = xy_to_cct_duv(x, y)
    s = f"\033[38;2;{r};{g};{b}m"
    s += f"RGB({r}, {g}, {b}), hex code #{r:02x}{g:02x}{b:02x}"
    s += f"\nCIE 1931 xyY coordinates: x={x:.4f} y={y:.4f} Y={Y:.4f}"
    s += f"\nCIE 1931 XYZ coordinates: X={X:.4f} Y={Y:.4f} Z={Z:.4f}"
    if abs(duv) <= 0.05:
        s += f"\nCorrelated color temperature: {cct:.0f} K"
        s += f"\nDUV: {duv:.4f}"
    if not i:
        s += f"\nWarning: Color not in sRGB gamut. The displayed value has been moved towards the D65 white point."
    if br:
        s += f"\nWarning: Specified color is above maximum sRGB brightness. Displayed value is darkened (Y value lowered)."
    s += "\033[0m"
    print(s)