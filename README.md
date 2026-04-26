# color-converter

The Python script color_converter_2.py allows conversion between sRGB color values (specified as RGB values like 149, 177, 255 or
hex values like 95b1ff), CIE 1931 xy coordinates, and correlated color temperature/DUV. It also allows users to convert color
temperature (blackbody or daylight) to sRGB. Coming soon are CIE XYZ, xyY, and LAB color spaces, and HSV/HSL.

## Syntax for color_converter_2.py

This file requires the third-party `numpy` library, which can be installed using `pip install numpy`.

`python3 color_converter_2.py rgb <R> <G> <B>`: Sets the color to the given sRGB value. It accepts either integer arguments in 
the range [0, 255], such as `255 128 0`, or decimals in the range [0, 1], such as `1.0 0.5 0.0`. The RGB value is understood to
be in sRGB.

`python3 color_converter_2.py hex <hex>`: Similar to `rgb`, but using a hex code (such as `ff8000`) rather than individual RGB 
values.

`python3 color_converter_2.py hsl <H> <S> <L>`: Sets the color to the given HSL (hue, saturation, lightness) value, a
transformation of RGB. Hue is given in degrees (red = 0, green = 120, blue = 240), and saturation and lightness are in the range
[0, 1]. Lightness of 0 is always black and lightness 1 is always white.

`python3 color_converter_2.py hsv <H> <S> <V>`: Sets the color to the given HSV (hue, saturation, value) value, a transformation 
of RGB. Hue is given in degrees (red = 0, green = 120, blue = 240), and saturation and value are in the range
[0, 1]. A value of 0 is always black, while a value of 1 means at least one of the RGB values is equal to 1.0 or 255.

`python3 color_converter_2.py xyy <x> <y> [Y]`: Sets the color to the given coordinate in 
[CIE xyY color space](https://en.wikipedia.org/wiki/CIE_1931_color_space). Here, the x and y coordinates represent the
chromaticity (hue + saturation), and Y represents linear brightness relative to RGB white.

`python3 color_converter_2.py xyz [X] [Y] [Z]`: Sets the color to the given coordinate in CIE XYZ color space, a transformation
of xyY color space. Y in XYZ is the same as Y in xyY.

`python3 color_converter_2.py temp <T>`: Sets the color to that of a black body at `T` kelvins. T can range from 800 K (the 
Draper point, below which objects emit negligible visible light) to infinity, where the Planckian locus terminates at
`x=0.2399 y=0.2340`, corresponding to sRGB(148, 177, 255) or hex code 94b1ff. Colors are calculated based on Planck's law
and the CIE color-matching functions in `CIE_xyz_1931_2deg.csv`.

`python3 color_converter_2.py daylight <T>`: Similar to `temp`, but produces a color from the daylight locus rather than the
Planckian (blackbody) locus. Here, T must be between 4000 and 25000. The color `daylight 6500` is exactly the same as the D65
white point which corresponds to RGB(255, 255, 255) in sRGB.

`python3 color_converter_2.py Lab <L> <a> <b>`: Sets the color to the given coordinate in CIE Lab color space.

`python3 color_converter_2.py Lab <L> <a> <b>`: Sets the color to the given coordinate in CIE Luv color space.

`python3 color_converter_2.py spectral <wavelength> [n]`: Sets the color to the spectral color of the given wavelength in
nanometers. If the letter `n` is added after the argument, the brightness is set to its maximum brightness.

## Notes about color_converter_2.py

* The default RGB color space used is sRGB. If a color is outside the sRGB color gamut, it is moved towards the D65 white point
until it is within the gamut. If a color is above the maximum brightness supported in sRGB for the given chromaticity, its
brightness (Y in XYZ/xyY) is reduced.

## color_converter.py

This is an old and deprecated file, `color_converter_2.py` should be used as it has all the capabilities of this file and more,
while being more precise.

## hsv_circle.py

This file requires the third-party `numpy` library, which can be installed using `pip install pillow`.

This file produces `hsv_circle.png`, the circular face at the top of the HSV color cone/cylinder. Hue is the angle clockwise from
top, saturation is distance from center, and value is a constant 1, so the image contains all full-brightness sRGB colors. Any
other sRGB color can be produced by mixing one of these colors with black.

## CSV files

`CIE_xyx_1931_2deg.csv` shows the XYZ coordinates of each spectral color, with Y specifying brightness relative to 555 nm (the
wavelength at which the eyes are most sensitive), and comes from the 
[CIE color matching functions](https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer).

`CIE_xy_locus.csv` shows the xy coordinates of each wavelength, derived from their XYZ coordinates. It is used to determine
whether a color can be produced by a real light spectrum, or is an impossible color.