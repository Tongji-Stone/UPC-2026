"""Point and probabilistic metrics on cases with observed and predicted crossings."""
import numpy as np


def summarize_errors(truth, prediction):
    a, b = np.asarray(truth, float), np.asarray(prediction, float)
    if a.shape != b.shape or a.ndim != 2 or a.shape[1] != 2 or len(a) == 0:
        raise ValueError('truth and prediction must be nonempty matching (N,2) arrays')
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('all evaluated crossings must be finite')
    e = np.linalg.norm(a-b, axis=1)
    return {'n': len(e), 'mean_m': float(e.mean()), 'median_m': float(np.median(e)),
            'p90_m': float(np.quantile(e, .9))}


def energy_score(samples, truth, weights=None):
    """Energy score of an empirical (optionally weighted) distribution, metres."""
    s, y = np.asarray(samples, float), np.asarray(truth, float)
    if s.ndim != 2 or s.shape[1] != 2 or len(s) == 0 or y.shape != (2,):
        raise ValueError('expected samples (N,2) and truth (2,)')
    if not np.isfinite(s).all() or not np.isfinite(y).all():
        raise ValueError('values must be finite')
    w = np.ones(len(s)) if weights is None else np.asarray(weights, float)
    if w.shape != (len(s),) or not np.isfinite(w).all() or np.any(w < 0) or w.sum() <= 0:
        raise ValueError('weights must be finite, nonnegative, and have positive sum')
    w = w / w.sum()
    pair = sum(wi * (np.linalg.norm(s - row, axis=1) @ w) for wi, row in zip(w, s))
    return float(np.linalg.norm(s-y, axis=1) @ w - .5 * pair)


def coverage(in_region):
    v = np.asarray(in_region)
    if v.ndim != 1 or len(v) == 0 or v.dtype.kind != 'b':
        raise ValueError('expected nonempty boolean values')
    return {'covered': int(v.sum()), 'n': len(v), 'rate': float(v.mean())}


def brier_score(probabilities, outcomes):
    """Proper score for the crossing event, including cases without a crossing."""
    p, y = np.asarray(probabilities, float), np.asarray(outcomes)
    if (p.ndim != 1 or len(p) == 0 or y.shape != p.shape or y.dtype.kind != 'b'
            or not np.isfinite(p).all() or np.any((p < 0) | (p > 1))):
        raise ValueError('expected probabilities in [0,1] and matching boolean outcomes')
    return {'n': len(p), 'mean': float(np.mean((p-y)**2))}


def ellipse_contains(samples, truth, level):
    """Empirical Mahalanobis ellipse; singular clouds have no 2D region."""
    s, y = np.asarray(samples, float), np.asarray(truth, float)
    if (s.ndim != 2 or s.shape[1] != 2 or len(s) < 3 or y.shape != (2,)
            or not np.isfinite(s).all() or not np.isfinite(y).all()
            or not np.isfinite(level) or not 0 < level < 1):
        raise ValueError('finite samples (N>=3,2), truth (2,), and level in (0,1) required')
    center = s.mean(axis=0)
    covariance = np.cov(s.T)
    if np.linalg.matrix_rank(covariance) < 2:
        raise ValueError('singular prediction region')
    inverse = np.linalg.inv(covariance)
    delta = s-center
    distances = np.einsum('ni,ij,nj->n', delta, inverse, delta)
    residual = y-center
    return bool(residual @ inverse @ residual <= np.quantile(distances, level))
