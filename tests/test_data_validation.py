import numpy as np
import pytest
from football.data.validation import ball3d_track, early_observations, crossing, align_forward
from football.evaluation.metrics import summarize_errors, energy_score, coverage


def test_no_future_frames_and_heldout_crossing():
    t = np.arange(12) / 25
    p = np.column_stack((30*t, 2*t, 1+t))
    a, _ = early_observations(t, p, .05)
    b, _ = early_observations(t, p, .10)
    np.testing.assert_allclose(a, [0, .04])
    np.testing.assert_allclose(b, [0, .04, .08])
    when, point = crossing(t, p, 11, .10)
    assert when == pytest.approx(11/30)
    assert point[0] == pytest.approx(11)


def test_units_and_metrics():
    t, p = ball3d_track([0, 1], [[0, 0, 2], [1, 0, 3]], 25)
    assert t[1] == pytest.approx(.04)
    assert p[1, 2] == pytest.approx(.3)
    np.testing.assert_allclose(align_forward(p, [1, 0]), p)
    assert summarize_errors([[0, 0]], [[3, 4]])['mean_m'] == 5
    assert energy_score([[0, 0]], [3, 4]) == 5
    assert coverage([True, False])['rate'] == .5
    with pytest.raises(ValueError):
        ball3d_track([0, 0], [[0, 0, 0], [1, 0, 0]], 25)
