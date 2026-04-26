import sys
import csv
import numpy as np
import math
from dataclasses import dataclass

Point = tuple[float, float]
Triplet = tuple[float, float, float]
Polygon = list[tuple[float, float]]

C2 = 1.438776877e-2  # second radiation constant in Planck's law (m*K)

@dataclass(frozen=True)
class RGBSpace:
    red: Point
    green: Point
    blue: Point
    white: Point
    transfer_curve: str

D65 = (0.3127, 0.3290) # D65 white point
SRGB       = RGBSpace((0.6400, 0.3300), (0.3000, 0.6000), (0.1500, 0.0600), D65, "srgb")
DISPLAY_P3 = RGBSpace((0.6800, 0.3200), (0.2650, 0.6900), (0.1500, 0.0600), D65, "srgb")
ADOBE_RGB  = RGBSpace((0.6400, 0.3300), (0.2100, 0.7100), (0.1500, 0.0600), D65, "2.2")
REC_2020   = RGBSpace((0.7079, 0.2920), (0.1702, 0.7965), (0.1314, 0.0459), D65, "rec2020")

def load_cie_1931_csv(path: str):
    wavelengths_nm = []
    xbar = []
    ybar = []
    zbar = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            wavelengths_nm.append(float(row[0]))
            xbar.append(float(row[1]))
            ybar.append(float(row[2]))
            zbar.append(float(row[3]))
    return (np.array(wavelengths_nm, dtype=float),np.array(xbar, dtype=float),np.array(ybar, dtype=float),np.array(zbar, dtype=float),)

WAVELENGTHS_NM, XBAR, YBAR, ZBAR = load_cie_1931_csv("CIE_xyz_1931_2deg.csv")
WAVELENGTHS_M = WAVELENGTHS_NM * 1e-9

def load_xy_polygon(filename: str) -> Polygon:
    polygon = []
    with open(filename, "r", newline="") as file:
        reader = csv.reader(file)
        next(reader)  # skip header
        for row in reader:
            x = float(row[1])
            y = float(row[2])
            polygon.append((x, y))
    return polygon

def distance_point_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    closest_x = ax + t * dx
    closest_y = ay + t * dy
    return math.hypot(px - closest_x, py - closest_y)

def point_in_polygon_or_near(x: float, y: float, polygon, epsilon=5e-5) -> bool:
    n = len(polygon)
    # Check if point is on or near boundary
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        if distance_point_to_segment(x, y, ax, ay, bx, by) <= epsilon:
            return True
    # Standard ray-casting point-in-polygon test
    inside = False
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        if (ay > y) != (by > y):
            x_intersect = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < x_intersect:
                inside = not inside
    return inside

def color_is_valid(x: float, y: float, epsilon=5e-5) -> bool:
    polygon = load_xy_polygon("CIE_xy_locus.csv")
    return point_in_polygon_or_near(x, y, polygon, epsilon)

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(x, hi))

def HSL_to_RGB(H: float, S: float, L: float) -> Triplet:
    H %= 360
    C = (1 - abs(2 * L - 1)) * S
    Hp = H / 60
    X = C * (1- abs(Hp % 2 - 1))

    if Hp < 1:
        r1, g1, b1 = C, X, 0
    elif Hp < 2:
        r1, g1, b1 = X, C, 0
    elif Hp < 3:
        r1, g1, b1 = 0, C, X
    elif Hp < 4:
        r1, g1, b1 = 0, X, C
    elif Hp < 5:
        r1, g1, b1 = X, 0, C
    else:
        r1, g1, b1 = C, 0, X
    
    m = L - C / 2
    R = r1 + m
    G = g1 + m
    B = b1 + m
    return R, G, B

def HSV_to_RGB(H: float, S: float, V: float) -> Triplet:
    H %= 360
    C = V * S
    Hp = H / 60
    X = C * (1- abs(Hp % 2 - 1))

    if Hp < 1:
        r1, g1, b1 = C, X, 0
    elif Hp < 2:
        r1, g1, b1 = X, C, 0
    elif Hp < 3:
        r1, g1, b1 = 0, C, X
    elif Hp < 4:
        r1, g1, b1 = 0, X, C
    elif Hp < 5:
        r1, g1, b1 = X, 0, C
    else:
        r1, g1, b1 = C, 0, X
    
    m = V - C
    R = r1 + m
    G = g1 + m
    B = b1 + m
    return R, G, B

