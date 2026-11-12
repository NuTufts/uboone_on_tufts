#!/usr/bin/env python
"""Extract wire-plane products from a MicroBooNE art/LArSoft file into HDF5.

Runs inside the uboonecode environment (python 2.7 + ROOT 6.12 + gallery); use
run_extract_wireplane.sh, which starts the container and sets everything up.

Products (defaults are the tags of the Tufts v08_00_00_40a_dl production):
  rawdigit   raw::RawDigit            driftWC:orig:Detsim     simulated raw waveforms
  wire       recob::Wire              butcher::McRecoStage1   deconvolved waveforms
  simch      sim::SimChannel          driftWC:simpleSC:Detsim ionization arriving on wires
  edep       sim::SimEnergyDeposit    largeant:TPCActive:G4EDep  3D energy deposits, true positions
  edep_sce   sim::SimEnergyDeposit    ionization::G4EDep      same deposits after ShiftEdepSCE: positions
                                                              moved by the space-charge map, electrons
                                                              after recombination (the WireCell drift input)
  chstatus   std::vector<int>         simnfspl1:badchannels / badmasks (McRecoStage1)  dead-channel mask
  particles  simb::MCParticle         largeant::G4EDep        track-ID lookup table
  opdet      raw::OpDetWaveform       pmtreadout:<instance>:Detsim   PMT waveforms (see --opdet-tags)

See README.md for the schema.
"""
from __future__ import print_function
import argparse, os, sys, time
import numpy as np
import h5py
import ROOT

HERE = os.path.dirname(os.path.abspath(__file__))

# MicroBooNE channel layout (channel -> plane): U 0-2399, V 2400-4799, Y 4800-8255
UB_PLANE_FIRST_CHANNEL = [0, 2400, 4800]
UB_PLANE_NWIRES = [2400, 2400, 3456]


# beam = one 1500-sample window per channel in time with the beam gate;
# cosmic = short self-triggered windows; each in a high- and a low-gain copy.
# *_satcorr = the reconstruction's merge of high and low gain (saturation correction).
OPDET_DEFAULT = ",".join([
    "beam_highgain=pmtreadout:OpdetBeamHighGain:Detsim",
    "beam_lowgain=pmtreadout:OpdetBeamLowGain:Detsim",
    "cosmic_highgain=pmtreadout:OpdetCosmicHighGain:Detsim",
    "cosmic_lowgain=pmtreadout:OpdetCosmicLowGain:Detsim",
    "beam_satcorr=saturation:OpdetBeamHighGain:McRecoStage1",
    "cosmic_satcorr=saturation:OpdetCosmicHighGain:McRecoStage1",
])


def tag(s):
    p = s.split(":")
    while len(p) < 3:
        p.append("")
    return p[0], p[1], p[2]


