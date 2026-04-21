import sys
from math import sqrt

def rgb_to_cie(R: int, G: int, B: int) -> tuple[float, float]:
    """Converts sRGB color values to the CIE 1931 color space."""
    r = (R / 3294.6) if R <= 10 else ((R/255 + 0.055)/1.055)**2.4
    g = (G / 3294.6) if G <= 10 else ((G/255 + 0.055)/1.055)**2.4
    b = (B / 3294.6) if B <= 10 else ((B/255 + 0.055)/1.055)**2.4
    x = 0.4124564*r + 0.3575761*g + 0.1804375*b
    y = 0.2126729*r + 0.7151522*g + 0.0721750*b
    z = 0.0193339*r + 0.1191920*g + 0.9503041*b
    s = x + y + z
    return (1/3, 1/3) if s == 0 else (x/s, y/s)

def cie_to_rgb(x: float, y: float) -> tuple[int, int, int, bool]:
    """Converts CIE xy chromaticity coordinates to sRGB, normalized so at least 1 of the RGB values is 255 (100%).
    If the color lies outside the sRGB gamut, it is shifted towards sRGB's D65 white point."""
    X = x / y
    Y = 1
    Z = ((1 - x - y) / y) * Y
    r = 3.2404542 * X + (-1.5371385) * Y + (-0.4985314) * Z
    g = -0.9692660 * X +  1.8760108 * Y +  0.0415560 * Z
    b = 0.0556434 * X + (-0.2040259) * Y +  1.0572252 * Z
    maximum = max(r, g, b)
    r /= maximum
    g /= maximum
    b /= maximum
    maximum = max(r, g, b)
    minimum = min(r, g, b)
    in_gamut = minimum >= 0.0
    if not in_gamut:
        r = (r - minimum) / (maximum - minimum)
        g = (g - minimum) / (maximum - minimum)
        b = (b - minimum) / (maximum - minimum)
    R = 12.92 * r if r <= 0.0031308 else 1.055 * (r ** (1 / 2.4)) - 0.055
    G = 12.92 * g if g <= 0.0031308 else 1.055 * (g ** (1 / 2.4)) - 0.055
    B = 12.92 * b if b <= 0.0031308 else 1.055 * (b ** (1 / 2.4)) - 0.055
    return round(R*255), round(G*255), round(B*255), in_gamut

def temp_to_cie(t: float, daylight: bool = False) -> tuple[float, float]:
    """Converts color temp to CIE color coordinates. Formulas from:
    https://web.archive.org/web/20190303161843/http://pdfs.semanticscholar.org/cc7f/c2e67601ccb1a8fec048c9b78a4224c34d26.pdf
    by Bongsoon Kang et al., extended below 1600 K as needed. It is most accurate above 1600 K.
    If daylight is set to true, it provides a value in the daylight locus, rather than the color of a blackbody. The
    daylight locus is slightly above (greener than) the Planckian or blackbody locus. Note that the daylight option
    breaks down when t < 4000."""
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
    return x, y

def temp_to_rgb(t: float, daylight: bool = False) -> tuple[int, int, int, bool]:
    """Converts color temp to sRGB color coordinates. If daylight is true, it provides a value in the daylight locus,
    rather than the Planckian (blackbody) locus."""
    x, y = temp_to_cie(t, daylight)
    return cie_to_rgb(x, y)

def xy_to_uv(x: float, y: float) -> tuple[float, float]:
    """Converts CIE 1931 xy coordinates to the CIE 1960 UCS or uv color system."""
    u = (4*x) / (-2*x + 12*y + 3)
    v = (6*y) / (-2*x + 12*y + 3)
    return u, v

