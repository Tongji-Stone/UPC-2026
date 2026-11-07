"""Audit saved coupled-model outputs, energy, observations and paper values."""
import csv,json,hashlib
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig,forces,rotational_torque,coefficients,state_derivative
from football.inference.coupled_fit import observed_trajectory

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/coupled_model'
def load(path):return json.loads((OUT/path).read_text(encoding='utf-8'))
def main():
    s=load('problem/summary.json');cfg=PhysicsConfig.for_model('M5',**s['input']['physics'])
    for c in s['candidate_predictions']:
        q=np.array(c['initial_state']);t=np.array(s['input']['times_s']);p=np.array(s['input']['positions_m'])
        assert np.max(np.abs(observed_trajectory(t,p[0],q,cfg)[:,:3]-p))<1e-8
    with (OUT/'problem/trajectory_candidate_0.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
    energy=[];spin=[]
    for row in rows:
        v=np.array([float(row[k]) for k in ('vx','vy','vz')]);w=np.array([float(row[k]) for k in ('wx','wy','wz')])
        p=np.array([float(row[k]) for k in ('x_m','y_m','z_m')]);parts=forces(v,w,cfg);q=rotational_torque(w,cfg)
        assert abs(parts['magnus']@v)<1e-8
        dy=state_derivative(0,np.r_[p,v,w],cfg)
        actual=cfg.mass*v@dy[3:6]+cfg.mass*cfg.gravity*v[2]+cfg.moment_of_inertia*w@dy[6:9]
        loss=parts['drag']@v+q@w
        assert abs(actual-loss)<1e-7 and loss<=0
        cd,cl,_,_,_=coefficients(v,w,cfg)
        assert abs(cd-float(row['CD']))<1e-12 and abs(cl-float(row['CL']))<1e-12
        energy.append(float(row['energy_J']));spin.append(float(row['omega_rad_s']))
    assert np.all(np.diff(energy)<0) and np.all(np.diff(spin)<0)
    real=load('real/summary.json')
    for path in (OUT/'real').glob('J*.json'):
        event=json.loads(path.read_text(encoding='utf-8'))
        assert np.allclose(event['input_times_s'],[0,.04,.08])
        assert len(event['input_positions_m'])==3
        assert event['fit']['parameter_prior'] is None and event['fit']['measurement_noise_model'] is None
    tex=(ROOT/'paper/main.tex').read_text(encoding='utf-8')
    assert r'\subsection{Aerodynamic Coefficients}' not in tex
    assert r'\subsection{Numerical Solution and Comparison Models}' not in tex
    for obsolete in ('eq:baseline-laws','Linthorne','495','600 sampled'):assert obsolete not in tex,obsolete
    report=dict(model=s['configuration']['model_id'],mechanical_consistency=True,
        exact_problem_candidate_count=len(s['candidate_predictions']),
        energy_and_spin_decrease=True,coefficient_tables_match_dynamics=True,
        real_cases=real['n'],reached_cases=real['successful_crossings'],
        early_frame_inputs_only=True,measurement_noise_model=None,parameter_prior=None,
        integration_convergence_m=s['convergence_position_difference_m'],
        interpretation='Mechanically consistent under declared settings; the inverse state is not unique.',
        important_coverage_result='The two fitted competition spins exceed the Asai 2007 spin range.',
        files_sha256={str(path.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ('src','configs','scripts') for path in (ROOT/folder).rglob('*.py' if folder!='configs' else '*.json')
            if '__pycache__' not in path.parts})
    (OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files_sha256'},indent=2))


if __name__=='__main__':main()
