"""Generate all numerical report tables and macros from saved result JSON."""
import json
from pathlib import Path
import numpy as np
from football.physics import PhysicsConfig
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/structure_linear_spin'
def js(p):return json.loads((OUT/p).read_text(encoding='utf-8'))
def scientific(value,precision=2):
    text=f'{value:.{precision}g}'
    if 'e' in text:
        a,b=text.split('e');return r'\ensuremath{'+a+r'\times10^{'+str(int(b))+'}}'
    return text
def table(caption,label,columns,head,rows):
    return ('\\begin{table}[H]\\centering\\small\n\\caption{'+caption+'}\\label{'+label+'}\n'
        '\\begin{tabular}{'+columns+'}\\toprule\n'+head+r'\\\midrule'+'\n'+'\n'.join(rows)+
        '\n\\bottomrule\\end{tabular}\\end{table}\n')
def main():
    commands=[]
    def macro(name,value):commands.append('\\newcommand{\\'+name+'}{'+str(value)+'}\n')
    p=js('problem/problem_b_M4.json')['record'];s=np.array(p['initial_state']);c=p['coverage'];q=p['event']
    for name,value in dict(ProblemY=f"{q['position'][1]:.3f}",ProblemZ=f"{q['position'][2]:.3f}",
        ProblemTime=f"{q['time']:.4f}",ProblemAlphaD=f"{p['fitted_cd']:.4f}",ProblemAlphaL=f"{p['fitted_alpha']:.4f}",
        ProblemSpin=f'{np.linalg.norm(s[3:]):.2f}',ProblemResidual=scientific(p['max_residual_m']),
        ProblemSpeedMin=f"{c['speed_range'][0]:.2f}",ProblemSpeedMax=f"{c['speed_range'][1]:.2f}",
        ProblemReMin=f"{c['Re_range'][0]/1e5:.2f}",ProblemReMax=f"{c['Re_range'][1]/1e5:.2f}",
        ProblemSpMin=f"{c['Sp_range'][0]:.3f}",ProblemSpMax=f"{c['Sp_range'][1]:.3f}").items():macro(name,value)
    for name,value in zip(['ProblemVX','ProblemVY','ProblemVZ','ProblemWX','ProblemWY','ProblemWZ'],s):macro(name,f'{value:.3f}')
    cfg=PhysicsConfig.for_model('M4');macro('ReferenceCD',f'{cfg.drag_coefficient:.4f}');macro('ReferenceCL',f'{cfg.lift_coefficient:.4f}')
    forward=js('forward/summary.json');f=forward['records'];rows=[]
    for c in forward['cases']:
        label='Zero spin' if c['case']=='zero_spin' else 'Topspin '+c['case'][-1]
        rows.append(f"{label} & {c['position'][0]:.4f} & {c['position'][2]:.4f} & {c['velocity'][0]:.3f} & {c['velocity'][2]:.3f} & {c['spin'][1]:.2f}"+r'\\')
    macro('ForwardInitialTable',table('Initial conditions for the controlled forward examples, reconstructed as described above.','tab:forward-initial','lrrrrr',r'Launch & $x_0$ (m) & $z_0$ (m) & $v_{x0}$ (m/s) & $v_{z0}$ (m/s) & $\omega_{y0}$ (rad/s)',rows))
    rows=[]
    for r in f:
        if r['case']=='zero_spin':
            rows.append(f"{r['model']} & {r['predicted_range_m']:.3f} & {r['range_error_m']:+.3f}"+r'\\')
            if r['model']=='M4':macro('ForwardMFourRange',f"{r['predicted_range_m']:.3f}");macro('ForwardMFourError',f"{r['range_error_m']:+.3f}")
    macro('ForwardRangeTable',table('Nonspinning controlled launch: predicted landing and signed range error. The reported range is 21.9 m.','tab:forward-range','lrr','Model & Range (m) & Prediction minus measurement (m)',rows))
    rows=[]
    for case in ['topspin_a','topspin_b','topspin_c','topspin_d']:
        rr=[next(r for r in f if r['case']==case and r['model']==m) for m in ['M1','M2','M4']]
        rows.append(case[-1]+' & '+' & '.join(f"{r['spatial_rmse_m']:.4f}" for r in rr)+r'\\')
    macro('ForwardSpinTable',table('Height RMSE (m) at digitized horizontal positions for the four topspin segments.','tab:forward-spin','lrrr','Launch & M1 & M2 & M4',rows))
    rows=[]
    for m in ['M1','M2','M3','M4']:
        r=js(f'problem/problem_b_{m}.json')['record'];e=r['event']
        rows.append(f"{m} & {r['fitted_cd']:.4f}" if m=='M4' else f'{m} & ---')
        rows[-1]+=(f" & {r['fitted_alpha']:.4f}" if m == 'M4' else ' & ---')
        rows[-1]+=' & '+scientific(r['max_residual_m'])+f" & {e['position'][1]:.3f} & {e['position'][2]:.3f} & {e['time']:.4f}"+r'\\'
    macro('ProblemResultsTable',table('Inverse predictions for the competition observations. Residual is the maximum absolute early-coordinate difference.','tab:problem','lrrrrrr',r'Model & $C_D$ & $\alpha$ & Residual (m) & $y_g$ (m) & $z_g$ (m) & $t_g$ (s)',rows))
    matches=js('matches/summary.json')['records'];rows=[]
    names={'J03WOH_18232100000487':'WOH 0487 (head)','J03WOH_18232100000606':'WOH 0606 (foot)',
        'J03WOH_18232100000968':'WOH 0968 (foot)','J03WQQ_18232200001227':'WQQ 1227 (head)',
        'penalty_18232100000995':'Penalty'}
    # Derive the actual WQQ identifier from the frozen input rather than assume it.
    for r in matches:
        label=names.get(r['case'],'WQQ '+r['case'][-4:]+' ('+r.get('shot_type','shot')+')')
        err=f"{r['error_m']:.3f}" if r.get('error_m') is not None else '---'
        status={'plane':'plane','ground':'ground','none':'time limit',
            'terminated_before_last_observation':'early termination','fit_failure':'fit failure'}[r['status']]
        residual=scientific(r['max_residual_m'],3) if 'max_residual_m' in r else '---'
        rows.append(f"{label} & {r['model']} & {status} & {residual} & {err}"+r'\\')
    macro('MatchResultsTable',table('All five recorded flights and all four inverse models. Error is the Euclidean difference in goal-plane $(y,z)$.','tab:match-results','lllrr','Event & Model & Termination & Early residual (m) & Plane error (m)',rows))
    rows=[];discussion=[]
    for m in ['M1','M2','M3','M4']:
        rs=[r for r in matches if r['model']==m];errors=[r['error_m'] for r in rs if r.get('error_m') is not None]
        mean=f'{np.mean(errors):.3f}' if errors else '---';ground=sum(r['status']=='ground' for r in rs);failure=sum(r['status']=='fit_failure' for r in rs)
        other_count=len(rs)-len(errors)-ground-failure
        rows.append(f'{m} & {len(errors)}/5 & {ground} & {other_count} & {failure} & {mean}'+r'\\')
        discussion.append(f'{m} reaches the goal plane in {len(errors)} of five cases')
    macro('MatchAggregateTable',table('Reached-case errors and termination counts. Individual errors are retained in the preceding table.','tab:match-aggregate','lrrrrr','Model & Reached & Ground & Other & Fit failures & Mean error (m)',rows))
    best_coverage=max(['M1','M2','M3','M4'],key=lambda m:sum(r['error_m'] is not None for r in matches if r['model']==m))
    macro('MatchDiscussion','; '.join(discussion)+f'. {best_coverage} gives the largest number of goal-plane predictions in these five recorded flights. The table reports each reached-case mean together with its contributing count. Large force corrections and iteration-limit cases reveal a strong dependence on the early recorded motion. Fit failures denote numerical iteration limits; their candidate trajectories are retained in the calculation records.')
    other=js('other/summary.json');macro('TorqueViscousRatio',scientific(other['viscous_to_inertial_torque_ratio_at_launch']))
    macro('TorqueDisplacement',f"{other['goal_displacement_m']:.3f}")
    ref,high,both=[r['event'] for r in other['records']]
    macro('TorqueResults',f"The damped goal-plane centre is $({high['position'][1]:.3f},{high['position'][2]:.3f})$ m, compared with $({ref['position'][1]:.3f},{ref['position'][2]:.3f})$ m at constant spin. The displacement is {other['goal_displacement_m']:.3f} m, or {other['displacement_pct_of_11m']:.2f}\\% of the 11 m flight distance. Spin decreases by {other['spin_loss_pct']:.2f}\\%, and the goal-crossing time changes by {other['time_change_pct']:+.2f}\\%. Adding the much weaker viscous term changes the damped crossing by {other['viscous_goal_difference_m']:.2g} m. Thus this reference torque has a visible effect on spin and a smaller, measurable effect on the short-flight endpoint.")
    rows=[]
    for r in other['wind_estimates']:
        rows.append(f"{r['wind_m_s']:.0f} & {r['headwind_q_change_pct']:+.2f} & {r['tailwind_q_change_pct']:+.2f} & {r['crosswind_q_change_pct']:+.2f} & {r['crosswind_airflow_angle_deg']:.2f}"+r'\\')
    macro('WindResultsTable',table('Illustrative wind estimates at the fitted launch speed. Percentages describe dynamic pressure at fixed aerodynamic coefficients.','tab:wind','rrrrr',r'$w$ (m/s) & Headwind (\%) & Tailwind (\%) & Crosswind (\%) & Airflow angle ($^\circ$)',rows))
    macro('WindThreshold',f"{other['five_percent_dynamic_pressure_wind_threshold_m_s']:.2f}")
    (ROOT/'paper/report_results.tex').write_text('% Generated from results/structure_linear_spin; do not edit numerical values manually.\n'+''.join(commands),encoding='utf-8')
    print('paper numerical macros and tables refreshed')
if __name__=='__main__':main()
