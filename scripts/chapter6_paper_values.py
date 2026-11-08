"""Refresh only the bilingual Chapter 6 result macros from saved calculations."""
import re
import numpy as np
from football.reporting import ROOT,read_json
from latex_blocks import write_block

OUT=ROOT/'results/chapter6'


def scientific(x):
    a,b=f'{x:.2e}'.split('e');return a+r'\times10^{'+str(int(b))+'}'


def table(caption,label,head,rows,columns):
    return (r'\begin{table}[H]\centering\small'+'\n'+r'\caption{'+caption+r'}\label{'+label+'}\n'+
        r'\setlength{\tabcolsep}{5pt}\begin{tabular}{'+columns+r'}\toprule'+'\n'+head+r'\\\midrule'+'\n'+
        '\n'.join(row+r'\\' for row in rows)+'\n'+r'\bottomrule\end{tabular}\end{table}')


def remove_command(source,name):
    start=source.find('\\newcommand{\\'+name+'}')
    if start<0:return source
    a=source.index('{',start+len('\\newcommand{\\'+name+'}'));level=0
    for i in range(a,len(source)):
        if source[i]=='{':level+=1
        elif source[i]=='}':
            level-=1
            if level==0:return source[:start]+source[i+1:].lstrip('\n')
    raise ValueError('unbalanced macro '+name)


def main():
    tor=read_json(OUT/'torque/summary.json')
    wind=read_json(OUT/'wind/summary.json');base=np.array(tor['baseline']['event']['position'])
    shared=dict(ChSixReMin=f"{tor['baseline']['Re_range'][0]/1e5:.2f}",ChSixReMax=f"{tor['baseline']['Re_range'][1]/1e5:.2f}",
        ChSixAngular=f"{tor['configuration']['angular_drag_coefficient']:g}",
        ChSixGoalShift=scientific(tor['goal_displacement_m']),ChSixSpinLoss=f"{tor['spin_loss_pct']:.2f}",
        ChSixGoalShiftCM=f"{100*tor['goal_displacement_m']:.2f}",
        ChSixFinalSpin=f"{tor['damped']['final_spin_rad_s']:.4f}",
        ChSixViscousRatio=scientific(tor['viscous_to_quadratic_reference']),
        ChSixViscousShift=scientific(tor['viscous_goal_difference_m']),
        ChSixWindBound=f"{wind['reported_bound_m_s']:.2f}",
        ChSixWindWorstAngle=f"{wind['worst']['azimuth_deg']:.1f}",
        ChSixWindMaxShift=f"{100*wind['max_displacement_at_and_below_bound_m']:.3f}")
    for zh,folder in [(False,'paper'),(True,'_中文版')]:
        path=ROOT/folder/'main.tex';source=path.read_text(encoding='utf-8')
        for name in ['TorqueViscousRatio','TorqueDisplacement','TorqueResults','WindResultsTable','WindThreshold']:
            source=remove_command(source,name)
        if '% BEGIN CHAPTER6_RESULTS' not in source:
            source=source.replace('% END REPORT_RESULTS','% END REPORT_RESULTS\n\n% BEGIN CHAPTER6_RESULTS\n% END CHAPTER6_RESULTS',1)
        path.write_text(source,encoding='utf-8')
        commands=['% Generated exclusively from results/chapter6.\n']
        def macro(k,v):commands.append('\\newcommand{\\'+k+'}{'+v+'}\n')
        def tr(en,cn):return cn if zh else en
        for k,v in shared.items():macro(k,v)
        rows=[]
        for key,title in [('baseline','M4'),('damped',tr('M4 + torque','M4 + 阻尼'))]:
            r=tor[key];e=r['event'];y,z=e['position'][1:]
            rows.append(f"{title} & {y:.4f} & {z:.4f} & {e['time']:.6f} & {r['final_spin_rad_s']:.4f}")
        macro('ChSixTorqueTable',table(tr(r'Goal crossing and spin; the damping model fixes $C_{\rm angular}=1.5$.',r'球门交点与自旋对照，阻尼模型固定 $C_{\rm angular}=1.5$。'),
            'tab:torque-goals',r'Model & $y_g$ (m) & $z_g$ (m) & $t_g$ (s) & $\|\boldsymbol\omega_g\|$ (rad/s)' if not zh else
            r'模型 & $y_g$ (m) & $z_g$ (m) & $t_g$ (s) & $\|\boldsymbol\omega_g\|$ (rad/s)',rows,'lrrrr'))
        names={'tailwind':tr('Tailwind','顺风'),'headwind':tr('Headwind','逆风'),
            'left_crosswind':tr('Left crosswind','左侧风'),'right_crosswind':tr('Right crosswind','右侧风')}
        rows=[names[r['direction']]+f" & {r['reported_bound_m_s']:.2f}" for r in wind['cardinal']]
        rows.append(tr('All horizontal directions','水平全风向')+f" & {wind['reported_bound_m_s']:.2f}")
        macro('ChSixWindTable',table(tr('Wind-speed limits for a goal-crossing shift of at most 5 cm.','球门交点偏移不超过5 cm的风速界限。'),
            'tab:wind',tr('Wind direction & Speed limit (m/s)','风向 & 风速界限 (m/s)'),rows,'lr'))
        write_block(path,'CHAPTER6_RESULTS',''.join(commands))
    print('Chapter 6 bilingual values refreshed',flush=True)


if __name__=='__main__':main()
