"""Render saved validation outputs; no fitting or random simulation here."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=Path('results/data_validation'))
    args = parser.parse_args()
    records = json.loads((args.results/'predictions.json').read_text(encoding='utf-8'))
    summary = json.loads((args.results/'summary.json').read_text(encoding='utf-8'))
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.facecolor': '#f7f3ec', 'axes.facecolor': '#fffdf8',
                         'text.color': '#3d352e', 'axes.labelcolor': '#3d352e',
                         'savefig.facecolor': '#f7f3ec', 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    for ax, duration, color in zip(axes[0], (.05, .10), ('#b77351', '#7e896a')):
        models = ['M0','M1','M2','M3','M4','M5','M1_noise']
        data, labels = [], []
        for model in models:
            values = [r['error_m'] for r in records if r['duration_s'] == duration
                      and r['model'] == model and r['error_m'] is not None]
            if values:
                data.append(values)
                labels.append(f"{model.replace('_noise', '+noise')}\nn={len(values)}")
        boxes = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=.55)
        for box in boxes['boxes']:
            box.set(facecolor=color, alpha=.65)
        for median in boxes['medians']:
            median.set(color='#3d352e', linewidth=1.5)
        ax.set(ylabel='Plane crossing error (m)', title=f'DFL: observation window {duration:.2f} s')
        ax.grid(axis='y', alpha=.2)
    ax = axes[1, 0]
    for duration, marker, color in ((.05, 'o', '#b77351'), (.10, 's', '#7e896a')):
        group = summary['groups'][f'{duration}_M1_noise']
        levels = [.68, .95]
        observed = [group['conditional_coverage_'+str(int(x*100))]['rate'] for x in levels]
        ax.plot(levels, observed, marker=marker, color=color, label=f'{duration:.2f} s')
    ax.plot([0,1], [0,1], '--', color='#9d9285', label='Nominal')
    sigma = summary['configuration']['assumed_position_sigma_m']
    ax.set(xlim=(.6,1), ylim=(0,1.05), xlabel='Nominal region probability', ylabel='Observed coverage',
           title=f'M1 measurement-noise propagation: assumed sigma={sigma:g} m')
    ax.legend()
    ax.grid(alpha=.2)
    ax = axes[1, 1]
    for model, color in zip(('M0','M1','M2','M3','M4','M5'),
                             ('#b77351','#7e896a','#b29a60','#8c7970','#687e83','#997a82')):
        means = [summary['groups'][f'{d}_{model}']['errors'] for d in (.05,.10)]
        ax.plot([.05,.10], [x['mean_m'] if x else np.nan for x in means], '-o', color=color, label=model)
    ax.set(xlabel='Observation window (s)', ylabel='Mean crossing error (m)',
           title='All successful pairs per model (counts shown above)', xticks=[.05,.10])
    ax.legend(ncol=3)
    ax.grid(alpha=.2)
    fig.suptitle('Fixed DFL J03WOH ordinary-flight samples | virtual plane 11 m ahead\n'
                 '25 Hz native frames; Z treated as metres; M4/M5 spin fixed at 30 rad/s', fontsize=13)
    for suffix in ('png','svg'):
        fig.savefig(args.results/f'validation.{suffix}', dpi=220)
    svg_path = args.results/'validation.svg'
    svg_path.write_text('\n'.join(line.rstrip() for line in svg_path.read_text(encoding='utf-8').splitlines())+'\n',
                        encoding='utf-8')
    plt.close(fig)
    print(args.results/'validation.png')


if __name__ == '__main__':
    main()
