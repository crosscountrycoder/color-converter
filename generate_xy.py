import csv
from color_converter_2 import XYZ_to_xyY

input_file = "CIE_xyz_1931_2deg.csv"
output_file = "CIE_xy_locus.csv"

with open(input_file, "r", newline="") as infile, open(output_file, "w", newline="") as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    writer.writerow(["wavelength", "x", "y"])

    for row in reader:
        wavelength = int(row[0])
        X = float(row[1])
        Y = float(row[2])
        Z = float(row[3])
        x, y, _ = XYZ_to_xyY(X, Y, Z)

        writer.writerow([
            wavelength,
            f"{x:.6f}" if x != "" else "",
            f"{y:.6f}" if y != "" else ""
        ])