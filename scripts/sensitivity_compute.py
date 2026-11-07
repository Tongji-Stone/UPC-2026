# HISTORICAL pipeline; not used by the current paper. Use scripts/coupled_compute.py.
"""保存演示范围内的物理参数敏感性结果，单独运行后再运行绘图脚本。"""
import csv
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from football.physics import PhysicsConfig, simulate, linthorne_patel_coefficients

OUT = ROOT / 'results' / 'sensitivity'
SEED = 20261107
COUNT = 256
BASE = {'speed': float(np.linalg.norm([29.2, 8.2, 6.49])),
        'yaw_deg': float(np.degrees(np.arctan2(8.2, 29.2))),
        'pitch_deg': float(np.degrees(np.arctan2(6.49, np.hypot(29.2, 8.2)))),
        'cd0': .18, 'density': 1.2, 'lift_scale': 1.,
        'spin_x': 0., 'spin_y': 0., 'spin_z': 30., 'spin_decay': 0.,
        'wind_x': 0., 'wind_y': 0., 'wind_z': 0.}
RANGES = {'speed': (29., 33.), 'yaw_deg': (13., 19.), 'pitch_deg': (9., 15.),
          'cd0': (.10, .20), 'density': (1.1, 1.3), 'lift_scale': (.8, 1.2),
          'spin_x': (-20., 20.), 'spin_y': (-20., 20.), 'spin_z': (0., 50.),
          'spin_decay': (0., 1.), 'wind_x': (-3., 3.), 'wind_y': (-3., 3.), 'wind_z': (-3., 3.)}


def run(parameters):
    p = parameters
    paper = linthorne_patel_coefficients(cd0=p['cd0'])
    def coefficients(re, sp):
        cd, cl = paper(re, sp)
        return cd, cl * p['lift_scale']
    cfg = PhysicsConfig.for_model('M5', coefficients=coefficients, air_density=p['density'],
                                  spin_decay=p['spin_decay'],
                                  wind=(p['wind_x'], p['wind_y'], p['wind_z']))
    yaw, pitch = np.radians([p['yaw_deg'], p['pitch_deg']])
    velocity = p['speed'] * np.array([np.cos(pitch)*np.cos(yaw), np.cos(pitch)*np.sin(yaw), np.sin(pitch)])
    r = simulate((2.96, .86, .74), velocity,
                 (p['spin_x'], p['spin_y'], p['spin_z']), cfg, t_span=(.1, 1.1))
    event = r.event
    point = event['position'] if event['position'] is not None else [np.nan] * 3
    return {**p, 'event': event['type'], 'event_time': event['time'],
            'x': point[0], 'y': point[1], 'z': point[2]}


def save(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    single = []
    for key, (low, high) in RANGES.items():
        for value in np.linspace(low, high, 11):
            p = dict(BASE)
            p[key] = float(value)
            single.append({'parameter': key, **run(p)})
    generator = np.random.default_rng(SEED)
    samples = []
    for _ in range(COUNT):
        p = {key: float(generator.uniform(*bounds)) for key, bounds in RANGES.items()}
        samples.append(run(p))
    save(OUT / 'single_factor.csv', single)
    save(OUT / 'random_scan.csv', samples)
    (OUT / 'config.json').write_text(json.dumps({'seed': SEED, 'samples': COUNT,
        'baseline': BASE, 'ranges': RANGES, 'distribution': 'independent uniform',
        'initial_time_s': .1, 'initial_position_m': [2.96, .86, .74],
        'coefficient_model': 'Linthorne & Patel 2011 equations 3-4, spin in revolutions per second',
        'coefficient_source': 'https://www.jssm.org/volume10/iss1/cap/jssm-10-203.pdf',
        'lift_scale_description': 'multiplicative model variation around paper lift formula',
        'description': 'illustrative assumptions, not fitted distributions'},
        ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {len(single)} single-factor runs and {len(samples)} random runs to {OUT}')
    print('Random events:', {e: sum(row['event'] == e for row in samples) for e in ('plane', 'ground', 'none')})


if __name__ == '__main__':
    main()
