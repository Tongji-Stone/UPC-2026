"""Audit source frames, selection states, physical endpoints and convergence."""
import hashlib
import numpy as np
from football.reporting import ROOT,DATA,OUT,MODELS,read_json,read_csv,save_json,fingerprint
from football.physics import PhysicsConfig,simulate
from football.physics.integration import observed_trajectory

def main():
    data=read_json(DATA/'inputs.json');checks={}
    def check(name,ok,**details):checks[name]=dict(passed=bool(ok),**details)
    check('39_original_frames',sum(len(c['samples']) for c in data['cases'])==39)
    for name,h in data['config']['original_file_sha256'].items():
        check('source_'+name,hashlib.sha256((DATA/name).read_bytes()).hexdigest()==h)
    forward=read_json(OUT/'forward/summary.json')['records'];inverse=read_json(OUT/'inverse/summary.json')['records']
    check('24_forward_12_inverse',len(forward)==24 and len(inverse)==12)
    for case in data['cases']:
        name=case['case'];t=case['fit_times_s'];p=case['fit_positions_m']
        check(name+'_selected_times',np.allclose(t,[0,.04,.08]))
        expected={'J03WMX':[152602,152603,152604],'J03WOH':[128955,128956,128957],'J03WR9':[176244,176245,176246]}[name]
        check(name+'_selected_source_frames',[int(f) for f in case['fit_frames']]==expected)
        check(name+'_time_roundtrip',all(abs(r['time_s']+case['time_origin_source_s']-r['source_time_s'])<1e-10 for r in case['samples']))
        check(name+'_goal_time_roundtrip',abs(case['goal']['time_s']+case['time_origin_source_s']-case['goal']['source_time_s'])<1e-10)
        check(name+'_coordinate_roundtrip',all(abs(r['x_m']+41.5-r['X_m'])<1e-12 and r['y_m']==r['Y_m'] and r['z_m']==r['Z_original'] for r in case['samples']))
        for m in MODELS:
            a=read_json(OUT/f'inverse/{name}_{m}.json');r=a['record'];fit=a['fit'];key=name+'_'+m
            check(key+'_fingerprint',a['source_fingerprint']==fingerprint())
            check(key+'_only_early_input',np.array_equal(a['fit_input']['times_s'],t) and np.array_equal(a['fit_input']['positions_m'],p))
            c=PhysicsConfig.for_model(m,**data['config']['physics'],drag_scale=r['drag_scale'],lift_scale=r['lift_scale'])
            pred=observed_trajectory(t,p[0],r['initial_state'],c,rtol=1e-11,atol=1e-13)[:,:3]
            check(key+'_saved_fit_matches_state',np.max(abs(pred-np.array(fit['fitted_positions'])))<1e-8)
            check(key+'_parameter_count',fit['active_parameters']==dict(M1=3,M2=4,M3=7,M4=8)[m])
            for i,stage in enumerate(fit['stages']):
                if 'parameters' not in stage:continue
                q=np.array(stage['parameters']);indices=[5,6] if m=='M3' else [6,7]
                check(key+f'_selection_state_{i}',abs(np.sum((q[indices]-1)**2)-stage['coefficient_distance'])<1e-12)
            trace=read_csv(OUT/f'inverse/{name}_{m}.csv');end=float(trace[-1]['time_s'])
            check(key+'_fit_interval',r['physical_fit_interval']==(end>=t[-1]-1e-9))
            check(key+'_fit_before_contact',r['physical_fit_interval'])
            if r['event']['type']=='plane':
                distance=np.linalg.norm(np.asarray(r['event']['position'])[1:]-np.asarray(case['goal']['local_position'])[1:])
                check(key+'_goal_distance',abs(distance-r['goal_error_m'])<1e-12)
            check(key+'_ground_truncation',r['event']['type']!='ground' or abs(float(trace[-1]['z_m'])-.11)<1e-8)
            check(key+'_limit_marked',fit['success'] or r['status'] in ['fit_limit','early_contact'])
            path=OUT/f'inverse/{name}_{m}_validation.csv';valid=read_csv(path) if path.exists() else []
            check(key+'_heldout_only',len(valid)==r['future_sample_count'] and all(t[-1]<float(v['time_s'])<=min(end,case['goal']['time_s'])+1e-9 for v in valid))
    check('WR9_repeated_frame_preserved',data['cases'][2]['samples'][1]['repeated']==1)
    c=PhysicsConfig.for_model('M4');s=next(r['initial_state'] for r in forward if r['case']=='curved' and r['model']=='M4')
    fs=[simulate([0,0,.11],s[:3],s[3:],c,plane_x=11,t_span=(0,5),rtol=tol,atol=tol/100,max_step=step) for tol,step in [(1e-10,.005),(1e-12,.0025)]]
    delta=np.linalg.norm(fs[0].event['position']-fs[1].event['position'])
    check('endpoint_convergence',delta<1e-7,difference_m=float(delta))
    check('drag_dissipation',np.max(np.sum(fs[0].forces['drag']*fs[0].velocity,axis=1))<1e-10)
    check('lift_no_work',np.max(abs(np.sum(fs[0].forces['magnus']*fs[0].velocity,axis=1)))<1e-10)
    check('constant_spin',np.max(abs(fs[0].spin-np.array(s[3:])))<1e-12)
    save_json(OUT/'verification.json',dict(all_passed=all(v['passed'] for v in checks.values()),checks=checks))
    failed=[k for k,v in checks.items() if not v['passed']];print(dict(checks=len(checks),failed=failed))
    if failed:raise SystemExit(1)

if __name__=='__main__':main()
