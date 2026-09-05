import math


def split_points(points):
    try:
        dimension = len(points[0])
    except TypeError:
        return len(points), 1, [float(p) for p in points], None, None
    return (
        len(points),
        dimension,
        [float(p[0]) for p in points],
        [float(p[1]) for p in points] if dimension > 1 else None,
        [float(p[2]) for p in points] if dimension > 2 else None,
    )

def mean(values_list):
    return tuple(
            sum(values) / len(values) for values in values_list)

def sum_list(values):
      return sum(values)

def products(values1, values2, values3 = None):
        return [
              values1[i] * values2[i] * values3[i]
                for i in range(len(values1))
                ]if values3 else [
                      values1[i] * values2[i]
                                  for i in range(len(values1))
                                  ]

def square(values):
    return [v**2 for v in values]

def square_root (values):
    return [v**0.5 for v in values]

def log(values):
    return [math.log(v) for v in values]

def distance(p0, p1):
    return square_root(
        sum(
            (p0[i] - p1[i]) ** 2
                for i in range(len(p0))
            ))

def shift(values_list, shiftvalue_list):
    return [
        list(
            map(
                lambda v: v - s, values
                ))for values, s in zip(
                    values_list, shiftvalue_list)]

def normal_matrix(values):
    values2 = square(values)
    values3 = products(values, values2)
    return [
        [len(values),       sum_list(values),   sum_list(values2)],
        [sum_list(values),  sum_list(values2),  sum_list(values3)],
        [sum_list(values2), sum_list(values3),  sum_list(square(values2))]
        ]

def normal_equation_vector(x, y):
    return [
        sum_list(y),
        sum_list(products(x, y)),
        sum_list(products(square(x), y))
        ]

def scatter(a, b):
    return sum(
        a[i] * b[i]
        for i in range(len(a))
        )

def power_iteration(C, iterations=100):
    b = [1.0, 1.0, 1.0]
    for _ in range(iterations):
        b_new = [
            C[0][0]*b[0] + C[0][1]*b[1] + C[0][2]*b[2],
            C[1][0]*b[0] + C[1][1]*b[1] + C[1][2]*b[2],
            C[2][0]*b[0] + C[2][1]*b[1] + C[2][2]*b[2],
        ]
    return [v / square_root((b_new[0]**2 + b_new[1]**2 + b_new[2]**2))
            for v in b_new]

def solve_3_3_Gauss(A, b):
    M = [
        A[0] + [b[0]],
        A[1] + [b[1]],
        A[2] + [b[2]]
    ]
    for i in range(3):
        pivot = M[i][i]
        for j in range(i, 4):
            M[i][j] /= pivot

        for k in range(i+1, 3):
            factor = M[k][i]
            for j in range(i, 4):
                M[k][j] -= factor * M[i][j]
    x = [0, 0, 0]
    for i in range(2, -1, -1):
        x[i] = M[i][3] - sum(M[i][j]*x[j]
                             for j in range(i+1, 3))
    return x


def solve_gauss(A, b):
    """General n x n Gauss-Jordan solve with partial pivoting -- like
    solve_3_3_Gauss but for any size, needed by fits with more than 3
    parameters (quadratic surface fit, multivariate regression,
    the normal equations inside the custom non-linear fit's
    Levenberg-Marquardt step)."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for i in range(n):
        pivot_row = max(range(i, n), key=lambda r: abs(M[r][i]))
        if abs(M[pivot_row][i]) < 1e-14:
            raise ValueError("Singular matrix -- fit is underdetermined or the data is degenerate.")
        M[i], M[pivot_row] = M[pivot_row], M[i]
        pivot = M[i][i]
        for j in range(i, n + 1):
            M[i][j] /= pivot
        for k in range(n):
            if k == i:
                continue
            factor = M[k][i]
            if factor == 0:
                continue
            for j in range(i, n + 1):
                M[k][j] -= factor * M[i][j]
    return [M[i][n] for i in range(n)]


def least_squares_fit(design_rows, y):
    """Ordinary least squares for an arbitrary linear-in-parameters
    model. design_rows: one row per data point, each row the list of
    basis-function values [f0(point), f1(point), ...] for that point
    (a constant 1.0 column gives an intercept). y: the target values,
    same length as design_rows. Solves the normal equations
    A^T A p = A^T y via solve_gauss and returns the parameter vector p,
    in the same order as the basis functions."""
    n_params = len(design_rows[0])
    AtA = [
        [sum(row[i] * row[j] for row in design_rows) for j in range(n_params)]
        for i in range(n_params)
    ]
    Aty = [sum(row[i] * yi for row, yi in zip(design_rows, y)) for i in range(n_params)]
    return solve_gauss(AtA, Aty)
