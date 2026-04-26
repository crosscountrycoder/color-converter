import color_converter_2 as cc2
from PIL import Image
import math
import sys

width, height = 1024, 1024
img = Image.new("RGBA", (width, height))
pixels = img.load()

if __name__ == "__main__":
    color_space = sys.argv[1].lower() if len(sys.argv) >= 2 else None

    if color_space is None: 
        icc_path = None
        file_name = "hsv_circle.png"
    elif color_space == "adobe": 
        icc_path = "icc_profiles/AdobeCompat-v4.icc"
        file_name = "hsv_circle_adobe.png"
    elif color_space == "p3": 
        icc_path = "icc_profiles/DisplayP3-v4.icc"
        file_name = "hsv_circle_p3.png"
    elif color_space == "rec2020": 
        icc_path = "icc_profiles/Rec2020-v4.icc"
        file_name = "hsv_circle_rec2020.png"
    else: 
        icc_path = "icc_profiles/sRGB-v4.icc"
        file_name = "hsv_circle_srgb.png"

    for y in range(height):
        for x in range(width):
            # Normalize coordinates to -1..1
            half_width = width / 2
            rel_x = (x + 0.5 - half_width) / half_width
            rel_y = -(y + 0.5 - half_width) / half_width

            # Formula to generate HSV color circle
            d = math.sqrt(rel_x**2 + rel_y**2)
            V = 1
            S = min(d, 1)
            H = (math.atan2(rel_x, rel_y)*180/math.pi) % 360
            r, g, b = cc2.HSV_to_RGB(H, S, V)
            R = round(r*255)
            G = round(g*255)
            B = round(b*255)
            A = 0 if d > 1 else 255
            pixels[x, y] = (R, G, B, A)

    save_kwargs = {}
    if icc_path is not None:
        with open(icc_path, "rb") as f:
            save_kwargs["icc_profile"] = f.read()
    img.save(file_name, **save_kwargs)
    print(f"Wrote {file_name}")