def RGB_to_HSV(R: float, G: float, B: float) -> Triplet:
    V = max(R, G, B)
    delta = V - min(R, G, B)
    if delta == 0:
        H = 0.0
    elif R == V:
        H = 60 * (((G - B) / delta) % 6)
    elif G == V:
        H = 60 * (((B - R) / delta) + 2)
    else:
        H = 60 * (((R - G) / delta) + 4)
    S = 0.0 if V == 0 else delta / V
    return H, S, V

def RGB_to_HSL(R: float, G: float, B: float) -> Triplet:
    cmax = max(R, G, B)
    cmin = min(R, G, B)
    delta = cmax - cmin

    L = (cmax + cmin) / 2

    if delta == 0:
        H = 0.0
        S = 0.0
    else:
        if cmax == R:
            H = 60 * (((G - B) / delta) % 6)
        elif cmax == G:
            H = 60 * (((B - R) / delta) + 2)
        else:
            H = 60 * (((R - G) / delta) + 4)

        S = delta / (1 - abs(2 * L - 1))

    return H, S, L

def RGB_to_XYZ_matrix(space: RGBSpace = SRGB) -> np.ndarray:
    R = np.array(xyY_to_XYZ(*space.red), dtype=float)
    G = np.array(xyY_to_XYZ(*space.green), dtype=float)
    B = np.array(xyY_to_XYZ(*space.blue), dtype=float)
    W = np.array(xyY_to_XYZ(*space.white), dtype=float)
    M = np.column_stack([R, G, B])
    S = np.linalg.solve(M, W)
    return M @ np.diag(S)

def RGB_to_linear(R: float, G: float, B: float, curve: str) -> Triplet:
    if curve == "srgb":
        r = R / 12.92 if R <= 0.04045 else ((R + 0.055)/1.055)**2.4
        g = G / 12.92 if G <= 0.04045 else ((G + 0.055)/1.055)**2.4
        b = B / 12.92 if B <= 0.04045 else ((B + 0.055)/1.055)**2.4
    elif curve == "rec2020":
        ALPHA, BETA = 1.0993, 0.0181
        r = R / 4.5 if R <= 4.5 * BETA else ((R + ALPHA - 1) / ALPHA) ** (1 / 0.45)
        g = G / 4.5 if G <= 4.5 * BETA else ((G + ALPHA - 1) / ALPHA) ** (1 / 0.45)
        b = B / 4.5 if B <= 4.5 * BETA else ((B + ALPHA - 1) / ALPHA) ** (1 / 0.45)
    else:
        r = R ** float(curve)
        g = G ** float(curve)
        b = B ** float(curve)
    return clamp(r), clamp(g), clamp(b)

def linear_to_RGB(r: float, g: float, b: float, curve: str) -> Triplet:
    if curve == "srgb":
        R = 12.92 * r if r <= 0.0031308 else 1.055 * (r ** (1 / 2.4)) - 0.055
        G = 12.92 * g if g <= 0.0031308 else 1.055 * (g ** (1 / 2.4)) - 0.055
        B = 12.92 * b if b <= 0.0031308 else 1.055 * (b ** (1 / 2.4)) - 0.055
    elif curve == "rec2020":
        ALPHA, BETA = 1.0993, 0.0181
        R = 4.5 * r if r <= BETA else ALPHA * (r ** 0.45) - (ALPHA - 1)
        G = 4.5 * g if g <= BETA else ALPHA * (g ** 0.45) - (ALPHA - 1)
        B = 4.5 * b if b <= BETA else ALPHA * (b ** 0.45) - (ALPHA - 1)
    else:
        R = r ** (1 / float(curve))
        G = g ** (1 / float(curve))
        B = b ** (1 / float(curve))
    return clamp(R), clamp(G), clamp(B)

def xyY_to_XYZ(x: float, y: float, Y: float = 1.0) -> Triplet:
    if y == 0.0:
        raise ValueError("y cannot be zero unless Y is also zero")
    X = x * Y / y
    Z = (1.0 - x - y) * Y / y
    return X, Y, Z

