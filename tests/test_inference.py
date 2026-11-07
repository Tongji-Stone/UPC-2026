import numpy as np
from football.models.baseline import predict
from football.inference.kinematic import fit, posterior, sample_predictions

T = np.array([0., .05, .1])
P = np.array([[0.,0.,.11],[1.5,.45,.44],[2.96,.86,.74]])
MU = np.array([[30.,8.,6.],[-8.,0.,-9.81]])
SD = np.array([[10.,10.,10.],[15.,15.,15.]])

def test_baseline_reference_values():
    assert np.allclose(predict(T[:2], P[:2])[1:], [3.3,1.96], atol=.002)
    assert np.allclose(predict(T[1:], P[1:])[1:], [3.118,1.953], atol=.003)
    assert np.allclose(predict(T, P, 'M2')[1:], [2.495,1.920], atol=.004)

def test_early_prediction_ignores_later_observation():
    a = posterior(T[:2], P[:2], .01, MU, SD)
    modified = P.copy(); modified[2] = 100
    b = posterior(T[:2], modified[:2], .01, MU, SD)
    assert all(np.array_equal(x,y) for x,y in zip(a,b))
    assert fit(T[:2], P[:2], .01, MU, SD)['rank'] == 3
    assert fit(T, P, .01, MU, SD)['rank'] == 6

def test_sampling_reproducible_and_probabilities_consistent():
    a = sample_predictions(T, P, .01, MU, SD, n=300, seed=4)
    b = sample_predictions(T, P, .01, MU, SD, n=300, seed=4)
    assert np.array_equal(a['points'], b['points'])
    assert 0 <= a['full_in'] <= a['center_in'] <= a['reached'] <= a['total']

def test_physical_fit_recovers_synthetic_velocity():
    from football.physics import PhysicsConfig
    from football.inference.physical_fit import fit_velocity
    velocity = np.array([30., 7., 6.])
    p = np.array([0., 0., .11]) + T[:,None]*velocity + .5*T[:,None]**2*np.array([0.,0.,-9.81])
    result = fit_velocity(T, p, PhysicsConfig.for_model('M1'), starts=[[25., 5., 3.], [35., 10., 8.]])
    assert np.allclose(result['velocity'], velocity, atol=1e-5)
    assert result['rank'] == 3
    assert len(result['starts']) == 2
