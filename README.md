# SDN congestion-aware rerouting

An OpenFlow 1.3 controller (OS-Ken) that watches link load on a two-path
Mininet topology and moves a flow to the idle path when its path congests.
It is compared against static routing, where everything stays on path A.

## Topology

```
h1 (main flow, 4 Mbps) --+          +-- s2 --+
                          s1 -------+        +-- s4 -- h2
h3 (background flow) ----+          +-- s3 --+
```

- Path A: s1-s2-s4. Path B: s1-s3-s4. Each link is 10 Mbps with a 50-packet queue.
- Host links are 100 Mbps.
- Everything starts on path A.

## Controllers (`controller/`)

| File | Behaviour |
|---|---|
| `static_route.py` | Fixed destination-based rules, path A only. |
| `adaptive_route.py` | Same start, but polls s1 port stats every 1 s. If the main flow's path stays at or above 8.5 Mbps (85% of the link) for 2 readings in a row and the other path is below 4.25 Mbps, it installs a higher-priority rule for h1 to h2 on the other path. |
| `basic_switch.py` | Learning switch (MAC to port table). Not used by the experiments. |
| `run_controller.py` | Launcher for OS-Ken apps. |

The adaptive controller reads `results/mode`. If it contains `static`, rerouting is disabled. The test runner writes this file, so one controller process serves both modes.

## Running

```bash
# terminal 1: controller (adaptive handles both modes)
python3 controller/run_controller.py controller/adaptive_route.py

# terminal 2: experiments (need root for Mininet)
sudo python3 tests/run_matrix.py            # full matrix, 2 modes x 3 loads x 3 repeats
sudo python3 tests/run_matrix.py quick      # one 8 Mbps run per mode
sudo python3 tests/run_timeline.py 8        # single static + adaptive pair, keeps events logs
python3 tests/plot_matrix.py                # results/matrix_comparison.png
python3 tests/analyze_timeline.py 8 9       # results/timeline_comparison.png, timeline_summary.csv
```

Each run: main flow h1 to h2 at 500 pps x 1000 B (4 Mbps) for 20 s. Background flow h3 to h2 starts at t = 5 s, runs 10 s, at 4, 8 or 10 Mbps. Traffic is UDP (`app/udp_sender.py`, `app/udp_receiver.py`), which measures loss, delay, jitter and throughput.

## Results (mean of 3 repeats, `results/matrix_results.csv`)

| Background | Mode | Main loss % | BG loss % | Main delay ms | Combined Mbps | Reaction s |
|---|---|---|---|---|---|---|
| 4 Mbps | static | 0.08 | 0.12 | 3.9 | 7.99 | - |
| 4 Mbps | adaptive | 0.60 | 0.73 | 6.7 | 7.95 | - |
| 8 Mbps | static | 20.31 | 22.05 | 22.6 | 9.39 | - |
| 8 Mbps | adaptive | 4.07 | 9.30 | 8.6 | 11.09 | 3.2 |
| 10 Mbps | static | 25.42 | 34.55 | 20.8 | 9.51 | - |
| 10 Mbps | adaptive | 7.09 | 17.58 | 6.0 | 11.93 | 2.9 |

Reaction is the time from background start to the reroute. The timeline run at 8 Mbps (`results/timeline_summary.csv`, `timeline_comparison.png`) shows congestion detected after 2.6 s and recovery to under 1% loss in 3.0 s with adaptive routing. Static routing took 11.0 s to recover, i.e. only after the background flow stopped.

Adaptive routing cuts main-flow loss by 4-5x under congestion and delay by about 2-3x, and uses both paths (combined throughput above the 10 Mbps of a single path).

## Notes and limitations

- **4 Mbps (no congestion):** adaptive looks slightly worse (0.6% vs 0.08% loss, 6.7 vs 3.9 ms). No reroute fired in these runs (combined load 8 Mbps is below the 8.5 Mbps threshold), and per-second delay is spiky in both modes (Mininet scheduling noise, spikes of 10-30 ms in both). With 3 repeats this is within noise, not a controller effect. More repeats would confirm it.
- Only the main flow (h1 to h2) is rerouted. The background flow stays on path A, so its loss stays high (about 18% at 10 Mbps). The combined load of about 14 Mbps cannot fit on one 10 Mbps path anyway.
- Single reroute per run: no reroute back to path A and no hysteresis beyond the 2-reading rule.
- Detection granularity is the 1 s poll period, so reaction time is 2-4 s.
- `results/archive_q50/` holds an earlier single-run comparison (queue size 50) kept for reference. It is superseded by the matrix.
