"""Deterministic, lexicographic early-position inversion for report models M1--M4."""
from dataclasses import dataclass, replace, asdict
import numpy as np
from scipy.optimize import least_squares, minimize
from .coupled_fit import observed_trajectory

RSS_ALLOWANCE = 6e-12  # m^2; numerical selection tolerance, not measurement noise
COEFFICIENT_ALLOWANCE = 1e-8


@dataclass(frozen=True)
class InverseBounds:
    """Finite component limits in SI units and force-scale scenario limits.

    The 35 m/s component bound references the Teamgeist fit's speed range in
    Kiratidis & Leinweber (2018), DOI 10.1088/1361-6404/aaa888. The 10 rev/s
    spin-component bound references Asai et al. (2007), DOI 10.1007/BF02844207.
    These component-wise boxes are analysis choices, not total-magnitude or
    universal physical bounds. Force multipliers [0.5, 1.5] are an illustrative
    scenario assumption, not an experimentally reported confidence interval.
    """
    velocity_component_max_m_s: float = 35.0
    spin_component_max_rad_s: float = 20.0 * np.pi
    force_scale_min: float = 0.5
    force_scale_max: float = 1.5

    def __post_init__(self):
        vals = (self.velocity_component_max_m_s, self.spin_component_max_rad_s,
                self.force_scale_min, self.force_scale_max)
        if not np.isfinite(vals).all() or self.velocity_component_max_m_s <= 0 or self.spin_component_max_rad_s <= 0:
            raise ValueError('velocity and spin component bounds must be finite and positive')
        if not 0 <= self.force_scale_min < self.force_scale_max:
            raise ValueError('force-scale bounds must be finite, ordered and nonnegative')


