"""Compute and save example predictions; plotting is a separate command."""
import json
from pathlib import Path
import numpy as np
from football.inference.kinematic import fit, sample_predictions
from football.models.baseline import predict

OUT = Path('results')
OUT.mkdir(exist_ok=True)
times = np.array([0., .05, .10])
positions = np.array([[0., 0., .11], [1.50, .45, .44], [2.96, .86, .74]])
prior_mean = np.array([[30., 8., 6.], [-8., 0., -9.81]])
prior_std = np.array([[10., 10., 10.], [15., 15., 15.]])
report = {'assumptions': {'sigma_m': .01, 'prior_mean_v_a': prior_mean.tolist(), 'prior_std_v_a': prior_std.tolist(), 'seed': 2026, 'samples': 20000, 'initial_position_fixed': True}}
report['baselines'] = {'M1_005': predict(times[:2], positions[:2]).tolist(), 'M1_010': predict(times[1:], positions[1:]).tolist(), 'M2_010': predict(times, positions, 'M2').tolist()}
for name, count in [('005', 2), ('010', 3)]:
    result = sample_predictions(times[:count], positions[:count], .01, prior_mean, prior_std, seed=2026)
    np.savez_compressed(OUT / f'prediction_{name}.npz', points=result.pop('points'))
    for key, value in result.items():
        if isinstance(value, np.ndarray): result[key] = value.tolist()
    diagnostic = fit(times[:count], positions[:count], .01, prior_mean, prior_std)
    result['fit'] = {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in diagnostic.items()}
    report[name] = result
(OUT / 'problem_b.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
