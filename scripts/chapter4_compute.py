"""Verify Chapter 4 from frozen real fits and the shared competition-case solver."""
from dataclasses import replace
import hashlib
import numpy as np
from football.physics import forces, config_record
from football.inference.four_model_fit import fit_early, InverseBounds
from football.reporting import ROOT, OUT, DATA, read_json, read_csv, save_json, save_csv, trace_rows
from four_model_compute import config, flight


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def main():
    dataset=read_json(DATA/'inputs.json'); summary=[]
    for case in dataset['cases']:
        for model in ('M1','M2','M3','M4'):
            saved=read_json(OUT/f"inverse/{case['case']}_{model}.json")
            assert np.allclose(saved['fit_input']['positions_m'],case['fit_positions_m'])
            assert np.allclose(saved['fit_input']['times_s'],case['fit_times_s'])
            r=saved['record']; event=r['event']
            if event['type']=='plane':
                error=float(np.linalg.norm(np.array(event['position'])[1:]-np.array(case['goal']['local_position'])[1:]))
                assert abs(error-r['scored_goal_error_m'])<1e-10
            else:
                assert r['scored_goal_error_m'] is None
            if model!='M4':continue
            v=np.array(r['initial_state'][:3]); w=np.array(r['initial_state'][3:])
            cfg=replace(config('M4'),drag_scale=r['drag_scale'],lift_scale=r['lift_scale'])
            f=forces(v,w,cfg)
            summary.append(dict(case=case['case'],speed_m_s=float(np.linalg.norm(v)),
                elevation_deg=float(np.degrees(np.arctan2(v[2],np.linalg.norm(v[:2])))),
                vertical_speed_m_s=float(v[2]),drag_N=float(np.linalg.norm(f['drag'])),
                lift_N=float(np.linalg.norm(f['magnus'])),lift_vector_N=f['magnus'],
                spin_axis=w/np.linalg.norm(w)))
    save_json(OUT/'chapter4/physical_summary.json',dict(records=summary,real_fits_checked=12))
    times=np.array([0,.05,.10]); positions=np.array([[0,0,.11],[1.50,.45,.44],[2.96,.86,.74]])
    cfg=config('M4')
    fit=fit_early(times,positions,cfg,'M4',max_nfev=dataset['config']['fit']['max_nfev'],
        bounds=InverseBounds(**dataset['config']['inverse_bounds']))
    cfg=replace(cfg,drag_scale=fit['drag_scale'],lift_scale=fit['lift_scale'])
    state=np.array(fit['initial_state']); trajectory=flight(positions[0],state,cfg)
    reference=read_json(ROOT/'results/structure_linear_spin/problem/problem_b_M4.json')['record']
    # A numerical repeat must reproduce the displayed crossing and initial speed.
    assert np.allclose(state[:3],reference['initial_state'][:3],rtol=0,atol=1e-6)
    assert np.allclose(state[3:],reference['initial_state'][3:],rtol=0,atol=2e-5)
    assert np.allclose(trajectory.event['position'],reference['event']['position'],rtol=0,atol=1e-6)
    assert abs(trajectory.event['time']-reference['event']['time'])<1e-8
    record=dict(initial_state=state,event=trajectory.event,fitted_cd=cfg.drag_coefficient*cfg.drag_scale,
        fitted_alpha=cfg.lift_coefficient*cfg.lift_scale,speed_m_s=float(np.linalg.norm(state[:3])),
        elevation_deg=float(np.degrees(np.arctan2(state[2],np.linalg.norm(state[:2])))))
    save_json(OUT/'problem/problem_b_M4.json',dict(input=dict(times_s=times,positions_m=positions),
        record=record,fit=fit,configuration=config_record(cfg),
        repeat_difference=dict(state=state-np.array(reference['initial_state']),
            crossing_m=np.array(trajectory.event['position'])-reference['event']['position'],
            arrival_s=trajectory.event['time']-reference['event']['time']),
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'src/football/physics/model.py',
            ROOT/'src/football/inference/four_model_fit.py']},sensitivity_reference_verified=True))
    save_csv(OUT/'problem/problem_b_M4.csv',trace_rows(trajectory,cfg))
    print('12 real fits checked; fresh competition M4 agrees with Chapter 5 reference',flush=True)


if __name__=='__main__':main()
