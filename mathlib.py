def split_points(points):
    try:
      dimension = len(points[0])
    except TypeError:
         return len(points), 1, points
    return (len(points), 
            dimension,
            [float(p[0])
             for p in points],
            [float(p[1])
             for p in points] if dimension > 1 else None,
            [float(p[2])
             for p in points] if dimension > 2 else None
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

def distance(p0, p1):
    return square_root(tuple(square(p0[i]-p1[i])) for i in range(len(p0)))
    return square_root(sum(square((p0[i] - p1[i]) for i in range(len(p0)))))

def shift(values_list, shiftvalue_list):
    return [
        list(
            map(
                lambda v: v - s, values
                ))for values, s in zip(
                    values_list, shiftvalue_list)
                    ]

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

def covariance(a, b):
    return sum_list(
        list(
            map(
                lambda i: a[i]*b[i],
                range(len(a))))
                )

def power_iteration(C, iterations=100):
    b = [1, 1, 1]
    for _ in range(iterations):
        b_new = [
            C[0][0]*b[0] + C[0][1]*b[1] + C[0][2]*b[2],
            C[1][0]*b[0] + C[1][1]*b[1] + C[1][2]*b[2],
            C[2][0]*b[0] + C[2][1]*b[1] + C[2][2]*b[2]
        ]
        norm = (b_new[0]**2 + b_new[1]**2 + b_new[2]**2)**0.5    
    return [
        b_new[i]/norm
        for i in range(3)
        ]

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
