"""Recompute the review-only early-position feasible set; preserve published inputs."""
from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import time
import numpy as np
from numba import njit
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/chapter5_review/fig13'
OUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('original_sensitivity', ROOT / 'scripts/sensitivity_v2_compute.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
BASE, CFG, OBS = original.BASE, original.CFG, original.OBS
from football.physics.model import PhysicsConfig
physics = PhysicsConfig.for_model('M4')
CD, ALPHA = physics.drag_coefficient, physics.lift_coefficient
prefactor = .5 * CFG['rho'] * np.pi * CFG['radius']**2 / CFG['mass']

@njit(cache=False)
def rhs(s, w, ad, al):
    v = s[3:]
    speed = np.sqrt(np.dot(v, v))
    drag = prefactor * CD * ad * speed
    lift = prefactor * CFG_RADIUS * ALPHA * al
    r = np.empty(6)
    r[:3] = v
    r[3] = -drag*v[0] + lift*(w[1]*v[2]-w[2]*v[1])
    r[4] = -drag*v[1] + lift*(w[2]*v[0]-w[0]*v[2])
    r[5] = -9.81-drag*v[2] + lift*(w[0]*v[1]-w[1]*v[0])
    return r

CFG_RADIUS = CFG['radius']

@njit(cache=False)
def early(state, ad, al, steps=20):
    s = np.empty(6)
    s[:3] = np.array([0.,0.,.11])
    s[3:] = state[:3]
    w = state[3:]
    h = .05/steps
    ans = np.empty((2,3))
    for j in range(2):
        for k in range(steps):
            k1 = rhs(s,w,ad,al)
            k2 = rhs(s+h*k1/2,w,ad,al)
            k3 = rhs(s+h*k2/2,w,ad,al)
            k4 = rhs(s+h*k3,w,ad,al)
            s += h*(k1+2*k2+2*k3+k4)/6
        ans[j,:] = s[:3]
    return ans

def write_csv(name, rows):
    with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    started=time.monotonic()
    protected=[ROOT/d/n for d in ['paper','_中文版'] for n in ['main.tex','main.pdf']]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    baseline=original.flight(BASE,tight=True)
    first_err=float(np.max(abs(early(BASE,1.5,1.5)-original.observed(BASE,{**CFG,'ad':1.5,'al':1.5},tight=True))))
    assert first_err<1e-8,first_err
    old=list(csv.DictReader((ROOT/'results/sensitivity_linear/profile.csv').open(encoding='utf-8-sig')))
    old_check=[]
    for row in old:
        state=np.array([float(row[f's{k}']) for k in range(6)])
        cfg={**CFG,'ad':float(row['ad']),'al':float(row['al'])}
        obs=original.observed(state,cfg,tight=True)
        flight=original.flight(state,cfg,tight=True)
        old_check.append(dict(y=flight['y'],z=flight['z'],wx=state[3],max_coordinate_residual_m=float(np.max(abs(obs-OBS))),
                              crossing_reproduction_m=float(np.hypot(flight['y']-float(row['y']),flight['z']-float(row['z'])))))
    write_csv('old_points_reintegrated.csv',old_check)
    print('Reintegrated original 153 states; largest crossing difference',max(r['crossing_reproduction_m'] for r in old_check),flush=True)
    # Fix one spin component at a time so acceptable interior states are retained,
    # rather than selecting one least-squares optimum for each coefficient pair.
    scale=np.array([30.,30.,30.,60.,60.])
    lower=np.array([0.,-1.4,-1.4,-1.,-1.]);upper=np.array([1.4,1.4,1.4,1.,1.])
    values=np.linspace(1.2,1.8,17)
    wx_values=np.linspace(-60,60,33)
    attempts=[];accepted=[];alt_differences=[]
    for i,ad in enumerate(values):
        for j,al in enumerate(values):
            previous=None
            for k,wx in enumerate(wx_values):
                def unpack(q): return np.r_[q[:3]*30,wx,q[3:]*60]
                def residual(q): return ((early(unpack(q),ad,al)-OBS)/.11).ravel()
                seed=BASE.copy();seed[3:]*=1.5/al
                seed=np.r_[seed[:3],seed[4:]]/scale
                if previous is not None: seed=previous
                fit=least_squares(residual,np.clip(seed,lower+1e-10,upper-1e-10),bounds=(lower,upper),
                                  max_nfev=100,ftol=2e-11,xtol=2e-11,gtol=2e-11)
                previous=fit.x
                state=unpack(fit.x)
                err=float(np.max(abs(early(state,ad,al,40)-OBS)))
                good=err<=.002+1e-12 and np.linalg.norm(state[:3])<=35 and np.max(abs(state[3:]))<=60+1e-9
                row=dict(i=i,j=j,k=k,ad=float(ad),al=float(al),wx=float(wx),residual_m=err,accepted=bool(good),
                         nfev=fit.nfev,success=bool(fit.success),**{f's{n}':float(x) for n,x in enumerate(state)})
                attempts.append(row)
                if good:
                    f=original.flight(state,{**CFG,'ad':ad,'al':al})
                    accepted.append(dict(**row,inner=bool(1.35-1e-9<=ad<=1.65+1e-9 and 1.35-1e-9<=al<=1.65+1e-9),**f))
                if i==8 and j==8 and k%4==0:
                    opposite=np.r_[BASE[:3],-BASE[4:]]/scale
                    alt=least_squares(residual,np.clip(opposite,lower+1e-10,upper-1e-10),bounds=(lower,upper),
                                      max_nfev=160,ftol=2e-11,xtol=2e-11,gtol=2e-11)
                    alt_differences.append(float(np.linalg.norm(residual(alt.x)-residual(fit.x))))
        print(f'coefficient row {i+1}/17; accepted {len(accepted)}/{len(attempts)}; {time.monotonic()-started:.1f}s',flush=True)
    write_csv('profile_attempts.csv',attempts)
    write_csv('feasible_crossings.csv',accepted)
    checks=[]
    chosen=list(np.linspace(0,len(accepted)-1,48,dtype=int))
    for key in ['y','z']:
        chosen.extend([int(np.argmin([r[key] for r in accepted])),int(np.argmax([r[key] for r in accepted]))])
    for ix in sorted(set(chosen)):
        row=accepted[ix];state=np.array([row[f's{k}'] for k in range(6)]);cfg={**CFG,'ad':row['ad'],'al':row['al']}
        dop=original.observed(state,cfg,tight=True)
        check=dict(index=int(ix),rk4_vs_dop853_m=float(np.max(abs(early(state,row['ad'],row['al'],40)-dop))),
                   dop853_max_coordinate_residual_m=float(np.max(abs(dop-OBS))))
        checks.append(check)
    assert max(r['rk4_vs_dop853_m'] for r in checks)<1e-8
    assert max(r['dop853_max_coordinate_residual_m'] for r in checks)<=.002+1e-9
    old_y=np.sort([r['y'] for r in old_check]);gap_index=int(np.argmax(np.diff(old_y)));gap=[float(old_y[gap_index]),float(old_y[gap_index+1])]
    groups={}
    for name,group in [('wide',accepted),('narrow',[r for r in accepted if r['inner']])]:
        planes=[r for r in group if r['event']=='plane']
        groups[name]=dict(states=len(planes),coefficient_nodes=len(set((r['i'],r['j']) for r in planes)),
                          y_range=[min(r['y'] for r in planes),max(r['y'] for r in planes)],
                          z_range=[min(r['z'] for r in planes),max(r['z'] for r in planes)],
                          t_range=[min(r['t'] for r in planes),max(r['t'] for r in planes)],
                          max_displacement=max(np.hypot(r['y']-baseline['y'],r['z']-baseline['z']) for r in planes))
    summary=dict(groups=groups,total_attempts=len(attempts),spin_x_slices=33,original_points=153,
                 old_max_adjacent_y_gap_m=gap,new_points_in_old_y_gap=sum(gap[0]<r['y']<gap[1] for r in accepted),
                 baseline=baseline,initial_rk4_check_m=first_err,alternate_start_residual_differences=alt_differences,
                 integrator_checks=checks,old_max_crossing_reproduction_m=max(r['crossing_reproduction_m'] for r in old_check),
                 max_coordinate_residual_m=max(r['residual_m'] for r in accepted),
                 protected_hashes=before,original_paper_unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items()),
                 source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),elapsed_seconds=time.monotonic()-started)
    assert summary['original_paper_unchanged']
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k in ['groups','new_points_in_old_y_gap','old_max_adjacent_y_gap_m','elapsed_seconds']},ensure_ascii=True),flush=True)

if __name__=='__main__':main()
