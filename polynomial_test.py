import color_converter_2 as cc2
import math
from itertools import chain

BREAKPOINT_1 = 1661.0
BREAKPOINT_2 = 4328.0

if __name__ == "__main__":
    max_squared_error = 0.0
    r = chain(range(800, 10000), range(10000, 100000, 10), range(100000, 5000001, 50))
    t_max_error = 0
    for t in r:
        X, Y, Z = cc2.temp_to_XYZ(t)
        Xp, Yp, Zp = cc2.temp_to_XYZ(t, 1, True)
        x, y, _ = cc2.XYZ_to_xyY(X, Y, Z)
        xp, yp, _ = cc2.XYZ_to_xyY(Xp, Yp, Zp)
        squared_error = (xp - x) ** 2 + (yp - y) ** 2
        if squared_error > max_squared_error:
            max_squared_error = squared_error
            t_max_error = t
    max_error = math.sqrt(max_squared_error)
    
    x1m, y1m, _ = cc2.XYZ_to_xyY(*cc2.temp_to_XYZ(BREAKPOINT_1 - 1e-10, 1, True))
    x1p, y1p, _ = cc2.XYZ_to_xyY(*cc2.temp_to_XYZ(BREAKPOINT_1 + 1e-10, 1, True))
    x2m, y2m, _ = cc2.XYZ_to_xyY(*cc2.temp_to_XYZ(BREAKPOINT_2 - 1e-10, 1, True))
    x2p, y2p, _ = cc2.XYZ_to_xyY(*cc2.temp_to_XYZ(BREAKPOINT_2 + 1e-10, 1, True))
    gap_1 = math.sqrt((x1p - x1m) ** 2 + (y1p - y1m) ** 2)
    gap_2 = math.sqrt((x2p - x2m) ** 2 + (y2p - y2m) ** 2)

    print(f"Max error: {max_error:.8f} at T = {t_max_error}")
    print(f"Gaps at polynomial breaks: {gap_1:.8f}, {gap_2:.8f}")
    print()

    for t in [800, 2000, 3000, 4000, t_max_error, 5000, 6500, 8000, 10000, 25000, 100000, float("inf")]:
        Xp, Yp, Zp = cc2.temp_to_XYZ(t, 1, True)
        xp, yp, _ = cc2.XYZ_to_xyY(Xp, Yp, Zp)
        x, y, _ = cc2.XYZ_to_xyY(*cc2.temp_to_XYZ(t, 1, False))
        error = math.sqrt((x - xp) ** 2 + (y - yp) ** 2)
        cct, duv = cc2.XYZ_to_CCT_Duv(Xp, Yp, Zp)
        print(f"{t} K: {error:.8f} (Duv: {duv:.8f})")