"""Unweighted initial velocity/spin fitting with the shared nine-state dynamics."""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from football.physics import state_derivative, validate_config

SCALE = np.array([30.,30.,30.,20*np.pi,20*np.pi,20*np.pi])


def observed_trajectory(times, position, initial_state, config, rtol=2e-9, atol=1e-11):
    sol = solve_ivp(lambda t,y:state_derivative(t,y,config),
                    (times[0],times[-1]), np.r_[position,initial_state],
                    t_eval=times, method='DOP853', rtol=rtol, atol=atol)
    if not sol.success or sol.y.shape[1]!=len(times):
        raise RuntimeError(sol.message)
    return sol.y.T


def fit_initial_state(times, positions, config, starts=None, max_nfev=400):
    """Estimate six initial-state components; no noise distribution or priors.

    19 deterministic starts use zero spin and 2,6,10 rev/s around +/- axes.
    These are numerical starts, not bounds on or assumptions about fitted spin.
    All distinct near-best minima are retained; no uniqueness is asserted.
    """
    validate_config(config)
    t=np.asarray(times,float);p=np.asarray(positions,float)
    if (t.ndim!=1 or len(t)<3 or p.shape!=(len(t),3)
        or np.any(np.diff(t)<=0) or not np.isfinite(p).all()):
        raise ValueError('at least three finite ordered positions are required')
    dt=t-t[0]
    # Quadratic interpolation supplies a velocity starting guess, not a fitted force.
    design=np.column_stack((dt[1:],.5*dt[1:]**2))
    velocity=np.linalg.lstsq(design,p[1:]-p[0],rcond=None)[0][0]
    velocity[0]=max(velocity[0],.01)
    if starts is None:
        starts=[np.r_[velocity,np.zeros(3)]]
        for rev in (2.,6.,10.):
            for axis in np.eye(3):
                for sign in (-1.,1.):
                    starts.append(np.r_[velocity,sign*2*np.pi*rev*axis])
    def residual(q):
        pred=observed_trajectory(t,p[0],q*SCALE,config)[:,:3]
        return ((pred[1:]-p[1:])/config.radius).ravel()
    records=[];solutions=[]
    for index,guess in enumerate(starts):
        try:
            fit=least_squares(residual,np.asarray(guess)/SCALE,
                bounds=([1e-8,-np.inf,-np.inf,-np.inf,-np.inf,-np.inf],np.full(6,np.inf)),
                jac='3-point',ftol=1e-10,xtol=1e-10,gtol=1e-10,max_nfev=max_nfev)
            state=fit.x*SCALE
            pred=observed_trajectory(t,p[0],state,config)
            difference=pred[:,:3]-p
            rss=float(np.sum(difference[1:]**2))
            singular=np.linalg.svd(fit.jac,compute_uv=False)
            rank=int(np.linalg.matrix_rank(fit.jac))
            record=dict(start=index,initial_guess=np.asarray(guess).tolist(),
                initial_state=state.tolist(),rss_m2=rss,
                max_component_residual_m=float(np.max(np.abs(difference[1:]))),
                rmse_3d_m=float(np.sqrt(np.mean(np.sum(difference[1:]**2,axis=1)))),
                residuals_m=difference.tolist(),success=bool(fit.success),status=int(fit.status),
                message=fit.message,nfev=int(fit.nfev),jacobian_scaled=fit.jac.tolist(),
                singular_values=singular.tolist(),rank=rank,
                practical_rank=int(np.sum(singular>singular[0]*1e-7)),
                practical_rank_relative_threshold=1e-7,
                condition_number=float(singular[0]/singular[-1]) if singular[-1]>0 else None,
                state_scaling=SCALE.tolist())
            records.append(record);solutions.append(record)
        except (RuntimeError,ValueError,FloatingPointError,np.linalg.LinAlgError) as exc:
            records.append(dict(start=index,success=False,error=str(exc)))
    if not solutions:
        raise RuntimeError('all initial-state optimization starts failed')
    solutions.sort(key=lambda r:r['rss_m2']);best=solutions[0]
    rss_tolerance=max(1e-12,1e-6*best['rss_m2'])
    selected=[]
    for record in solutions:
        if record['rss_m2']>best['rss_m2']+rss_tolerance:continue
        q=np.asarray(record['initial_state'])/SCALE
        if all(np.linalg.norm(q-np.asarray(old['initial_state'])/SCALE)>1e-3 for old in selected):
            selected.append(record)
    return dict(best=best,candidates=selected,starts=records,
        number_of_starts=len(starts),distinct_near_best=len(selected),
        near_best_rss_tolerance_m2=rss_tolerance,
        objective='unweighted position least squares; radius scaling changes units only',
        parameter_prior=None,measurement_noise_model=None,
        uniqueness='multistart search does not prove global uniqueness')
