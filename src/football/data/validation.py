"""Early observations and held-out crossing points for independent validation."""
import numpy as np


def validate_track(times, positions, max_speed=60.0):
    t = np.asarray(times, dtype=float)
    p = np.asarray(positions, dtype=float)
    if t.ndim != 1 or p.shape != (len(t), 3) or len(t) < 2:
        raise ValueError('expected times (N,) and positions (N,3), N >= 2')
    if not np.isfinite(t).all() or not np.isfinite(p).all():
        raise ValueError('missing or non-finite data')
    if np.any(np.diff(t) <= 0):
        raise ValueError('times must be strictly increasing; duplicates are not allowed')
    if not np.isfinite(max_speed) or max_speed <= 0:
        raise ValueError('max_speed must be finite and positive')
    if np.any(np.linalg.norm(np.diff(p, axis=0), axis=1) / np.diff(t) > max_speed):
        raise ValueError('speed exceeds quality-control limit')
    return t, p


def early_observations(times, positions, duration):
    """Only measured frames no later than first time + duration; no interpolation."""
    t, p = np.asarray(times, float), np.asarray(positions, float)
    if not np.isfinite(duration) or duration < 0:
        raise ValueError('duration must be finite and nonnegative')
    if t.ndim != 1 or len(t) == 0 or p.shape != (len(t), 3):
        raise ValueError('expected times (N,) and positions (N,3)')
    if not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError('times must be finite and strictly increasing')
    # Check position quality only after truncation: a bad future position must
    # not invalidate or otherwise alter the input available at this cutoff.
    end = np.searchsorted(t, t[0] + duration, side='right')
    if end < 2:
        raise ValueError('at least two measured observations are required')
    observed_t, observed_p = validate_track(t[:end], p[:end])
    return observed_t.copy(), observed_p.copy()


def crossing(times, positions, plane_x, after_time):
    """First forward crossing interpolated from held-out samples only."""
    t, p = validate_track(times, positions)
    if not np.isfinite(plane_x) or not np.isfinite(after_time):
        raise ValueError('plane and cutoff must be finite')
    for i in range(len(t) - 1):
        if t[i] <= after_time or not (p[i, 0] < plane_x <= p[i + 1, 0]):
            continue
        frac = (plane_x - p[i, 0]) / (p[i + 1, 0] - p[i, 0])
        return float(t[i] + frac * (t[i + 1] - t[i])), p[i] + frac * (p[i + 1] - p[i])
    return None


def ball3d_track(frame, xyz_dm, fps):
    """Return raw frame time and positions in metres; coordinate rotation is separate."""
    if not np.isfinite(fps) or fps <= 0:
        raise ValueError('fps must be positive')
    return validate_track(np.asarray(frame, dtype=float) / fps, np.asarray(xyz_dm, dtype=float) / 10)


def align_forward(positions, direction):
    """Translate first position to horizontal origin and rotate direction to +x."""
    p = np.asarray(positions, dtype=float)
    d = np.asarray(direction, dtype=float)
    if (p.ndim != 2 or p.shape[1] != 3 or len(p) == 0 or d.shape != (2,)
            or not np.isfinite(p).all() or not np.isfinite(d).all() or np.linalg.norm(d) == 0):
        raise ValueError('invalid positions or horizontal direction')
    d = d / np.linalg.norm(d)
    q = p.copy()
    xy = p[:, :2] - p[0, :2]
    q[:, 0] = xy @ d
    q[:, 1] = xy @ np.array([-d[1], d[0]])
    return q
