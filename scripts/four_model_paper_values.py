"""Build both editions' tables from the same saved current results."""
import numpy as np
from football.reporting import ROOT,OUT,DATA,read_json
from football.physics import PhysicsConfig

def scientific(x):
    if x is None:return '---'
    a,b=f'{x:.2e}'.split('e')
    return '$'+a+r'\times10^{'+str(int(b))+'}$'

def table(caption,label,columns,head,rows):
    return (r'\begin{table}[H]\centering\footnotesize'+'\n'+r'\caption{'+caption+r'}\label{'+label+'}\n'
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
        names=dict(zip([c['case'] for c in data['config']['forward']],
            ['大力射门','推射','弧线球','上旋','下旋','挑射'] if zh else ['Power','Placement','Curved','Topspin','Backspin','Chip']))
        c=PhysicsConfig.for_model('M3');macro('ReferenceCD',f'{c.drag_coefficient:.4f}');macro('ReferenceCL',f'{c.lift_coefficient:.4f}')
        macro('ForwardReMin',f'{14*2*.11/1.5e-5/1e5:.2f}');macro('ForwardReMax',f'{27*2*.11/1.5e-5/1e5:.2f}')
        rows=[]
        for c in data['config']['forward']:
            rows.append(f"{names[c['case']]} & {c['speed_m_s']} & {c['elevation_deg']} & $({','.join(map(str,c['spin_rad_s']))})$")
        macro('ForwardInputsTable',table(tr('Prescribed initial conditions.','自设初始条件。'),'tab:forward-inputs','lrrl',
            tr(r'Kick & $v_0$ (m/s) & $\beta$ ($^\circ$) & $\boldsymbol\omega_0$ (rad/s)',r'踢法 & $v_0$ (m/s) & $\beta$ ($^\circ$) & $\boldsymbol\omega_0$ (rad/s)'),rows))
        rows=[]
        for r in forward:
            e=r['event'];status=tr('goal','球门') if e['type']=='plane' else tr('ground','触地')
            rows.append(f"{names[r['case']]} & {r['model']} & {status} & "+' & '.join(f'{x:.3f}' for x in e['position'])+f" & {e['time']:.4f}")
        macro('ForwardOutcomesTable',table(tr('First goal-plane or ground endpoint for all 24 flights.','24 次飞行的首次球门平面或触地终点。'),'tab:forward-outcomes','lllrrrr',
            tr(r'Kick & Model & End & $x$ (m) & $y$ (m) & $z$ (m) & $t$ (s)',r'踢法 & 模型 & 终止 & $x$ (m) & $y$ (m) & $z$ (m) & $t$ (s)'),rows))
        r=next(r for r in forward if r['case']=='curved' and r['model']=='M4');e=r['event']
        for name,val in dict(CurvedY=e['position'][1],CurvedZ=e['position'][2],CurvedTime=e['time'],CurvedVX=r['initial_state'][0],CurvedVZ=r['initial_state'][2]).items():macro(name,f'{val:.4f}')
        rows=[]
        for c in data['cases']:
            rows.append(c['case']+' & '+str(len(c['samples']))+' & '+','.join(f'{t:.2f}' for t in c['fit_times_s'])+' & $('+','.join(f'{v:.2f}' for v in c['fit_positions_m'][0])+')$')
        macro('PenaltyInputsTable',table(tr('Frame counts, fitting times and measured local starting positions.','原始帧数、反演时刻与实测局部起点。'),'tab:penalty-inputs','lrrl',
            tr(r'Event & Frames & Fit times (s) & $\boldsymbol r_0$ (m)',r'事件 & 帧数 & 反演时刻 (s) & $\boldsymbol r_0$ (m)'),rows))
        rows=[r'$v_{x0}$ & $[0,35]$ m/s',r'$v_{y0},v_{z0}$ & $[-35,35]$ m/s',r'$\omega_{x0},\omega_{y0},\omega_{z0}$ (M4) & $[-20\pi,20\pi]$ rad/s',
            tr(r'Azimuth, elevation (M3) & $[-\pi,\pi],[-\pi/2,\pi/2]$ rad',r'方位角、仰角 (M3) & $[-\pi,\pi],[-\pi/2,\pi/2]$ rad'),r'$\alpha_D,\alpha_L$ & $[0.5,1.5]$']
        macro('InverseBoundsTable',table(tr('Component bounds and force-correction settings for inversion.','反演分量边界与气动力修正设定。'),'tab:inverse-bounds','ll',tr('Quantity & Search interval','物理量 & 搜索区间'),rows))
        rows=[]
        statuses={'plane':tr('goal','球门'),'ground':tr('ground','触地'),'fit_limit':tr('limit','迭代上限'),'early_contact':tr('early ground','过早触地'),'fit_failure':tr('failure','失败')}
        for r in inverse:
            value=lambda k:f"{r[k]:.3f}" if r.get(k) is not None else '---'
            rows.append(f"{r['case'][-3:]} & {r['model']} & {statuses[r['status']]} & "+scientific(r.get('early_max_residual_m'))+' & '+value('future_rmse_3d_m')+f"/{r['future_sample_count']} & "+value('goal_error_m')+' & '+value('goal_time_error_s'))
        macro('InverseResultsTable',table(tr('All inversions: maximum early coordinate residual, later 3D RMSE/sample count, goal error and arrival-time error. Limit rows describe the saved iteration-limit candidate.','全部反演：早期最大坐标残差、后续三维 RMSE/点数、交点误差与时间差。迭代上限行给出保存候选的指标。'),'tab:inverse-results','lllrrrr',
            tr(r'Event & Model & Status & Resid. (m) & RMSE (m)/$n$ & Goal (m) & $\Delta t$ (s)',r'事件 & 模型 & 状态 & 残差 (m) & RMSE (m)/$n$ & 交点 (m) & $\Delta t$ (s)'),rows))
        for case,command in [('J03WMX','WMXDiscussion'),('J03WOH','WOHDiscussion'),('J03WR9','WRDiscussion')]:
            rr=[r for r in inverse if r['case']==case];m4=rr[-1]
            if case=='J03WMX':text=tr('The recorded path stays close to the turf. Gravity-only and drag-only predictions reach the ground before the goal; upward Magnus force in M3 and M4 sustains the low flight.','实测路径接近草地。仅重力和仅阻力预测在球门前触地；M3、M4 的向上马格努斯力支撑了这段低空飞行。')
            elif case=='J03WOH':text=tr('The first two horizontal increments are 0.71 and 1.22 m in equal time intervals. This accelerating early sequence drives the drag correction to its lower bound. The M4 search reaches the iteration limit; its candidate is retained and marked in the figure and table.','前两个等时间间隔的水平位移分别为 0.71 和 1.22 m。早期加速序列使阻力修正到达下边界。M4 搜索达到迭代上限，其候选在图表中单独标记。')
            else:text=tr('Using 0, 0.08 and 0.12 s avoids treating the duplicated first position as a separate displacement. The measured lateral motion is substantial, and fitted lift direction controls the later sideways bending.','使用 0、0.08、0.12 s 避免将首个重复位置作为独立位移。实测横向运动明显，拟合升力方向决定了后续侧向弯曲。')
            if m4.get('goal_error_m') is not None:
                text+=tr(f" The M4 candidate crossing error is {m4['goal_error_m']:.3f} m, with arrival-time difference {m4['goal_time_error_s']:+.3f} s.",f" M4 候选的交点误差为 {m4['goal_error_m']:.3f} m，到达时间差为 {m4['goal_time_error_s']:+.3f} s。")
            macro(command,text)
        macro('TorqueViscousRatio',scientific(other['viscous_to_inertial_ratio']));macro('TorqueDisplacement',f"{other['goal_displacement_m']:.4f}")
        a,b=[r['event'] for r in other['records'][:2]]
        text=tr(f"The damped crossing is $({b['position'][1]:.4f},{b['position'][2]:.4f})$ m, compared with $({a['position'][1]:.4f},{a['position'][2]:.4f})$ m at constant spin. The displacement is {other['goal_displacement_m']:.4f} m ({other['displacement_pct_of_11m']:.3f}\\% of 11 m). Spin falls by {other['spin_loss_pct']:.3f}\\%, and crossing time changes by {other['time_change_pct']:+.3f}\\%. Adding viscous torque shifts the damped crossing by {other['viscous_goal_difference_m']:.2g} m. The short-flight endpoint is less sensitive than spin magnitude to this reference torque.",
            f"阻尼交点为 $({b['position'][1]:.4f},{b['position'][2]:.4f})$ m，恒定自旋为 $({a['position'][1]:.4f},{a['position'][2]:.4f})$ m。位移为 {other['goal_displacement_m']:.4f} m，占 11 m 的 {other['displacement_pct_of_11m']:.3f}\\%。自旋降低 {other['spin_loss_pct']:.3f}\\%，到达时间变化 {other['time_change_pct']:+.3f}\\%。再加入黏性力矩使阻尼交点改变 {other['viscous_goal_difference_m']:.2g} m。短程交点的变化小于自旋幅值的变化。")
        macro('TorqueResults',text)
        rows=[' & '.join([f"{r['wind_m_s']:.0f}",f"{r['head_pct']:+.2f}",f"{r['tail_pct']:+.2f}",f"{r['cross_pct']:+.2f}",f"{r['angle_deg']:.2f}"]) for r in other['wind']]
        macro('WindResultsTable',table(tr('Illustrative wind at the 24 m/s curved-shot launch: dynamic-pressure changes at fixed coefficients.','24 m/s 弧线球初速下的示例风况：固定系数时的动压变化。'),'tab:wind','rrrrr',
            tr(r'$w$ (m/s) & Headwind (\%) & Tailwind (\%) & Crosswind (\%) & Angle ($^\circ$)',r'$w$ (m/s) & 逆风 (\%) & 顺风 (\%) & 侧风 (\%) & 偏角 ($^\circ$)'),rows))
        macro('WindThreshold',f"{other['wind_threshold_m_s']:.2f}")
        (ROOT/folder/'report_results.tex').write_text('% Generated exclusively from results/current_report.\n'+''.join(commands),encoding='utf-8')
    print('bilingual tables refreshed from 24 forward and 12 inverse results')

if __name__=='__main__':main()
