import color_converter_2 as cc2
from PIL import Image
import math

width, height = 1024, 1024

img = Image.new("RGBA", (width, height))
pixels = img.load()
COLOR_SPACE = cc2.SRGB

if __name__ == "__main__":
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

    img.save("hsv_circle.png")