def addr(a):
    return a.ctypes.data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", required=True, help="art ROOT file")
    ap.add_argument("-o", "--output", required=True, help="output HDF5 file")
    ap.add_argument("-n", "--nevents", type=int, default=-1)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--rawdigit-tag", default="driftWC:orig:Detsim")
    ap.add_argument("--wire-tag", default="butcher::McRecoStage1", help="'' to skip")
    ap.add_argument("--simch-tag", default="driftWC:simpleSC:Detsim")
    ap.add_argument("--edep-tag", default="largeant:TPCActive:G4EDep", help="true positions; '' to skip")
    ap.add_argument("--edep-sce-tag", default="ionization::G4EDep", help="SCE-shifted; '' to skip")
    ap.add_argument("--badch-tag", default="simnfspl1:badchannels:McRecoStage1", help="'' to skip")
    ap.add_argument("--badmask-tag", default="simnfspl1:badmasks:McRecoStage1", help="'' to skip")
    ap.add_argument("--particle-tag", default="largeant::G4EDep", help="'' to skip")
    ap.add_argument("--opdet-tags", default=OPDET_DEFAULT,
                    help="comma list of name=label:instance:process for raw::OpDetWaveform products "
                         "written to opdet/<name>; '' to skip. Missing products are skipped")
    ap.add_argument("--tdc-offset", type=int, default=4900,
                    help="simch/tick = tdc - offset (RawDigit tick of the charge arrival). "
                         "4900 for the uboone MC clock settings; checked with validate_wireplane_h5.py")
    ap.add_argument("--wire-tick0", type=int, default=2400,
                    help="RawDigit tick corresponding to recob::Wire tick 0 (stored as an attribute)")
    ap.add_argument("--gzip", type=int, default=4)
    ap.add_argument("--build-dir", default=None, help="where ACLiC puts the compiled reader")
    args = ap.parse_args()

    for lib in ("libgallery", "libcanvas", "liblardataobj_RawData", "liblardataobj_RecoBase",
                "liblardataobj_Simulation", "libnusimdata_SimulationBase"):
        ROOT.gSystem.Load(lib)
    if args.build_dir:
        if not os.path.isdir(args.build_dir):
            os.makedirs(args.build_dir)
        ROOT.gSystem.SetBuildDir(args.build_dir, True)
    if ROOT.gROOT.ProcessLine(".L %s/wireplane_products.cxx+" % HERE) != 0 and not hasattr(ROOT, "WireplaneReader"):
        sys.exit("failed to compile wireplane_products.cxx")

    rd = ROOT.WireplaneReader(args.input)
    ntot = rd.nEvents()
    stop = ntot if args.nevents < 0 else min(ntot, args.start + args.nevents)
    gz = dict(compression="gzip", compression_opts=args.gzip, shuffle=True)

    fout = h5py.File(args.output, "w")
    fout.attrs["source_file"] = os.path.abspath(args.input)
    fout.attrs["rawdigit_tag"] = args.rawdigit_tag
    fout.attrs["wire_tag"] = args.wire_tag
    fout.attrs["simch_tag"] = args.simch_tag
    fout.attrs["edep_tag"] = args.edep_tag
    fout.attrs["edep_sce_tag"] = args.edep_sce_tag
    fout.attrs["badch_tag"] = args.badch_tag
    fout.attrs["opdet_tags"] = args.opdet_tags
    fout.attrs["badmask_tag"] = args.badmask_tag
    fout.attrs["particle_tag"] = args.particle_tag
    fout.attrs["plane_first_channel"] = np.array(UB_PLANE_FIRST_CHANNEL, dtype=np.int32)
    fout.attrs["plane_nwires"] = np.array(UB_PLANE_NWIRES, dtype=np.int32)
    fout.attrs["uboonecode_version"] = os.environ.get("UBOONECODE_VERSION", "unknown")
    fout.attrs["extractor_git_commit"] = os.environ.get("WIREPLANE_GIT_COMMIT", "unknown")
    fout.attrs["simch_tdc_to_tick_offset"] = args.tdc_offset
    fout.attrs["wire_tick0_raw_tick"] = args.wire_tick0

    nwritten = 0
    for ie in range(args.start, stop):
        t0 = time.time()
        rd.goTo(ie)
        g = fout.create_group("event_%06d" % ie)
        g.attrs["run"] = rd.run(); g.attrs["subrun"] = rd.subrun(); g.attrs["event"] = rd.event()
        g.attrs["entry"] = ie

        # ---- raw digits
        nd = rd.loadRawDigits(*tag(args.rawdigit_tag))
        nch, nt = rd.nChannels(), rd.nTicks()
        adc = np.zeros((nch, nt), dtype=np.int16)
        ped = np.zeros(nch, dtype=np.float32); sig = np.zeros(nch, dtype=np.float32)
        present = np.zeros(nch, dtype=np.uint8)
        rd.fillRawDigits(addr(adc), addr(ped), addr(sig), addr(present))
        gr = g.create_group("rawdigit")
        gr.create_dataset("adc", data=adc, chunks=(16, nt), **gz)
        gr.create_dataset("pedestal", data=ped)
        gr.create_dataset("sigma", data=sig)
        gr.create_dataset("present", data=present)
        del adc

        # ---- deconvolved wires
        nw = 0
        if args.wire_tag:
            nw = rd.loadWires(*tag(args.wire_tag))
            wnch, wnt = rd.wireNChannels(), rd.wireNTicks()
            wsig = np.zeros((wnch, wnt), dtype=np.float32)
            rd.fillWires(addr(wsig))
            gw = g.create_group("wire")
            gw.create_dataset("signal", data=wsig, chunks=(16, wnt), **gz)
            del wsig

        # ---- sim channels
        n = rd.loadSimChannels(*tag(args.simch_tag))
        i4 = lambda: np.zeros(n, dtype=np.int32)
        f4 = lambda: np.zeros(n, dtype=np.float32)
        ch, tdc, tid, ne, en, x, y, z = i4(), i4(), i4(), f4(), f4(), f4(), f4(), f4()
        rd.fillSimChannels(*[addr(a) for a in (ch, tdc, tid, ne, en, x, y, z)])
        gs = g.create_group("simch")
        for name, a in (("channel", ch), ("tdc", tdc), ("track_id", tid), ("num_electrons", ne),
                        ("energy", en), ("x", x), ("y", y), ("z", z)):
            gs.create_dataset(name, data=a, **gz)
        gs.create_dataset("tick", data=(tdc - args.tdc_offset).astype(np.int32), **gz)
        nide = n

        # ---- channel status (WireCell noise-filter masks used by the signal processing)
        nbad = -1
        if args.badch_tag:
            nbad = rd.loadIntVector(*tag(args.badch_tag))
            if nbad >= 0:
                bad = np.zeros(nbad, dtype=np.int32)
                rd.fillIntVector(addr(bad))
                gc = g.create_group("chstatus")
                gc.create_dataset("bad_channels", data=bad)
                dead = np.zeros(nch, dtype=np.uint8)
                dead[bad[(bad >= 0) & (bad < nch)]] = 1
                gc.create_dataset("dead", data=dead)
                nm = rd.loadIntVector(*tag(args.badmask_tag)) if args.badmask_tag else -1
                if nm >= 0 and nm % 3 == 0:
                    masks = np.zeros(nm, dtype=np.int32)
                    rd.fillIntVector(addr(masks))
                    gc.create_dataset("bad_masks", data=masks.reshape(-1, 3))

        # ---- energy deposits
        ndep = 0
        for gname, etag in (("edep", args.edep_tag), ("edep_sce", args.edep_sce_tag)):
            if not etag:
                continue
            n = rd.loadEnergyDeposits(*tag(etag))
            tid, pdg, ne, nph = [np.zeros(n, dtype=np.int32) for _ in range(4)]
            en = np.zeros(n, dtype=np.float32)
            st = np.zeros((n, 3), dtype=np.float32); ed = np.zeros((n, 3), dtype=np.float32)
            tt = np.zeros((n, 2), dtype=np.float64)
            rd.fillEnergyDeposits(*[addr(a) for a in (tid, pdg, ne, nph, en, st, ed, tt)])
            ge = g.create_group(gname)
            for name, a in (("track_id", tid), ("pdg", pdg), ("num_electrons", ne), ("num_photons", nph),
                            ("energy", en), ("start_xyz", st), ("end_xyz", ed)):
                ge.create_dataset(name, data=a, **gz)
            ge.create_dataset("t_start", data=tt[:, 0].copy(), **gz)
            ge.create_dataset("t_end", data=tt[:, 1].copy(), **gz)
            ndep = n

        # ---- optical detector waveforms
        nop = 0
        for item in [v for v in args.opdet_tags.split(",") if v]:
            oname, otag = item.split("=", 1)
            n = rd.loadOpWaveforms(*tag(otag))
            if n < 0:
                continue
            ns_tot = rd.nOpSamples()
            och = np.zeros(n, dtype=np.int32); ons = np.zeros(n, dtype=np.int32)
            ooff = np.zeros(n, dtype=np.int64); ots = np.zeros(n, dtype=np.float64)
            oadc = np.zeros(max(ns_tot, 1), dtype=np.int16)
            if n > 0:
                rd.fillOpWaveforms(*[addr(a) for a in (och, ons, ooff, ots, oadc)])
            go = g.require_group("opdet").create_group(oname)
            go.attrs["tag"] = otag
            go.create_dataset("channel", data=och)
            go.create_dataset("nsamples", data=ons)
            go.create_dataset("offset", data=ooff)
            go.create_dataset("timestamp", data=ots)
            go.create_dataset("adc", data=oadc[:ns_tot], **(gz if ns_tot > 0 else {}))
            nop += n

        # ---- particles
        npart = 0
        if args.particle_tag:
            n = rd.loadParticles(*tag(args.particle_tag))
            cols_i = [np.zeros(n, dtype=np.int32) for _ in range(8)]
            en = np.zeros(n, dtype=np.float32); mass = np.zeros(n, dtype=np.float32)
            st, ed, mom = [np.zeros((n, 3), dtype=np.float32) for _ in range(3)]
            tt = np.zeros((n, 2), dtype=np.float64)
            rd.fillParticles(*[addr(a) for a in cols_i + [en, mass, st, ed, mom, tt]])
            gp = g.create_group("particles")
            for name, a in zip(("track_id", "pdg", "mother", "ancestor", "status", "process", "origin",
                                "truth_index"), cols_i):
                gp.create_dataset(name, data=a, **gz)
            for name, a in (("energy", en), ("mass", mass), ("start_xyz", st), ("end_xyz", ed),
                            ("momentum", mom)):
                gp.create_dataset(name, data=a, **gz)
            gp.create_dataset("t_start", data=tt[:, 0].copy(), **gz)
            gp.create_dataset("t_end", data=tt[:, 1].copy(), **gz)
            gp.attrs["process_names"] = str(rd.processNames())
            gp.attrs["have_origin"] = bool(rd.haveOrigin())
            npart = n

        nwritten += 1
        print("entry %d run %d subrun %d event %d: rawdigit %d (%dx%d) wire %d simch IDE %d edep %d particles %d badch %d opwf %d  [%.1fs]"
              % (ie, rd.run(), rd.subrun(), rd.event(), nd, nch, nt, nw, nide, ndep, npart, nbad, nop, time.time() - t0))
        sys.stdout.flush()

    fout.attrs["nevents"] = nwritten
    fout.close()
    print("wrote %s (%d events, %.1f MB)" % (args.output, nwritten, os.path.getsize(args.output) / 1e6))


if __name__ == "__main__":
    main()
