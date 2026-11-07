# HISTORICAL pipeline; not used by the current paper. Use scripts/coupled_compute.py.
"""Fit complete selected DFL tracks and evaluate reconstruction, not prediction."""
import argparse
import csv
from collections import Counter
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from scipy.integrate import solve_ivp
from football.physics import PhysicsConfig, forces, linthorne_patel_coefficients
from football.inference.physical_fit import fit_velocity
from datetime import datetime
from football.data.validation import align_forward, crossing


def metrics(x):
    x=np.asarray(x,float)
    if not len(x): return {'n':0}
    return {'n':len(x),'mean_m':float(x.mean()),'median_m':float(np.median(x)),
            'p90_m':float(np.quantile(x,.9))}


def curve(model,t,p,plane_x=11.):
    """Return prediction at observations until contact and first plane crossing."""
    if model == 'M2':
        h=np.column_stack((t,.5*t*t))
        params=np.linalg.lstsq(h[1:],(p-p[0])[1:],rcond=None)[0]
        def pos(x): return p[0]+x*params[0]+.5*x*x*params[1]
        roots=np.roots([.5*params[1,2],params[0,2],p[0,2]-.11])
        ground=[r.real for r in roots if abs(r.imag)<1e-8 and 0<r.real<=t[-1] and params[0,2]+params[1,2]*r.real<0]
        stop=min(ground) if ground else t[-1]
        plane_roots=np.roots([.5*params[1,0],params[0,0],p[0,0]-plane_x])
        hits=[r.real for r in plane_roots if abs(r.imag)<1e-8 and 0<=r.real<=stop and params[0,0]+params[1,0]*r.real>0]
        hit=pos(min(hits))[1:] if hits else None
        return np.array([pos(v) for v in t[t<=stop+1e-10]]),hit,('ground' if ground else 'completed')
    spin=(0.,0.,30.) if model in ('M4','M5') else (0.,0.,0.)
    config=PhysicsConfig.for_model(model,**({'coefficients':linthorne_patel_coefficients()} if model=='M5' else {}))
    fitted=fit_velocity(t,p,config,spin=spin)
    def rhs(_,s):
        return np.r_[s[3:6],sum(forces(s[3:6],s[6:9],config).values())/config.mass,
                     -config.spin_decay*s[6:9]]
    def ground(_,s): return s[2]-config.radius
    ground.terminal=True;ground.direction=-1
    def plane(_,s): return s[0]-plane_x
    plane.terminal=False;plane.direction=1
    sol=solve_ivp(rhs,(t[0],t[-1]),np.r_[p[0],fitted['velocity'],spin],
                  events=(ground,plane),dense_output=True,rtol=1e-8,atol=1e-10)
    if not sol.success: raise RuntimeError(sol.message)
    observed=t[t<=sol.t[-1]+1e-10]
    fitted_points=sol.sol(observed)[:3].T
    hit=sol.y_events[1][0,1:3] if len(sol.t_events[1]) else None
    return fitted_points,hit,('ground' if len(sol.t_events[0]) else 'completed')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('ball_csv')
    parser.add_argument('--count',type=int,default=30)
    parser.add_argument('--out',default='results/dfl_full_trajectory_fit')
    args=parser.parse_args()
    with open(args.ball_csv,encoding='utf8',newline='') as f: rows=list(csv.DictReader(f))
    # First N complete consecutive runs above 0.3 m, bounded by low frames;
    # do not join runs, and retain their original frame times.
    def high(r):
        try: return r['status']=='1' and .3<float(r['z_raw'])<15
        except (ValueError,TypeError): return False
    selected=[]; rejected=Counter(); i=1
    while i<len(rows)-1 and len(selected)<args.count:
        if not high(rows[i]) or high(rows[i-1]):
            i+=1; continue
        start=i
        while i<len(rows) and high(rows[i]) and rows[i]['section']==rows[start]['section']:
            i+=1
        w=rows[start:i]
        if i>=len(rows) or rows[i]['section']!=w[0]['section'] or rows[i-1]['section']!=rows[start-1]['section']:
            rejected['boundary']+=1; continue
        try:
            if float(rows[start-1]['z_raw'])>.3 or float(rows[i]['z_raw'])>.3:
                rejected['not_height_bounded']+=1; continue
            if len(w)<10 or len(w)>125:
                rejected['duration']+=1; continue
            t0=datetime.fromisoformat(w[0]['timestamp'])
            t=np.array([(datetime.fromisoformat(r['timestamp'])-t0).total_seconds() for r in w])
            p=np.array([[float(r[k]) for k in ('x_m','y_m','z_raw')] for r in w])
            if not np.isfinite(p).all() or not np.allclose(np.diff(t),.04,atol=1e-6):
                rejected['missing_or_irregular']+=1; continue
            speed=np.linalg.norm(np.diff(p,axis=0),axis=1)/.04
            if np.any((speed<2)|(speed>45)):
                rejected['speed']+=1; continue
            direction=p[1,:2]-p[0,:2]
            if np.linalg.norm(direction)<.2:
                rejected['initial_direction']+=1; continue
            p=align_forward(p,direction)
            hit=crossing(t,p,11,.1)
            if hit is None:
                rejected['no_plane_crossing']+=1; continue
            selected.append((w,t,p,hit))
        except (ValueError,TypeError):
            rejected['invalid']+=1
    sample_records=[]; point_records=[]
    for sample,(w,t,p,hit) in enumerate(selected,1):
        key=(w[0]['section'],w[0]['frame'],w[0]['timestamp'])
        for model in ('M0','M1','M2','M3','M4','M5'):
            start_time=perf_counter()
            try:
                fit,plane,event=curve(model,t,p)
                residual=np.linalg.norm(fit-p[:len(fit)],axis=1)
                for i,e in enumerate(residual):
                    point_records.append({'sample':sample,'model':model,'frame':w[i]['frame'],
                        'time_s':t[i],'dx_m':fit[i,0]-p[i,0],'dy_m':fit[i,1]-p[i,1],
                        'dz_assumed_m':fit[i,2]-p[i,2],'error_3d_assumed_m':e})
                complete=len(fit)==len(t)
                result={'sample':sample,'section':key[0],'start_frame':key[1],'timestamp':key[2],
                    'model':model,'event':event,'observed_frames':len(t),'fitted_frames':len(fit),
                    'trajectory_rmse_m':float(np.sqrt(np.mean(residual**2))),
                    'terminal_error_m':float(residual[-1]) if complete else '',
                    'plane_error_m':float(np.linalg.norm(plane-hit[1][1:])) if plane is not None else '',
                    'runtime_s':perf_counter()-start_time}
            except (ValueError,RuntimeError,FloatingPointError,np.linalg.LinAlgError) as exc:
                result={'sample':sample,'section':key[0],'start_frame':key[1],'timestamp':key[2],
                    'model':model,'event':'error:'+type(exc).__name__,'observed_frames':len(t),'fitted_frames':0,
                    'trajectory_rmse_m':'','terminal_error_m':'','plane_error_m':'',
                    'runtime_s':perf_counter()-start_time}
            sample_records.append(result)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for name,records in [('sample_metrics.csv',sample_records),('frame_residuals.csv',point_records)]:
        with (out/name).open('w',encoding='utf8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=records[0]);writer.writeheader();writer.writerows(records)
    summary={'interpretation':'complete observed above-threshold arc fitted, in-sample reconstruction, not independent prediction',
             'samples':len(selected),'selection_rejections':dict(rejected),
             'selection':'first 30 height-bounded non-overlapping runs with active ball, .3<z<15, 10–125 frames, 25 Hz, 2–45 m/s, forward x=11 crossing',
             'z_unit':'assumed metre','models':{}}
    for model in ('M0','M1','M2','M3','M4','M5'):
        subset=[r for r in sample_records if r['model']==model]
        full=[r for r in subset if r['fitted_frames']==r['observed_frames']]
        summary['models'][model]={'events':dict(Counter(r['event'] for r in subset)),
            'full_trajectory_rmse':metrics([r['trajectory_rmse_m'] for r in full]),
            'terminal_error':metrics([r['terminal_error_m'] for r in full]),
            'plane_error':metrics([r['plane_error_m'] for r in subset if r['plane_error_m']!='']),
            'mean_runtime_s':float(np.mean([r['runtime_s'] for r in subset]))}
    common=[i for i in range(1,len(selected)+1) if all(any(r['sample']==i and r['model']==model and
            r['event']=='completed' and r['plane_error_m']!='' for r in sample_records)
            for model in ('M0','M1','M2','M3','M4','M5'))]
    summary['common_completed_samples']=common
    summary['common_metrics']={}
    for model in ('M0','M1','M2','M3','M4','M5'):
        group=[r for r in sample_records if r['model']==model and r['sample'] in common]
        summary['common_metrics'][model]={key:metrics([r[key] for r in group])
            for key in ('trajectory_rmse_m','terminal_error_m','plane_error_m')}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
