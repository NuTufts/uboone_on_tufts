#!/usr/bin/env python3
"""Sanity checks + plots for a wire-plane HDF5 file made by extract_wireplane_h5.py.

Needs python3 with h5py, numpy, matplotlib (e.g. the pointcept container).

  python3 validate_wireplane_h5.py test_output/wireplane_test_nue.h5 [-o plot_dir] [--event 0]

Checks: dataset inventory, simch TDC -> raw tick offset (cross-correlation, per
plane), deconvolved-wire tick offset, flat/dead channels, IDE position content,
electron bookkeeping simch vs edep, track-ID coverage by the particle table.
Plots: per-plane raw / deconvolved / simch-truth images, full view and a zoom on
the neutrino interaction.
"""
import argparse, os
import numpy as np
import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PLANES = "UVY"


def best_lag(a, b, maxlag=None):
    """lag L maximising sum_ch sum_t a[ch,t+L] * b[ch,t] (rows = channels)."""
    n = a.shape[1]
    nfft = 1 << int(np.ceil(np.log2(2 * n)))
    c = np.fft.irfft(np.fft.rfft(a, nfft, axis=1) * np.conj(np.fft.rfft(b, nfft, axis=1)), nfft, axis=1).sum(axis=0)
    lags = np.arange(nfft); lags[lags > nfft // 2] -= nfft
    if maxlag is not None:
        c = np.where(np.abs(lags) <= maxlag, c, -np.inf)
    i = int(np.argmax(c))
    return int(lags[i]), c, lags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("h5")
    ap.add_argument("-o", "--outdir", default=None)
    ap.add_argument("--event", type=int, default=0, help="index into the event groups")
    args = ap.parse_args()
    outdir = args.outdir or os.path.join(os.path.dirname(os.path.abspath(args.h5)), "validation_plots")
    os.makedirs(outdir, exist_ok=True)

    f = h5py.File(args.h5, "r")
    print("file attrs:")
    for k, v in f.attrs.items():
        print("  %-28s %s" % (k, v))
    evname = sorted(k for k in f.keys() if k.startswith("event_"))[args.event]
    g = f[evname]
    print("\n%s  run %d subrun %d event %d" % (evname, g.attrs["run"], g.attrs["subrun"], g.attrs["event"]))
    def inventory(name, obj):
        if isinstance(obj, h5py.Dataset):
            print("  %-28s %-16s %-8s %8.2f MB on disk" % (name, obj.shape, obj.dtype, obj.id.get_storage_size() / 1e6))
    g.visititems(inventory)

    first = f.attrs["plane_first_channel"]; nw = f.attrs["plane_nwires"]
    psl = [slice(int(a), int(a + n)) for a, n in zip(first, nw)]

    adc = g["rawdigit/adc"][:]
    ped = g["rawdigit/pedestal"][:]
    nch, nt = adc.shape
    # baseline: per-channel median (robust; the stored pedestal is the nominal one)
    base = np.median(adc, axis=1)
    raw = adc.astype(np.float32) - base[:, None].astype(np.float32)
    rms = raw.std(axis=1)
    # noise estimate insensitive to signal: 1.4826 * MAD
    mad = 1.4826 * np.median(np.abs(raw), axis=1)

    s = g["simch"]
    ch = s["channel"][:]; tdc = s["tdc"][:]; tid = s["track_id"][:]; ne = s["num_electrons"][:]
    tdc0 = int(tdc.min())
    print("\nsimch: %d IDEs, channels %d..%d, tdc %d..%d (span %d)" % (len(ch), ch.min(), ch.max(), tdc.min(), tdc.max(), tdc.max() - tdc.min() + 1))
    span = int(tdc.max() - tdc0 + 1)
    q = np.zeros((nch, max(span, nt)), dtype=np.float32)
    np.add.at(q, (ch, tdc - tdc0), ne)

    # ---- IDE position content
    print("\nsimch IDE coordinates:")
    for c in "xyz":
        v = s[c][:]
        print("  %s: min %.3f max %.3f mean %.3f  n_unique %d" % (c, v.min(), v.max(), v.mean(), len(np.unique(v))))
    e = g["edep"]
    exyz = e["start_xyz"][:]
    print("edep start_xyz: x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f" % (
        exyz[:, 0].min(), exyz[:, 0].max(), exyz[:, 1].min(), exyz[:, 1].max(), exyz[:, 2].min(), exyz[:, 2].max()))
    print("edep t_start: %.1f..%.1f ns" % (e["t_start"][:].min(), e["t_start"][:].max()))

    # ---- tdc -> tick offset per plane (|raw| vs simch charge)
    print("\nsimch TDC -> RawDigit tick  (tick = tdc - offset):")
    offsets = []
    for ip, sl in enumerate(psl):
        a = np.abs(raw[sl]) if ip < 2 else np.clip(raw[sl], 0, None)
        lag, c, lags = best_lag(a, q[sl, :nt])
        # raw[t + lag] ~ q[tdc - tdc0]  ->  tick = tdc - tdc0 + lag
        off = tdc0 - lag
        offsets.append(off)
        print("  plane %s: lag %+d ticks  -> offset %d   (%s)" % (PLANES[ip], lag, off,
              "|adc-ped| vs electrons" if ip < 2 else "max(adc-ped,0) vs electrons"))

    # ---- deconvolved wires
    have_wire = "wire" in g
    wire_off = None
    if have_wire:
        wire = g["wire/signal"][:]
        wnt = wire.shape[1]
        print("\nrecob::Wire: shape %s, nonzero fraction %.4f" % (wire.shape, float((wire != 0).mean())))
        print("deconvolved tick -> simch:  wire tick = tdc - offset")
        wire_off = []
        for ip, sl in enumerate(psl):
            b = np.zeros((nw[ip], max(wnt, q.shape[1])), dtype=np.float32); b[:, :wnt] = wire[sl]
            qq = np.zeros_like(b); qq[:, :q.shape[1]] = q[sl]
            lag, c, lags = best_lag(b, qq)
            wire_off.append(tdc0 - lag)
            print("  plane %s: lag %+d -> offset %d  (=> wire tick 0 is raw tick %d)" % (PLANES[ip], lag, tdc0 - lag, tdc0 - lag - offsets[ip]))

    # ---- channel response: does the waveform respond where there is truth charge?
    print("\nchannel response where there is truth charge (>50 e/tick, +-4 ticks):")
    print("  noise (1.48*MAD) per channel: median %.2f ADC; RMS percentiles (0,50,100): %s; exactly-flat channels: %d" % (
        np.median(mad), np.percentile(rms, [0, 50, 100]).round(2), int((rms == 0).sum())))
    for ip, sl in enumerate(psl):
        nraw = nquiet = nwin = nnoroi = 0
        noroi = []
        for c in range(sl.start, sl.stop):
            j = np.arange(nt) + offsets[ip] - tdc0
            okj = (j >= 0) & (j < q.shape[1])
            m = np.zeros(nt, bool); m[okj] = q[c, j[okj]] > 50
            if m.sum() < 10:
                continue
            m = np.convolve(m, np.ones(9), "same") > 0
            nraw += 1
            if np.abs(raw[c][m]).mean() < 1.5 * max(mad[c], 1e-6):
                nquiet += 1
            if have_wire:
                shift = wire_off[ip] - offsets[ip]
                mw = m[shift:shift + wire.shape[1]]
                if mw.sum() >= 10:
                    nwin += 1
                    if not (wire[c][:len(mw)][mw] > 0).any():
                        nnoroi += 1; noroi.append(c)
        print("  plane %s: %d channels with truth charge; raw waveform at noise level on %d" % (PLANES[ip], nraw, nquiet)
              + ("; deconvolved has no ROI on %d of %d %s" % (nnoroi, nwin, _runs(np.array(noroi))) if have_wire else ""))

    # ---- electrons bookkeeping
    etid = e["track_id"][:]
    # electrons after recombination are in edep_sce (same rows); older files have them in edep
    ene = (g["edep_sce"] if "edep_sce" in g else e)["num_electrons"][:].astype(np.float64)
    tot_e = ene.sum()
    print("\nelectrons: edep total %.4g" % tot_e)
    for ip, sl in enumerate(psl):
        m = (ch >= sl.start) & (ch < sl.stop)
        print("  plane %s simch total %.4g  ratio to edep %.3f" % (PLANES[ip], ne[m].sum(), ne[m].sum() / tot_e))
    print("track IDs: simch %d unique (%d negative), edep %d unique (%d negative)" % (
        len(np.unique(tid)), int((np.unique(tid) < 0).sum()), len(np.unique(etid)), int((np.unique(etid) < 0).sum())))

    # ---- particle table coverage
    nu_tids = None
    if "particles" in g:
        p = g["particles"]
        ptid = p["track_id"][:]; origin = p["origin"][:]; ppdg = p["pdg"][:]
        names = p.attrs["process_names"]
        names = names.decode() if isinstance(names, bytes) else names
        print("\nparticles: %d; origin counts %s (1=beam neutrino, 2=cosmic); processes: %s" % (
            len(ptid), dict(zip(*np.unique(origin, return_counts=True))), names))
        for label, ids, w in (("edep", etid, ene), ("simch", tid, ne.astype(np.float64))):
            inp = np.isin(np.abs(ids), ptid)
            print("  %s rows whose |track_id| is in the table: %.4f (electron-weighted %.4f)" % (label, inp.mean(), (w * inp).sum() / w.sum()))
        nu_tids = ptid[origin == 1]
        prim = (origin == 1) & (p["mother"][:] == 0)
        print("  neutrino primaries (pdg, E GeV):", [(int(a), round(float(b), 3)) for a, b in zip(ppdg[prim], p["energy"][:][prim])])

    # ---- plots
    def panel(ax, img, extent, title, sym=True, vmax=None):
        vmax = vmax if vmax is not None else np.percentile(np.abs(img), 99.5) or 1.0
        im = ax.imshow(img.T, origin="lower", aspect="auto", extent=extent, interpolation="nearest",
                       cmap="RdBu_r" if sym else "viridis", vmin=-vmax if sym else 0, vmax=vmax)
        ax.set_title(title, fontsize=9); plt.colorbar(im, ax=ax, pad=0.01)

    def make_fig(tag, wlo, whi, tlo, thi):
        ncol = 3 if have_wire else 2
        fig, axs = plt.subplots(3, ncol, figsize=(6 * ncol, 13), squeeze=False)
        for ip, sl in enumerate(psl):
            c0 = sl.start + wlo[ip]; c1 = sl.start + whi[ip]
            ext = [wlo[ip], whi[ip], tlo, thi]
            panel(axs[ip, 0], raw[c0:c1, tlo:thi], ext, "plane %s raw (ADC - baseline)" % PLANES[ip])
            # truth charge placed on the raw tick axis
            qi = np.zeros((c1 - c0, thi - tlo), dtype=np.float32)
            j0 = tlo + offsets[ip] - tdc0; j1 = thi + offsets[ip] - tdc0
            a0, a1 = max(j0, 0), min(j1, q.shape[1])
            if a1 > a0:
                qi[:, a0 - j0:a1 - j0] = q[c0:c1, a0:a1]
            panel(axs[ip, 1], qi, ext, "plane %s SimChannel electrons (tick = tdc - %d)" % (PLANES[ip], offsets[ip]), sym=False)
            if have_wire:
                wi = np.zeros((c1 - c0, thi - tlo), dtype=np.float32)
                shift = wire_off[ip] - offsets[ip]  # raw tick of wire tick 0
                j0 = tlo - shift; j1 = thi - shift
                a0, a1 = max(j0, 0), min(j1, wire.shape[1])
                if a1 > a0:
                    wi[:, a0 - j0:a1 - j0] = wire[c0:c1, a0:a1]
                panel(axs[ip, 2], wi, ext, "plane %s deconvolved (wire tick 0 = raw tick %d)" % (PLANES[ip], shift), sym=False)
            for ax in axs[ip]:
                ax.set_xlabel("wire in plane"); ax.set_ylabel("raw tick")
        fig.suptitle("%s  %s  %s" % (os.path.basename(args.h5), evname, tag), fontsize=10)
        fig.tight_layout(rect=[0, 0, 1, 0.98])
        out = os.path.join(outdir, "%s_%s.png" % (evname, tag)); fig.savefig(out, dpi=110); plt.close(fig)
        print("  wrote", out)

    print("\nplots:")
    make_fig("full", [0, 0, 0], [int(n) for n in nw], 0, nt)
    if nu_tids is not None and len(nu_tids):
        m = np.isin(np.abs(tid), nu_tids)
        if m.any():
            wlo, whi = [], []
            tl, th = [], []
            for ip, sl in enumerate(psl):
                mm = m & (ch >= sl.start) & (ch < sl.stop)
                if not mm.any():
                    wlo.append(0); whi.append(int(nw[ip])); continue
                w = ch[mm] - sl.start; t = tdc[mm] - offsets[ip]
                lo, hi = np.percentile(w, [1, 99]); wlo.append(max(int(lo) - 40, 0)); whi.append(min(int(hi) + 40, int(nw[ip])))
                a, b = np.percentile(t, [1, 99]); tl.append(a); th.append(b)
            tlo = max(int(min(tl)) - 150, 0); thi = min(int(max(th)) + 150, nt)
            print("  neutrino interaction window: ticks %d..%d, wires %s" % (tlo, thi, list(zip(wlo, whi))))
            make_fig("nuzoom", wlo, whi, tlo, thi)

    # waveform-level overlay on the Y-plane channel with the most neutrino (or any) charge
    sl = psl[2]
    sel = np.isin(np.abs(tid), nu_tids) if nu_tids is not None and len(nu_tids) else np.ones(len(tid), bool)
    sel &= (ch >= sl.start)
    if sel.any():
        cbest = int(np.bincount(ch[sel], weights=ne[sel]).argmax())
        ip = int(np.searchsorted(first, cbest, side="right") - 1)
        tq = np.nonzero(q[cbest])[0]
        tc = int(np.average(tq, weights=q[cbest][tq])) + tdc0 - offsets[ip]
        t0, t1 = max(tc - 200, 0), min(tc + 200, nt)
        fig, ax = plt.subplots(figsize=(11, 4))
        ax.plot(np.arange(t0, t1), raw[cbest, t0:t1], label="raw ADC - baseline", color="k", lw=1)
        ax2 = ax.twinx()
        tt = np.arange(t0, t1) + offsets[ip] - tdc0
        ok = (tt >= 0) & (tt < q.shape[1])
        ax2.fill_between(np.arange(t0, t1)[ok], q[cbest, tt[ok]], step="mid", alpha=0.35, color="C1", label="SimChannel electrons")
        if have_wire:
            shift = wire_off[ip] - offsets[ip]
            wt = np.arange(t0, t1) - shift; ok = (wt >= 0) & (wt < wire.shape[1])
            ax.plot(np.arange(t0, t1)[ok], wire[cbest, wt[ok]], color="C0", lw=1, label="deconvolved")
        ax.set_xlabel("raw tick"); ax.set_ylabel("ADC"); ax2.set_ylabel("electrons / tick")
        ax.set_title("channel %d (plane %s wire %d)" % (cbest, PLANES[ip], cbest - first[ip]))
        ax.legend(loc="upper left"); ax2.legend(loc="upper right")
        out = os.path.join(outdir, "%s_waveform_ch%d.png" % (evname, cbest)); fig.tight_layout(); fig.savefig(out, dpi=110); plt.close(fig)
        print("  wrote", out)


def _runs(idx, maxshow=8):
    if len(idx) == 0:
        return ""
    runs = []; a = b = int(idx[0])
    for i in idx[1:]:
        i = int(i)
        if i == b + 1: b = i
        else: runs.append((a, b)); a = b = i
    runs.append((a, b))
    s = ", ".join("%d" % a if a == b else "%d-%d" % (a, b) for a, b in runs[:maxshow])
    return "[" + s + (", ..." if len(runs) > maxshow else "") + "]"


if __name__ == "__main__":
    main()
