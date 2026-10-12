"""
Probability distributions for the statistics tools (private helper, skipped by tool discovery).

Standard library only: the special functions (regularized incomplete beta/gamma, normal quantile) are implemented here, every distribution is a small class with the same interface:

    pdf(x)      density (continuous) or mass function (discrete)
    cdf(x)      P(X <= x)
    sf(x)       P(X > x), computed directly where possible so tiny p-values do not collapse to 0
    ppf(p)      quantile: smallest x with P(X <= x) >= p (discrete: smallest integer)
    mean(), variance()   None where the moment does not exist
    support()   (lower, upper), None = unbounded

`DISTRIBUTIONS` maps a key to the class (used by the Probability Distributions tool's picker), `create(key, texts)` parses user-typed parameters and validates them.
"""

import math

_EPS = 1e-15
_TINY = 1e-300


# -- special functions -----------------------------------------------------

def _betacf(a: float, b: float, x: float) -> float:
    # continued fraction for the incomplete beta function (modified Lentz)
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > _TINY else _TINY)
    h = d
    for m in range(1, 10000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > _TINY else _TINY)
        c = 1.0 + aa / c
        c = c if abs(c) > _TINY else _TINY
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > _TINY else _TINY)
        c = 1.0 + aa / c
        c = c if abs(c) > _TINY else _TINY
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_front = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    front = math.exp(ln_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _gamma_series(a: float, x: float) -> float:
    # lower regularized P(a, x), converges fast for x < a + 1
    ap, term = a, 1.0 / a
    total = term
    for _ in range(100000):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * _EPS:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_cf(a: float, x: float) -> float:
    # upper regularized Q(a, x) by continued fraction, for x >= a + 1
    b = x + 1.0 - a
    c = 1.0 / _TINY
    d = 1.0 / b
    h = d
    for i in range(1, 100000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = d if abs(d) > _TINY else _TINY
        c = b + an / c
        c = c if abs(c) > _TINY else _TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gammainc_p(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x)."""
    if x <= 0.0:
        return 0.0
    return _gamma_series(a, x) if x < a + 1.0 else 1.0 - _gamma_cf(a, x)


def gammainc_q(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) = 1 - P(a, x)."""
    if x <= 0.0:
        return 1.0
    return 1.0 - _gamma_series(a, x) if x < a + 1.0 else _gamma_cf(a, x)


def norm_cdf(z: float) -> float:
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def norm_ppf(p: float) -> float:
    """Standard normal quantile (Acklam's rational approximation + one Halley refinement step)."""
    if not 0.0 < p < 1.0:
        raise ValueError("Quantile probability must lie strictly between 0 and 1.")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00)
    low = 0.02425
    if p < low:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    elif p > 1.0 - low:
        q = math.sqrt(-2.0 * math.log1p(-p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    err = norm_cdf(x) - p
    u = err * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    return x - u / (1.0 + x * u / 2.0)


# -- base class --------------------------------------------------------------

class Distribution:
    key = ""
    label = ""
    param_names: tuple = ()
    param_defaults: tuple = ()
    x_default = "0"
    discrete = False

    def __init__(self, *params):
        self.params = params

    @property
    def density_name(self) -> str:
        return "pmf" if self.discrete else "pdf"

    def describe(self) -> str:
        return f"{self.label}(" + ", ".join(f"{n}={v:g}" for n, v in zip(self.param_names, self.params)) + ")"

    def support(self):
        return (None, None)

    def pdf(self, x): raise NotImplementedError
    def cdf(self, x): raise NotImplementedError
    def mean(self): return None
    def variance(self): return None

    def sf(self, x):
        return 1.0 - self.cdf(x)

    def ppf(self, p):
        if not 0.0 < p < 1.0:
            raise ValueError("Quantile probability must lie strictly between 0 and 1.")
        return self._ppf_discrete(p) if self.discrete else self._ppf_continuous(p)

    def _ppf_continuous(self, p):
        lo, hi = self.support()
        if lo is None:
            lo = -1.0
            while self.cdf(lo) > p and lo > -1e300:
                lo *= 2.0
        if hi is None:
            hi = 1.0 if lo < 1.0 else lo + 1.0
            while self.cdf(hi) < p and hi < 1e300:
                hi *= 2.0
        for _ in range(300):
            mid = 0.5 * (lo + hi)
            if self.cdf(mid) < p:
                lo = mid
            else:
                hi = mid
            if hi - lo <= 1e-15 * max(1.0, abs(mid)):
                break
        return 0.5 * (lo + hi)

    def _ppf_discrete(self, p):
        lo, hi = self.support()
        lo = 0 if lo is None else int(lo)
        target = p - 1e-12
        if hi is None:
            hi = max(lo + 1, 1)
            while self.cdf(hi) < target and hi < 10 ** 15:
                hi *= 2
        hi = int(hi)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.cdf(mid) >= target:
                hi = mid
            else:
                lo = mid + 1
        return float(lo)


def _positive(value: float, name: str) -> float:
    if not value > 0:
        raise ValueError(f"Parameter '{name}' must be > 0.")
    return value


# -- continuous --------------------------------------------------------------

class Normal(Distribution):
    key, label = "normal", "Normal"
    param_names, param_defaults, x_default = ("mu", "sigma"), ("0", "1"), "0"

    def __init__(self, mu, sigma):
        super().__init__(mu, sigma)
        self.mu, self.sigma = mu, _positive(sigma, "sigma")

    def pdf(self, x):
        z = (x - self.mu) / self.sigma
        return math.exp(-0.5 * z * z) / (self.sigma * math.sqrt(2.0 * math.pi))

    def cdf(self, x):
        return 0.5 * math.erfc(-(x - self.mu) / (self.sigma * math.sqrt(2.0)))

    def sf(self, x):
        return 0.5 * math.erfc((x - self.mu) / (self.sigma * math.sqrt(2.0)))

    def ppf(self, p):
        return self.mu + self.sigma * norm_ppf(p)

    def mean(self): return self.mu
    def variance(self): return self.sigma ** 2


class StudentT(Distribution):
    key, label = "t", "Student t"
    param_names, param_defaults, x_default = ("df",), ("10",), "0"

    def __init__(self, df):
        super().__init__(df)
        self.df = _positive(df, "df")

    def pdf(self, x):
        v = self.df
        log_c = math.lgamma((v + 1) / 2) - math.lgamma(v / 2) - 0.5 * math.log(v * math.pi)
        return math.exp(log_c - (v + 1) / 2 * math.log1p(x * x / v))

    def cdf(self, x):
        if x == 0:
            return 0.5
        z = x * x / (self.df + x * x)
        if z < 0.5:  # near the center df/(df+x^2) rounds to 1.0 -- use the complementary form P(|T| < x) instead
            inner = 0.5 * betainc(0.5, self.df / 2, z)
            return 0.5 + inner if x > 0 else 0.5 - inner
        tail = 0.5 * betainc(self.df / 2, 0.5, self.df / (self.df + x * x))
        return 1.0 - tail if x > 0 else tail

    def sf(self, x):
        return self.cdf(-x)

    def mean(self): return 0.0 if self.df > 1 else None

    def variance(self):
        if self.df > 2:
            return self.df / (self.df - 2)
        return math.inf if self.df > 1 else None


class ChiSquare(Distribution):
    key, label = "chi2", "Chi-square"
    param_names, param_defaults, x_default = ("df",), ("3",), "3"

    def __init__(self, df):
        super().__init__(df)
        self.df = _positive(df, "df")

    def support(self): return (0.0, None)

    def pdf(self, x):
        k = self.df
        if x < 0:
            return 0.0
        if x == 0:
            return math.inf if k < 2 else (0.5 if k == 2 else 0.0)
        return math.exp((k / 2 - 1) * math.log(x) - x / 2 - (k / 2) * math.log(2) - math.lgamma(k / 2))

    def cdf(self, x): return gammainc_p(self.df / 2, x / 2)
    def sf(self, x): return gammainc_q(self.df / 2, x / 2)
    def mean(self): return self.df
    def variance(self): return 2 * self.df


class FDistribution(Distribution):
    key, label = "f", "F"
    param_names, param_defaults, x_default = ("d1", "d2"), ("5", "10"), "1"

    def __init__(self, d1, d2):
        super().__init__(d1, d2)
        self.d1, self.d2 = _positive(d1, "d1"), _positive(d2, "d2")

    def support(self): return (0.0, None)

    def pdf(self, x):
        d1, d2 = self.d1, self.d2
        if x < 0:
            return 0.0
        if x == 0:
            return math.inf if d1 < 2 else (1.0 if d1 == 2 else 0.0)
        log_beta = math.lgamma(d1 / 2) + math.lgamma(d2 / 2) - math.lgamma((d1 + d2) / 2)
        log_pdf = 0.5 * (d1 * math.log(d1 * x) + d2 * math.log(d2) - (d1 + d2) * math.log(d1 * x + d2)) - math.log(x) - log_beta
        return math.exp(log_pdf)

    def cdf(self, x):
        if x <= 0:
            return 0.0
        return betainc(self.d1 / 2, self.d2 / 2, self.d1 * x / (self.d1 * x + self.d2))

    def sf(self, x):
        if x <= 0:
            return 1.0
        return betainc(self.d2 / 2, self.d1 / 2, self.d2 / (self.d1 * x + self.d2))

    def mean(self): return self.d2 / (self.d2 - 2) if self.d2 > 2 else None

    def variance(self):
        d1, d2 = self.d1, self.d2
        if d2 > 4:
            return 2 * d2 ** 2 * (d1 + d2 - 2) / (d1 * (d2 - 2) ** 2 * (d2 - 4))
        return math.inf if d2 > 2 else None


class Exponential(Distribution):
    key, label = "exponential", "Exponential"
    param_names, param_defaults, x_default = ("lambda",), ("1",), "1"

    def __init__(self, rate):
        super().__init__(rate)
        self.rate = _positive(rate, "lambda")

    def support(self): return (0.0, None)
    def pdf(self, x): return self.rate * math.exp(-self.rate * x) if x >= 0 else 0.0
    def cdf(self, x): return -math.expm1(-self.rate * x) if x > 0 else 0.0
    def sf(self, x): return math.exp(-self.rate * x) if x > 0 else 1.0

    def ppf(self, p):
        if not 0.0 < p < 1.0:
            raise ValueError("Quantile probability must lie strictly between 0 and 1.")
        return -math.log1p(-p) / self.rate

    def mean(self): return 1 / self.rate
    def variance(self): return 1 / self.rate ** 2


class Uniform(Distribution):
    key, label = "uniform", "Uniform"
    param_names, param_defaults, x_default = ("a", "b"), ("0", "1"), "0.5"

    def __init__(self, a, b):
        super().__init__(a, b)
        if not a < b:
            raise ValueError("Uniform needs a < b.")
        self.a, self.b = a, b

    def support(self): return (self.a, self.b)
    def pdf(self, x): return 1 / (self.b - self.a) if self.a <= x <= self.b else 0.0
    def cdf(self, x): return min(1.0, max(0.0, (x - self.a) / (self.b - self.a)))
    def sf(self, x): return min(1.0, max(0.0, (self.b - x) / (self.b - self.a)))

    def ppf(self, p):
        if not 0.0 < p < 1.0:
            raise ValueError("Quantile probability must lie strictly between 0 and 1.")
        return self.a + p * (self.b - self.a)

    def mean(self): return (self.a + self.b) / 2
    def variance(self): return (self.b - self.a) ** 2 / 12


class Gamma(Distribution):
    key, label = "gamma", "Gamma"
    param_names, param_defaults, x_default = ("k", "theta"), ("2", "1"), "2"

    def __init__(self, k, theta):
        super().__init__(k, theta)
        self.k, self.theta = _positive(k, "k"), _positive(theta, "theta")

    def support(self): return (0.0, None)

    def pdf(self, x):
        k, th = self.k, self.theta
        if x < 0:
            return 0.0
        if x == 0:
            return math.inf if k < 1 else (1 / th if k == 1 else 0.0)
        return math.exp((k - 1) * math.log(x) - x / th - k * math.log(th) - math.lgamma(k))

    def cdf(self, x): return gammainc_p(self.k, x / self.theta)
    def sf(self, x): return gammainc_q(self.k, x / self.theta)
    def mean(self): return self.k * self.theta
    def variance(self): return self.k * self.theta ** 2


class Beta(Distribution):
    key, label = "beta", "Beta"
    param_names, param_defaults, x_default = ("a", "b"), ("2", "5"), "0.3"

    def __init__(self, a, b):
        super().__init__(a, b)
        self.a, self.b = _positive(a, "a"), _positive(b, "b")

    def support(self): return (0.0, 1.0)

    def pdf(self, x):
        a, b = self.a, self.b
        if x < 0 or x > 1:
            return 0.0
        if x == 0:
            return math.inf if a < 1 else (b if a == 1 else 0.0)
        if x == 1:
            return math.inf if b < 1 else (a if b == 1 else 0.0)
        log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        return math.exp((a - 1) * math.log(x) + (b - 1) * math.log1p(-x) - log_beta)

    def cdf(self, x): return betainc(self.a, self.b, x)
    def sf(self, x): return betainc(self.b, self.a, 1.0 - x) if 0 < x < 1 else (1.0 if x <= 0 else 0.0)
    def mean(self): return self.a / (self.a + self.b)

    def variance(self):
        s = self.a + self.b
        return self.a * self.b / (s * s * (s + 1))


# -- discrete ----------------------------------------------------------------

class Binomial(Distribution):
    key, label, discrete = "binomial", "Binomial", True
    param_names, param_defaults, x_default = ("n", "p"), ("10", "0.5"), "5"

    def __init__(self, n, p):
        super().__init__(n, p)
        if n < 0 or n != int(n):
            raise ValueError("Binomial: n must be a non-negative integer.")
        if not 0.0 <= p <= 1.0:
            raise ValueError("Binomial: p must lie in [0, 1].")
        self.n, self.p = int(n), p

    def support(self): return (0, self.n)

    def pdf(self, x):
        if x != int(x) or x < 0 or x > self.n:
            return 0.0
        k, n, p = int(x), self.n, self.p
        if p == 0.0:
            return 1.0 if k == 0 else 0.0
        if p == 1.0:
            return 1.0 if k == n else 0.0
        return math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p))

    def cdf(self, x):
        k = math.floor(x)
        if k < 0:
            return 0.0
        if k >= self.n:
            return 1.0
        return betainc(self.n - k, k + 1, 1.0 - self.p)

    def sf(self, x):
        k = math.floor(x)
        if k < 0:
            return 1.0
        if k >= self.n:
            return 0.0
        return betainc(k + 1, self.n - k, self.p)

    def mean(self): return self.n * self.p
    def variance(self): return self.n * self.p * (1 - self.p)


class Poisson(Distribution):
    key, label, discrete = "poisson", "Poisson", True
    param_names, param_defaults, x_default = ("lambda",), ("4",), "3"

    def __init__(self, rate):
        super().__init__(rate)
        self.rate = _positive(rate, "lambda")

    def support(self): return (0, None)

    def pdf(self, x):
        if x != int(x) or x < 0:
            return 0.0
        k = int(x)
        return math.exp(k * math.log(self.rate) - self.rate - math.lgamma(k + 1))

    def cdf(self, x):
        k = math.floor(x)
        return 0.0 if k < 0 else gammainc_q(k + 1, self.rate)

    def sf(self, x):
        k = math.floor(x)
        return 1.0 if k < 0 else gammainc_p(k + 1, self.rate)

    def mean(self): return self.rate
    def variance(self): return self.rate


DISTRIBUTIONS = {cls.key: cls for cls in (Normal, StudentT, ChiSquare, FDistribution, Exponential, Uniform, Gamma, Beta, Binomial, Poisson)}


def parse_params(text: str) -> list[str]:
    """Splits a parameter entry: ';' if present (so decimal commas work), otherwise ','."""
    sep = ";" if ";" in text else ","
    return [p.strip() for p in text.split(sep) if p.strip()]


def create(key: str, texts: list[str]) -> Distribution:
    cls = DISTRIBUTIONS[key]
    if len(texts) != len(cls.param_names):
        raise ValueError(f"{cls.label} needs {len(cls.param_names)} parameter(s) ({', '.join(cls.param_names)}), got {len(texts)}.")
    values = []
    for name, text in zip(cls.param_names, texts):
        try:
            values.append(float(text.replace(",", ".")))
        except ValueError:
            raise ValueError(f"Parameter '{name}' must be a number, got '{text}'.")
    return cls(*values)
