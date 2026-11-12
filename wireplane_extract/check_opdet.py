#!/usr/bin/env python3
"""Summary and plot of the optical-detector waveforms in a wireplane HDF5 file.

  python3 check_opdet.py <file.h5> [--event 0] [--plots plot_dir]

Prints, per opdet group, the readout windows by length, channel range and time, the
number of saturated samples, and compares the time of the light in the beam window with
the neutrino interaction time from the particle table.
"""
import argparse
import os

import h5py
import numpy as np

TICK_US = 0.015625       # optical clock, 64 MHz
TRIGGER_US = 4050.0      # electronics time of the trigger = Geant4 t = 0


def windows(o):
    ch, ns, off, ts = (o[k][()] for k in ("channel", "nsamples", "offset", "timestamp"))
    adc = o["adc"][()]
    return ch, ns, ts, [adc[a:a + n] for a, n in zip(off, ns)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("h5"); ap.add_argument("--event", type=int, default=0)
    ap.add_argument("--plots", default=None)
    args = ap.parse_args()
    g = h5py.File(args.h5, "r")["event_%06d" % args.event]
    od = g["opdet"]
    data = {}
    for name in od:
        ch, ns, ts, wf = windows(od[name])
        data[name] = (ch, ns, ts, wf)
        print("%s  (%s): %d waveforms" % (name, od[name].attrs["tag"], len(ch)))
        for n in np.unique(ns):
            m = ns == n
            sat = sum(int((w >= 4095).sum()) for w, k in zip(wf, m) if k)
            print("   %5d-sample windows: %4d on channels %d-%d (%d PMTs), t - trigger %.1f to %.1f us, "
                  "saturated samples (>= 4095): %d" % (n, m.sum(), ch[m].min(), ch[m].max(),
                                                       len(np.unique(ch[m] % 100)), ts[m].min() - TRIGGER_US,
                                                       ts[m].max() - TRIGGER_US, sat))
    # light in the beam window vs the neutrino time
    ch, ns, ts, wf = data["beam_highgain"]
    beam = np.array([w.astype(np.float64) - np.median(w[:100]) for w, n in zip(wf, ns) if n == ns.max()])
    tot = beam.sum(0)
    t_beam = (ts[0] - TRIGGER_US) + np.arange(len(tot)) * TICK_US
    thr = 0.1 * tot.max()
    t_light = t_beam[np.argmax(tot > thr)]
    msg = "beam window: summed high-gain light rises (10%% of peak) at %.3f us after the trigger" % t_light
    if "particles" in g:
        p = g["particles"]
        nu = (p["origin"][()] == 1) & (p["mother"][()] == 0)
        if nu.any():
            msg += "; neutrino primaries are made at Geant4 t = %.3f us" % (p["t_start"][()][nu].min() * 1e-3)
    print(msg)
    if "beam_satcorr" in data and "cosmic_satcorr" in data:
        for a, b in (("beam_highgain", "beam_satcorr"), ("cosmic_highgain", "cosmic_satcorr")):
            wa, wb = data[a][3], data[b][3]
            nd = sum(1 for x, y in zip(wa, wb) if len(x) != len(y) or (x != y).any())
            print("%s vs %s: %d of %d waveforms differ; max ADC %d -> %d" % (
                a, b, nd, len(wa), max(w.max() for w in wa), max(w.max() for w in wb)))

    if args.plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        os.makedirs(args.plots, exist_ok=True)
        fig, (a0, a1) = plt.subplots(1, 2, figsize=(15, 5.5), constrained_layout=True)
        for w in beam:
            a0.plot(t_beam, w, color="#9aa3ad", lw=0.6)
        a0.plot(t_beam, tot / 8.0, color="#2a6fb0", lw=1.6, label="sum of the 32 PMTs / 8")
        a0.plot([], [], color="#9aa3ad", lw=0.6, label="one PMT")
        a0.set_xlabel("time after the trigger (us)"); a0.set_ylabel("ADC above baseline (high gain)")
        a0.set_title("Beam window: %d samples on every PMT" % beam.shape[1]); a0.legend(frameon=False)
        for name, color, label in (("cosmic_highgain", "#2a6fb0", "high gain"),
                                   ("beam_lowgain", "#d9480f", "low gain")):
            ch, ns, ts, wf = data[name]
            m = ns < 1000
            off = 0.0 if name == "cosmic_highgain" else 0.3
            a1.scatter((ts[m] - TRIGGER_US) * 1e-3, ch[m] % 100 + off, s=14, color=color,
                       label="%s (%d windows)" % (label, m.sum()))
        a1.axvspan(0, beam.shape[1] * TICK_US * 1e-3, color="#c9ccd1", lw=0)
        a1.set_xlabel("window start, time after the trigger (ms)"); a1.set_ylabel("PMT")
        a1.set_title("Self-triggered 40-sample windows")
        a1.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
        out = os.path.join(args.plots, "event_%06d_opdet.png" % args.event)
        fig.savefig(out, dpi=110); print("wrote", out)


if __name__ == "__main__":
    main()
