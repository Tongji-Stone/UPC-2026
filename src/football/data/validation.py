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
    if np.any(np.linalg.norm(np.diff(p, axis=0), axis=1) / np.diff(t) > max_speed):
        raise ValueError('speed exceeds quality-control limit')
    return t, p


def early_observations(times, positions, duration):
    """Only measured frames no later than first time + duration; no interpolation."""
    t, p = validate_track(times, positions)
    mask = t <= t[0] + duration + 1e-12
    return t[mask].copy(), p[mask].copy()


def crossing(times, positions, plane_x, after_time):
    """First forward crossing interpolated from held-out samples only."""
    t, p = validate_track(times, positions)
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
    if p.ndim != 2 or p.shape[1] != 3 or d.shape != (2,) or np.linalg.norm(d) == 0:
        raise ValueError('invalid positions or horizontal direction')
    d = d / np.linalg.norm(d)
    q = p.copy()
    xy = p[:, :2] - p[0, :2]
    q[:, 0] = xy @ d
    q[:, 1] = xy @ np.array([-d[1], d[0]])
    return q
