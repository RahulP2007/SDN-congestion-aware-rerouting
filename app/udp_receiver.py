#!/usr/bin/env python3
import argparse, csv, socket, struct, time

HDR = struct.Struct('!Id')   # sequence number, send timestamp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=5001)
    ap.add_argument('--idle', type=float, default=3.0,
                    help='stop after this many seconds of silence')
    ap.add_argument('--out', default='recv_log.csv')
    a = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', a.port))
    s.settimeout(1.0)
    rows, last = [], time.time()
    print('listening on UDP', a.port)
    try:
        while True:
            try:
                data, _ = s.recvfrom(65535)
            except socket.timeout:
                if rows and time.time() - last > a.idle:
                    break
                continue
            now = time.time()
            last = now
            if len(data) < HDR.size:
                continue
            seq, ts = HDR.unpack(data[:HDR.size])
            rows.append((now, seq, ts, len(data)))
    except KeyboardInterrupt:
        pass

    if not rows:
        print('nothing received')
        return
    with open(a.out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['recv_time', 'seq', 'send_time', 'bytes'])
        w.writerows(rows)

    got = len(rows)
    expected = max(r[1] for r in rows) + 1
    delays = [(r[0] - r[2]) * 1000 for r in rows]
    jitter = (sum(abs(delays[i] - delays[i - 1])
                  for i in range(1, len(delays))) / max(1, len(delays) - 1))
    span = rows[-1][0] - rows[0][0]
    mbps = sum(r[3] for r in rows) * 8 / span / 1e6 if span > 0 else 0
    print('received %d of %d  loss %.2f%%' %
          (got, expected, 100 * (1 - got / expected)))
    print('avg delay %.2f ms  jitter %.2f ms  throughput %.2f Mbps' %
          (sum(delays) / got, jitter, mbps))


if __name__ == '__main__':
    main()
