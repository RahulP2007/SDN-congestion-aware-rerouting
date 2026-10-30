#!/usr/bin/env python3
"""Run ONE static and ONE adaptive experiment and keep each run's events log.
Usage (controller must already be running in another terminal):
    sudo python3 tests/run_timeline.py [bg_mbps]     # default 8
"""
import os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_matrix as rm
from mininet.log import setLogLevel

REP = 9


def main():
    setLogLevel('warning')
    os.makedirs(rm.OUT, exist_ok=True)
    bg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8
    for mode in ('static', 'adaptive'):
        print('running %s, background %d Mbps ...' % (mode, bg), flush=True)
        r = rm.run_once(mode, bg, REP)
        label = '%s_%dmbps_r%d' % (mode, bg, REP)
        if os.path.exists(rm.EVENTS):
            shutil.copy(rm.EVENTS,
                        os.path.join(rm.OUT, label + '_events.log'))
        print('  main loss %s%%  delay %s ms  reaction %s s'
              % (r['main_loss'], r['main_delay'], r['reaction_s']))
    print('done. files are in', rm.OUT)


if __name__ == '__main__':
    main()