def fit_early(times, positions, config, model, max_nfev=240, bounds=None):
    t, p = np.asarray(times, float), np.asarray(positions, float)
    bounds = InverseBounds() if bounds is None else bounds
    if not isinstance(bounds, InverseBounds):
        raise TypeError('bounds must be an InverseBounds instance')
    if model not in ('M1', 'M2', 'M3', 'M4'):
        raise ValueError('model must be M1, M2, M3 or M4')
    if t.shape != (3,) or p.shape != (3, 3) or np.any(np.diff(t) <= 0):
        raise ValueError('exactly three ordered positions are required')
    dt = t[1:] - t[0]
    velocity = np.linalg.lstsq(np.c_[dt, .5*dt**2], p[1:]-p[0], rcond=None)[0][0]
    velocity[0] = max(velocity[0], .01)
    if model == 'M1':
        offset = p[1:]-p[0] + np.c_[np.zeros(2), np.zeros(2), .5*config.gravity*dt**2]
        v = np.clip(np.sum(dt[:, None]*offset, axis=0)/np.sum(dt**2),
                    [0., -bounds.velocity_component_max_m_s, -bounds.velocity_component_max_m_s],
                    [bounds.velocity_component_max_m_s]*3)
        state = np.r_[v, np.zeros(3)]
        predicted = observed_trajectory(t, p[0], state, config)[:, :3]
        rss = float(np.sum((predicted[1:]-p[1:])**2))
        return dict(model=model, initial_state=state.tolist(), drag_scale=1., lift_scale=1.,
            rss_m2=rss, max_residual_m=float(np.max(abs(predicted-p))), fitted_positions=predicted.tolist(),
            active_parameters=3, spin_representation='not used', coefficient_distance=0.,
            starts=[], stages=[], selection='bounded gravity-only linear least squares', success=True,
            fit_bounds=asdict(bounds), at_parameter_bound=bool(np.any(np.isclose(v,
                [0., -bounds.velocity_component_max_m_s, -bounds.velocity_component_max_m_s],atol=1e-7))
                or np.any(np.isclose(v, [bounds.velocity_component_max_m_s]*3,atol=1e-7))))

    def unpack(q):
        if model == 'M2':
            return np.r_[30*q[:3], np.zeros(3)], replace(config, drag_scale=q[3])
        if model == 'M3':
            az, el = q[3:5]
            axis = np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])
            return np.r_[30*q[:3], axis], replace(config, drag_scale=q[5], lift_scale=q[6])
        return np.r_[30*q[:3], 60*q[3:6]], replace(config, drag_scale=q[6], lift_scale=q[7])

    count = {'M2':4, 'M3':7, 'M4':8}[model]
    vmax = bounds.velocity_component_max_m_s / 30.
    lower = np.full(count, -1.); upper = np.full(count, 1.)
    lower[:3] = [0., -vmax, -vmax]; upper[:3] = vmax
    scale_indices = [3] if model == 'M2' else [5,6] if model == 'M3' else [6,7]
    lower[scale_indices] = bounds.force_scale_min
    upper[scale_indices] = bounds.force_scale_max
    if model == 'M3':
        lower[3:5], upper[3:5] = [-np.pi, -np.pi/2], [np.pi, np.pi/2]
    if model == 'M4':
        lower[3:6] = -bounds.spin_component_max_rad_s / 60.
        upper[3:6] = bounds.spin_component_max_rad_s / 60.
    guesses = []
    if model == 'M2': guesses = [np.r_[velocity/30, 1.]]
    elif model == 'M3':
        for az, el in [(0,0),(np.pi/2,0),(np.pi,0),(-np.pi/2,0),(0,1.4),(0,-1.4)]:
            guesses.append(np.r_[velocity/30, az, el, 1., 1.])
    else:
        guesses = [np.r_[velocity/30, np.zeros(3), 1., 1.]]
        for angular_speed in (4*np.pi,30.,20*np.pi):
            for axis in np.eye(3):
                for sign in (-1.,1.): guesses.append(np.r_[velocity/30, sign*angular_speed*axis/60, 1.,1.])

    def residual(q):
        state, cfg = unpack(q)
        pred = observed_trajectory(t, p[0], state, cfg, rtol=3e-10, atol=2e-12)[:, :3]
        return ((pred[1:]-p[1:])/config.radius).ravel()

    def distance(q): return float(np.sum((q[scale_indices]-1.)**2))
    records, solutions = [], []
    for i, guess in enumerate(guesses):
        try:
            guess = np.clip(guess, lower, upper)
            opt = least_squares(residual, guess, bounds=(lower,upper),
                ftol=2e-11, xtol=2e-11, gtol=2e-11, max_nfev=max_nfev)
            q_opt = np.clip(opt.x, lower, upper)
            rss = float(np.sum(residual(q_opt)**2)*config.radius**2)
            records.append(dict(start=i, rss_m2=rss, success=bool(opt.success),
                nfev=opt.nfev, parameters=opt.x.tolist(), message=opt.message))
            solutions.append((rss,opt.x))
            print(f'{model} start {i+1}/{len(guesses)}: RSS={rss:.5g}, nfev={opt.nfev}', flush=True)
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            records.append(dict(start=i, success=False, error=str(exc)))
    if not solutions: raise RuntimeError('all fitting starts failed')
    solutions.sort(key=lambda x:x[0]); min_rss, best = solutions[0]
    primary_converged=min((r for r in records if 'rss_m2' in r),key=lambda r:r['rss_m2'])['success']
    stages = [dict(stage='positions', rss_m2=min_rss, coefficient_distance=distance(best))]
    limit = min_rss + RSS_ALLOWANCE
    if primary_converged and model in ('M3','M4'):
        # Equality constraints are well conditioned for essentially exact fits.
        exact = min_rss < 1e-15
        constraint = ({'type':'eq','fun':residual} if exact else
            {'type':'ineq','fun':lambda q:(limit/config.radius**2)-np.sum(residual(q)**2)})
        # Search each distinct force/state basin. Coefficient preference precedes spin preference.
        candidates = [q for rss,q in solutions if rss<=limit]
        candidates.sort(key=distance)
        chosen = []
        for q in candidates:
            if all(np.linalg.norm(q-old)>1e-2 for old in chosen): chosen.append(q)
            if len(chosen)>=4:break
        admissible = [(distance(q),q) for q in candidates]
        for q in chosen:
            print(f'{model}: coefficient selection', flush=True)
            opt = minimize(distance,q,method='SLSQP',bounds=list(zip(lower,upper)),
                constraints=[constraint],options={'maxiter':300,'ftol':1e-12})
            rss = float(np.sum(residual(opt.x)**2)*config.radius**2)
            stages.append(dict(stage='coefficients',success=bool(opt.success),message=opt.message,
                rss_m2=rss,coefficient_distance=distance(opt.x)))
            if rss <= limit and np.isfinite(q_opt).all(): admissible.append((distance(q_opt),q_opt))
        admissible.sort(key=lambda x:x[0]); dmin,best=admissible[0]
        if model == 'M4':
            print('M4: spin selection', flush=True)
            constraints=[constraint,{'type':'ineq','fun':lambda q:dmin+COEFFICIENT_ALLOWANCE-distance(q)}]
            opt=minimize(lambda q:float(q[3:6]@q[3:6]),best,method='SLSQP',
                bounds=list(zip(lower,upper)),constraints=constraints,options={'maxiter':250,'ftol':1e-12})
            q_opt=np.clip(opt.x,lower,upper)
            rss=float(np.sum(residual(q_opt)**2)*config.radius**2)
            accepted=bool(rss<=limit and distance(q_opt)<=dmin+COEFFICIENT_ALLOWANCE+1e-12)
            stages.append(dict(stage='spin',success=bool(opt.success),accepted=accepted,
                message=opt.message,rss_m2=rss,coefficient_distance=distance(q_opt)))
            if accepted:best=q_opt
    state,cfg=unpack(best)
    pred=observed_trajectory(t,p[0],state,cfg,rtol=1e-11,atol=1e-13)[:,:3]
    # Position-only finite-difference Jacobian, separated from selection objectives.
    step=1e-5
    jac=np.column_stack([(residual(best+np.eye(count)[i]*step)-residual(best-np.eye(count)[i]*step))/(2*step)
                         if best[i]-step>=lower[i] and best[i]+step<=upper[i]
                         else (residual(best)-residual(best-np.eye(count)[i]*step))/step
                         if best[i]-step>=lower[i]
                         else (residual(best+np.eye(count)[i]*step)-residual(best))/step for i in range(count)])
    sv=np.linalg.svd(jac,compute_uv=False)
    return dict(model=model,initial_state=state.tolist(),drag_scale=float(cfg.drag_scale),
        lift_scale=float(cfg.lift_scale),rss_m2=float(np.sum((pred[1:]-p[1:])**2)),
        minimum_search_rss_m2=min_rss,max_residual_m=float(np.max(abs(pred-p))),
        fitted_positions=pred.tolist(),active_parameters=count,
        spin_representation='unit axis; magnitude absent from constant-CL forces' if model=='M3' else
                            'not used' if model=='M2' else 'rad/s vector',
        coefficient_distance=distance(best),rss_allowance_m2=RSS_ALLOWANCE,
        coefficient_distance_allowance=COEFFICIENT_ALLOWANCE,
        starts=records,stages=stages,position_jacobian_singular_values=sv.tolist(),
        position_jacobian_rank=int(np.sum(sv>sv[0]*1e-7)),
        selection='positions, then coefficients nearest one, then smallest M4 spin',success=bool(primary_converged),
        position_stage_converged=bool(primary_converged), fit_bounds=asdict(bounds),
        at_parameter_bound=bool(np.any(np.isclose(best,lower,atol=1e-7)) or np.any(np.isclose(best,upper,atol=1e-7))))
