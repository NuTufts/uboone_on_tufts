#!/usr/bin/env python3
"""How completely do the 3D energy deposits label what is seen in the wire-plane images?

Projects the true energy deposits (edep: x, y, z, t) into (plane, tick, wire) with
pysbn-detinfo's DetInfo.project_to_image -- space-charge displacement + drift + deposit
time -- and compares the projected labels with the signal pixels of the deconvolved and
raw images.

  1. projection check   projected deposits vs the SimChannel charge of the same track
  2. coverage           fraction of signal pixels that have a projected deposit within
                        +-dw wires and +-dt ticks, for a list of tolerances; the same
                        with SimChannel as the label source (the best any label can do)
  3. label efficiency   fraction of projected electrons that have a signal pixel nearby,
                        split into live and dead channels
  4. plot               neutrino-region zoom: signal pixels covered / not covered

Signal pixels:
  deconvolved   wire/signal > --wire-threshold on channels that are not dead
  raw           |adc - baseline| > --raw-nsigma * (sigma-clipped channel noise RMS)

Run in the pointcept container (python3, numpy, scipy, h5py, matplotlib):
  export PYSBN_DETINFO_PATH=/cluster/tufts/wongjiradlab/larbys/detinfo
  python3 check_edep_coverage.py test_output/wireplane_test_nue.h5 --plots test_output/coverage_plots
"""
import argparse
import os
import sys

import h5py
import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
PLANES = "UVY"


def load_detinfo(src, detector, version):
    if src:
        sys.path.insert(0, src)
    os.environ.setdefault("PYSBN_DETINFO_PATH", "/cluster/tufts/wongjiradlab/larbys/detinfo")
    from pysbn_detinfo import load
    return load(detector, version)


def rasterize(channel, tick, nch, nt, weight=None):
    """Sum of weight (or a count) per (channel, tick) pixel; out-of-range rows dropped."""
    ok = (channel >= 0) & (channel < nch) & (tick >= 0) & (tick < nt)
    flat = channel[ok].astype(np.int64) * nt + tick[ok].astype(np.int64)
    w = None if weight is None else weight[ok]
    return np.bincount(flat, weights=w, minlength=nch * nt).reshape(nch, nt)


def dilate(mask, dw, dt):
    if dw == 0 and dt == 0:
        return mask
    return ndimage.maximum_filter(mask.view(np.uint8), size=(2 * dw + 1, 2 * dt + 1),
                                  mode="constant", cval=0).astype(bool)


