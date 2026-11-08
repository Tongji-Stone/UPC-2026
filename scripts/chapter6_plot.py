"""One two-curve spin comparison, plotted exclusively from Chapter 6 CSVs."""
import hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from football.reporting import ROOT,read_csv,read_json,save_json


def main():
    out=ROOT/'results/chapter6';figdir=out/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman'],'font.size':11,
        'axes.labelweight':'bold','axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'svg.fonttype':'none','mathtext.fontset':'stix'})
    fig,ax=plt.subplots(figsize=(6.4,3.25));sources=[];minspin=30.
    for name,label,color,style,width in [
        ('constant_spin','M4: constant spin','#444B49','-',2.6),
        ('default_damping',r'M4: $C_{\mathrm{angular}}=1.5$','#C17754','--',1.9)]:
        path=out/f'torque/{name}.csv';data=read_csv(path)
        t=np.array([float(r['time_s']) for r in data]);w=np.array([float(r['omega_rad_s']) for r in data])
        assert np.isfinite(w).all() and np.all(np.diff(t)>0)
        ax.plot(t,w,label=label,color=color,ls=style,lw=width)
        minspin=min(minspin,float(w.min()));sources.append(dict(path=str(path.relative_to(ROOT)),points=len(t),
            time_range_s=[float(t[0]),float(t[-1])],spin_range_rad_s=[float(w.min()),float(w.max())],
            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    if 30-minspin<.01:ax.set_ylim(29.5,30.5)
    else:ax.set_ylim(max(0,minspin-1),31)
    ax.set(xlabel='Time (s)',ylabel='Spin magnitude (rad/s)',xlim=(0,max(r['time_range_s'][1] for r in sources)*1.03))
    ax.grid(alpha=.18);ax.legend(frameon=False,fontsize=10,loc='lower left');fig.tight_layout()
    for ext in ['pdf','svg','png']:fig.savefig(figdir/f'problem_spin_comparison.{ext}',dpi=300)
    plt.close(fig)
    save_json(figdir/'figure_record.json',dict(core_claim='Spin histories after fitting the same early positions',
        layout='one axes; exactly two curves',sources=sources,units='SI',size_inches=[6.4,3.25],
        dpi=300,formats=['pdf','svg','png'],uncertainty_bands='none',
        near_coincident_curves=bool(30-minspin<.01)))


if __name__=='__main__':main()
