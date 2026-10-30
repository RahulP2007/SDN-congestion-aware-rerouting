#!/usr/bin/env python3
import csv, os, re, statistics, sys, time
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'topology'))
from two_path import build
from mininet.log import setLogLevel

APP = os.path.join(BASE, 'app')
RES = os.path.join(BASE, 'results')
OUT = os.path.join(RES, 'matrix')
EVENTS = os.path.join(RES, 'events.log')
MODEFILE = os.path.join(RES, 'mode')

MODES = ['static', 'adaptive']
BG_RATES = [4, 8, 10]     # Mbps of background traffic
REPEATS = 3
if 'quick' in sys.argv:
    BG_RATES, REPEATS = [8], 1


def parse(path):
    d = {}
    try:
        t = open(path).read()
    except OSError:
        return d
    m = re.search(r'received (\d+) of (\d+)\s+loss ([\d.]+)%', t)
    if m:
        d['loss'] = float(m.group(3))
    m = re.search(r'avg delay ([\d.]+) ms\s+jitter ([\d.]+) ms\s+'
                  r'throughput ([\d.]+) Mbps', t)
    if m:
        d['delay'], d['jitter'], d['mbps'] = map(float, m.groups())
    return d


def reroute_ts():
    try:
        for line in open(EVENTS):
            if 'REROUTED' in line:
                return float(line.split()[0])
    except OSError:
        pass
    return None


def run_once(mode, bg, rep):
    label = '%s_%dmbps_r%d' % (mode, bg, rep)
    open(MODEFILE, 'w').write(mode)
    if os.path.exists(EVENTS):
        os.remove(EVENTS)
    net = build()
    net.start()
    net.staticArp()
    h1, h2, h3 = net.get('h1', 'h2', 'h3')
    time.sleep(3)
    for port, name in ((5001, 'main'), (5002, 'bg')):
        h2.cmd('python3 %s/udp_receiver.py --port %d --idle 4 '
               '--out %s/%s_%s.csv > %s/%s_%s.txt 2>&1 &'
               % (APP, port, OUT, label, name, OUT, label, name))
    time.sleep(1)
    pps = bg * 125
    t_launch = time.time()
    h3.cmd('(sleep 5; python3 %s/udp_sender.py --dst 10.0.0.2 --port 5002 '
           '--rate %d --size 1000 --duration 10 > %s/%s_bgsend.txt 2>&1) &'
           % (APP, pps, OUT, label))
    h1.cmd('python3 %s/udp_sender.py --dst 10.0.0.2 --port 5001 '
           '--rate 500 --size 1000 --duration 20' % APP)
    time.sleep(8)
    net.stop()
    main = parse('%s/%s_main.txt' % (OUT, label))
    bgd = parse('%s/%s_bg.txt' % (OUT, label))
    actual = ''
    try:
        m = re.search(r'([\d.]+) Mbps actual',
                      open('%s/%s_bgsend.txt' % (OUT, label)).read())
        actual = float(m.group(1)) if m else ''
    except OSError:
        pass
    rt = reroute_ts()
    return {'mode': mode, 'bg': bg, 'rep': rep,
            'main_loss': main.get('loss', ''), 'bg_loss': bgd.get('loss', ''),
            'main_delay': main.get('delay', ''),
            'main_jitter': main.get('jitter', ''),
            'total_mbps': round(main.get('mbps', 0) + bgd.get('mbps', 0), 2),
            'bg_actual': actual,
            'reaction_s': round(rt - (t_launch + 5), 1) if rt else ''}


def avg(vals):
    vals = [v for v in vals if v != '']
    return round(statistics.mean(vals), 2) if vals else '-'


def main():
    setLogLevel('warning')
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for rep in range(1, REPEATS + 1):
        for bg in BG_RATES:
            for mode in MODES:
                r = run_once(mode, bg, rep)
                rows.append(r)
                print('done %s bg=%d run=%d: main loss %s%%  bg sent %s Mbps'
                      % (mode, bg, rep, r['main_loss'], r['bg_actual']),
                      flush=True)
    with open(os.path.join(RES, 'matrix_results.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print()
    print('mode      bg_Mbps  main_loss%  bg_loss%  delay_ms  total_Mbps  '
          'reaction_s')
    for bg in BG_RATES:
        for mode in MODES:
            sel = [r for r in rows if r['mode'] == mode and r['bg'] == bg]
            print('%-9s %7d  %10s  %8s  %8s  %10s  %10s' % (
                mode, bg, avg([r['main_loss'] for r in sel]),
                avg([r['bg_loss'] for r in sel]),
                avg([r['main_delay'] for r in sel]),
                avg([r['total_mbps'] for r in sel]),
                avg([r['reaction_s'] for r in sel])))
    print('saved', os.path.join(RES, 'matrix_results.csv'))


if __name__ == '__main__':
    main()
