"""Fit initial velocity with a fixed physical configuration from a JSON input."""
import argparse
import json
from pathlib import Path
import numpy as np
from football.inference.physical_fit import fit_velocity
from football.physics import PhysicsConfig, simulate

parser = argparse.ArgumentParser()
parser.add_argument('input', help='JSON file containing times, positions, and optional spin and physics')
parser.add_argument('--model', choices=['M0','M1','M3','M4','M5'], default='M3')
parser.add_argument('--output', default='results/custom_prediction.json')
args = parser.parse_args()
data = json.loads(Path(args.input).read_text(encoding='utf-8'))
cfg = PhysicsConfig.for_model(args.model, **data.get('physics', {}))
times = np.asarray(data['times'], float); positions = np.asarray(data['positions'], float)
spin = data.get('spin', [0,0,0]); sigma = data.get('sigma', .01)
fitted = fit_velocity(times, positions, cfg, sigma=sigma, spin=spin)
flight = simulate(positions[0], fitted['velocity'], spin=spin, config=cfg, t_span=(float(times[0]), float(times[0])+2), plane_x=data.get('plane_x',11.))
def serialize(x):
    if isinstance(x, np.ndarray): return x.tolist()
    if isinstance(x, np.generic): return x.item()
    raise TypeError(type(x).__name__)
out = {'model': args.model, 'input':data, 'fit': fitted, 'event':flight.event}
path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=serialize), encoding='utf-8')
print(path)
