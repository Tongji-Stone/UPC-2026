"""Draw exactly two curves per coefficient, using precomputed coefficient tables."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def read(name):
    with (ROOT/'data'/name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def main():
    points, curves = read('comparison_points.csv'), read('formula_curves.csv')
    plt.rcParams.update({'font.family':'serif', 'font.serif':['Times New Roman'],
        'font.size':10, 'axes.labelsize':11, 'axes.spines.top':False,
        'axes.spines.right':False, 'xtick.direction':'out', 'ytick.direction':'out',
        'pdf.fonttype':42, 'ps.fonttype':42, 'svg.fonttype':'none',
        'savefig.facecolor':'white'})
    audit = {}
    for coefficient in ('CD','CL'):
        measured = [p for p in points if p['coefficient']==coefficient]
        formula = [p for p in curves if p['coefficient']==coefficient]
        fig, ax = plt.subplots(figsize=(5.8,3.35), layout='constrained')
        ax.plot([float(p['Sp']) for p in formula], [float(p['formula']) for p in formula],
                color='#0072B2', lw=1.8, label='Kiratidis–Leinweber (2018)')
        ax.plot([float(p['Sp']) for p in measured], [float(p['measured']) for p in measured],
                color='#D55E00', lw=1.5, ls='--', marker='o', ms=5,
                markerfacecolor='white', label='Asai et al. (2007), digitized')
        ax.set(xlabel=r'Spin parameter $Sp$', ylabel=r'$C_D$' if coefficient=='CD' else r'$C_L$')
        ax.set_xlim(.035,.24)
        ax.set_ylim((.15,.29) if coefficient=='CD' else (0,.32))
        ax.legend(frameon=False, loc='upper left', fontsize=9)
        assert len(ax.lines)==2 and len(ax.collections)==0
        for extension in ('pdf','svg','png'):
            fig.savefig(ROOT/f'{coefficient.lower()}_comparison.{extension}', dpi=300)
        audit[coefficient] = dict(curves=len(ax.lines), measured_points=len(measured),
            formula_samples=len(formula), physical_size_inches=[5.8,3.35], png_dpi=300,
            x_variable='Sp', fixed_Re=455172, shaded_regions=0)
        plt.close(fig)
    (ROOT/'data'/'figure_audit.json').write_text(json.dumps(audit,indent=2), encoding='utf-8')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':
    main()
