import numpy as np
from scipy.optimize import differential_evolution
import color_converter_2 as cc2


def generate_temp_samples(num_samples=3000, Tmin=800, Tmax=5e6):
    u_min = 1.0 / Tmax
    u_max = 1.0 / Tmin

    u = np.linspace(u_min, u_max, num_samples)
    T = np.divide(1.0, u, out=np.full_like(u, np.inf, dtype=float), where=(u != 0))   

    rows = []

    for temp in T:
        X, Y, Z = cc2.temp_to_XYZ(temp)
        x, y, _ = cc2.XYZ_to_xyY(X, Y, Z)
        rows.append((temp, 1.0 / temp, x, y))

    return np.array(rows, dtype=float)


def build_design_matrix(u, breaks, degree):
    u = np.asarray(u, dtype=float)

    num_pieces = len(breaks) - 1
    cols_per_piece = degree + 1

    A = np.zeros((len(u), num_pieces * cols_per_piece))

    for i in range(num_pieces):
        if i == num_pieces - 1:
            mask = (breaks[i] <= u) & (u <= breaks[i + 1])
        else:
            mask = (breaks[i] <= u) & (u < breaks[i + 1])

        powers = np.vstack([u[mask] ** k for k in range(cols_per_piece)]).T

        start = i * cols_per_piece
        end = start + cols_per_piece

        A[mask, start:end] = powers

    return A


def build_continuity_constraints(breaks, degree):
    num_pieces = len(breaks) - 1
    cols_per_piece = degree + 1

    constraints = []

    for j in range(1, len(breaks) - 1):
        ub = breaks[j]
        row = np.zeros(num_pieces * cols_per_piece)

        for k in range(cols_per_piece):
            row[(j - 1) * cols_per_piece + k] = ub ** k
            row[j * cols_per_piece + k] = -(ub ** k)

        constraints.append(row)

    if len(constraints) == 0:
        return np.empty((0, num_pieces * cols_per_piece))

    return np.vstack(constraints)


def fit_continuous_piecewise(u, values, breaks, degree):
    A = build_design_matrix(u, breaks, degree)
    C = build_continuity_constraints(breaks, degree)

    ATA = A.T @ A
    ATb = A.T @ values

    zeros = np.zeros((C.shape[0], C.shape[0]))

    KKT = np.block([
        [ATA, C.T],
        [C, zeros],
    ])

    rhs = np.concatenate([
        ATb,
        np.zeros(C.shape[0]),
    ])

    solution = np.linalg.solve(KKT, rhs)

    coeffs_flat = solution[:A.shape[1]]

    num_pieces = len(breaks) - 1
    return coeffs_flat.reshape(num_pieces, degree + 1)


def eval_piecewise_poly(u, coeffs, breaks):
    u = np.asarray(u, dtype=float)

    scalar_input = u.ndim == 0
    u = np.atleast_1d(u)

    num_pieces = len(breaks) - 1
    degree = coeffs.shape[1] - 1

    result = np.empty_like(u, dtype=float)

    outside = (u < breaks[0]) | (u > breaks[-1])
    if np.any(outside):
        raise ValueError("u value outside fitted range")

    for i in range(num_pieces):
        if i == num_pieces - 1:
            mask = (breaks[i] <= u) & (u <= breaks[i + 1])
        else:
            mask = (breaks[i] <= u) & (u < breaks[i + 1])

        powers = np.vstack([u[mask] ** k for k in range(degree + 1)]).T
        result[mask] = powers @ coeffs[i]

    return result[0] if scalar_input else result


def temp_to_xy_piecewise(T, coeff_x, coeff_y, breaks):
    u = 1.0 / T
    x = eval_piecewise_poly(u, coeff_x, breaks)
    y = eval_piecewise_poly(u, coeff_y, breaks)
    return float(x), float(y)


def max_component_errors(coeff_x, coeff_y, breaks, num_test=20000,
                         Tmin=800, Tmax=5e6):
    samples = generate_temp_samples(num_test, Tmin, Tmax)

    T = samples[:, 0]
    u = samples[:, 1]
    x_true = samples[:, 2]
    y_true = samples[:, 3]

    x_pred = eval_piecewise_poly(u, coeff_x, breaks)
    y_pred = eval_piecewise_poly(u, coeff_y, breaks)

    x_err = np.abs(x_pred - x_true)
    y_err = np.abs(y_pred - y_true)

    ix = np.argmax(x_err)
    iy = np.argmax(y_err)

    return {
        "max_x_error": x_err[ix],
        "temperature_at_max_x_error": T[ix],
        "max_y_error": y_err[iy],
        "temperature_at_max_y_error": T[iy],
        "max_component_error": max(x_err[ix], y_err[iy]),
    }


