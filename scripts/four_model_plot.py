"""Plot the current forward scenarios and real penalties from saved results only."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from football.reporting import DATA,OUT,MODELS,read_json,read_csv,save_json

FIG=OUT/'figures';COLORS=['#444B49','#0072B2','#D55E00','#009E73'];STYLES=['-','--','-.',':']
CASE_LABELS={'J03WMX':'Case 1','J03WR9':'Case 2','J03WOH':'Case 3'}
def col(rows,key):return np.array([float(r[key]) for r in rows])
def trace(group,case,model):return read_csv(OUT/f'{group}/{case}_{model}.csv')
def save(fig,name,rect=None,manual_layout=False):
    if not manual_layout:fig.tight_layout(rect=rect)
    for ext in ['pdf','svg','png']:
        path=FIG/f'{name}.{ext}';fig.savefig(path,dpi=300)
        if ext=='svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)
def goal(ax):
    ax.plot([11]*5,[-3.66,3.66,3.66,-3.66,-3.66],[0,0,2.44,2.44,0],color='#8B8B83',lw=.8)
    ax.set(xlabel='x (m)',ylabel='y (m)',zlabel='z (m)');ax.view_init(22,-64)
    ax.set_box_aspect((11,7.32,3.0));ax.tick_params(labelsize=7)
def flight3d(ax,case):
    for model,c,s in zip(MODELS,COLORS,STYLES):
        r=trace('forward',case,model)
        ax.plot(col(r,'x_m'),col(r,'y_m'),col(r,'z_m'),label=model,color=c,ls=s,lw=1.4)
        ax.scatter(float(r[-1]['x_m']),float(r[-1]['y_m']),float(r[-1]['z_m']),s=12,color=c)
    goal(ax);ax.set_title(case.title(),fontsize=10)

def forward():
    for case in ['power','placement','curved','chip']:
        fig=plt.figure(figsize=(6.3,3.5));ax=fig.add_subplot(111,projection='3d')
        flight3d(ax,case);ax.legend(frameon=False,fontsize=8,loc='upper left');save(fig,'case_'+case)
    fig=plt.figure(figsize=(6.5,3.2))
    for i,case in enumerate(['topspin','backspin']):flight3d(fig.add_subplot(1,2,i+1,projection='3d'),case)
    fig.legend(MODELS,loc='upper center',ncol=4,frameon=False,fontsize=8);save(fig,'case_spin',rect=[0,0,1,.90])
    fig,axes=plt.subplots(2,3,figsize=(6.5,4.5))
    for i,case in enumerate(['curved','topspin']):
        for ax,field,label in zip(axes[i],['speed_m_s','drag_N','lift_N'],['Speed (m/s)','Drag (N)','Lift magnitude (N)']):
            for m,c,s in zip(MODELS,COLORS,STYLES):
                r=trace('forward',case,m);ax.plot(col(r,'time_s'),col(r,field),color=c,ls=s,label=m,lw=1.3)
            ax.set(xlabel='Time (s)',ylabel=label,title=case.title());ax.tick_params(labelsize=8)
    axes[0,0].legend(frameon=False,fontsize=7);save(fig,'forward_dynamics')

def inverse(only=None):
    for case in read_json(DATA/'inputs.json')['cases']:
        if only and case['case']!=only:continue
        power=case['case']=='J03WOH'
        if power:
            fig=plt.figure(figsize=(7.5,6.5))
            grid=fig.add_gridspec(2,2,left=.09,right=.975,bottom=.10,top=.84,wspace=.55,hspace=.48)
            ax3=fig.add_subplot(grid[0,0],projection='3d')
            axes=[fig.add_subplot(grid[0,1]),fig.add_subplot(grid[1,0]),fig.add_subplot(grid[1,1])]
        else:
            fig=plt.figure(figsize=(6.5,5.3));ax3=fig.add_subplot(2,2,1,projection='3d')
            axes=[fig.add_subplot(2,2,i) for i in [2,3,4]]
        actual=case['goal'];tend=actual['time_s']
        rows=[r for r in case['samples'] if 0<=r['time_s']<=tend+1e-10 and r['X_m']<=52.5+1e-10]
        xyz=np.array([[r[k] for k in ['x_m','y_m','z_m']] for r in rows]);times=np.array([r['time_s'] for r in rows])
        fit=np.array(case['fit_positions_m']);tf=np.array(case['fit_times_s'])
        ax3.plot(*xyz.T,color='black',marker='o',ms=2.5,lw=1,label='Measured samples')
        ax3.scatter(*fit.T,facecolors='white',edgecolors='black',s=24,depthshade=False,label='Fit inputs')
        ax3.scatter(*actual['local_position'],marker='x',color='black',s=25)
        for j,ax in enumerate(axes):
            ax.plot(times,xyz[:,j],color='black',marker='o',ms=2.7,lw=1,label='Measured samples')
            ax.scatter(tf,fit[:,j],facecolors='white',edgecolors='black',s=26,zorder=6,label='Fit inputs')
            if actual['source']=='linear interpolation':ax.scatter([tend],[actual['local_position'][j]],marker='x',color='black',s=24)
        for m,c,s in zip(MODELS,COLORS,STYLES):
            result=read_json(OUT/f"inverse/{case['case']}_{m}.json")['record']
            if not (OUT/f"inverse/{case['case']}_{m}.csv").exists():continue
            rows=trace('inverse',case['case'],m);mask=col(rows,'time_s')<=tend+1e-10
            label=m+('*' if result['status']=='fit_limit' else '')
            ax3.plot(col(rows,'x_m')[mask],col(rows,'y_m')[mask],col(rows,'z_m')[mask],color=c,ls=s,lw=1.3,label=label)
            for ax,field in zip(axes,['x_m','y_m','z_m']):
                ax.plot(col(rows,'time_s')[mask],col(rows,field)[mask],color=c,ls=s,lw=1.3,label=label)
                if result['event']['type']=='ground' and result['event']['time']<=tend:
                    ax.scatter([float(rows[-1]['time_s'])],[float(rows[-1][field])],color=c,marker='s',s=13)
        goal(ax3);ax3.set_title(CASE_LABELS[case['case']],fontsize=10)
        for ax,field in zip(axes,['x','y','z']):ax.set(xlabel='Time (s)',ylabel=field+' (m)',xlim=(0,tend*1.025));ax.tick_params(labelsize=8)
        if power:
            ax3.set_xlabel('x (m)',labelpad=1,fontsize=10)
            ax3.set_ylabel('y (m)',labelpad=1,fontsize=10)
            ax3.set_zlabel('z (m)',labelpad=2,fontsize=10)
            ax3.tick_params(labelsize=8,pad=1)
            for ax in axes:
                ax.xaxis.label.set_fontsize(10);ax.yaxis.label.set_fontsize(10)
                ax.tick_params(labelsize=9)
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False,fontsize=9.5 if power else 8)
        if power:
            fig.canvas.draw();renderer=fig.canvas.get_renderer()
            left=[axis.label for axis in [ax3.xaxis,ax3.yaxis,ax3.zaxis]]
            for axis,limits in [(ax3.xaxis,ax3.get_xlim()),(ax3.yaxis,ax3.get_ylim()),(ax3.zaxis,ax3.get_zlim())]:
                lo,hi=sorted(limits)
                left.extend(tick.label1 for tick in axis.get_major_ticks() if lo<=tick.get_loc()<=hi)
            right=[axes[0].yaxis.label]+axes[0].get_yticklabels()
            gap=min(t.get_window_extent(renderer).x0 for t in right if t.get_text())-max(t.get_window_extent(renderer).x1 for t in left if t.get_text())
            if gap<8:raise ValueError(f'Power-shot panel labels overlap: gap={gap}')
            save_json(FIG/'power_panel_layout.json',dict(figsize_inches=[7.5,6.5],
                layout='2 by 2; 3D, x(t), y(t), z(t)',horizontal_label_gap_pixels=float(gap),
                labels_nonoverlapping=True,source_case='J03WOH'))
        save(fig,'penalty_'+case['case'],rect=[0,0,1,.90],manual_layout=power)

def inverse_overview(case_names=None,basename='placement_spatial_comparison'):
    """Enlarged side-by-side placement paths from saved data."""
    cases=read_json(DATA/'inputs.json')['cases']
    case_names=case_names or ['J03WMX','J03WR9']
    cases=[next(c for c in cases if c['case']==name) for name in case_names]
    fig=plt.figure(figsize=(8,3.8))
    for i,case in enumerate(cases):
        ax=fig.add_subplot(1,len(cases),i+1,projection='3d')
        actual=case['goal'];tend=actual['time_s']
        rows=[r for r in case['samples'] if 0<=r['time_s']<=tend+1e-10 and r['X_m']<=52.5+1e-10]
        xyz=np.array([[r[k] for k in ('x_m','y_m','z_m')] for r in rows])
        ax.plot(*xyz.T,color='black',marker='o',ms=2.1,lw=.85)
        ax.scatter(*np.array(case['fit_positions_m']).T,facecolors='white',edgecolors='black',s=20,depthshade=False)
        ax.scatter(*actual['local_position'],marker='x',color='black',s=30)
        for model,color,style in zip(MODELS,COLORS,STYLES):
            path=OUT/f"inverse/{case['case']}_{model}.csv"
            if not path.exists():continue
            data=trace('inverse',case['case'],model);mask=col(data,'time_s')<=tend+1e-10
            ax.plot(col(data,'x_m')[mask],col(data,'y_m')[mask],col(data,'z_m')[mask],color=color,ls=style,lw=1.25)
        goal(ax);ax.set_title(CASE_LABELS[case['case']],fontsize=10,pad=0)
        ax.tick_params(labelsize=8,pad=1)
        ax.set_xlabel('x (m)',labelpad=1);ax.set_ylabel('y (m)',labelpad=1);ax.set_zlabel('z (m)',labelpad=1)
    handles=[Line2D([0],[0],color='black',marker='o',markersize=3,lw=.8,label='Measured'),
             Line2D([0],[0],color='black',marker='o',markerfacecolor='white',markersize=5,lw=0,label='Fit input')]
    handles += [Line2D([0],[0],color=c,ls=s,lw=1.3,label=m) for m,c,s in zip(MODELS,COLORS,STYLES)]
    handles += [Line2D([0],[0],color='black',marker='x',markersize=5,lw=0,label='Goal crossing')]
    fig.legend(handles=handles,loc='upper center',ncol=4,frameon=False,fontsize=9)
    fig.subplots_adjust(left=.01,right=.96,bottom=.05,top=.78,wspace=.10)
    save(fig,basename,manual_layout=True)

def penalty_dynamics():
    """Split technique groups with identical time and quantity axes."""
    cases=[('J03WMX','#8b5a3c','-'),('J03WR9','#6b8060','--'),('J03WOH','#4d6679','-.')]
    for group,selected in [('placement',cases[:2]),('power',cases[2:])]:
        fig,axes=plt.subplots(1,3,figsize=(7.2,2.6))
        for case,color,style in selected:
            data=trace('inverse',case,'M4')
            for ax,key in zip(axes,['speed_m_s','drag_N','lift_N']):
                ax.plot(col(data,'time_s'),col(data,key),label=CASE_LABELS[case],color=color,ls=style,lw=1.5)
        for ax,label,limits in zip(axes,['Speed (m/s)','Drag (N)','Magnus force (N)'],[(20,33),(0,8),(0,6)]):
            ax.set(xlabel='Time (s)',ylabel=label,xlim=(0,.4),ylim=limits);ax.grid(alpha=.2);ax.tick_params(labelsize=8)
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False,fontsize=9)
        save(fig,'penalty_'+group+'_dynamics',rect=[0,0,1,.87])


def problem():
    data=read_json(OUT/'problem/problem_b_M4.json'); rows=read_csv(OUT/'problem/problem_b_M4.csv')
    fig=plt.figure(figsize=(6.5,3.9));ax=fig.add_subplot(111,projection='3d')
    ax.plot(col(rows,'x_m'),col(rows,'y_m'),col(rows,'z_m'),color=COLORS[3],lw=1.8,label='M4')
    ax.scatter(*np.array(data['input']['positions_m']).T,facecolors='white',edgecolors='black',s=35,depthshade=False,label='Input positions')
    ax.scatter(*data['record']['event']['position'],color=COLORS[3],marker='X',s=45,label='Predicted crossing')
    goal(ax);ax.tick_params(labelsize=9);ax.set_title('Competition Problem B',fontsize=11)
    ax.legend(loc='upper left',frameon=False,fontsize=9);save(fig,'problem_b_M4')

def other():
    fig,axes=plt.subplots(1,3,figsize=(6.5,2.7))
    for key,c,s,label in [('constant_spin',COLORS[1],'-','Constant spin'),('inertial_torque',COLORS[2],'--','Quadratic torque')]:
        r=read_csv(OUT/f'other/{key}.csv')
        axes[0].plot(col(r,'time_s'),col(r,'omega_rad_s'),color=c,ls=s,label=label)
        for ax,field in zip(axes[1:],['y_m','z_m']):ax.plot(col(r,'x_m'),col(r,field),color=c,ls=s)
    axes[0].set(xlabel='Time (s)',ylabel='Spin (rad/s)');axes[1].set(xlabel='x (m)',ylabel='y (m)');axes[2].set(xlabel='x (m)',ylabel='z (m)')
    axes[0].legend(frameon=False,fontsize=7);save(fig,'torque_comparison')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--inverse-only',action='store_true')
    parser.add_argument('--placement-only',action='store_true');parser.add_argument('--chapter4-only',action='store_true')
    parser.add_argument('--case',choices=['J03WMX','J03WOH','J03WR9']);args=parser.parse_args()
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],'font.size':9,'font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold',
        'axes.spines.right':False,'axes.spines.top':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    if args.chapter4_only:
        inverse('J03WOH');inverse_overview();penalty_dynamics();problem()
    elif args.case:
        inverse(args.case)
    elif args.placement_only:
        inverse_overview(['J03WMX','J03WR9'],'placement_spatial_comparison')
    else:
        if args.inverse_only:inverse();inverse_overview();penalty_dynamics();problem()
        else:forward();inverse();inverse_overview();penalty_dynamics();problem();other()
    save_json(FIG/'figure_contract.json',dict(width_inches=6.5,dpi=300,formats=['pdf','svg','png'],
        panel_layout_overrides={'penalty_J03WOH':dict(figsize_inches=[7.5,6.5],layout='2 by 2: 3D and three time histories'),
            'placement_spatial_comparison':dict(figsize_inches=[8,3.8],layout='two side-by-side 3D paths')},
        dynamics_axes=dict(time_s=[0,.4],speed_m_s=[20,33],drag_N=[0,8],lift_N=[0,6]),
        units='SI',models=list(MODELS),raw_frames=39,
        inverse_input_rule='corrected consecutive source frames; zero time at selected start; original repeated samples retained',
        forward_claim='force mechanisms under prescribed initial conditions',inverse_claim='continuation compared with held-out real samples',
        status_markers='asterisk: iteration limit; square: ground; cross: measured/interpolated goal crossing',
        probabilities='none',palette=COLORS))
    print('current shared report figures exported',flush=True)