def cie_to_cct_duv(x: float, y: float) -> tuple[float, float]:
    """Calculates correlated color temperature and DUV of an illuminant given its CIE xy coordinates.
    Correlated color temperature measures how blue or orange a light source is, higher color temperature means the light is
    more blue. The color #ffffff in sRGB has a CCT of about 6500 K.
    DUV measures how green or purple a light is. A positive DUV means the light is greener than a blackbody of the same CCT,
    while a negative DUV means the light is more purple than that blackbody.
    CCT and DUV are most meaningful for lights that are relatively close to a blackbody, so it makes little sense to speak
    of the CCT of say, #00ff00. For this reason, CCT and DUV are printed only when abs(DUV) <= 0.05."""
    u, v = xy_to_uv(x, y)
    best_t = None
    best_dist = float("inf")
    best_u = best_v = 0.0
    for t in range(1000, 50001, 5):
        xb, yb = temp_to_cie(t)
        ub, vb = xy_to_uv(xb, yb)
        d = (u-ub)**2 + (v-vb)**2
        if d <= best_dist:
            best_dist = d
            best_t = t
            best_u = ub
            best_v = vb
    if best_t == 50000:
        for t in range(51000, 1000001, 1000):
            xb, yb = temp_to_cie(t)
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

def rgb_to_cct_duv(r: int, g: int, b: int) -> tuple[float, float]:
    """Converts sRGB values to correlated color temperature and DUV."""
    x, y = rgb_to_cie(r, g, b)
    return cie_to_cct_duv(x, y)

def print_color_patch(r, g, b, width=15, height=4):
    """Prints a color patch with the given RGB value."""
    for _ in range(height):
        print(f"\033[48;2;{r};{g};{b}m" + " " * width + "\033[0m")

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Syntax:")
        print("python3 color_converter.py rgb <R> <G> <B>")
        print("python3 color_converter.py hex <hexcode> (example: ffe6d0, do not include #)")
        print("python3 color_converter.py cie <x> <y>")
        print("python3 color_converter.py temp <T> [daylight] \033[3m(use the word 'daylight' to indicate daylight rather than black body)")
        exit(1)
    if sys.argv[1] == "rgb" or sys.argv[1] == "hex":
        if sys.argv[1] == "rgb":
            r = int(sys.argv[2])
            g = int(sys.argv[3])
            b = int(sys.argv[4])
        else:
            s = sys.argv[2]
            color = int(s, 16)
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
        print_color_patch(r, g, b)
        x, y = rgb_to_cie(r, g, b)
        cct, duv = cie_to_cct_duv(x, y)
        s = f"\033[38;2;{r};{g};{b}m"
        s += f"RGB({r}, {g}, {b}), hex code #{r:02x}{g:02x}{b:02x}"
        s += f"\nCIE 1931 xy coordinates: ({x:.4f}, {y:.4f})"
        if abs(duv) <= 0.05:
            s += f"\nCorrelated color temperature: {cct:.0f} K"
            s += f"\nDUV: {duv:.4f}"
        s += "\033[0m"
        print(s)
    elif sys.argv[1] == "temp":
        t = float(sys.argv[2])
        d = len(sys.argv) == 4 and sys.argv[3] == "daylight"
        x, y = temp_to_cie(t, d)
        r, g, b, i = cie_to_rgb(x, y)
        print_color_patch(r, g, b)
        s = f"\033[38;2;{r};{g};{b}m"
        s += f"RGB({r}, {g}, {b}), hex code #{r:02x}{g:02x}{b:02x}"
        s += f"\nCIE 1931 xy coordinates: ({x:.4f}, {y:.4f})"
        cct, duv = cie_to_cct_duv(x, y)
        if abs(duv) <= 0.05:
            s += f"\nCorrelated color temperature: {cct:.0f} K"
            s += f"\nDUV: {duv:.4f}"
        if not i:
            s += "\nWarning: Not in sRGB color gamut"
        s += "\033[0m"
        print(s)
    elif sys.argv[1] == "cie":
        x = float(sys.argv[2])
        y = float(sys.argv[3])
        r, g, b, i = cie_to_rgb(x, y)
        print_color_patch(r, g, b)
        s = f"\033[38;2;{r};{g};{b}m"
        s += f"RGB({r}, {g}, {b}), hex code #{r:02x}{g:02x}{b:02x}"
        s += f"\nCIE 1931 xy coordinates: ({x:.4f}, {y:.4f})"
        cct, duv = cie_to_cct_duv(x, y)
        if abs(duv) <= 0.05:
            s += f"\nCorrelated color temperature: {cct:.0f} K"
            s += f"\nDUV: {duv:.4f}"
        if not i:
            s += "\nWarning: Not in sRGB color gamut"
        s += "\033[0m"
        print(s)