# HISTORICAL pipeline; not used by the current paper. Use scripts/coupled_compute.py.
"""Importance sampling for a physical trajectory with uncertain spin and drag.

The first ball position is fixed. Independent Gaussian errors apply to later
positions. A data-conditioned Gaussian velocity proposal is corrected by its
importance weight, so it does not change the stated prior.
"""
from dataclasses import replace
import numpy as np
from scipy.integrate import solve_ivp
from scipy.special import logsumexp
from scipy.stats import multivariate_normal
from football.physics import PhysicsConfig, forces, linthorne_patel_coefficients


def infer_physical(times, positions, sigma=.01, n=2000, seed=2026, plane_x=11.,
                   velocity_mean=(30., 8., 6.), velocity_sd=(10., 10., 10.),
                   spin_sd=30., cd0_range=(.1, .2), max_time=2.):
    times = np.asarray(times, float); pos = np.asarray(positions, float)
    mu = np.asarray(velocity_mean, float); sd = np.asarray(velocity_sd, float)
    if (len(times) < 2 or pos.shape != (len(times), 3) or np.any(np.diff(times) <= 0)
        or sigma <= 0 or np.any(sd <= 0) or spin_sd <= 0 or n < 10
        or cd0_range[0] >= cd0_range[1]):
        raise ValueError('invalid observations, prior, or sample count')
    dt = times[1:] - times[0]
    if plane_x <= pos[0,0] or max_time <= dt[-1]:
        raise ValueError('prediction plane and maximum time must be ahead of observations')
    base = PhysicsConfig.for_model('M5')
    rng = np.random.default_rng(seed)
    spin = rng.normal(0., spin_sd, (n,3))
    cd0 = rng.uniform(*cd0_range, n)
    weights = np.full(n, -np.inf); events = np.full(n, 0, dtype=np.int8)
    yz = np.full((n,2), np.nan); velocities = np.empty((n,3))
    # Each component has the same proposal variance, but a nuisance-dependent mean.
    proposal_var = 1 / (1/sd**2 + np.sum(dt**2)/sigma**2)
    prior = multivariate_normal(mean=mu, cov=np.diag(sd**2))
    empirical_v = (pos[-1]-pos[0])/dt[-1]
    for i in range(n):
        coeff = linthorne_patel_coefficients(cd0=cd0[i], radius=base.radius,
                                             kinematic_viscosity=base.kinematic_viscosity)
        config = replace(base, coefficients=coeff)
        acc = sum(forces(empirical_v, spin[i], config).values())/config.mass
        y = pos[1:] - pos[0] - .5 * dt[:,None]**2 * acc
        proposal_mean = proposal_var*(mu/sd**2 + (dt[:,None]*y).sum(axis=0)/sigma**2)
        v = rng.normal(proposal_mean, np.sqrt(proposal_var)); velocities[i] = v
        def rhs(_, x):
            f = forces(x[3:6], x[6:9], config)
            return np.r_[x[3:6], sum(f.values())/config.mass, -config.spin_decay*x[6:9]]
        def plane(_, x): return x[0]-plane_x
        plane.terminal = True; plane.direction = 1
        def ground(_, x): return x[2]-config.radius
        ground.terminal = True; ground.direction = -1
        sol = solve_ivp(rhs, (0., max_time), np.r_[pos[0],v,spin[i]],
                        events=(plane, ground), dense_output=True, rtol=2e-6, atol=1e-8)
        if not sol.success or sol.t[-1] < dt[-1]:
            continue
        resid = (sol.sol(dt)[:3].T-pos[1:])/sigma
        proposal = multivariate_normal.logpdf(v, mean=proposal_mean, cov=np.diag(proposal_var))
        weights[i] = -.5*np.sum(resid**2) + prior.logpdf(v) - proposal
        if len(sol.t_events[0]):
            events[i] = 1; yz[i] = sol.y_events[0][0,1:3]
        elif len(sol.t_events[1]): events[i] = 2
    if not np.isfinite(weights).any(): raise RuntimeError('no valid weighted samples')
    w = np.exp(weights-logsumexp(weights)); ess = 1/np.sum(w*w)
    return {'weights':w, 'events':events, 'yz':yz, 'velocity':velocities, 'spin':spin, 'cd0':cd0,
            'effective_sample_size':float(ess), 'n':n}


def summarize_physical(result, seed=2027, draws=10000, radius=.11):
    rng = np.random.default_rng(seed)
    idx = rng.choice(result['n'], size=draws, p=result['weights'])
    event = result['events'][idx]; points = result['yz'][idx[event == 1]]
    if len(points) < 10: raise ValueError('too few sampled plane crossings')
    full = (np.abs(points[:,0]) <= 3.66-radius) & (points[:,1] >= radius) & (points[:,1] <= 2.44-radius)
    center = (np.abs(points[:,0]) <= 3.66) & (points[:,1] >= 0) & (points[:,1] <= 2.44)
    mean = points.mean(axis=0); cov = np.cov(points.T)
    d = np.einsum('ni,ij,nj->n', points-mean, np.linalg.pinv(cov), points-mean)
    from scipy.stats import gaussian_kde
    candidates = points[rng.choice(len(points), min(1000,len(points)),replace=False)]
    mode = candidates[np.argmax(gaussian_kde(points.T)(candidates.T))]
    return {'points':points, 'mode':mode, 'mean':mean, 'covariance':cov,
            'ellipse_mahalanobis2':np.quantile(d,[.68,.95]), 'total':draws,
            'reached':int(len(points)), 'ground':int((event == 2).sum()),
            'no_event':int((event == 0).sum()), 'center_in':int(center.sum()), 'full_in':int(full.sum()),
            'effective_sample_size':result['effective_sample_size']}
