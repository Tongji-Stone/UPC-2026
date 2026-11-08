"""Build both editions' tables from the same saved current results."""
import numpy as np
from football.reporting import ROOT,OUT,DATA,read_json
from football.physics import PhysicsConfig
from latex_blocks import write_block

def scientific(x):
    if x is None:return '---'
    a,b=f'{x:.2e}'.split('e')
    return '$'+a+r'\times10^{'+str(int(b))+'}$'

def table(caption,label,columns,head,rows,size=r'\footnotesize',row_stretch=None):
    spacing = (r'\renewcommand{\arraystretch}{'+str(row_stretch)+'}'+'\n') if row_stretch else ''
    return (r'\begin{table}[H]\centering'+size+'\n'+spacing+r'\caption{'+caption+r'}\label{'+label+'}\n'
        r'\setlength{\tabcolsep}{4pt}\begin{tabular}{'+columns+r'}\toprule'+'\n'+head+r'\\\midrule'+'\n'+
        '\n'.join(row+r'\\' for row in rows)+'\n'+r'\bottomrule\end{tabular}\end{table}')

def main():
    data=read_json(DATA/'inputs.json');forward=read_json(OUT/'forward/summary.json')['records']
    inverse=read_json(OUT/'inverse/summary.json')['records'];other=read_json(OUT/'other/summary.json')
    for zh,folder in [(False,'paper'),(True,'_中文版')]:
        if not (ROOT/folder).exists():continue
        commands=[]
        def macro(name,value):commands.append('\\newcommand{\\'+name+'}{'+str(value)+'}\n')
        def tr(en,cn):return cn if zh else en
        def case_label(case):return tr('Case ','案例')+str({'J03WMX':1,'J03WR9':2,'J03WOH':3}[case])
        for case,prefix in [('J03WMX','WMX'),('J03WOH','WOH'),('J03WR9','WR')]:
            for model in ('M1','M2','M3','M4'):
                r=next(item for item in inverse if item['case']==case and item['model']==model)
                goal=r.get('scored_goal_error_m');rmse=r.get('future_rmse_3d_m')
                goal_text=f'{goal:.3f}' if goal is not None else '---'
                model_word={'M1':'MOne','M2':'MTwo','M3':'MThree','M4':'MFour'}[model]
                macro(prefix+model_word+'GoalError',goal_text)
                macro(prefix+model_word+'PathRMSE',f'{rmse:.3f}' if rmse is not None else '---')
                macro(prefix+model_word+'EarlyResidual',f"{1000*r['early_max_residual_m']:.2f}")
                if model=='M4':
                    macro(prefix+'Speed',f"{np.linalg.norm(r['initial_state'][:3]):.2f}")
                    v=np.asarray(r['initial_state'][:3]);cfg=PhysicsConfig.for_model('M4')
                    drag=.5*cfg.air_density*np.pi*cfg.radius**2*r['fitted_cd']*float(v@v)
                    macro(prefix+'Drag',f'{drag:.2f}')
                    macro(prefix+'CD',f"{r['fitted_cd']:.4f}")
                    macro(prefix+'Alpha',f"{r['fitted_alpha']:.4f}")
        for name,cases,label,title in [
            ('PlacementCrossingTable',['J03WMX','J03WR9'],'tab:placement-crossings',tr('Placement-shot goal crossings and distance errors (m).','精准推射的球门交点与距离误差（m）。')),
            ('PowerCrossingTable',['J03WOH'],'tab:power-crossings',tr('Power-shot goal crossings and distance errors (m).','大力抽射的球门交点与距离误差（m）。'))]:
            crossing_rows=[]
            for case in cases:
                observed=next(c for c in data['cases'] if c['case']==case)['goal']['local_position'][1:]
                for model in ('M1','M2','M3','M4'):
                    r=next(r for r in inverse if r['case']==case and r['model']==model)
                    valid=r['scored_goal_error_m'] is not None
                    p=r['event']['position'][1:] if valid else None
                    pair=lambda a:f'$({a[0]:.3f},{a[1]:.3f})$'
                    crossing_rows.append(f'{case_label(case)} & {model} & '+pair(observed)+' & '+(pair(p) if valid else '---')+' & '+(f"{r['scored_goal_error_m']:.3f}" if valid else '---'))
            macro(name,table(title,label,'llrrr',tr(r'Case & Model & Observed $(y,z)$ & Predicted $(y,z)$ & Distance',r'案例 & 模型 & 实测 $(y,z)$ & 预测 $(y,z)$ & 距离'),crossing_rows,size=r'\normalfont\normalsize',row_stretch=1.12))
        physical=read_json(OUT/'chapter4/physical_summary.json')['records']
        for case,prefix in [('J03WMX','WMX'),('J03WR9','WR'),('J03WOH','WOH')]:
            r=next(r for r in physical if r['case']==case)
            c=next(c for c in data['cases'] if c['case']==case)
            macro(prefix+'PositionZero','('+','.join(f'{v:.2f}' for v in c['fit_positions_m'][0])+')')
            for field,suffix in [('elevation_deg','Elevation'),('vertical_speed_m_s','VerticalSpeed'),('lift_N','Lift')]:
                macro(prefix+suffix,f'{r[field]:.2f}')
            macro(prefix+'VerticalLift',f"{r['lift_vector_N'][2]:+.2f}")
        problem=read_json(OUT/'problem/problem_b_M4.json')['record']
        macro('ProblemSpeed',f"{problem['speed_m_s']:.2f}");macro('ProblemElevation',f"{problem['elevation_deg']:.2f}")
        m3=next(r for r in inverse if r['case']=='J03WMX' and r['model']=='M3')
        x0=next(c for c in data['cases'] if c['case']=='J03WMX')['fit_positions_m'][0][0]
        macro('WMXMThreeMaxX',f"{x0-m3['initial_state'][0]**2/(2*m3['constant_acceleration'][0]):.3f}")
        macro('WMXMThreeAX',f"{m3['constant_acceleration'][0]:.2f}")
        rows=[]
        for case in ['J03WMX','J03WR9','J03WOH']:
            r=next(r for r in inverse if r['case']==case and r['model']=='M4')
            axis=np.asarray(r['initial_state'][3:])/30
            rows.append(case_label(case)+' & '+f"{np.linalg.norm(r['initial_state'][:3]):.2f} & {r['fitted_cd']:.4f} & {r['fitted_alpha']:.4f} & "+' & '.join(f'{x:.4f}' for x in axis))
        macro('MFourParameterTable',table(tr('Fitted M4 states at the selected starting frames.','选定起始帧的 M4 反演参数。'),
            'tab:m4-parameters','lrrrrrr',tr(r'Event & $v_0$ (m/s) & $C_D$ & $\alpha$ & $n_x$ & $n_y$ & $n_z$',
                r'事件 & $v_0$ (m/s) & $C_D$ & $\alpha$ & $n_x$ & $n_y$ & $n_z$'),rows,size=r'\small'))
        c=PhysicsConfig.for_model('M4');macro('ReferenceCD',f'{c.drag_coefficient:.4f}');macro('ReferenceCL',f'{c.lift_coefficient:.4f}')
        macro('ForwardReMin',f'{14*2*.11/1.5e-5/1e5:.2f}');macro('ForwardReMax',f'{27*2*.11/1.5e-5/1e5:.2f}')
        r=next(r for r in forward if r['case']=='curved' and r['model']=='M4');e=r['event']
        for name,val in dict(CurvedY=e['position'][1],CurvedZ=e['position'][2],CurvedTime=e['time'],CurvedVX=r['initial_state'][0],CurvedVZ=r['initial_state'][2]).items():macro(name,f'{val:.4f}')
        rows=[r'$v_{x0}$ (M1, M2, M4) & $[0,35]$ m/s',r'$v_{y0},v_{z0}$ (M1, M2, M4) & $[-35,35]$ m/s',
            r'$\|\boldsymbol\omega_0\|$ (M4) & $30$ rad/s',
            tr(r'Azimuth, elevation (M4) & $[-\pi,\pi],[-\dfrac{\pi}{2},\dfrac{\pi}{2}]$ rad',r'方位角、仰角 (M4) & $[-\pi,\pi],[-\dfrac{\pi}{2},\dfrac{\pi}{2}]$ rad'),r'$\dfrac{C_D}{C_D^*},\dfrac{\alpha}{\alpha^*}$ & $[0.5,1.5]$']
        observation_rows=[]
        for case in ['J03WMX','J03WR9','J03WOH']:
            c=next(item for item in data['cases'] if item['case']==case)
            title=({'J03WMX':'推射 1','J03WR9':'推射 2','J03WOH':'大力抽射'} if zh else
                   {'J03WMX':'Placement 1','J03WR9':'Placement 2','J03WOH':'Power shot'})[case]
            for t,p in zip(c['fit_times_s'][1:],c['fit_positions_m'][1:]):
                observation_rows.append(case_label(case)+f' & {t:.2f} & $('+','.join(f'{v:.2f}' for v in p)+')$ & '+
                    ('$('+','.join(f'{v:.4f}' for v in c['goal']['local_position'][1:])+')$' if t==c['fit_times_s'][1] else ''))
            goal=c['goal']
        observation_table=table(tr('Two later input positions and observed goal crossings; coordinates in m.',
            '两次后续输入位置与实测球门交点，坐标单位为 m。'),'tab:penalty-observations','lrrr',
            tr(r'Case & $t$ (s) & $(x,y,z)$ & Observed $(y_g,z_g)$',
               r'案例 & $t$ (s) & $(x,y,z)$ & 实测 $(y_g,z_g)$'),observation_rows,size=r'\normalsize')
        macro('PenaltyObservationTable',observation_table)
        macro('InverseBoundsTable',table(tr('Component bounds and force-correction settings for inversion.','反演分量边界与气动力修正设定。'),'tab:inverse-bounds','ll',tr('Quantity & Search interval','物理量 & 搜索区间'),rows))
        macro('TorqueViscousRatio',scientific(other['viscous_to_inertial_ratio']));macro('TorqueDisplacement',f"{other['goal_displacement_m']:.4f}")
        text=tr(f"Spin falls by {other['spin_loss_pct']:.3f}\\%, while the crossing moves {other['goal_displacement_m']:.4f} m ({other['displacement_pct_of_11m']:.3f}\\% of the 11 m distance) and arrival time changes by {other['time_change_pct']:+.3f}\\%. Rotational damping therefore has a small endpoint effect in this short reference flight.",
            f"自旋降低 {other['spin_loss_pct']:.3f}\\%，球门交点移动 {other['goal_displacement_m']:.4f} m，占 11 m 距离的 {other['displacement_pct_of_11m']:.3f}\\%；到达时间变化 {other['time_change_pct']:+.3f}\\%。因此，在这一短程参考飞行中，旋转阻尼对落点的影响较小。")
        macro('TorqueResults',text)
        rows=[' & '.join([f"{r['wind_m_s']:.0f}",f"{r['head_pct']:+.2f}",f"{r['tail_pct']:+.2f}",f"{r['cross_pct']:+.2f}",f"{r['angle_deg']:.2f}"]) for r in other['wind']]
        macro('WindResultsTable',table(tr('Illustrative wind at the 24 m/s curved-shot launch: dynamic-pressure changes at fixed coefficients.','24 m/s 弧线球初速下的示例风况：固定系数时的动压变化。'),'tab:wind','rrrrr',
            tr(r'$w$ (m/s) & Headwind (\%) & Tailwind (\%) & Crosswind (\%) & Angle ($^\circ$)',r'$w$ (m/s) & 逆风 (\%) & 顺风 (\%) & 侧风 (\%) & 偏角 ($^\circ$)'),rows))
        macro('WindThreshold',f"{other['wind_threshold_m_s']:.2f}")
        write_block(ROOT/folder/'main.tex','REPORT_RESULTS','% Generated exclusively from results/current_report.\n'+''.join(commands))
    print('bilingual tables refreshed from 24 forward and 12 inverse results')

if __name__=='__main__':main()
