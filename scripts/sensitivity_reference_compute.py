"""Refit the competition positions with the current shared linear-spin M4 model."""
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from football.physics import PhysicsConfig, simulate, config_record
from football.inference.four_model_fit import fit_early, InverseBounds


def main():
    path = ROOT / 'configs/sensitivity_v2.json'
    inputs = json.loads(path.read_text(encoding='utf-8'))
    p = inputs['physics']
    cfg = PhysicsConfig.for_model('M4', mass=p['mass'], radius=p['radius'],
        air_density=p['rho'], kinematic_viscosity=p['nu'], gravity=p['gravity'])
    fit = fit_early(inputs['times_s'], inputs['positions_m'], cfg, 'M4',
                    max_nfev=240, bounds=InverseBounds())
    cfg = replace(cfg, drag_scale=fit['drag_scale'], lift_scale=fit['lift_scale'])
    state = np.array(fit['initial_state'])
    flight = simulate(inputs['positions_m'][0], state[:3], state[3:], cfg,
        plane_x=11., t_span=(0., 5.), rtol=2e-12, atol=2e-14, max_step=.005)
    result = dict(input=inputs, fit=fit, configuration=config_record(cfg),
        record=dict(case='problem_b', model='M4', initial_state=state.tolist(),
            drag_scale=fit['drag_scale'], lift_scale=fit['lift_scale'],
            fitted_cd=cfg.drag_coefficient*cfg.drag_scale,
            fitted_alpha=cfg.lift_coefficient*cfg.lift_scale,
            max_residual_m=fit['max_residual_m'], event=flight.event),
        source_sha256={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
            for name in ['src/football/physics/model.py',
                         'src/football/inference/four_model_fit.py',
                         'configs/sensitivity_v2.json']})
    output = ROOT / inputs['baseline_result']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2,
        default=lambda x: x.tolist() if isinstance(x, np.ndarray) else x.item(),
        allow_nan=False), encoding='utf-8')
    print(json.dumps(json.loads(output.read_text(encoding='utf-8'))['record'],
                     ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