def RGB_to_XYZ(R: float, G: float, B: float, space: RGBSpace = SRGB) -> Triplet:
    r, g, b = RGB_to_linear(R, G, B, space.transfer_curve)
    M = RGB_to_XYZ_matrix(space)
    XYZ = M @ np.array([r, g, b], dtype=float)
    return tuple(float(v) for v in XYZ)

def temp_to_XYZ(T: float) -> Triplet:
    if T < 800:
        raise ValueError("Temperature must be at or above the Draper point (800 K)")
    t = min(T, 1e15) # reduce "infinite" temperature to 1e15 to make calculation possible
    exponent = C2 / (WAVELENGTHS_M * t)
    spd = 1.0 / ((WAVELENGTHS_M ** 5) * np.expm1(exponent))
    X = np.sum(spd * XBAR)
    Y = np.sum(spd * YBAR)
    Z = np.sum(spd * ZBAR)
    # Normalize so Y = 1
    return float(X / Y), 1.0, float(Z / Y)

def daylight_to_XYZ(T: float) -> Triplet:
    if 4000 <= T <= 25000:
        if T <= 7000:
            x = 0.244063 + 99.11/T + 2967800/T**2 - 4.607e9/T**3
        else:
            x = 0.23704 + 247.48/T + 1901800/T**2 - 2.0064e9/T**3
    else:
        raise ValueError("Temperature for daylight must be between 4000 and 25000 K")
    y = -3*x**2 + 2.87*x - 0.275
    X, Y, Z = xyY_to_XYZ(x, y, 1)
    return X, Y, Z

def Lab_to_XYZ(L: float, a: float, b: float, white: Point = D65) -> Triplet: 
    Xn, Yn, Zn = xyY_to_XYZ(*white)
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    DELTA = 6.0 / 29.0
    X = Xn * (fx ** 3 if fx > DELTA else 3 * (DELTA ** 2) * ((fx - 4.0) / 29.0))
    Y = Yn * (fy ** 3 if fy > DELTA else 3 * (DELTA ** 2) * ((fy - 4.0) / 29.0))
    Z = Zn * (fz ** 3 if fz > DELTA else 3 * (DELTA ** 2) * ((fz - 4.0) / 29.0))
    return X, Y, Z

def XYZ_to_uv_prime(X: float, Y: float, Z: float) -> Point:
    denom = X + 15*Y + 3*Z
    if denom == 0:
        return 0.0, 0.0
    else:
        return 4*X/denom, 9*Y/denom

def Luv_to_XYZ(L: float, u_star: float, v_star: float, white: Point = D65) -> Triplet:
    if L == 0:
        return 0.0, 0.0, 0.0
    Xn, Yn, Zn = xyY_to_XYZ(*white)
    un, vn = XYZ_to_uv_prime(Xn, Yn, Zn)
    u = u_star / (13 * L) + un
    v = v_star / (13 * L) + vn
    DELTA = 6.0 / 29.0
    fy = (L + 16) / 116
    Y = Yn * fy**3 if fy > DELTA else Yn * (3 * DELTA**2 * (fy - 4/29))
    if v == 0:
        return 0.0, 0.0, 0.0
    X = Y * 9 * u / (4 * v)
    Z = Y * (12 - 3*u - 20*v) / (4*v)
    return X, Y, Z   

def spectral_to_XYZ(wavelength_nm: float, normalize: bool = False) -> Triplet:
    if wavelength_nm < WAVELENGTHS_NM[0] or wavelength_nm > WAVELENGTHS_NM[-1]:
        raise ValueError("Wavelength out of range")
    X = np.interp(wavelength_nm, WAVELENGTHS_NM, XBAR)
    Y = np.interp(wavelength_nm, WAVELENGTHS_NM, YBAR)
    Z = np.interp(wavelength_nm, WAVELENGTHS_NM, ZBAR)
    if normalize:
        return float(X) / Y, 1, float(Z) / Y
    return float(X), float(Y), float(Z)

