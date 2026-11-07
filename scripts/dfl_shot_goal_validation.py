"""Fit event-synchronised shots to their complete paths through real goal lines.

All shots in one match are screened by the same fixed rules. The trajectory is
fully used for reconstruction and reported as such.
"""
import argparse, csv, json, xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np
from dfl_full_trajectory_fit import curve
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares
from football.physics import PhysicsConfig, forces, linthorne_patel_coefficients

def fit_six(t, p, plane):
    """M5 with 3 initial velocity + 3 initial spin parameters, Cd0 fixed."""
    cfg=PhysicsConfig.for_model('M5',coefficients=linthorne_patel_coefficients(cd0=.18))
    def rhs(_,s):return np.r_[s[3:6],sum(forces(s[3:6],s[6:9],cfg).values())/cfg.mass,[0.,0.,0.]]
    def solve(q,stop=False):
        def ground(_,s):return s[2]-cfg.radius
        ground.terminal=True;ground.direction=-1
        def hit(_,s):return s[0]-plane
        hit.terminal=False;hit.direction=1
        return solve_ivp(rhs,(t[0],t[-1]),np.r_[p[0],q],events=(ground,hit) if stop else None,
                         dense_output=True,rtol=1e-7,atol=1e-9)
    def residual(q):return (solve(q).sol(t)[:3].T-p).ravel()
    v=(p[-1]-p[0])/(t[-1]-t[0]);q=np.r_[v,0.,0.,30.]
    q=np.clip(q,[.01,-59.,-39.,-149.,-149.,-149.],[79.,59.,59.,149.,149.,149.])
    fit=least_squares(residual,q,bounds=([0.,-60.,-40.,-150.,-150.,-150.],[80.,60.,60.,150.,150.,150.]),max_nfev=200)
    sol=solve(fit.x,True)
    observed=t[t<=sol.t[-1]+1e-10]
    return sol.sol(observed)[:3].T,sol.y_events[1][0,1:3] if len(sol.t_events[1]) else None,('ground' if len(sol.t_events[0]) else 'completed')

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--match',default='J03WOH')
parser.add_argument('--ball-csv',default='data/processed/J03WOH_ball.csv')
parser.add_argument('--event-xml',default='data/raw/J03WOH_events.xml')
parser.add_argument('--output',default='results/dfl_real_shot_validation')
args=parser.parse_args()
with (ROOT/args.ball_csv).open(encoding='utf8',newline='') as f: rows=list(csv.DictReader(f))
indices={(r['section'],r['frame']):i for i,r in enumerate(rows)}
event_root=ET.parse(ROOT/args.event_xml).getroot()
events=[e for e in event_root.iter('Event') if e.find('.//ShotAtGoal') is not None]
counts=Counter(); samples=[]; points=[]; fitted_points=[]; per_model=[]
for e in events:
    shot=e.find('.//ShotAtGoal'); outcome=shot[0].tag if len(shot) else 'unknown'
    frame=e.get('CalculatedFrame'); stamp=e.get('CalculatedTimestamp')
    if frame is None or stamp is None:
        counts['no_synchronised_frame']+=1;continue
    idx=next((indices[k] for k in indices if k[1]==frame),None)
    if idx is None:
        counts['frame_not_found']+=1;continue
    start=rows[idx]; start_t=datetime.fromisoformat(start['timestamp'])
    event_t=datetime.fromisoformat(stamp)
    if abs((start_t-event_t).total_seconds())>.05:
        counts['sync_timestamp_mismatch']+=1;continue
    if abs((event_t-datetime.fromisoformat(e.get('EventTime'))).total_seconds())>1.0:
        counts['event_sync_offset_over_1s']+=1;continue
    # DFL event coordinates use a 105m-long pitch from zero to 105m.
    side=1 if float(e.get('X-Source-Position',e.get('X-Position')))>52.5 else -1
    end=None
    for j in range(idx,min(idx+51,len(rows)-1)):
        if rows[j]['section']!=start['section'] or rows[j+1]['section']!=start['section']:break
        if side*float(rows[j]['x_m'])<52.5<=side*float(rows[j+1]['x_m']): end=j+1;break
    if end is None:
        counts['no_forward_goal_crossing_within_2s']+=1;continue
    w=rows[idx:end+1]
    if len(w)<8:
        counts['fewer_than_8_frames']+=1;continue
    t=np.array([(datetime.fromisoformat(r['timestamp'])-start_t).total_seconds() for r in w]);
    p=np.array([[float(r[k]) for k in ('x_m','y_m','z_raw')] for r in w])
    if not np.isfinite(p).all() or not np.allclose(np.diff(t),.04,atol=1e-6):
        counts['missing_or_irregular']+=1;continue
    if np.any(p[:,2]<.11):
        counts['recorded_height_below_ball_radius']+=1;continue
    speed=np.linalg.norm(np.diff(p,axis=0),axis=1)/.04
    if np.any((speed<2)|(speed>45)):
        counts['speed_outside_range']+=1;continue
    if np.any(side*np.diff(p[:,0])<=0):
        counts['not_continuously_goalward']+=1;continue
    # Rotate both horizontal axes by 180 degrees for negative-x goal, preserving handedness.
    local=p.copy();local[:,0]=side*(p[:,0]-p[0,0]);local[:,1]=side*(p[:,1]-p[0,1])
    plane=52.5-side*p[0,0]; a=(side*52.5-p[-2,0])/(p[-1,0]-p[-2,0])
    truth=p[-2]+a*(p[-1]-p[-2]); truth_local=local[-2]+a*(local[-1]-local[-2])
    sample={'event_id':e.get('EventId'),'event_outcome':outcome,'type_of_shot':shot.get('TypeOfShot'),
       'first_frame':frame,'last_frame':w[-1]['frame'],'frames':len(w),'duration_s':float(t[-1]),
       'goal_x_m':side*52.5,'tracking_goal_y_m':float(truth[1]),'tracking_goal_z_assumed_m':float(truth[2]),
       'event_timestamp':e.get('EventTime'),'sync_timestamp':stamp,
       'event_to_sync_s':(event_t-datetime.fromisoformat(e.get('EventTime'))).total_seconds()}
    samples.append(sample);counts['selected']+=1
    for model in ['M0','M1','M2','M3','M4','M5','M5_6']:
        rec={'event_id':sample['event_id'],'model':model}
        try:
            fit,hit,event=fit_six(t,local,plane) if model=='M5_6' else curve(model,t,local,plane_x=plane)
            errs=np.linalg.norm(fit-local[:len(fit)],axis=1)
            for ti, xyz in zip(t,fit):
                fitted_points.append({'event_id':sample['event_id'],'model':model,'time_s':float(ti),
                    'x_m':float(side*xyz[0]+p[0,0]),'y_m':float(side*xyz[1]+p[0,1]),'z_assumed_m':float(xyz[2])})
            rec.update(event=event,frames_used=len(w),frames_completed=len(fit),
              trajectory_rmse_m=float(np.sqrt(np.mean(errs**2))) if len(fit)==len(w) else None,
              plane_error_m=float(np.linalg.norm(hit-truth_local[1:])) if hit is not None else None,
              goal_y_m=float(side*hit[0]+p[0,1]) if hit is not None else None,
              goal_z_assumed_m=float(hit[1]) if hit is not None else None)
        except (ValueError,RuntimeError,np.linalg.LinAlgError) as exc:
            rec.update(event='error:'+type(exc).__name__,frames_used=len(w),frames_completed=0,
                       trajectory_rmse_m=None,plane_error_m=None,goal_y_m=None,goal_z_assumed_m=None)
        per_model.append(rec)
    for ti,xyz,row in zip(t,p,w):
        points.append({'event_id':sample['event_id'],'frame':row['frame'],'time_s':float(ti),
                       'x_m':float(xyz[0]),'y_m':float(xyz[1]),'z_assumed_m':float(xyz[2])})
out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
for filename,records in [('samples.csv',samples),('positions.csv',points),('fitted_positions.csv',fitted_points),('model_metrics.csv',per_model)]:
    if records:
        with (out/filename).open('w',encoding='utf8',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=records[0]);wr.writeheader();wr.writerows(records)
summary={'match':args.match,'event_count':len(events),'filter_counts':dict(counts),
 'selection':'CalculatedFrame and CalculatedTimestamp required and within 1 s of event time; start at synchronised frame; first forward crossing of actual +/-52.5 m goal line within 2 s; >=8 frames; all z >=0.11 m under metre assumption; regular 25 Hz; speed 2–45 m/s; continuously goalward x',
 'interpretation':'all selected samples are fully fitted; reconstruction agreement, not prediction',
 'height_unit':'assumed metres; dataset paper does not establish unit',
 'sample_details':samples,'model_results':per_model,
 'source':'DFL Sportec open dataset https://doi.org/10.1038/s41597-025-04505-y, CC BY 4.0'}
(out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'counts':dict(counts),'samples':samples,'model_results':per_model},indent=2,ensure_ascii=False))
