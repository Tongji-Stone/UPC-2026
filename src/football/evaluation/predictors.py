"""Validation-only adapters around the integration team's model interfaces."""
import numpy as np

from football.inference.physical_fit import fit_velocity
from football.physics import PhysicsConfig, linthorne_patel_coefficients, simulate
from .benchmark import Prediction


def physical_predictor(model):
    if model not in ('M0', 'M1', 'M2', 'M3', 'M4', 'M5'):
        raise ValueError('unknown model')

    def predict(request, rng):
        t = request.times_s-request.times_s[0]
        p = request.positions_m
        if model == 'M2':
            if len(t) < 3:
                return Prediction('insufficient_observations')
            coef = np.linalg.solve(np.column_stack((np.ones(3), t[-3:], t[-3:]**2)), p[-3:])
            roots = np.roots([coef[2, 0], coef[1, 0], coef[0, 0]-request.plane_x_m])
            candidates = sorted(r.real for r in roots if abs(r.imag) < 1e-9
                                and r.real >= request.cutoff_s-request.times_s[0]
                                and r.real <= 2.
                                and coef[1, 0]+2*coef[2, 0]*r.real > 0)
            if not candidates:
                return Prediction('none', crossing_probability=0.)
            arrival = candidates[0]
            ground = np.roots([coef[2, 2], coef[1, 2], coef[0, 2]-.11])
            if any(abs(r.imag) < 1e-9 and 0 <= r.real <= arrival
                   and coef[1, 2]+2*coef[2, 2]*r.real < 0 for r in ground):
                return Prediction('ground', crossing_probability=0.)
            point = coef[0]+coef[1]*arrival+coef[2]*arrival**2
            return Prediction('plane', point[1:], 1.)
        spin = (0., 0., 30.) if model in ('M4', 'M5') else (0., 0., 0.)
        kwargs = {'coefficients': linthorne_patel_coefficients()} if model == 'M5' else {}
        config = PhysicsConfig.for_model(model, **kwargs)
        fit = fit_velocity(t, p, config, spin=spin)
        result = simulate(p[0], fit['velocity'], spin=spin, config=config,
                          t_span=(0., 2.), plane_x=request.plane_x_m)
        status = result.event['type']
        if status == 'plane' and result.event['time'] <= request.cutoff_s-request.times_s[0]:
            return Prediction('none', crossing_probability=0.)
        return Prediction(status, result.event['position'][1:] if status == 'plane' else None,
                          float(status == 'plane'))
    return predict


def gravity_ensemble(*, sigma_m=.01, samples=256):
    """Perturb observed positions by assumed iid Gaussian noise, refit M1.

    This measurement-noise propagation is an explicit baseline. It uses the
    same observed prefix as deterministic M1, including all available frames.
    """
    if not np.isfinite(sigma_m) or sigma_m <= 0 or samples < 3 or int(samples) != samples:
        raise ValueError('positive sigma and at least three integer samples required')

    def predict(request, rng):
        t = request.times_s-request.times_s[0]
        p = request.positions_m[None, :, :] + rng.normal(0, sigma_m, (samples, len(t), 3))
        acceleration = np.array([0., 0., -9.81])
        adjusted = p-p[:, :1, :]- .5*t[None, :, None]**2*acceleration
        velocity = np.einsum('t,ntd->nd', t, adjusted) / (t @ t)
        origin = p[:, 0, :]
        with np.errstate(divide='ignore', invalid='ignore'):
            arrival = (request.plane_x_m-origin[:, 0]) / velocity[:, 0]
            ground = (velocity[:, 2]+np.sqrt(velocity[:, 2]**2+2*9.81*np.maximum(origin[:, 2]-.11, 0))) / 9.81
            points = origin + velocity*arrival[:, None] + .5*acceleration*arrival[:, None]**2
        valid = ((velocity[:, 0] > 0) & (arrival > request.cutoff_s-request.times_s[0])
                 & (arrival < ground) & (arrival <= 2.) & (origin[:, 2] >= .11)
                 & np.isfinite(points).all(axis=1))
        probability = float(np.mean(valid))
        cloud = points[valid, 1:]
        if not len(cloud):
            return Prediction('none', crossing_probability=probability)
        return Prediction('plane', cloud.mean(axis=0), probability, cloud)
    return predict
