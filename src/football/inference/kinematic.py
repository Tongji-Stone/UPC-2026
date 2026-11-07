"""Gaussian inference for initial velocity and uncertain constant acceleration.

The first position is treated as a fixed origin. Subsequent independent position
errors are Gaussian. This approximation is explicit so that the same prior is
used for either observation window.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import gaussian_kde


def design(times):
    t = np.asarray(times, float)
    if len(t) < 2 or np.any(np.diff(t) <= 0):
        raise ValueError("times must be strictly increasing")
    dt = t[1:] - t[0]
    return np.column_stack((dt, .5 * dt**2))


def fit(times, positions, sigma, prior_mean, prior_std, regularize=True):
    """Return bounded WLS fit and data-only identifiability diagnostics."""
    H = design(times)
    y = np.asarray(positions, float)[1:] - np.asarray(positions, float)[0]
    mean, std = np.asarray(prior_mean, float), np.asarray(prior_std, float)
    if sigma <= 0 or np.any(std <= 0):
        raise ValueError("sigma and prior standard deviations must be positive")
    def residual(q):
        p = q.reshape(2, 3)
        data = ((H @ p - y) / sigma).ravel()
        return np.r_[data, ((p - mean) / std).ravel()] if regularize else data
    lower = np.array([[0., -50., -30.], [-100., -100., -100.]]).ravel()
    upper = np.array([[70., 50., 50.], [100., 100., 100.]]).ravel()
    opt = least_squares(residual, np.clip(mean.ravel(), lower+1e-8, upper-1e-8), bounds=(lower, upper))
    J = np.kron(H, np.eye(3)) / sigma
    singular = np.linalg.svd(J, compute_uv=False)
    cov = np.linalg.pinv(J.T @ J)
    d = np.sqrt(np.diag(cov))
    rank = int(np.linalg.matrix_rank(J))
    # A pseudoinverse does not represent parameter uncertainty in a null space.
    corr = cov / np.maximum(np.outer(d, d), 1e-30) if rank == J.shape[1] else None
    return {"parameters": opt.x.reshape(2, 3), "residuals": (H @ opt.x.reshape(2, 3)-y),
            "rank": rank, "singular_values": singular, "correlation": corr,
            "cost": float(opt.cost)}


def posterior(times, positions, sigma, prior_mean, prior_std):
    """Exact Gaussian posterior for the linear model (no artificial bounds)."""
    H = design(times)
    y = np.asarray(positions, float)[1:] - np.asarray(positions, float)[0]
    if sigma <= 0:
        raise ValueError("positive sigma required for posterior")
    mu, sd = np.asarray(prior_mean, float), np.asarray(prior_std, float)
    means, covs = [], []
    for k in range(3):
        precision = np.diag(1 / sd[:, k]**2) + H.T @ H / sigma**2
        cov = np.linalg.inv(precision)
        means.append(cov @ (mu[:, k] / sd[:, k]**2 + H.T @ y[:, k] / sigma**2))
        covs.append(cov)
    return np.array(means), np.array(covs)


def sample_predictions(times, positions, sigma, prior_mean, prior_std, n=20000, seed=2026, plane_x=11., radius=.11):
    means, covs = posterior(times, positions, sigma, prior_mean, prior_std)
    rng = np.random.default_rng(seed)
    q = np.stack([rng.multivariate_normal(means[k], covs[k], n) for k in range(3)], axis=1)
    p0 = np.asarray(positions, float)[0]
    vx, ax = q[:, 0, 0], q[:, 0, 1]
    disc = vx*vx + 2*ax*(plane_x-p0[0])
    # Stable first positive root of x(t)=plane_x.
    denom = vx + np.sqrt(np.maximum(disc, 0))
    time = np.divide(2*(plane_x-p0[0]), denom, out=np.full(n, np.nan), where=(disc >= 0)&(denom > 0))
    yz = p0[1:] + q[:, 1:, 0]*time[:, None] + .5*q[:, 1:, 1]*time[:, None]**2
    vz, az = q[:, 2, 0], q[:, 2, 1]
    ground_disc = vz*vz + 2*az*(radius-p0[2])
    ground_t = np.full(n, np.inf)
    if p0[2] <= radius + 1e-12:
        ground_t[vz <= 0] = 0.
    # At initial contact, only a later descending crossing counts.
    mask = (ground_disc >= 0) & (np.abs(az) > 1e-12)
    for sign in (-1, 1):
        root = np.divide(-vz + sign*np.sqrt(np.maximum(ground_disc, 0)), az, out=np.full(n, np.inf), where=mask)
        ground_t = np.minimum(ground_t, np.where((root > 1e-9) & (vz+az*root < 0), root, np.inf))
    valid = np.isfinite(time) & (time > 0) & (time < ground_t)
    points = yz[valid]
    if len(points) < 10:
        raise ValueError("too few trajectories reach the plane before ground")
    kde = gaussian_kde(points.T)
    # Estimate mode from a bounded random subset to control evaluation cost.
    candidates = points[rng.choice(len(points), min(1000, len(points)), replace=False)]
    mode = candidates[np.argmax(kde(candidates.T))]
    center = points.mean(axis=0)
    cov = np.cov(points.T)
    dist = np.einsum('ni,ij,nj->n', points-center, np.linalg.pinv(cov), points-center)
    center_in = (np.abs(points[:, 0]) <= 3.66) & (points[:, 1] >= 0) & (points[:, 1] <= 2.44)
    full = (np.abs(points[:, 0]) <= 3.66-radius) & (points[:, 1] >= radius) & (points[:, 1] <= 2.44-radius)
    return {"points": points, "mode": mode, "mean": center, "covariance": cov,
            "ellipse_mahalanobis2": np.quantile(dist, [.68, .95]),
            "reached": int(valid.sum()), "total": n, "center_in": int(center_in.sum()), "full_in": int(full.sum())}
