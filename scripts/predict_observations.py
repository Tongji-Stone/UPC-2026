"""Report-v2 constant-spin inverse prediction; explicit model selection."""
import argparse,json
from pathlib import Path
import numpy as np
from dataclasses import replace
from football.physics import PhysicsConfig,simulate,config_record
from football.inference.four_model_fit import fit_early, InverseBounds


def main():
    parser=argparse.ArgumentParser();parser.add_argument('input')
    parser.add_argument('--output',default='results/structure_v2/custom_prediction.json')
    parser.add_argument('--model',choices=['M1','M2','M3','M4'],default='M4')
    args=parser.parse_args();data=json.loads(Path(args.input).read_text(encoding='utf-8'))
    times=data.get('times_s',data.get('times'));positions=data.get('positions_m',data.get('positions'))
    cfg=PhysicsConfig.for_model(args.model,**data.get('physics',{}))
    fitted=fit_early(times,positions,cfg,args.model,bounds=InverseBounds(**data.get('inverse_bounds',{})))
    cfg=replace(cfg,drag_scale=fitted['drag_scale'],lift_scale=fitted['lift_scale'])
    q=fitted['initial_state']
    f=simulate(positions[0],q[:3],q[3:],cfg,plane_x=data.get('plane_x_m',11.),
        t_span=(float(times[0]),float(times[0])+5),rtol=1e-10,atol=1e-12,max_step=.005)
    predictions=[dict(event=f.event,coverage=f.diagnostics)]
    def serialize(value):
        if isinstance(value,np.ndarray):return value.tolist()
        if isinstance(value,np.generic):return value.item()
        raise TypeError(type(value).__name__)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(dict(input=data,config=config_record(cfg),fit=fitted,
        predictions=predictions),indent=2,default=serialize,allow_nan=False),encoding='utf-8');print(path)


if __name__=='__main__':main()
