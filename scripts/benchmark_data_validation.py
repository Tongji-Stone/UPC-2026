"""Evaluate M0-M5 and an assumed-noise M1 ensemble on the frozen DFL manifest."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import scipy

from football.evaluation.benchmark import run_benchmark, summarize_benchmark
from football.evaluation.predictors import gravity_ensemble, physical_predictor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data/processed/data_validation'))
    parser.add_argument('--out', type=Path, default=Path('results/data_validation'))
    parser.add_argument('--samples', type=int, default=256)
    parser.add_argument('--sigma', type=float, default=.01)
    parser.add_argument('--seed', type=int, default=20261107)
    args = parser.parse_args()
    raw_manifest = (args.data/'manifest.json').read_bytes()
    manifest = json.loads(raw_manifest)
    if hashlib.sha256((args.data/'selected_tracks.csv').read_bytes()).hexdigest() != manifest['selected_tracks_sha256']:
        raise ValueError('selected tracks do not match the frozen manifest checksum')
    with (args.data/'selected_tracks.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    ids = [entry['sample_id'] for entry in manifest['samples']]
    if set(ids) != {row['sample_id'] for row in rows}:
        raise ValueError('track IDs do not match frozen manifest')
    cases = []
    for entry in manifest['samples']:
        selected = [row for row in rows if row['sample_id'] == entry['sample_id']]
        cases.append({'sample_id': entry['sample_id'], 'times': np.array([float(r['t_s']) for r in selected]),
                      'positions': np.array([[float(r[k]) for k in ('x_m','y_m','z_m')] for r in selected]),
                      'truth_yz_m': np.array(entry['truth_yz_m'])})
    predictors = {name: physical_predictor(name) for name in ('M0','M1','M2','M3','M4','M5')}
    predictors['M1_noise'] = gravity_ensemble(sigma_m=args.sigma, samples=args.samples)
    records = run_benchmark(cases, predictors, seed=args.seed,
                            plane_x=manifest['selection_config']['plane_x_m'])
    summary = summarize_benchmark(records)
    summary['configuration'] = {'seed': args.seed, 'ensemble_samples': args.samples,
                                'assumed_position_sigma_m': args.sigma, 'windows_s': [.05,.10],
                                'manifest_sha256': hashlib.sha256(raw_manifest).hexdigest(),
                                'tracks_sha256': hashlib.sha256((args.data/'selected_tracks.csv').read_bytes()).hexdigest(),
                                'dataset': 'DFL J03WOH, ordinary flights, virtual x=11m plane',
                                'z_unit_status': manifest['z_unit_status'],
                                'M4_M5_spin_rad_s': [0.,0.,30.], 'M4_Cd_Cl': [.25,.2],
                                'M5_coefficients': 'Linthorne-Patel, Cd0=0.18',
                                'prediction_horizon_s': 2., 'velocity_fit_sigma_m': .01,
                                'ensemble_method': 'perturb only observed positions by iid Gaussian noise; refit M1',
                                'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
                                'platform': platform.platform(),
                                'base_commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                                'code_sha256': {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                                for path in sorted(Path('src/football').rglob('*.py'))}}
    args.out.mkdir(parents=True, exist_ok=True)
    for filename, value in [('summary.json', summary), ('predictions.json', records)]:
        (args.out/filename).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