def centroid_by_track(ids, w, a, b):
    o = np.argsort(ids, kind="stable")
    ids, w, a, b = ids[o], w[o], a[o], b[o]
    u, i0 = np.unique(ids, return_index=True)
    sw = np.add.reduceat(w, i0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return u, sw, np.add.reduceat(w * a, i0) / sw, np.add.reduceat(w * b, i0) / sw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("h5")
    ap.add_argument("--event", type=int, default=0)
    ap.add_argument("--detinfo-src", default=os.path.join(HERE, "..", "external", "pysbn-detinfo", "src"),
                    help="pysbn-detinfo src directory ('' if it is installed)")
    ap.add_argument("--detector", default="uboone")
    ap.add_argument("--detinfo-version", default=None)
    ap.add_argument("--tick-offset", type=float, default=10.0,
                    help="raw tick of the charge arrival = projected tick + offset "
                         "(WireCell simulation of uboonecode v08: 10.1, measured in step 1)")
    ap.add_argument("--wire-threshold", type=float, default=5.0)
    ap.add_argument("--raw-nsigma", type=float, default=5.0)
    ap.add_argument("--tolerances", default="0x0,1x2,1x5,2x10,3x20",
                    help="comma list of <dw>x<dt>: half-widths in wires and ticks")
    ap.add_argument("--plots", default=None, help="directory for the plot")
    args = ap.parse_args()
    tols = [tuple(int(v) for v in s.split("x")) for s in args.tolerances.split(",")]

    di = load_detinfo(args.detinfo_src, args.detector, args.detinfo_version)
    f = h5py.File(args.h5, "r")
    g = f["event_%06d" % args.event]
    first = [int(v) for v in f.attrs["plane_first_channel"]]
    nwires = [int(v) for v in f.attrs["plane_nwires"]]
    tdc_off = int(f.attrs["simch_tdc_to_tick_offset"])
    wire_t0 = int(f.attrs["wire_tick0_raw_tick"])
    print("file %s event %d\ndetinfo %s %s (simulation: uboonecode %s)" % (
        args.h5, args.event, di.detector, di.version, f.attrs["uboonecode_version"]))

    # ---------------------------------------------------------------- inputs
    e = g["edep"]
    mid = 0.5 * (e["start_xyz"][()].astype(np.float64) + e["end_xyz"][()])
    tmid = 0.5 * (e["t_start"][()] + e["t_end"][()])
    etid = np.abs(e["track_id"][()])
    if "edep_sce" in g:
        ne = g["edep_sce/num_electrons"][()].astype(np.float64)       # after recombination
        sce_start = g["edep_sce/start_xyz"][()].astype(np.float64)
    else:
        ne, sce_start = e["energy"][()].astype(np.float64), None
    sc = g["simch"]
    sch, stdc, sq = sc["channel"][()], sc["tdc"][()], sc["num_electrons"][()].astype(np.float64)
    stid = np.abs(sc["track_id"][()])
    nch, nt = g["rawdigit/adc"].shape
    dead = g["chstatus/dead"][()].astype(bool) if "chstatus" in g else np.zeros(nch, bool)
    print("deposits %d   SimChannel IDEs %d   dead channels %d (U %d, V %d, Y %d)" % (
        len(mid), len(sch), dead.sum(), *[dead[first[p]:first[p] + nwires[p]].sum() for p in range(3)]))

    # ---------------------------------------------------------------- 1. projection check
    pr = di.project_to_image(mid, tmid, sce=True)
    pr0 = di.project_to_image(mid, tmid, sce=False)
    print("\n== 1. projection check ==")
    if sce_start is not None:
        start = e["start_xyz"][()].astype(np.float64)
        pos, _, tp = di.drifted_position(start)
        d = (pos - sce_start)[tp >= 0]
        print("space-charge displacement (step start points): mean |shift| %.2f, %.2f, %.2f cm; "
              "pysbn-detinfo minus the simulation's ShiftEdepSCE positions, max |d| = %.1e, %.1e, %.1e cm"
              % (*np.abs(sce_start - start).mean(0), *np.abs(d).max(0)))
    print("per-track charge centroid, SimChannel minus projected deposits (tracks with > 2e4 e-):")
    print("  %-5s %-8s %7s %22s %26s" % ("plane", "SCE", "tracks", "wire: median (IQR)", "tick: median (IQR)"))
    meas_off = []
    for p in range(3):
        m = (sch >= first[p]) & (sch < first[p] + nwires[p])
        u2, w2, a2, b2 = centroid_by_track(stid[m], sq[m], (sch[m] - first[p]).astype(float),
                                           (stdc[m] - tdc_off).astype(float))
        for name, r in (("on", pr), ("off", pr0)):
            ok = r["in_image"][:, p]
            u1, w1, a1, b1 = centroid_by_track(etid[ok], ne[ok], r["wire_coordinate"][ok, p], r["tick"][ok, p])
            _, i1, i2 = np.intersect1d(u1, u2, return_indices=True)
            # keep tracks whose charge is fully inside the readout on both sides
            big = (w2[i2] > 2e4) & (w1[i1] > 0.5 * w2[i2]) & (w1[i1] < 2.0 * w2[i2])
            dw, dt = (a2[i2] - a1[i1])[big], (b2[i2] - b1[i1])[big]
            iqr = lambda v: np.subtract(*np.percentile(v, [75, 25]))
            print("  %-5s %-8s %7d %12.3f (%6.3f) %16.2f (%6.2f)" % (
                PLANES[p], name, big.sum(), np.median(dw), iqr(dw), np.median(dt), iqr(dt)))
            if name == "on":
                meas_off.append(np.median(dt))
    print("measured tick offset (SCE on): U %.2f  V %.2f  Y %.2f   [using --tick-offset %.1f]" % (
        *meas_off, args.tick_offset))

    # ---------------------------------------------------------------- label maps (raw tick frame)
    pr = di.project_to_image(mid, tmid, sce=True, tick_offset=args.tick_offset)
    lab_ch, lab_tk, lab_w = [], [], []
    for p in range(3):
        ok = pr["in_image"][:, p]
        lab_ch.append(pr["channel"][ok, p]); lab_tk.append(pr["row"][ok, p]); lab_w.append(ne[ok])
    lab_ch, lab_tk, lab_w = np.concatenate(lab_ch), np.concatenate(lab_tk), np.concatenate(lab_w)
    edep_q = rasterize(lab_ch, lab_tk, nch, nt, lab_w)
    simch_q = rasterize(sch, stdc - tdc_off, nch, nt, sq)
    edep_m, simch_m = edep_q > 0, simch_q > 0
    planes_of = np.zeros(nch, dtype=np.int8)
    for p in range(3):
        planes_of[first[p]:first[p] + nwires[p]] = p
    tot = ne.sum()
    print("\ndeposit electrons: %.3e total; inside the readout window and on a wire: U %.3f V %.3f Y %.3f" % (
        tot, *[ne[pr["in_image"][:, p]].sum() / tot for p in range(3)]))
    print("SimChannel electrons / projected in-image deposit electrons: " + "  ".join(
        "%s %.3f" % (PLANES[p], simch_q[planes_of == p].sum() / max(edep_q[planes_of == p].sum(), 1))
        for p in range(3)))

    # ---------------------------------------------------------------- signal pixels
    wsig = g["wire/signal"][()]
    wnt = wsig.shape[1]
    sig_wire = np.zeros((nch, nt), dtype=bool)
    sig_wire[:, wire_t0:wire_t0 + wnt] = wsig > args.wire_threshold
    sig_wire[dead] = False
    wamp = np.zeros((nch, nt), dtype=np.float32)
    wamp[:, wire_t0:wire_t0 + wnt] = np.where(wsig > args.wire_threshold, wsig, 0)
    wamp[dead] = 0
    del wsig
    adc = g["rawdigit/adc"][()].astype(np.float32)
    base = np.median(adc, axis=1, keepdims=True)
    adc -= base
    # channel noise RMS: sigma-clipped (the MAD of integer ADC values is too coarse)
    rms = 1.4826 * np.median(np.abs(adc), axis=1, keepdims=True) + 1.0
    for _ in range(3):
        keep = np.abs(adc) < 4.0 * rms
        rms = np.sqrt((adc * adc * keep).sum(1, keepdims=True) / np.maximum(keep.sum(1, keepdims=True), 1))
    del keep
    sig_raw = np.abs(adc) > args.raw_nsigma * np.maximum(rms, 0.5)
    ramp = np.where(sig_raw, np.abs(adc), 0)
    del adc
    # the deconvolved product only spans raw ticks [wire_t0, wire_t0 + wnt)
    in_wire_window = np.zeros(nt, dtype=bool); in_wire_window[wire_t0:wire_t0 + wnt] = True

    # ---------------------------------------------------------------- 2. coverage
    print("\n== 2. coverage: fraction of signal pixels with a label within +-dw wires, +-dt ticks ==")
    print("(pixel fraction / amplitude-weighted fraction)")
    results = {}
    for iname, sig, amp in (("deconvolved (wire/signal > %g, live channels)" % args.wire_threshold, sig_wire, wamp),
                            ("raw (|adc - baseline| > %g sigma, all channels)" % args.raw_nsigma, sig_raw, ramp)):
        print("\n%s: %d signal pixels (U %d, V %d, Y %d)" % (
            iname, sig.sum(), *[sig[planes_of == p].sum() for p in range(3)]))
        print("  %-9s %-9s %s" % ("label", "dw x dt", "   ".join("%-15s" % PLANES[p] for p in range(3)) + "   all"))
        for lname, lm in (("edep", edep_m), ("simch", simch_m)):
            for dw, dt in tols:
                # dilate per plane so labels do not leak across the plane boundaries
                cov = np.zeros_like(lm)
                for p in range(3):
                    sl = slice(first[p], first[p] + nwires[p])
                    cov[sl] = dilate(lm[sl], dw, dt)
                hit = sig & cov
                cells = []
                for sel in [planes_of == p for p in range(3)] + [np.ones(nch, bool)]:
                    n = sig[sel].sum(); a = amp[sel].sum()
                    cells.append("%.3f / %.3f" % (hit[sel].sum() / max(n, 1), amp[sel][hit[sel]].sum() / max(a, 1e-9)))
                print("  %-9s %-9s %s" % (lname, "%dx%d" % (dw, dt), "   ".join("%-15s" % c for c in cells)))
                results[(iname[:3], lname, dw, dt)] = cov if (dw, dt) == tols[min(2, len(tols) - 1)] else None
            # where the pixels without any label (widest tolerance, last computed) sit
            per = (sig & ~cov).sum(1)
            top = np.argsort(per)[::-1][:5]
            print("  %-9s uncovered at %dx%d: %d pixels; top channels (channel: pixels, noise RMS): %s" % (
                lname, dw, dt, per.sum(), ", ".join("%d: %d, %.1f" % (c, per[c], rms[c, 0]) for c in top if per[c] > 0)))

    # ---------------------------------------------------------------- 3. label efficiency
    print("\n== 3. label efficiency: fraction of projected deposit electrons with a deconvolved "
          "signal pixel within +-dw, +-dt ==")
    print("(deposits projected inside the deconvolved window, raw ticks %d-%d)" % (wire_t0, wire_t0 + wnt))
    q = edep_q * in_wire_window[None, :]
    print("  %-9s %s" % ("dw x dt", "   ".join("%-24s" % (PLANES[p] + " live / all channels") for p in range(3))))
    for dw, dt in tols:
        cells = []
        for p in range(3):
            sl = slice(first[p], first[p] + nwires[p])
            near = dilate(sig_wire[sl], dw, dt)
            live = ~dead[sl]
            cells.append("%.3f / %.3f" % ((q[sl][live] * near[live]).sum() / max(q[sl][live].sum(), 1),
                                          (q[sl] * near).sum() / max(q[sl].sum(), 1)))
        print("  %-9s %s" % ("%dx%d" % (dw, dt), "   ".join("%-24s" % c for c in cells)))
    print("  electrons projected onto dead channels: " + "  ".join(
        "%s %.3f" % (PLANES[p], q[first[p]:first[p] + nwires[p]][dead[first[p]:first[p] + nwires[p]]].sum()
                     / max(q[first[p]:first[p] + nwires[p]].sum(), 1)) for p in range(3)))

    # ---------------------------------------------------------------- 4. plot
    if args.plots:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        os.makedirs(args.plots, exist_ok=True)
        dw, dt = tols[min(2, len(tols) - 1)]
        cov = results[("dec", "edep", dw, dt)]
        # zoom on the neutrino interaction: deposits of origin-1 particles
        part = g["particles"]
        nu_ids = set(part["track_id"][()][part["origin"][()] == 1].tolist())
        isnu = np.fromiter((t in nu_ids for t in etid), bool, len(etid))
        fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), constrained_layout=True)
        cmap = ListedColormap(["#ffffff", "#c9ccd1", "#2a6fb0", "#d9480f"])
        for p, ax in enumerate(axes):
            ok = pr["in_image"][:, p] & isnu
            if not ok.any():
                ax.set_title("%s plane: no neutrino deposits in the image" % PLANES[p]); continue
            w, tk = pr["nearest_wire"][ok, p], pr["row"][ok, p]
            w0, w1 = max(int(np.percentile(w, 1)) - 40, 0), min(int(np.percentile(w, 99)) + 40, nwires[p])
            t0, t1 = max(int(np.percentile(tk, 1)) - 150, 0), min(int(np.percentile(tk, 99)) + 150, nt)
            sl = (slice(first[p] + w0, first[p] + w1), slice(t0, t1))
            cat = np.zeros((w1 - w0, t1 - t0), dtype=np.uint8)
            cat[np.broadcast_to(dead[sl[0]][:, None], cat.shape)] = 1
            cat[sig_wire[sl] & cov[sl]] = 2
            cat[sig_wire[sl] & ~cov[sl]] = 3
            ax.imshow(cat.T, origin="lower", aspect="auto", cmap=cmap, vmin=0, vmax=3,
                      extent=(w0, w1, t0, t1), interpolation="nearest")
            n = sig_wire[sl].sum()
            ax.set_title("%s plane: %.1f%% of %d signal pixels covered" % (
                PLANES[p], 100.0 * (sig_wire[sl] & cov[sl]).sum() / max(n, 1), n))
            ax.set_xlabel("wire"); ax.set_ylabel("raw tick")
        handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ("#2a6fb0", "#d9480f", "#c9ccd1")]
        fig.legend(handles, ["signal pixel with a projected deposit within +-%d wires, +-%d ticks" % (dw, dt),
                             "signal pixel with no projected deposit nearby", "dead channel"],
                   loc="outside lower center", ncol=3, frameon=False)
        fig.suptitle("Deconvolved signal (> %g) vs projected energy deposits, neutrino region, event %d"
                     % (args.wire_threshold, args.event))
        out = os.path.join(args.plots, "event_%06d_edep_coverage.png" % args.event)
        fig.savefig(out, dpi=110)
        print("\nwrote", out)


if __name__ == "__main__":
    main()
