#!/usr/bin/env python3
import csv, os, statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, 'results')
rows = list(csv.DictReader(open(os.path.join(RES, 'matrix_results.csv'))))
bgs = sorted({int(r['bg']) for r in rows})


def stat(mode, bg, col):
    v = [float(r[col]) for r in rows
         if r['mode'] == mode and int(r['bg']) == bg and r[col] != '']
    return statistics.mean(v), min(v), max(v)


panels = [('main_loss', 'main flow loss (%)'),
          ('main_delay', 'main flow delay (ms)'),
          ('total_mbps', 'combined throughput (Mbps)')]
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
w = 0.38
for ax, (col, title) in zip(axes, panels):
    for k, mode in enumerate(('static', 'adaptive')):
        xs = [i + (k - 0.5) * w for i in range(len(bgs))]
        m, lo, hi = [], [], []
        for bg in bgs:
            mean, a, b = stat(mode, bg, col)
            m.append(mean)
            lo.append(mean - a)
            hi.append(b - mean)
        ax.bar(xs, m, w, yerr=[lo, hi], capsize=3, label=mode)
    ax.set_xticks(range(len(bgs)))
    ax.set_xticklabels(['%d Mbps' % b for b in bgs])
    ax.set_xlabel('background load')
    ax.set_title(title)
axes[0].legend()
plt.tight_layout()
out = os.path.join(RES, 'matrix_comparison.png')
plt.savefig(out)
print('saved', out)
