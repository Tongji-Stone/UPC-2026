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


def energy_score(samples, truth):
    """Multivariate energy score in metres; empirical ensemble, equal weights."""
    s, y = np.asarray(samples, float), np.asarray(truth, float)
    if s.ndim != 2 or s.shape[1] != 2 or len(s) == 0 or y.shape != (2,):
        raise ValueError('expected samples (N,2) and truth (2,)')
    if not np.isfinite(s).all() or not np.isfinite(y).all():
        raise ValueError('values must be finite')
    # Accumulate pair distances by rows to avoid a large N x N x 2 allocation.
    pair = sum(np.linalg.norm(s - row, axis=1).sum() for row in s) / len(s)**2
    return float(np.linalg.norm(s-y, axis=1).mean() - .5 * pair)


def coverage(in_region):
    v = np.asarray(in_region, dtype=bool)
    if v.ndim != 1 or len(v) == 0:
        raise ValueError('expected nonempty boolean values')
    return {'covered': int(v.sum()), 'n': len(v), 'rate': float(v.mean())}
