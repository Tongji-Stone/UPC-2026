"""Generate all reported numerical values and table rows from saved results."""
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/coupled_model'
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def vector(values):return '('+', '.join(f'{x:.4f}' for x in values)+')'
def main():
    p=read('problem/summary.json');real=read('real/summary.json');sens=read('sensitivity/summary.json');surf=read('surface/summary.json')
    values={}
    for i,c in enumerate(p['candidate_predictions']):
        letter=chr(65+i);q=c['initial_state'];e=c['event'];fit=p['fit']['candidates'][i]
        values.update({f'Fit{letter}Velocity':vector(q[:3]),f'Fit{letter}Spin':vector(q[3:]),
            f'Fit{letter}Y':f'{e["position"][1]:.4f}',f'Fit{letter}Z':f'{e["position"][2]:.4f}',
            f'Fit{letter}Time':f'{e["time"]:.5f}',f'Fit{letter}Condition':f'{fit["condition_number"]:.1f}'})
    a,b=[np.array(c['event']['position'][1:]) for c in p['candidate_predictions'][:2]]
    values.update(GoalSeparation=f'{np.linalg.norm(a-b):.5f}',
        StartSpin=f'{p["initial_spin_norm"]:.3f}',EndSpin=f'{p["final_spin_norm"]:.3f}',
        StartRev=f'{p["initial_spin_norm"]/(2*np.pi):.1f}',
        StartSp=f'{p["best_prediction"]["coverage"]["Sp_range"][1]:.4f}',
        RealReached=str(real['successful_crossings']),RealTotal=str(real['n']),
        RealMeanError=f'{real["mean_error_m"]:.4f}')
    for name,group in sens['groups'].items():
        prefix={'speed_scale':'Speed','azimuth_deg':'Angle','spin_scale':'Spin','angular_drag_scale':'Damping'}[name]
        for coord in ('y','z'):
            values[prefix+coord.upper()+'Min']=f'{group[coord+"_range"][0]:.4f}'
            values[prefix+coord.upper()+'Max']=f'{group[coord+"_range"][1]:.4f}'
    soccer,smooth=surf['cases']
    values.update(SurfaceSoccerZ=f'{soccer["event"]["position"][2]:.4f}',
        SurfaceSmoothZ=f'{smooth["event"]["position"][2]:.4f}',
        SurfaceDifference=f'{abs(soccer["event"]["position"][2]-smooth["event"]["position"][2]):.5f}',
        SurfaceSoccerTime=f'{soccer["event"]["time"]:.5f}',SurfaceSmoothTime=f'{smooth["event"]["time"]:.5f}')
    text='% Automatically generated from results/coupled_model; do not edit values manually.\n'
    text+='\n'.join('\\newcommand{\\'+name+'}{'+value+'}' for name,value in values.items())+'\n'
    table=[]
    for i,r in enumerate(real['records']):
        err=f'{r["error_m"]:.4f}' if r.get('error_m') is not None else '---'
        table.append(f'{i+1} & {r["match"]} & {r["shot_type"]} & {r["status"]} & {r["max_fit_residual_m"]:.4f} & {err} \\\\')
    text+='\\newcommand{\\RealTableRows}{\n'+'\n'.join(table)+'\n}\n'
    (ROOT/'paper/coupled_results.tex').write_text(text,encoding='utf-8')
    print('Generated paper/coupled_results.tex from computed results.')

if __name__=='__main__':main()