def XYZ_to_RGB(X: float, Y: float, Z: float, space: RGBSpace = SRGB) -> tuple[Triplet, bool, bool]:
    XYZ = np.array([X, Y, Z], dtype=float)
    M = RGB_to_XYZ_matrix(space)
    M_inv = np.linalg.inv(M)
    rgb = M_inv @ XYZ # Linear RGB, possibly out of gamut

    # If channels are outside the (0, 1) range, move towards D65 white point at same Y.
    white_same_Y = np.array([Y, Y, Y], dtype=float)
    out_of_gamut = False
    max_bright = False
    min_channel = np.min(rgb)
    out_of_gamut = min_channel < -1e-8
    if min_channel < 0.0:
        t_values = []
        for c in rgb:
            if c < 0.0:
                t_values.append(-c / (Y - c))
        t = max(t_values)
        rgb = (1.0 - t) * rgb + t * white_same_Y
    max_channel = np.max(rgb)
    max_bright = max_channel > 1 + 1e-8
    if max_channel > 1.0:
        rgb = rgb / max_channel

    rgb = np.clip(rgb, 0.0, 1.0)
    R, G, B = linear_to_RGB(float(rgb[0]), float(rgb[1]), float(rgb[2]), space.transfer_curve)
    return (R, G, B), out_of_gamut, max_bright

def XYZ_to_xyY(X: float, Y: float, Z: float) -> Triplet:
    if X + Y + Z == 0.0:
        return 1/3, 1/3, Y # 1/3, 1/3 is the xy chromaticity of an equal SPD across the visible spectrum
    x = X / (X + Y + Z)
    y = Y / (X + Y + Z)
    return x, y, Y

def XYZ_to_Lab(X: float, Y: float, Z: float, white: Point = D65) -> Triplet:
    Xn, Yn, Zn = xyY_to_XYZ(*white)
    xr = X / Xn
    yr = Y / Yn
    zr = Z / Zn
    DELTA = 6/29
    fx = xr**(1/3) if xr>DELTA**3 else xr/(3*DELTA**2)+4/29
    fy = yr**(1/3) if yr>DELTA**3 else yr/(3*DELTA**2)+4/29
    fz = zr**(1/3) if zr>DELTA**3 else zr/(3*DELTA**2)+4/29
    L = 116 * fy - 16
    a_star = 500 * (fx - fy)
    b_star = 200 * (fy - fz)
    return L, a_star, b_star

def XYZ_to_Luv(X: float, Y: float, Z: float, white: Point = D65) -> Triplet:
    if L == 0:
        return 0.0, 0.0, 0.0
    Xn, Yn, Zn = xyY_to_XYZ(*white)
    u, v = XYZ_to_uv_prime(X, Y, Z)
    un, vn = XYZ_to_uv_prime(Xn, Yn, Zn)
    yr = Y / Yn
    DELTA = 6/29
    L = (yr**(1/3) if yr>DELTA**3 else yr/(3*DELTA**2)+4/29) * 116 - 16
    u_star = 13 * L * (u - un)
    v_star = 13 * L * (v - vn)
    return L, u_star, v_star

def XYZ_to_CCT_Duv(X: float, Y: float, Z: float) -> tuple[float, float]:
    u, v = XYZ_to_uv_prime(X, Y, Z)
    v *= 2/3
    Tmin = 800.0 # Draper point, where blackbody radiation starts to become visible
    Tmax = 5000000.0 # At 5000000 K, blackbody radiation reaches limit of x=0.2399, y=0.2340
    samples = 200

    # Search over reciprocal temperature, which behaves better numerically
    m_min = 1 / Tmax
    m_max = 1 / Tmin
    best_m = m_min
    best_d2 = float("inf")
    for i in range(samples):
        m = m_min + (m_max - m_min) * i / (samples - 1)
        T = 1 / m
        Xt, Yt, Zt = temp_to_XYZ(T)
        ut, vt = XYZ_to_uv_prime(Xt, Yt, Zt)
        vt *= 2/3
        d2 = (u - ut)**2 + (v - vt)**2
        if d2 < best_d2:
            best_d2 = d2
            best_m = m
    
    # Refine locally with ternary search
    step = (m_max - m_min) / (samples - 1)
    lo = max(m_min, best_m - 2 * step)
    hi = min(m_max, best_m + 2 * step)
    for _ in range(20):
        m1 = lo + (hi - lo) / 3
        m2 = hi - (hi - lo) / 3
        u1, v1 = XYZ_to_uv_prime(*temp_to_XYZ(1/m1))
        u2, v2 = XYZ_to_uv_prime(*temp_to_XYZ(1/m2))
        v1 *= 2/3
        v2 *= 2/3
        d1 = (u - u1)**2 + (v - v1)**2
        d2 = (u - u2)**2 + (v - v2)**2
        if d1 < d2:
            hi = m2
        else:
            lo = m1
    m_best = (lo + hi) / 2
    CCT = 1 / m_best
    ub, vb = XYZ_to_uv_prime(*temp_to_XYZ(CCT))
    vb *= 2/3
    Duv = (1 if v >= vb else -1) * ((u - ub) ** 2 + (v - vb) ** 2) ** 0.5
    return CCT, Duv

