# color-converter

The Python script color-converter.py allows conversion between sRGB color values (specified as RGB values like 149, 177, 255 or
hex values like 95b1ff), CIE 1931 xy coordinates, and correlated color temperature/DUV. It also allows users to convert color
temperature (blackbody or daylight) to sRGB. Coming soon are CIE XYZ, xyY, and LAB color spaces, and HSV/HSL.

## Syntax for color-converter.py

`python3 color_converter.py rgb <R> <G> <B>`: Sets the color to the given sRGB value. R, G, B must be positive integers between 0 and
255, inclusive. For any given color, it shows the CIE 1931 xy chromaticity coordinates. If it is sufficiently close to the Planckian 
locus, it shows the correlated color temperature and DUV. A positive DUV means the light is greener than the nearest blackbody, and a 
negative DUV means the light is more purple than the blackbody.

`python3 color_converter.py hex <hexcode>`: Sets the color to the given hex value (representing an RGB value). Again, it shows the
RGB value, xy color, and color temperature/DUV if applicable.

`python3 color_converter.py cie <x> <y>`: Sets the color to the given CIE xy coordinate, with maximum brightness (that is, at least
one of the RGB values is 255). Shows the RGB values and hex code, as well as color temperature/DUV if applicable.

`python3 color_converter.py temp <T>`: Sets the color to that of a blackbody with the given temperature in kelvins, and shows the RGB,
hex, and CIE xy values. If the word "daylight" is added after the temperature argument, the color given will be on the daylight locus,
not the Planckian (blackbody) locus. For example, `python3 color_converter.py temp 6500 daylight` sets the color to 6500 K on the
daylight locus. The daylight option breaks down at temperatures below 3000 K.

If T is set to `inf` (infinity), it will show `#95b1ff`, which is the color of a black body as its temperature approaches infinity.
This value is similar to the value `#94b1ff` calculated by David Madore: (https://johncarlosbaez.wordpress.com/2022/01/16/the-color-of-infinite-temperature/)