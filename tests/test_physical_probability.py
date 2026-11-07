import numpy as np
from football.inference.physical_probability import infer_physical, summarize_physical


def test_physical_posterior_reproducible_and_early_window_independent():
    t = np.array([0., .05, .1])
    p = np.array([[0.,0.,.11],[1.5,.45,.44],[2.96,.86,.74]])
    changed = p.copy(); changed[-1] = [99.,99.,99.]
    a = infer_physical(t[:2],p[:2],n=80,seed=42)
    b = infer_physical(t[:2],changed[:2],n=80,seed=42)
    assert np.allclose(a['weights'],b['weights'])
    assert np.allclose(a['yz'],b['yz'],equal_nan=True)
    assert np.isclose(a['weights'].sum(),1)
    assert 1 <= a['effective_sample_size'] <= 80 + 1e-8
    summary = summarize_physical(a, draws=300, seed=2)
    assert summary['reached']+summary['ground']+summary['no_event'] == 300
    assert summary['full_in'] <= summary['center_in'] <= summary['reached']
