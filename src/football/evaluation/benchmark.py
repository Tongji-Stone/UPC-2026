"""Run isolated early-observation predictors on a shared fixed sample list."""
from collections import Counter
from dataclasses import dataclass
import hashlib
from time import perf_counter

import numpy as np

from football.data.validation import early_observations
from .metrics import brier_score, coverage, ellipse_contains, energy_score, summarize_errors


@dataclass(frozen=True)
class PredictionRequest:
    times_s: np.ndarray
    positions_m: np.ndarray
    cutoff_s: float
    plane_x_m: float


@dataclass
class Prediction:
    status: str
    yz_m: np.ndarray | None = None
    crossing_probability: float | None = None
    samples_yz_m: np.ndarray | None = None


def validate_prediction(prediction):
    if not isinstance(prediction, Prediction):
        raise ValueError('predictors must return Prediction')
    if prediction.status not in ('plane', 'ground', 'none', 'insufficient_observations'):
        raise ValueError('unknown event status')
    if prediction.status == 'plane':
        yz = np.asarray(prediction.yz_m, float)
        if yz.shape != (2,) or not np.isfinite(yz).all():
            raise ValueError('plane prediction requires finite yz (2,)')
    elif prediction.yz_m is not None:
        raise ValueError('noncrossing prediction cannot have a crossing point')
    probability = prediction.crossing_probability
    if probability is not None and (not np.isfinite(probability) or not 0 <= probability <= 1):
        raise ValueError('invalid crossing probability')
    if prediction.samples_yz_m is not None:
        cloud = np.asarray(prediction.samples_yz_m, float)
        if cloud.ndim != 2 or cloud.shape[1] != 2 or len(cloud) == 0 or not np.isfinite(cloud).all():
            raise ValueError('conditional samples must be finite (N,2)')


def run_benchmark(samples, predictors, *, durations=(.05, .10), plane_x=11., seed=20261107):
    """Predictor(request, rng) sees only copied, read-only prefix observations.

    Each sample contains sample_id, times, positions and truth_yz_m (or None
    for an observed noncrossing). Truth is used exclusively by the evaluator.
    """
    if not samples or not predictors or len(set(s['sample_id'] for s in samples)) != len(samples):
        raise ValueError('nonempty samples/predictors and unique sample IDs required')
    if (not np.isfinite(plane_x) or not durations or len(set(durations)) != len(durations)
            or any(not np.isfinite(d) or d <= 0 for d in durations)):
        raise ValueError('finite plane and unique positive durations required')
    records = []
    for sample in samples:
        truth = sample.get('truth_yz_m')
        if truth is not None:
            truth = np.asarray(truth, float)
            if truth.shape != (2,) or not np.isfinite(truth).all():
                raise ValueError('truth must be finite yz or None')
        for duration in durations:
            times, points = early_observations(sample['times'], sample['positions'], duration)
            for name, predictor in predictors.items():
                # Model order and other sample outcomes cannot change the seed.
                key = f"{sample['sample_id']}|{duration:.12g}|{name}".encode()
                entropy = int.from_bytes(hashlib.sha256(key).digest()[:8], 'little')
                rng = np.random.default_rng(np.random.SeedSequence([seed, entropy]))
                t, p = times.copy(), points.copy()
                t.setflags(write=False)
                p.setflags(write=False)
                request = PredictionRequest(t, p, float(times[0]+duration), plane_x)
                row = {'sample_id': sample['sample_id'], 'model': name, 'duration_s': duration,
                       'input_times_s': times.tolist(), 'n_observations': len(times),
                       'last_observed_s': float(times[-1]), 'truth_crossed': truth is not None,
                       'truth_yz_m': None if truth is None else truth.tolist()}
                started = perf_counter()
                try:
                    prediction = predictor(request, rng)
                    validate_prediction(prediction)
                    row['status'] = prediction.status
                    row['prediction_yz_m'] = (np.asarray(prediction.yz_m).tolist()
                                              if prediction.yz_m is not None else None)
                    row['crossing_probability'] = prediction.crossing_probability
                except (ValueError, RuntimeError, FloatingPointError, np.linalg.LinAlgError) as exc:
                    prediction = None
                    row.update(status='error', error_type=type(exc).__name__, error_message=str(exc),
                               prediction_yz_m=None, crossing_probability=None)
                row['runtime_s'] = perf_counter()-started
                row['error_m'] = (float(np.linalg.norm(np.asarray(prediction.yz_m)-truth))
                                  if truth is not None and prediction is not None and prediction.status == 'plane'
                                  else None)
                row['energy_score_m'] = None
                row['coverage_68'] = row['coverage_95'] = None
                if truth is not None and prediction is not None and prediction.samples_yz_m is not None:
                    cloud = np.asarray(prediction.samples_yz_m)
                    row['conditional_sample_count'] = len(cloud)
                    row['energy_score_m'] = energy_score(cloud, truth)
                    try:
                        row['coverage_68'] = ellipse_contains(cloud, truth, .68)
                        row['coverage_95'] = ellipse_contains(cloud, truth, .95)
                    except ValueError:
                        row['region_status'] = 'singular_or_too_few_samples'
                records.append(row)
    return records


