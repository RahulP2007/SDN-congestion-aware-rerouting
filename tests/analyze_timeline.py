#!/usr/bin/env python3
"""Recovery time and throughput-vs-time: one static run vs one adaptive run.
Usage: python3 tests/analyze_timeline.py [bg_mbps] [rep]     (default 8 9)
"""
import csv, math, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, 'results')
MAT = os.path.join(RES, 'matrix')
RATE = 500        # main flow packets per second
LOSS_OK = 1.0     # a second with loss below this (%) counts as recovered
BG = int(sys.argv[1]) if len(sys.argv) > 1 else 8
REP = int(sys.argv[2]) if len(sys.argv) > 2 else 9


def load(label, name):
    rows = []
    with open(os.path.join(MAT, '%s_%s.csv' % (label, name))) as f:
        for r in csv.DictReader(f):
            rows.append((float(r['recv_time']), int(r['seq']),
                         float(r['send_time']), int(r['bytes'])))
    return rows


def events(label):
    ev = {}
    try:
        for line in open(os.path.join(MAT, label + '_events.log')):
            ts, _, text = line.partition(' ')
            if text.startswith('CONGESTION_DETECTED'):
                ev.setdefault('detect', float(ts))
            elif text.startswith('REROUTED'):
                ev.setdefault('reroute', float(ts))
    except OSError:
        pass
    return ev


def analyse(mode):
    label = '%s_%dmbps_r%d' % (mode, BG, REP)
    main, bg, ev = load(label, 'main'), load(label, 'bg'), events(label)
    t0 = min(r[2] for r in main)          # main flow starts
    bg_start = min(r[2] for r in bg)      # congestion starts
    bg_len = max(r[2] for r in bg) - bg_start

    # main-flow throughput per second (by receive time)
    bins = {}
    for recv, _, _, size in main:
        k = math.floor(recv - bg_start)
        bins[k] = bins.get(k, 0) + size * 8 / 1e6
    keys = sorted(bins)[1:-1]             # drop partial first/last second
    thr = [(k + 0.5, bins[k]) for k in keys]
    during = [bins[k] for k in keys if 0 <= k < int(bg_len)]

    # main-flow loss per second (by sequence number)
    n = (max(r[1] for r in main) + 1) // RATE
    got = [0] * n
    for _, seq, _, _ in main:
        if seq // RATE < n:
            got[seq // RATE] += 1
    loss = [100.0 * (RATE - g) / RATE for g in got]
    loss_pts = [(t0 + i + 0.5 - bg_start, loss[i]) for i in range(n)]

    # recovery time = congestion start until the last lossy second ends
    # recovery = first second after congestion starts that begins two
    # consecutive seconds with loss below LOSS_OK (so one stray blip
    # later in the run does not count)
    recovery = None
    for i in range(n - 1):
        if (t0 + i + 1 > bg_start and loss[i] < LOSS_OK
                and loss[i + 1] < LOSS_OK):
            recovery = max(0.0, t0 + i - bg_start)
            break

    total = max(r[1] for r in main) + 1
    return {'mode': mode, 'thr': thr, 'loss_pts': loss_pts,
            'bg_len': bg_len,
            'detect': ev['detect'] - bg_start if 'detect' in ev else None,
            'reroute': ev['reroute'] - bg_start if 'reroute' in ev else None,
            'recovery': recovery,
            'avg_thr': sum(during) / len(during) if during else 0.0,
            'loss': 100.0 * (1 - len(main) / total),
            'delay': sum((r[0] - r[2]) * 1000 for r in main) / len(main)}


def fmt(v):
    return '-' if v is None else '%.1f' % v


def main():
    res = [analyse('static'), analyse('adaptive')]
    print('background %d Mbps, run %d. Time 0 = congestion starts' % (BG, REP))
    head = ['mode', 'detect_s', 'reroute_s', 'recovery_s',
            'main_thr_Mbps', 'loss_pct', 'delay_ms']
    print('%-9s %9s %10s %11s %14s %9s %9s' % tuple(head))
    rows = []
    for r in res:
        row = [r['mode'], fmt(r['detect']), fmt(r['reroute']),
               fmt(r['recovery']), '%.2f' % r['avg_thr'],
               '%.2f' % r['loss'], '%.2f' % r['delay']]
        rows.append(row)
        print('%-9s %9s %10s %11s %14s %9s %9s' % tuple(row))
    with open(os.path.join(RES, 'timeline_summary.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)

    fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for r in res:
        ax[0].plot(*zip(*r['thr']), marker='o', label=r['mode'])
        ax[1].plot(*zip(*r['loss_pts']), marker='o', label=r['mode'])
    ad = res[1]
    for a in ax:
        a.axvline(0, color='k', linestyle='--', label='congestion starts')
        if ad['reroute'] is not None:
            a.axvline(ad['reroute'], color='gray', linestyle='--',
                      label='reroute (adaptive)')
        a.axvline(res[0]['bg_len'], color='gray', linestyle=':',
                  label='background ends')
        a.grid(alpha=0.3)
    ax[0].set_ylabel('main flow throughput (Mbps)')
    ax[1].set_ylabel('main flow packet loss (%)')
    ax[1].set_xlabel('time since congestion started (s)')
    ax[0].legend()
    plt.tight_layout()
    out = os.path.join(RES, 'timeline_comparison.png')
    plt.savefig(out)
    print('saved', out)
    print('saved', os.path.join(RES, 'timeline_summary.csv'))


if __name__ == '__main__':
    main()
