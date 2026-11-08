"""Plot the current forward scenarios and real penalties from saved results only."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from football.reporting import DATA,OUT,MODELS,read_json,read_csv,save_json

FIG=OUT/'figures';COLORS=['#444B49','#0072B2','#D55E00','#009E73'];STYLES=['-','--','-.',':']
CASE_LABELS={'J03WMX':'Placement 1','J03WR9':'Placement 2','J03WOH':'Power shot'}
def col(rows,key):return np.array([float(r[key]) for r in rows])
def trace(group,case,model):return read_csv(OUT/f'{group}/{case}_{model}.csv')
def save(fig,name,rect=None):
    fig.tight_layout(rect=rect)
    for ext in ['pdf','svg','png']:fig.savefig(FIG/f'{name}.{ext}',dpi=300)
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

def inverse():
    for case in read_json(DATA/'inputs.json')['cases']:
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
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False,fontsize=8)
        save(fig,'penalty_'+case['case'],rect=[0,0,1,.90])

def inverse_overview():
    """Show all three spatial paths together using the saved fit and tracking data."""
    cases=read_json(DATA/'inputs.json')['cases']
    fig=plt.figure(figsize=(10,3.35))
    for i,case in enumerate(cases):
        ax=fig.add_subplot(1,3,i+1,projection='3d')
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
        ax.tick_params(labelsize=7,pad=0)
        ax.set_xlabel('x (m)',labelpad=-2);ax.set_ylabel('y (m)',labelpad=-2);ax.set_zlabel('z (m)',labelpad=-2)
    handles=[Line2D([0],[0],color='black',marker='o',markersize=3,lw=.8,label='Measured'),
             Line2D([0],[0],color='black',marker='o',markerfacecolor='white',markersize=5,lw=0,label='Fit input')]
    handles += [Line2D([0],[0],color=c,ls=s,lw=1.3,label=m) for m,c,s in zip(MODELS,COLORS,STYLES)]
    handles += [Line2D([0],[0],color='black',marker='x',markersize=5,lw=0,label='Goal crossing')]
    fig.legend(handles=handles,loc='upper center',ncol=7,frameon=False,fontsize=8)
    save(fig,'penalty_spatial_overview',rect=[0,0,1,.88])

def penalty_dynamics():
    """Compare inferred M4 speed and forces for the three recorded penalties."""
    cases=[('J03WMX','#8b5a3c','-'),('J03WR9','#6b8060','--'),('J03WOH','#4d6679','-.')]
    fig,axes=plt.subplots(1,3,figsize=(7.2,2.6))
    for case,color,style in cases:
        data=trace('inverse',case,'M4')
        for ax,key in zip(axes,['speed_m_s','drag_N','lift_N']):
            ax.plot(col(data,'time_s'),col(data,key),label=CASE_LABELS[case],color=color,ls=style,lw=1.5)
    for ax,label in zip(axes,['Speed (m/s)','Drag (N)','Magnus force (N)']):
        ax.set(xlabel='Time (s)',ylabel=label);ax.grid(alpha=.2);ax.tick_params(labelsize=8)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=3,frameon=False,fontsize=8)
    save(fig,'penalty_m4_dynamics',rect=[0,0,1,.87])

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
    parser=argparse.ArgumentParser();parser.add_argument('--inverse-only',action='store_true');args=parser.parse_args()
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],'font.size':9,'font.weight':'bold','axes.labelweight':'bold','axes.titleweight':'bold',
        'axes.spines.right':False,'axes.spines.top':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    if args.inverse_only:inverse();inverse_overview();penalty_dynamics()
    else:forward();inverse();inverse_overview();penalty_dynamics();other()
    save_json(FIG/'figure_contract.json',dict(width_inches=6.5,dpi=300,formats=['pdf','svg','png'],
        units='SI',models=list(MODELS),raw_frames=39,
        inverse_input_rule='corrected consecutive source frames; zero time at selected start; original repeated samples retained',
        forward_claim='force mechanisms under prescribed initial conditions',inverse_claim='continuation compared with held-out real samples',
        status_markers='asterisk: iteration limit; square: ground; cross: measured/interpolated goal crossing',
        probabilities='none',palette=COLORS))
    print('current shared report figures exported',flush=True)
