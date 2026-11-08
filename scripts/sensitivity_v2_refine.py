"""Refine goal-coordinate extrema subject to the same six exact observations."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from sensitivity_v2_compute import (DATA,BASE,CFG,P0,OBS,SCALE,flight,observed,save_csv,save_json,hashes)


def main():
    before=hashes()
    import csv
    with (DATA/'profile.csv').open(encoding='utf-8-sig') as f:
        profile=list(csv.DictReader(f))
    attempts=[];accepted=[]
    for name,low,high in [('inner',.9,1.1),('wide',.8,1.2)]:
        group=[r for r in profile if r['event']=='plane' and (name=='wide' or r['inner']=='True')]
        def unpack(q):return q[:6]*SCALE,{**CFG,'ad':q[6],'al':q[7]}
        def constraints(q):
            state,cfg=unpack(q)
            return (observed(state,cfg)-OBS).ravel()/.11
        def inequalities(q):
            state,_=unpack(q)
            return np.array([1.-np.linalg.norm(state[:3])/35.,1.-np.linalg.norm(state[3:])/200.])
        for field in ('y','z','t'):
            for sign in (-1.,1.):
                seed_row=(max if sign<0 else min)(group,key=lambda r:float(r[field]))
                seed=np.array([float(seed_row[f's{i}']) for i in range(6)]+[float(seed_row['ad']),float(seed_row['al'])])
                for seed_id,start in enumerate([np.r_[seed[:6]/SCALE,seed[6:]],np.r_[BASE/SCALE,CFG['ad'],CFG['al']]]):
                    def objective(q):
                        state,cfg=unpack(q);f=flight(state,cfg)
                        return sign*(f[field] if f['event']=='plane' else 100.)
                    opt=minimize(objective,start,method='SLSQP',
                        bounds=[(0.,1.4),(-1.4,1.4),(-1.4,1.4)]+[(-200./120,200./120)]*3+[(low,high)]*2,
                        constraints=[{'type':'eq','fun':constraints},{'type':'ineq','fun':inequalities}],
                        options={'maxiter':220,'ftol':2e-12})
                    state,cfg=unpack(opt.x)
                    err=float(np.max(abs(observed(state,cfg,tight=True)-OBS)))
                    f=flight(state,cfg,tight=True,step=.01)
                    ok=bool(err<=1e-7 and inequalities(opt.x).min()>=-1e-8 and
                            low-1e-9<=cfg['ad']<=high+1e-9 and low-1e-9<=cfg['al']<=high+1e-9 and f['event']=='plane')
                    row=dict(scope=name,field=field,goal='max' if sign<0 else 'min',seed_id=seed_id,
                        accepted=ok,success=bool(opt.success),message=str(opt.message),iterations=int(opt.nit),
                        residual_m=err,ad=float(cfg['ad']),al=float(cfg['al']),
                        speed=float(np.linalg.norm(state[:3])),spin=float(np.linalg.norm(state[3:])),
                        **{f's{i}':float(s) for i,s in enumerate(state)},**f)
                    if ok:
                        other=flight(state,cfg,method='RK45',step=.0025,tight=True)
                        row.update(integrator_difference_m=float(np.hypot(f['y']-other['y'],f['z']-other['z'])),
                                   integrator_time_difference_s=abs(f['t']-other['t']))
                        accepted.append(row)
                    attempts.append(row)
                    print(name,field,row['goal'],seed_id,'accepted',ok,'success',opt.success,'value',f[field],flush=True)
    save_csv('extrema_attempts.csv',attempts)
    save_csv('extrema.csv',accepted)
    summary={}
    for name in ('inner','wide'):
        original=[{k:float(r[k]) for k in ('y','z','t','spin','residual_m')} for r in profile
                  if r['event']=='plane' and (name=='wide' or r['inner']=='True')]
        extra=[r for r in accepted if r['scope']==name]
        all_rows=original+extra
        baseline=flight(BASE)
        summary[name]=dict(grid_states=len(original),accepted_refinements=len(extra),
            refined_y_range=[min(r['y'] for r in all_rows),max(r['y'] for r in all_rows)],
            refined_z_range=[min(r['z'] for r in all_rows),max(r['z'] for r in all_rows)],
            refined_t_range=[min(r['t'] for r in all_rows),max(r['t'] for r in all_rows)],
            max_displacement=max(float(np.hypot(r['y']-baseline['y'],r['z']-baseline['z'])) for r in all_rows),
            max_residual_m=max(r['residual_m'] for r in all_rows),
            max_integrator_difference_m=max(r['integrator_difference_m'] for r in extra),
            interpretation='Explored grid plus feasible local constrained extrema; not a certified global enclosure')
    q0=np.r_[BASE/SCALE,CFG['ad'],CFG['al']]
    def early(q):return (observed(q[:6]*SCALE,{**CFG,'ad':q[6],'al':q[7]},tight=True)-OBS).ravel()/.11
    jac=np.column_stack([(early(q0+np.eye(8)[i]*1e-5)-early(q0-np.eye(8)[i]*1e-5))/(2e-5) for i in range(8)])
    u,s,vt=np.linalg.svd(jac,full_matrices=True)
    summary['jacobian']=dict(shape=list(jac.shape),rank=int(np.sum(s>s[0]*1e-7)),
        singular_values=s.tolist(),null_space_dimension=8-int(np.sum(s>s[0]*1e-7)),
        scale_description='velocity/30 m/s, spin/120 rad/s, absolute force multipliers; residual/.11 m')
    summary['protected_unchanged']=before==hashes()
    assert summary['protected_unchanged']
    assert all(r['integrator_difference_m']<1e-7 for r in accepted)
    save_json('refinement_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