def summarize_benchmark(records):
    if not records:
        raise ValueError('no benchmark records')
    groups, common = {}, {}
    for duration in sorted({r['duration_s'] for r in records}):
        window = [r for r in records if r['duration_s'] == duration]
        available = sorted({r['model'] for r in window if r['status'] != 'insufficient_observations'})
        ids = sorted({r['sample_id'] for r in window})
        shared = [sid for sid in ids if all(any(
            r['sample_id'] == sid and r['model'] == name and r['error_m'] is not None
            for r in window) for name in available)] if available else []
        common[str(duration)] = {'sample_ids': shared, 'n': len(shared), 'models': available, 'errors': {}}
        for name in sorted({r['model'] for r in window}):
            group = [r for r in window if r['model'] == name]
            valid = [r for r in group if r['error_m'] is not None]
            info = {'cases': len(group), 'truth_crossing_n': sum(r['truth_crossed'] for r in group),
                    'prediction_crossing_n': sum(r['status'] == 'plane' for r in group),
                    'events': dict(Counter(r['status'] for r in group)), 'paired_crossing_n': len(valid),
                    'mean_runtime_s': float(np.mean([r['runtime_s'] for r in group])),
                    'p90_runtime_s': float(np.quantile([r['runtime_s'] for r in group], .9)),
                    'errors': summarize_errors([r['truth_yz_m'] for r in valid],
                                               [r['prediction_yz_m'] for r in valid]) if valid else None}
            probability_rows = [r for r in group if r['crossing_probability'] is not None]
            info['crossing_brier'] = brier_score([r['crossing_probability'] for r in probability_rows],
                                               [r['truth_crossed'] for r in probability_rows]) if probability_rows else None
            scored = [r['energy_score_m'] for r in group if r['energy_score_m'] is not None]
            info['conditional_energy_score'] = {'n': len(scored), 'mean_m': float(np.mean(scored)) if scored else None}
            for label in ('68', '95'):
                covered = [r['coverage_'+label] for r in group if r['coverage_'+label] is not None]
                info['conditional_coverage_'+label] = coverage(covered) if covered else {'n': 0, 'rate': None}
            groups[f'{duration}_{name}'] = info
            shared_rows = [r for r in valid if r['sample_id'] in shared]
            if shared_rows:
                common[str(duration)]['errors'][name] = summarize_errors(
                    [r['truth_yz_m'] for r in shared_rows], [r['prediction_yz_m'] for r in shared_rows])
    return {'groups': groups, 'common_cases': common,
            'denominators': {'point_errors': 'observed and predicted crossing pairs',
                             'coverage_energy': 'observed crossings with conditional ensemble/valid region',
                             'brier': 'all cases with a crossing probability, including observed noncrossings',
                             'common_cases': 'intersection of successful crossings for all available models'}}
