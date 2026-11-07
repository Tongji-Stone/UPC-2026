"""Known-truth synthetic check of truncation, event scoring and region coverage."""
import argparse
import json
from pathlib import Path

import numpy as np

from football.evaluation.benchmark import run_benchmark, summarize_benchmark
from football.evaluation.predictors import gravity_ensemble


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=int, default=100)
    parser.add_argument('--samples', type=int, default=256)
    parser.add_argument('--seed', type=int, default=20261107)
    parser.add_argument('--sigma', type=float, default=.01)
    parser.add_argument('--out', type=Path, default=Path('results/data_validation_synthetic'))
    args = parser.parse_args()
    if args.cases < 1:
        parser.error('--cases must be positive')
    predictor = gravity_ensemble(sigma_m=args.sigma, samples=args.samples)
    rng = np.random.default_rng(args.seed)
    times = np.arange(21)/25
    cases = []
    for i in range(args.cases):
        velocity = np.array([rng.uniform(25,35), rng.uniform(-4,4), rng.uniform(2,7)])
        positions = np.array([0.,0.,1.2])+times[:,None]*velocity
        positions[:,2] -= 4.905*times**2
        arrival = 11/velocity[0]
        truth = np.array([velocity[1]*arrival, 1.2+velocity[2]*arrival-4.905*arrival**2])
        measured = positions+rng.normal(0,args.sigma,positions.shape)
        cases.append({'sample_id': f'synthetic:{i:04}', 'times': times,
                      'positions': measured, 'truth_yz_m': truth})
    records = run_benchmark(cases, {'M1_noise': predictor}, seed=args.seed)
    summary = summarize_benchmark(records)
    summary['configuration'] = {'dataset_kind': 'synthetic analytic gravity trajectories',
                                'cases': args.cases, 'seed': args.seed, 'ensemble_samples': args.samples,
                                'true_and_assumed_sigma_m': args.sigma, 'native_fps': 25,
                                'initial_position_m': [0,0,1.2], 'vx_uniform_m_s': [25,35],
                                'vy_uniform_m_s': [-4,4], 'vz_uniform_m_s': [2,7],
                                'gravity_m_s2': 9.81, 'plane_x_m': 11.}
    args.out.mkdir(parents=True, exist_ok=True)
    for filename, value in [('summary.json',summary),('predictions.json',records)]:
        (args.out/filename).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(summary['groups'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
