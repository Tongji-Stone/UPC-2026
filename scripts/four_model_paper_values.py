"""Build both editions' tables from the same saved current results."""
import numpy as np
from football.reporting import ROOT,OUT,DATA,read_json
from football.physics import PhysicsConfig

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
        rows=[]
        statuses={'plane':tr('goal','球门'),'ground':tr('ground','触地'),'none':tr('no crossing','未到达'),
            'fit_limit':tr('iteration limit','迭代上限'),'early_contact':tr('early ground','提前触地'),'fit_failure':tr('fit failure','反演失败')}
        for case,prefix in [('J03WMX','WMX'),('J03WOH','WOH'),('J03WR9','WR')]:
            title=({'J03WMX':'推射 1','J03WOH':'大力抽射','J03WR9':'推射 2'} if zh else
                   {'J03WMX':'Placement 1','J03WOH':'Power shot','J03WR9':'Placement 2'})[case]
            for model in ('M1','M2','M3','M4'):
                r=next(item for item in inverse if item['case']==case and item['model']==model)
                goal=r.get('scored_goal_error_m');rmse=r.get('future_rmse_3d_m')
                goal_text=f'{goal:.3f}' if goal is not None else '---'
                rmse_text=f"{rmse:.3f}/{r['future_sample_count']}" if rmse is not None else '---/0'
                rows.append(f"{title} & {model} & {1000*r['early_max_residual_m']:.2f} & {rmse_text} & {goal_text} & {statuses[r['status']]}")
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
        macro('PenaltyErrorSummaryTable',table(
            tr('Early maximum coordinate residual, subsequent path RMSE/sample count, goal-plane error and termination.',
               '早期最大坐标残差、后续路径 RMSE/点数、球门交点误差与终止状态。'),
            'tab:penalty-errors','llrrrl',
            tr(r'Event & Model & Residual (mm) & RMSE (m)/$n$ & Goal (m) & Status',
               r'事件 & 模型 & 残差 (mm) & RMSE (m)/$n$ & 交点 (m) & 状态'),
            rows,size=r'\normalfont\normalsize',row_stretch=1.12))
        m3=next(r for r in inverse if r['case']=='J03WMX' and r['model']=='M3')
        x0=next(c for c in data['cases'] if c['case']=='J03WMX')['fit_positions_m'][0][0]
        macro('WMXMThreeMaxX',f"{x0-m3['initial_state'][0]**2/(2*m3['constant_acceleration'][0]):.3f}")
        rows=[]
        for case in ['J03WMX','J03WR9','J03WOH']:
            r=next(r for r in inverse if r['case']==case and r['model']=='M4')
            axis=np.asarray(r['initial_state'][3:])/30
            rows.append(case+' & '+f"{np.linalg.norm(r['initial_state'][:3]):.2f} & {r['fitted_cd']:.4f} & {r['fitted_alpha']:.4f} & "+' & '.join(f'{x:.4f}' for x in axis))
        macro('MFourParameterTable',table(tr('Fitted M4 states at the selected starting frames.','选定起始帧的 M4 反演参数。'),
            'tab:m4-parameters','lrrrrrr',tr(r'Event & $v_0$ (m/s) & $C_D$ & $\alpha$ & $n_x$ & $n_y$ & $n_z$',
                r'事件 & $v_0$ (m/s) & $C_D$ & $\alpha$ & $n_x$ & $n_y$ & $n_z$'),rows,size=r'\small'))
        c=PhysicsConfig.for_model('M4');macro('ReferenceCD',f'{c.drag_coefficient:.4f}');macro('ReferenceCL',f'{c.lift_coefficient:.4f}')
        macro('ForwardReMin',f'{14*2*.11/1.5e-5/1e5:.2f}');macro('ForwardReMax',f'{27*2*.11/1.5e-5/1e5:.2f}')
        r=next(r for r in forward if r['case']=='curved' and r['model']=='M4');e=r['event']
        for name,val in dict(CurvedY=e['position'][1],CurvedZ=e['position'][2],CurvedTime=e['time'],CurvedVX=r['initial_state'][0],CurvedVZ=r['initial_state'][2]).items():macro(name,f'{val:.4f}')
        rows=[]
        for c in data['cases']:
            rows.append(c['case']+' & '+str(len(c['samples']))+' & '+','.join(f'{t:.2f}' for t in c['fit_times_s'])+' & $('+','.join(f'{v:.2f}' for v in c['fit_positions_m'][0])+')$')
        macro('PenaltyInputsTable',table(tr('Frame counts, fitting times and measured local starting positions.','原始帧数、反演时刻与实测局部起点。'),'tab:penalty-inputs','lrrl',
            tr(r'Event & Frames & Fit times (s) & $\boldsymbol r_0$ (m)',r'事件 & 帧数 & 反演时刻 (s) & $\boldsymbol r_0$ (m)'),rows))
        rows=[r'$v_{x0}$ (M1, M2, M4) & $[0,35]$ m/s',r'$v_{y0},v_{z0}$ (M1, M2, M4) & $[-35,35]$ m/s',
            r'$\|\boldsymbol\omega_0\|$ (M4) & $30$ rad/s',
            tr(r'Azimuth, elevation (M4) & $[-\pi,\pi],[-\pi/2,\pi/2]$ rad',r'方位角、仰角 (M4) & $[-\pi,\pi],[-\pi/2,\pi/2]$ rad'),r'$C_D/C_D^*,\alpha/\alpha^*$ & $[0.5,1.5]$']
        observation_rows=[]
        for case in ['J03WMX','J03WR9','J03WOH']:
            c=next(item for item in data['cases'] if item['case']==case)
            title=({'J03WMX':'推射 1','J03WR9':'推射 2','J03WOH':'大力抽射'} if zh else
                   {'J03WMX':'Placement 1','J03WR9':'Placement 2','J03WOH':'Power shot'})[case]
            for t,p,f in zip(c['fit_times_s'],c['fit_positions_m'],c['fit_frames']):
                observation_rows.append(title+f' & {f} & {t:.2f} & '+' & '.join(f'{v:.3f}' for v in p))
            goal=c['goal']
            observation_rows.append(title+tr(' goal','门线')+' & '+'--'.join(goal['frames'])+f" & {goal['time_s']:.4f} & "+' & '.join(f'{v:.4f}' for v in goal['local_position']))
        observation_table=table(tr('Selected early positions and observed goal crossings in local coordinates.',
            '局部坐标下的早期输入位置与实测球门交点。'),'tab:penalty-observations','llrrrr',
            tr(r'Event & Source frame & $t$ (s) & $x$ (m) & $y$ (m) & $z$ (m)',
               r'事件 & 源帧 & $t$ (s) & $x$ (m) & $y$ (m) & $z$ (m)'),observation_rows,size=r'\small')
        macro('PenaltyObservationTable',observation_table)
        macro('InverseBoundsTable',table(tr('Component bounds and force-correction settings for inversion.','反演分量边界与气动力修正设定。'),'tab:inverse-bounds','ll',tr('Quantity & Search interval','物理量 & 搜索区间'),rows))
        statuses={'plane':tr('plane','平面'),'ground':tr('ground','触地'),'none':tr('time limit','时间上限'),'fit_limit':tr('limit','迭代上限'),'early_contact':tr('early ground','过早触地'),'fit_failure':tr('failure','失败')}
        def vector(values,axis=False):
            v=r'$\begin{pmatrix}'+r'\\'.join(f'{x:.3f}' for x in values)+r'\end{pmatrix}'+('^{*}' if axis else '')+'$'
            return v
        for case,command in [('J03WMX','WMX'),('J03WOH','WOH'),('J03WR9','WR')]:
            observed=next(c for c in data['cases'] if c['case']==case);rr=[r for r in inverse if r['case']==case]
            rows=[]
            for i,(t,pos,frame) in enumerate(zip(observed['fit_times_s'],observed['fit_positions_m'],observed['fit_frames'])):
                rows.append(f'$P_{i}$ & {frame} & {t:.2f} & '+' & '.join(f'{x:.3f}' for x in pos))
            goal=observed['goal'];source=tr('direct source frame','源帧直接记录') if goal['source']=='measured' else tr('linear interpolation','帧间线性插值')
            rows.append(tr('Goal','球门')+' & '+'--'.join(goal['frames'])+f" & {goal['time_s']:.4f} & 11.000 & {goal['local_position'][1]:.4f} & {goal['local_position'][2]:.4f}")
            macro(command+'MeasuredTable',table(tr(f'{case}: three measured fitting points and observed goal crossing ({source}).',f'{case}：三个实测拟合点与实测球门交点（{source}）。'),'tab:measured-'+case,'llrrrr',
                tr(r'Point & Source frame & $t$ (s) & $x$ (m) & $y$ (m) & $z$ (m)',r'点 & 源帧号 & $t$ (s) & $x$ (m) & $y$ (m) & $z$ (m)'),rows))
            rows=[]
            for r in rr:
                q=r.get('initial_state');event=r.get('event',{});reached=event.get('type')=='plane'
                yz=[f'{x:.4f}' for x in event['position'][1:]] if reached else ['---','---']
                spin=vector(q[3:]) if q is not None and r['model']=='M4' else '---'
                vel=vector(q[:3]) if q is not None else '---'
                distance=f"{r['goal_error_m']:.4f}" if reached else '---'
                rows.append(f"{r['model']} & {statuses[r['status']]} & "+' & '.join(yz)+f' & {vel} & {spin} & {distance}')
            cap=tr(f'{case}: inverse initial states and predicted goal-plane crossings. M4 uses a 30 rad/s reference spin magnitude; M1--M3 do not estimate spin.',
                f'{case}：反演初始状态与预测球门交点。M4 使用 30 rad/s 参考自旋大小；M1--M3 不反演自旋。')
            macro(command+'PredictedTable',table(cap,'tab:predicted-'+case,'llrrccr',
                tr(r'Model & Status & $y_g$ (m) & $z_g$ (m) & $\boldsymbol v_0$ (m/s) & Spin & $d_g$ (m)',
                   r'模型 & 状态 & $y_g$ (m) & $z_g$ (m) & $\boldsymbol v_0$ (m/s) & 自旋 & $d_g$ (m)'),rows))
            text=tr('The measured low flight requires sustained vertical support from lift.','实测低空飞行中，升力影响足球能否持续保持在草地上方。') if case=='J03WMX' else tr('The rising measured arc connects vertical launch velocity with the subsequent action of gravity and lift.','实测上升弧线体现了初始竖直速度，以及重力和升力对后续路径的共同作用。') if case=='J03WOH' else tr('The measured path bends laterally, so fitted spin direction affects the continuation towards the goal.','实测路径具有明显横向运动，拟合自旋方向影响了朝向球门的后续轨迹。')
            m4=rr[-1]
            if m4.get('goal_error_m') is not None:
                text+=tr(f" M4's crossing deviation is {m4['goal_error_m']:.4f} m.",f" M4 的交点偏离距离为 {m4['goal_error_m']:.4f} m。")
            elif m4.get('event',{}).get('type')=='ground':
                text+=tr(f" M4 reaches the ground at $x={m4['event']['position'][0]:.3f}$ m.",f" M4 在 $x={m4['event']['position'][0]:.3f}$ m 触地。")
            limits=[r['model'] for r in rr if r['status']=='fit_limit']
            if limits:text+=tr(' The iteration-limit candidates are '+', '.join(limits)+'.',' 达到迭代上限的候选为 '+ '、'.join(limits)+'。')
            ground=[r['model'] for r in rr if r.get('event',{}).get('type')=='ground']
            if ground:text+=tr(' Ground contact precedes the goal for '+', '.join(ground)+'.',' '+ '、'.join(ground)+' 在球门前触地。')
            macro(command+'Discussion',text)
        macro('TorqueViscousRatio',scientific(other['viscous_to_inertial_ratio']));macro('TorqueDisplacement',f"{other['goal_displacement_m']:.4f}")
        text=tr(f"Spin falls by {other['spin_loss_pct']:.3f}\\%, while the crossing moves {other['goal_displacement_m']:.4f} m ({other['displacement_pct_of_11m']:.3f}\\% of the 11 m distance) and arrival time changes by {other['time_change_pct']:+.3f}\\%. Rotational damping therefore has a small endpoint effect in this short reference flight.",
            f"自旋降低 {other['spin_loss_pct']:.3f}\\%，球门交点移动 {other['goal_displacement_m']:.4f} m，占 11 m 距离的 {other['displacement_pct_of_11m']:.3f}\\%；到达时间变化 {other['time_change_pct']:+.3f}\\%。因此，在这一短程参考飞行中，旋转阻尼对落点的影响较小。")
        macro('TorqueResults',text)
        rows=[' & '.join([f"{r['wind_m_s']:.0f}",f"{r['head_pct']:+.2f}",f"{r['tail_pct']:+.2f}",f"{r['cross_pct']:+.2f}",f"{r['angle_deg']:.2f}"]) for r in other['wind']]
        macro('WindResultsTable',table(tr('Illustrative wind at the 24 m/s curved-shot launch: dynamic-pressure changes at fixed coefficients.','24 m/s 弧线球初速下的示例风况：固定系数时的动压变化。'),'tab:wind','rrrrr',
            tr(r'$w$ (m/s) & Headwind (\%) & Tailwind (\%) & Crosswind (\%) & Angle ($^\circ$)',r'$w$ (m/s) & 逆风 (\%) & 顺风 (\%) & 侧风 (\%) & 偏角 ($^\circ$)'),rows))
        macro('WindThreshold',f"{other['wind_threshold_m_s']:.2f}")
        (ROOT/folder/'report_results.tex').write_text('% Generated exclusively from results/current_report.\n'+''.join(commands),encoding='utf-8')
    print('bilingual tables refreshed from 24 forward and 12 inverse results')

if __name__=='__main__':main()