def optimize_breaks(u_train, xs, ys, degree, num_pieces,
                    Tmin=800.0, Tmax=5e6,
                    num_test=10000):
    u_min = 1.0 / Tmax
    u_max = 1.0 / Tmin

    test_samples = generate_temp_samples(num_test, Tmin, Tmax)

    u_test = test_samples[:, 1]
    x_true = test_samples[:, 2]
    y_true = test_samples[:, 3]

    num_internal_breaks = num_pieces - 1

    def objective(raw_internal_breaks):
        internal_breaks = np.sort(raw_internal_breaks)

        breaks = np.concatenate([
            [u_min],
            internal_breaks,
            [u_max],
        ])

        # Prevent nearly zero-width pieces
        if np.any(np.diff(breaks) < 1e-10):
            return 1e9

        try:
            coeff_x = fit_continuous_piecewise(u_train, xs, breaks, degree)
            coeff_y = fit_continuous_piecewise(u_train, ys, breaks, degree)

            x_pred = eval_piecewise_poly(u_test, coeff_x, breaks)
            y_pred = eval_piecewise_poly(u_test, coeff_y, breaks)

            x_err = np.abs(x_pred - x_true)
            y_err = np.abs(y_pred - y_true)

            return max(np.max(x_err), np.max(y_err))

        except Exception:
            return 1e9

    bounds = [(u_min, u_max) for _ in range(num_internal_breaks)]

    result = differential_evolution(
        objective,
        bounds,
        tol=1e-10,
        polish=True,
        workers=1,
        updating="immediate",
    )

    internal_breaks = np.sort(result.x)

    breaks = np.concatenate([
        [u_min],
        internal_breaks,
        [u_max],
    ])

    return breaks, result.fun


def print_piecewise_formula(coeffs, breaks, name):
    num_pieces = coeffs.shape[0]
    degree = coeffs.shape[1] - 1

    for i in range(num_pieces):
        print()
        print(f"{name}(u), piece {i + 1}:")
        t0 = float("inf") if breaks[i+1] == 0 else 1/breaks[i+1]
        t1 = float("inf") if breaks[i] == 0 else 1/breaks[i]
        print(f"  valid for {breaks[i]:.12g} <= u <= {breaks[i+1]:.12g} ({t0:.12g} <= t <= {t1:.12g})")

        terms = []

        for k in range(degree + 1):
            c = coeffs[i, k]

            if k == 0:
                terms.append(f"{c:.16g}")
            elif k == 1:
                terms.append(f"{c:+.16g}*u")
            else:
                terms.append(f"{c:+.16g}*u^{k}")

        print("  " + " ".join(terms))


if __name__ == "__main__":
    Tmin = 800.0
    Tmax = float("inf")

    degree = 4
    num_pieces = 3

    num_train = 1000
    num_break_test = 2000
    num_final_test = 50000

    samples = generate_temp_samples(num_train, Tmin, Tmax)

    T = samples[:, 0]
    u = samples[:, 1]
    xs = samples[:, 2]
    ys = samples[:, 3]

    breaks, optimized_error = optimize_breaks(
        u_train=u,
        xs=xs,
        ys=ys,
        degree=degree,
        num_pieces=num_pieces,
        Tmin=Tmin,
        Tmax=Tmax,
        num_test=num_break_test,
    )

    coeff_x = fit_continuous_piecewise(u, xs, breaks, degree)
    coeff_y = fit_continuous_piecewise(u, ys, breaks, degree)

    print("Optimized reciprocal-temperature breaks:")
    print(breaks)

    print()
    print("Equivalent temperature breaks:")
    TEMPS = np.divide(1.0, breaks, out=np.full_like(breaks, np.inf, dtype=float), where=(breaks != 0))
    print(TEMPS)

    print()
    print("Optimization max component error:")
    print(optimized_error)

    print()
    print("Final errors:")
    print(max_component_errors(coeff_x, coeff_y, breaks, num_final_test, Tmin, Tmax))

    print()
    print("Example values:")
    for temp in [1000, 1500, 2000, 3000, 5000, 6500, 10000, 100000, 1_000_000]:
        x, y = temp_to_xy_piecewise(temp, coeff_x, coeff_y, breaks)
        print(f"{temp:10.0f} K -> x={x:.10f}, y={y:.10f}")

    print()
    print("x polynomial pieces:")
    print_piecewise_formula(coeff_x, breaks, "x")

    print()
    print("y polynomial pieces:")
    print_piecewise_formula(coeff_y, breaks, "y")