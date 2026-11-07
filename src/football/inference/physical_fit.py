"""Fit initial velocity for a configured forward physical model."""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from football.physics import state_derivative


def fit_velocity(times, positions, config, sigma=.01, spin=(0., 0., 0.), starts=None, prior=None):
    t = np.asarray(times, float); p = np.asarray(positions, float); spin = np.asarray(spin, float)
    if t.ndim != 1 or len(t) < 2 or p.shape != (len(t), 3) or np.any(np.diff(t) <= 0) or sigma <= 0:
        raise ValueError('ordered observations and positive measurement error required')
    def trajectory(v):
        def rhs(_, state):
            return state_derivative(_, state, config)
        sol = solve_ivp(rhs, (t[0], t[-1]), np.r_[p[0], v, spin], t_eval=t, rtol=1e-8, atol=1e-10)
        if not sol.success: raise RuntimeError(sol.message)
        return sol.y[:3].T
    def residual(v):
        r = ((trajectory(v)[1:] - p[1:])/sigma).ravel()
        if prior is not None:
            mean, std = map(np.asarray, prior)
            r = np.r_[r, (v-mean)/std]
        return r
    initial = (p[1]-p[0])/(t[1]-t[0])
    starts = [initial] if starts is None else starts
    fits = [least_squares(residual, v, bounds=([0.,-60.,-40.], [80.,60.,60.])) for v in starts]
    best = min(fits, key=lambda x:x.cost)
    jac = best.jac[:3*(len(t)-1)]
    singular = np.linalg.svd(jac, compute_uv=False)
    covariance = np.linalg.pinv(best.jac.T @ best.jac)
    scale = np.sqrt(np.diag(covariance)); correlation = covariance/np.maximum(np.outer(scale,scale), 1e-30)
    return {'velocity':best.x, 'residuals':trajectory(best.x)-p, 'jacobian':jac, 'singular_values':singular,
            'rank':int(np.linalg.matrix_rank(jac)), 'covariance':covariance, 'correlation':correlation,
            'starts': [{'velocity':item.x, 'cost':float(item.cost)} for item in fits]}
