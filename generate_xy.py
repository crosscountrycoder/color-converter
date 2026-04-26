import csv

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

        total = X + Y + Z

        if total == 0:
            x = ""
            y = ""
        else:
            x = X / total
            y = Y / total

        writer.writerow([
            wavelength,
            f"{x:.12f}" if x != "" else "",
            f"{y:.12f}" if y != "" else ""
        ])