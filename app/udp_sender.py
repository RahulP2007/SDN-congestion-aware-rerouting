#!/usr/bin/env python3
import argparse, socket, struct, time

HDR = struct.Struct('!Id')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dst', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=5001)
    ap.add_argument('--rate', type=float, default=500, help='packets/second')
    ap.add_argument('--size', type=int, default=1000, help='bytes/packet')
    ap.add_argument('--duration', type=float, default=10)
    a = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    n = int(a.rate * a.duration)
    pad = b'x' * (a.size - HDR.size)
    start = time.time()
    for seq in range(n):
        wait = start + seq / a.rate - time.time()
        if wait > 0:
            time.sleep(wait)
        s.sendto(HDR.pack(seq, time.time()) + pad, (a.dst, a.port))
    el = time.time() - start
    print('sent %d packets in %.1f s (%.2f Mbps offered, %.2f Mbps actual)' %
          (n, el, a.rate * a.size * 8 / 1e6, n * a.size * 8 / el / 1e6))


if __name__ == '__main__':
    main()
