import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from dfl_full_trajectory_fit import curve


def test_full_flight_and_goal_plane_for_analytic_projectile():
    t = np.linspace(0, .5, 11)
    p = np.array([0.,0.,.11]) + t[:,None]*np.array([30.,3.,6.]) + .5*t[:,None]**2*np.array([0.,0.,-9.81])
    positions, crossing, event = curve('M1',t,p,plane_x=10.94)
    tc = 10.94/30
    expected = np.array([3*tc, .11+6*tc-.5*9.81*tc**2])
    assert event == 'completed'
    assert np.allclose(positions,p,atol=1e-6)
    assert np.allclose(crossing,expected,atol=1e-6)
