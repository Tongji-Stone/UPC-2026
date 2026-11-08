"""Sample the shared equations at arbitrary observation times for inverse fitting."""
import numpy as np
from scipy.integrate import solve_ivp
from .model import state_derivative, validate_config


def observed_trajectory(times, position, initial_state, config, rtol=2e-9, atol=1e-11):
    validate_config(config)
    t=np.asarray(times,float)
    if t.ndim!=1 or len(t)<2 or not np.isfinite(t).all() or np.any(np.diff(t)<=0):
        raise ValueError('finite increasing observation times required')
    state=np.r_[position,initial_state]
    if state.shape!=(9,) or not np.isfinite(state).all():raise ValueError('nine finite state components required')
    sol=solve_ivp(lambda now,y:state_derivative(now,y,config),(t[0],t[-1]),state,
                  t_eval=t,method='DOP853',rtol=rtol,atol=atol)
    if not sol.success or sol.y.shape[1]!=len(t):raise RuntimeError(sol.message)
    return sol.y.T
