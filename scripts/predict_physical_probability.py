"""Run physical-model importance sampling, saving samples and metadata."""
import argparse
import json
from pathlib import Path
import numpy as np
from football.inference.physical_probability import infer_physical, summarize_physical

parser = argparse.ArgumentParser()
parser.add_argument('--samples',type=int,default=3000)
parser.add_argument('--sigma',type=float,default=.01)
parser.add_argument('--seed',type=int,default=2026)
args = parser.parse_args()
t = np.array([0.,.05,.10]); p = np.array([[0,0,.11],[1.50,.45,.44],[2.96,.86,.74]])
out = Path('results/physical_probability'); out.mkdir(parents=True,exist_ok=True)
report = {'assumptions':{'measurement_sigma_m':args.sigma,'fixed_initial_position':True,
    'velocity_prior_mean_m_s':[30,8,6],'velocity_prior_sd_m_s':[10,10,10],
    'spin_prior_component_sd_rad_s':30,'cd0_uniform':[.1,.2], 'samples':args.samples,'seed':args.seed,
    'coefficients':'Linthorne and Patel (2011) equations 3–4; 3D spin direction extension'}}
for name, length in [('005',2),('010',3)]:
    result = infer_physical(t[:length],p[:length],sigma=args.sigma,n=args.samples,seed=args.seed)
    np.savez_compressed(out/f'weighted_{name}.npz', **{k:v for k,v in result.items() if isinstance(v,np.ndarray)})
    stats = summarize_physical(result,seed=args.seed+1)
    np.savez_compressed(out/f'points_{name}.npz',points=stats.pop('points'))
    report[name] = {k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in stats.items()}
    print(name,report[name],flush=True)
(out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
