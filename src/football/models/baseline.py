"""Simple kinematic predictors, in SI units."""
import numpy as np


def predict(times, positions, model="M1", plane_x=11.0):
    t = np.asarray(times, float)
    p = np.asarray(positions, float)
    if len(t) < 2 or p.shape != (len(t), 3) or np.any(np.diff(t) <= 0):
        raise ValueError("at least two ordered observations are required")
    if model == "M2":
        if len(t) < 3:
            raise ValueError("M2 requires three observations")
        coef = np.linalg.solve(np.column_stack((np.ones(3), t[-3:], t[-3:] ** 2)), p[-3:])
        roots = np.roots([coef[2, 0], coef[1, 0], coef[0, 0] - plane_x])
        candidates = sorted(r.real for r in roots if abs(r.imag) < 1e-9 and r.real >= t[-1])
        if not candidates:
            return None
        q = candidates[0]
        return coef[0] + coef[1] * q + coef[2] * q*q
    if model not in ("M0", "M1"):
        raise ValueError("unknown baseline")
    a = np.array([0., 0., -9.81 if model == "M1" else 0.])
    dt = t[-1] - t[-2]
    v = (p[-1] - p[-2]) / dt + 0.5 * a * dt
    if v[0] <= 0:
        return None
    h = (plane_x - p[-1, 0]) / v[0]
    if h < 0:
        return None
    return p[-1] + v*h + 0.5*a*h*h
