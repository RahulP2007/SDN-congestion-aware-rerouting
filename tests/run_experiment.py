#!/usr/bin/env python3
import os, sys, time
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'topology'))
from two_path import build
from mininet.log import setLogLevel

APP = os.path.join(BASE, 'app')
RES = os.path.join(BASE, 'results')


def show(title, path):
    print('--- ' + title)
    try:
        print(open(path).read().strip())
    except OSError:
        print('(missing)')


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'static'
    setLogLevel('warning')
    net = build()
    net.start()
    net.staticArp()
    h1, h2, h3 = net.get('h1', 'h2', 'h3')
    time.sleep(3)
    for port, name in ((5001, 'main'), (5002, 'bg')):
        h2.cmd('python3 %s/udp_receiver.py --port %d --idle 4 '
               '--out %s/%s_%s.csv > %s/%s_%s.txt 2>&1 &'
               % (APP, port, RES, label, name, RES, label, name))
    time.sleep(1)
    h3.cmd('(sleep 5; python3 %s/udp_sender.py --dst 10.0.0.2 --port 5002 '
           '--rate 1000 --size 1000 --duration 10 > %s/%s_bg_sender.txt '
           '2>&1) &' % (APP, RES, label))
    print(h1.cmd('python3 %s/udp_sender.py --dst 10.0.0.2 --port 5001 '
                 '--rate 500 --size 1000 --duration 20' % APP).strip())
    time.sleep(8)
    show('main flow (h1 -> h2)', '%s/%s_main.txt' % (RES, label))
    show('background flow (h3 -> h2)', '%s/%s_bg.txt' % (RES, label))
    show('background sender', '%s/%s_bg_sender.txt' % (RES, label))
    net.stop()


if __name__ == '__main__':
    main()