def print_color_patch(r, g, b, width=15, height=4) -> None:
    """Prints a color patch with the given RGB value."""
    for _ in range(height):
        print(f"\033[48;2;{r};{g};{b}m" + " " * width + "\033[0m")

def get_colorspace(color_space: str) -> RGBSpace:
    color_space = color_space.lower()
    if color_space == "adobe": return ADOBE_RGB
    elif color_space == "p3": return DISPLAY_P3
    elif color_space == "rec2020": return REC_2020
    else: return SRGB

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Syntax:")
        print("python3 color_converter_2.py rgb <R> <G> <B> [srgb|adobe|p3|rec2020]")
        print("python3 color_converter_2.py hex <hexcode> [srgb|adobe|p3|rec2020]")
        print("python3 color_converter_2.py hsl <H> <S> <L> [srgb|adobe|p3|rec2020]")
        print("python3 color_converter_2.py hsv <H> <S> <V> [srgb|adobe|p3|rec2020]")
        print("python3 color_converter_2.py xyy <x> <y> [Y] (Y defaults to 1 if not specified)")
        print("python3 color_converter_2.py xyz <x> <y> <z>")
        print("python3 color_converter_2.py temp <T>")
        print("python3 color_converter_2.py daylight <T> - T must be between 4000 and 25000")
        print("python3 color_converter_2.py Lab <L> <a> <b>")
        print("python3 color_converter_2.py Luv <L> <u> <v>")
        print("python3 color_converter_2.py spectral <wavelength> [n] - wavelength is in nm, n normalizes to max brightness")
        exit(1)
    arg1 = sys.argv[1].lower()
    if arg1 == "rgb":
        rs, gs, bs = sys.argv[2], sys.argv[3], sys.argv[4]
        color_space = SRGB if len(sys.argv) == 5 else get_colorspace(sys.argv[5])
        if "." in rs or "." in gs or "." in bs:
            red = float(rs)
            green = float(gs)
            blue = float(bs)
        else:
            red = float(rs) / 255
            green = float(gs) / 255
            blue = float(bs) / 255
        X, Y, Z = RGB_to_XYZ(red, green, blue, color_space)
    elif arg1 == "hex":
        color_space = SRGB if len(sys.argv) == 3 else get_colorspace(sys.argv[3])
        color = int(sys.argv[2], 16)
        red = ((color >> 16) & 0xFF) / 255
        green = ((color >> 8) & 0xFF) / 255
        blue = (color & 0xFF) / 255
        X, Y, Z = RGB_to_XYZ(red, green, blue, color_space)
    elif arg1 == "hsl":
        color_space = SRGB if len(sys.argv) == 5 else get_colorspace(sys.argv[5])
        hue, sat, lum = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
        red, green, blue = HSL_to_RGB(hue, sat, lum)
        X, Y, Z = RGB_to_XYZ(red, green, blue, SRGB)
    elif arg1 == "hsv":
        color_space = SRGB if len(sys.argv) == 5 else get_colorspace(sys.argv[5])
        hue, sat, val = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
        red, green, blue = HSV_to_RGB(hue, sat, val)
        X, Y, Z = RGB_to_XYZ(red, green, blue, SRGB)
    elif arg1 == "xyy":
        x0, y0, Y0 = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) >= 5 else 1.0
        X, Y, Z = xyY_to_XYZ(x0, y0, Y0)
    elif arg1 == "xyz":
        X, Y, Z = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    elif arg1 == "temp":
        X, Y, Z = temp_to_XYZ(float(sys.argv[2]))
    elif arg1 == "daylight":
        X, Y, Z = daylight_to_XYZ(float(sys.argv[2]))
    elif arg1 == "lab":
        X, Y, Z = Lab_to_XYZ(float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]))
    elif arg1 == "luv":
        X, Y, Z = Luv_to_XYZ(float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]))
    elif arg1 == "spectral":
        X, Y, Z = spectral_to_XYZ(float(sys.argv[2]), (len(sys.argv) >= 4 and sys.argv[3].lower() == "n"))
    x, y, _ = XYZ_to_xyY(X, Y, Z)
    RGB, out_of_sRGB, max_bright = XYZ_to_RGB(X, Y, Z, SRGB)
    RGB_ADOBE, out_of_adobe, _ = XYZ_to_RGB(X, Y, Z, ADOBE_RGB)
    RGB_P3, out_of_p3, _ = XYZ_to_RGB(X, Y, Z, DISPLAY_P3)
    RGB_REC2020, out_of_rec2020, _ = XYZ_to_RGB(X, Y, Z, REC_2020)
    R, G, B = tuple(round(c * 255) for c in RGB)
    RA, GA, BA = tuple(round(c * 255) for c in RGB_ADOBE)
    RP3, GP3, BP3 = tuple(round(c * 255) for c in RGB_P3)
    R20, G20, B20 = tuple(round(c * 255) for c in RGB_REC2020)
    H, S_HSV, V = RGB_to_HSV(R/255, G/255, B/255)
    _, S_HSL, L = RGB_to_HSL(R/255, G/255, B/255)
    hex_value = (R << 16) + (G << 8) + B
    hex = f"{hex_value:06x}"
    cct, duv = XYZ_to_CCT_Duv(X, Y, Z)
    L_lab, a, b = XYZ_to_Lab(X, Y, Z)
    L_luv, u, v = XYZ_to_Luv(X, Y, Z)
    if not color_is_valid(x, y):
        print("Invalid color (cannot be produced by a real color spectrum)")
        exit(1)
    print_color_patch(R, G, B)
    s = f"\033[38;2;{R};{G};{B}m"
    s += f"sRGB({R}, {G}, {B}){("*" if out_of_sRGB else "")}, hex code #{hex}"
    s += f"\nHSV (sRGB): H={H:.2f}° S={S_HSV:.3f} V={V:.3f}"
    s += f"\nHSL (sRGB): H={H:.2f}° S={S_HSL:.3f} V={L:.3f}"
    s += f"\nAdobe RGB: ({RA}, {GA}, {BA})" + ("*" if out_of_adobe else "")
    s += f"; Display P3: ({RP3}, {GP3}, {BP3})" + ("*" if out_of_p3 else "")
    s += f"; Rec. 2020: ({R20}, {G20}, {B20})" + ("*" if out_of_rec2020 else "")
    s += f"\nCIE 1931 xyY coordinates: x={x:.4f} y={y:.4f} Y={Y:.4f}"
    s += f"\nCIE 1931 XYZ coordinates: X={X:.4f} Y={Y:.4f} Z={Z:.4f}"
    s += f"\nCIE Lab coordinates: L={L_lab:.4f} a={a:.4f} b={b:.4f}"
    s += f"\nCIE Luv coordinates: L={L_luv:.4f} u={u:.4f} v={v:.4f}"
    if abs(duv) <= 0.05:
        s += f"\nCorrelated color temperature: {cct:.0f} K (Duv: {duv:.4f})"
    if out_of_sRGB:
        s += f"\nNote: Color not in sRGB gamut. Displayed color (sRGB/HSV/HSL) has been moved towards the D65 white point."
        rx, ry, _ = XYZ_to_xyY(*RGB_to_XYZ(R/255, G/255, B/255, SRGB))
        s += f"\nThe CIE 1931 chromaticity of the displayed color is x={rx:.4f} y={ry:.4f}"
    if max_bright:
        REAL_Y = RGB_to_XYZ(R/255, G/255, B/255, SRGB)[1]
        s += f"\nNote: Specified color is above maximum sRGB brightness. The Y value of the displayed color is {REAL_Y:.4f}"
    s += "\033[0m"
    print(s)