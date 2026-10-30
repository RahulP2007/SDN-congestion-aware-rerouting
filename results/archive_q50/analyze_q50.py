#!/usr/bin/env python3
import csv, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(os.path.abspath(__file__))
RATE = 500   # main flow packets per second


def load(name):
    rows = []
    with open(os.path.join(RES, name)) as f:
        for x in csv.DictReader(f):
            rows.append((int(x['seq']), float(x['send_time'])))
    return rows


def per_second(rows):
    t0 = min(r[1] for r in rows)
    n = (max(r[0] for r in rows) + 1) // RATE
    got = [0] * n
    for seq, _ in rows:
        if seq // RATE < n:
            got[seq // RATE] += 1
    return t0, [100.0 * (RATE - g) / RATE for g in got]


def reroute_time():
    try:
        for line in open(os.path.join(RES, 'events.log')):
            if 'REROUTED' in line:
                return float(line.split()[0])
    except OSError:
        pass
    return None


def window(loss):
    bad = [i for i, v in enumerate(loss) if v > 1.0]
    return (bad[0], bad[-1], len(bad)) if bad else None


s_t0, s_loss = per_second(load('static_q50_main.csv'))
a_t0, a_loss = per_second(load('adaptive_q50_main.csv'))
rt = reroute_time()
r_sec = rt - a_t0 if rt else None

print('sec  static_loss%  adaptive_loss%')
for i in range(min(len(s_loss), len(a_loss))):
    print('%3d  %11.1f  %13.1f' % (i, s_loss[i], a_loss[i]))
for name, loss in (('static', s_loss), ('adaptive', a_loss)):
    w = window(loss)
    if w:
        print('%s: loss in seconds %d to %d (%d lossy seconds)' % ((name,) + w))
    else:
        print('%s: no lossy seconds' % name)
if r_sec is not None:
    print('reroute happened at %.1f s after the main flow started' % r_sec)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 4))
    plt.plot(range(len(s_loss)), s_loss, label='static routing')
    plt.plot(range(len(a_loss)), a_loss, label='adaptive routing')
    if r_sec is not None:
        plt.axvline(r_sec, color='gray', linestyle='--', label='reroute')
    plt.xlabel('time since main flow started (s)')
    plt.ylabel('main flow packet loss (%)')
    plt.legend()
    plt.tight_layout()
    out = os.path.join(RES, 'loss_comparison.png')
    plt.savefig(out)
    print('saved', out)
except ImportError:
    print('matplotlib missing: skipped the graph')
