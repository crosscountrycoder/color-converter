# color-converter

The Python script color_converter_2.py allows conversion between sRGB color values (specified as RGB values like 149, 177, 255 or
hex values like 95b1ff), CIE 1931 xy coordinates, and correlated color temperature/DUV. It also allows users to convert color
temperature (blackbody or daylight) to sRGB. Coming soon are CIE XYZ, xyY, and LAB color spaces, and HSV/HSL.

## Syntax for color_converter_2.py

This file requires the third-party `numpy` library, which can be installed using `pip install numpy`.

`python3 color_converter_2.py rgb <R> <G> <B> [colorspace]`: Sets the color to the given sRGB value. It accepts either integer 
arguments in the range [0, 255], such as `255 128 0`, or decimals in the range [0, 1], such as `1.0 0.5 0.0`. The RGB value is 
understood to be in sRGB. If `colorspace` is set to `adobe`, `p3`, or `rec2020` the color space of the RGB value is interpreted 
as being from the given color space; if it is omitted, or set to any other value, the color is interpreted as sRGB.

`python3 color_converter_2.py hex <hex> [colorspace]`: Similar to `rgb`, but using a hex code rather than individual RGB values. 
The hex code should not include the `#`, for example orange is `ff8000` not `#ff8000`. The `colorspace` argument is the same as 
`rgb`, and defaults to sRGB if not specified.

`python3 color_converter_2.py hsl <H> <S> <L> [colorspace]`: Sets the color to the given HSL (hue, saturation, lightness) value, a
transformation of RGB. Hue is given in degrees (red = 0, green = 120, blue = 240), and saturation and lightness are in the range
[0, 1]. Lightness of 0 is always black and lightness 1 is always white. `colorspace` is same as that of `rgb` and `hex`.

`python3 color_converter_2.py hsv <H> <S> <V> [colorspace]`: Sets the color to the given HSV (hue, saturation, value) value, a 
transformation of RGB. Hue is given in degrees (red = 0, green = 120, blue = 240), and saturation and value are in the range
[0, 1]. A value of 0 is always black, while a value of 1 means at least one of the RGB values is equal to 1.0 or 255. 
`colorspace` is same as that of `rgb` and `hex`.

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

## Output of color_converter_2.py
For any input, the program outputs the following:
* sRGB color, hexcode, HSV and HSL
* RGB values in Adobe RGB, Display P3, and Rec. 2020 (most modern Apple devices use Display P3, though colors are still
specified as sRGB)
* CIE 1931 xyY and XYZ coordinates, each normalized to be in the [0, 1] range
* CIE 1931 Lab and Luv coordinates. L is in the range [0, 100].
* Correlated color temperature and Duv. Correlated color temperature is the temperature of the blackbody whose color most closely
resembles the given color. Duv measures the distance from the blackbody color - zero Duv means the color is exactly the same as a
blackbody, positive Duv means it is more green than the nearest blackbody, and negative Duv means it is more purple.
    * CCT and Duv are only specified when Duv is between -0.05 and +0.05. Outside this range, they become less meaningful.
* If the color is outside the sRGB gamut, the displayed color is moved towards the D65 white point. If its brightness (Y in CIE 
xyY and XYZ) is above the maximum supported by sRGB for a particular chromaticity, Y is reduced while preserving xy chromaticity. 
In either case, the actual values of x, y, and Y are shown.
* If the color is outside the gamut of sRGB, Adobe RGB, Display P3, and/or Rec. 2020, an asterisk is displayed next to its RGB
value.

Example input: `python3 color_converter_2.py temp 1500` (the color of a 1500 K blackbody)

Example output:
![#ff6c00](https://placehold.co/20x20/ff6c00/ff6c00.png)
```
sRGB(255, 108, 0)*, hex code #ff6c00
HSV (sRGB): H=25.41° S=1.000 V=1.000
HSL (sRGB): H=25.41° S=1.000 V=0.500
Adobe RGB: (255, 120, 0)*; Display P3: (255, 121, 26); Rec. 2020: (255, 134, 18)
CIE 1931 xyY coordinates: x=0.5857 y=0.3931 Y=1.0000
CIE 1931 XYZ coordinates: X=1.4899 Y=1.0000 Z=0.0538
CIE Lab coordinates: L=100.0000 a=80.8268 b=126.6025
CIE Luv coordinates: L=100.0000 u=208.1012 v=93.8277
Correlated color temperature: 1500 K (Duv: -0.0000)
Note: Color not in sRGB gamut. Displayed color (sRGB/HSV/HSL) has been moved towards the D65 white point.
The CIE 1931 chromaticity of the displayed color is x=0.5662 y=0.3886
Note: Specified color is above maximum sRGB brightness. The Y value of the displayed color is 0.3199
```

Here, there are asterisks next to sRGB and Adobe RGB, but not P3 or Rec. 2020, indicating that the color of a 1500 K blackbody can
be displayed in Display P3 and Rec. 2020 but not sRGB or Adobe RGB. As the color is that of a blackbody radiator, the CCT is the
same as the color temperature and Duv is zero.

## color_converter.py

This is an old and deprecated file, `color_converter_2.py` should be used as it has all the capabilities of this file and more,
while being more precise.

## hsv_circle.py

This file requires the third-party `numpy` library, which can be installed using `pip install pillow`.

This file produces `hsv_circle.png`, the circular face at the top of the HSV color cone/cylinder. Hue is the angle clockwise from
top, saturation is distance from center, and value is a constant 1, so the image contains all full-brightness sRGB colors. Any
other sRGB color can be produced by mixing one of these colors with black.

If the argument `adobe`, `p3`, `srgb` or `rec2020` is added after the file name, it produces the same color circle in its 
respective color space. Since the default color space for PNG images is sRGB, the only difference between `hsv_circle.png` and
`hsv_circle_srgb.png` is that the latter has an ICC profile specifying its color space.

## CSV files

`CIE_xyx_1931_2deg.csv` shows the XYZ coordinates of each spectral color, with Y specifying brightness relative to 555 nm (the
wavelength at which the eyes are most sensitive), and comes from the 
[CIE color matching functions](https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer).

`CIE_xy_locus.csv` shows the xy coordinates of each wavelength, derived from their XYZ coordinates. It is used to determine
whether a color can be produced by a real light spectrum, or is an impossible color.

## ICC profiles
ICC profiles for Adobe, Display P3, Rec. 2020 and sRGB downloaded from (https://github.com/saucecontrol/Compact-ICC-Profiles).
They are used by hsv_circle.py to encode the color spaces of the HSV circles.