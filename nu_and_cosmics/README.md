# Generating fully simulated neutrino interactions + cosmics

Full-MC (CORSIKA cosmics + GENIE BNB neutrino) MicroBooNE samples generated on the
Tufts cluster. These are the source of the Sonata pre-training and LArFormer
training data (`ub_on_tufts` samples; see the provenance doc in the pointcept repo,
`docs/reference/Training_Sim_Provenance.md`).

We use a modified version of the "Full MC BNB" fhicl list on the
[Production Wiki](https://cdcvs.fnal.gov/redmine/projects/uboone-physics-analysis/wiki/MCC9_Production_Fhicls).

## Software

| Item | Version |
| ---- | ------- |
| uboonecode | `v08_00_00_40a_dl -q e17:prof` (from `/cvmfs/uboone.opensciencegrid.org`) |
| larsoft (mrb dev area) | `v08_05_00_13`, built with `mrb v3_05_03` |
| ublite (locally built, overrides cvmfs) | [`NuTufts/ublite`](https://github.com/NuTufts/ublite) tag `v08_00_00_40a_dl_tufts1` (branch `tufts/v08_00_00_40a_dl_simch_crt`), = upstream tag `v08_00_00_40a_dl` + one commit |
| container | `/cvmfs/uboone.opensciencegrid.org/containers/uboone-devel-sl7` (apptainer) |
| build area | `dev/v08_00_00_40a_dl/` (not in git; built 2025-11-11) |

`setup_uboonecode_env.sh` reproduces the environment the jobs ran in.

### What the ublite patch does

Two files in `ublite/LiteMaker` (a copy of the commit is in
`ublite_patches/v08_00_00_40a_dl_tufts1.patch`):

* `ScannerAlgo.template.h`
  * `sim::SimChannel` -> `larlite::simch`: keep **all three planes** (the stock code
    skipped channels < 4800, i.e. kept only the Y plane) and fill the IDE
    **x, y, z** (commented out in the stock code). This gives the true 3D position of
    every energy deposit directly, which is what the training labels are built from.
  * new `ScanData` specializations for `crt::CRTHit` and `crt::CRTTrack` that do not
    need a `raw::DAQHeaderTimeUBooNE`.
* `LiteScanner_module.cc`: `ScanDataCRT` falls back to that no-GPS-time path when the
  DAQ header is absent (pure MC) instead of returning without storing CRT products.

### Rebuilding the ublite dev area

Reconstructed from the layout of `dev/v08_00_00_40a_dl`; not re-run since the
original build. Inside the SL7 container:

```
source /cvmfs/uboone.opensciencegrid.org/products/setup_uboone.sh
unsetup mrb
setup mrb v3_05_03
setup uboonecode v08_00_00_40a_dl -q e17:prof
mkdir -p dev/v08_00_00_40a_dl && cd dev/v08_00_00_40a_dl
mrb newDev -v v08_05_00_13 -q e17:prof
source localProducts_larsoft_v08_05_00_13_e17_prof/setup
cd srcs
git clone git@github.com:NuTufts/ublite.git
cd ublite && git checkout v08_00_00_40a_dl_tufts1 && cd ..
mrb uc
cd $MRB_BUILDDIR
mrbsetenv
export IFDHC_INC=${IFDHC_FQ_DIR}/inc   # missing export on Tufts
mrb i -j4
```

Other dev areas under `dev/` (not in git): `v08_00_00_29e_dl` and
`v08_00_00_40a_dl_old` carry the same patch on older bases and were not used for
production. `v10_04_07_br` has only a partial, untested port of the SimChannel
change (with a debug print per IDE); it was not used for any sample. If a v10 port
is needed, redo it using the v08 commit as the reference.

## Processing chain (per output file)

Each `run_corsika_*.sh` loops over file numbers taken from a `*.runlist` and runs:

1. gen: `lar -c <gen fcl> -n NENTRIES` — the gen fcl is the `*_wbaseseedtemplate.fcl`
   with `__TEMPLATE_SEED_NJOB__` replaced by `10000 + fileno`, plus
   `source.firstRun: <fileno>`, `source.firstEvent: 1`
2. `wirecell_g4_uboone.fcl` (stock)
3. `wirecell_detsim_uboone.fcl` (stock)
4. `reco_uboone_mcc9_8_driver_stage1.fcl` (stock)
5. `standard_larcv_uboone_mctruth_prod_on_tufts_wcsimch.fcl` (ours) — writes
   `larlite_{opreco,reco2d,crt,mcinfo,simch}.root` and `larcv_mctruth.root`
6. `rootrm` the `larlite_id_tree` from all but the mcinfo file, then `hadd` into
   `dlmerged_<TAG>_fileno%06d.root`, copied to
   `<OUTPUT_DIR>/<fileno/1000>/<fileno/100>/`

Our modifications to the fcls:

* gen fcls: CORSIKA shower DBs and BNB gsimple flux files point to Tufts copies
  (`/cluster/tufts/wongjiradlabnu/larbys/uboone/{corsika/sqShowers,bnb_gsimple}`);
  per-file `NuRandomService` seed (`linearMapping`, `nJob = 10000 + fileno`).
* `standard_larcv_uboone_mctruth_prod_on_tufts_wcsimch.fcl`: adds the `crt` and
  `simch` larlite streams; CRT hits from `crthitsim`; SimChannels from
  `driftWC:simpleSC:Detsim`; supera config `supera_mctruthonly_on_tufts_reduced.fcl`.
* `supera_mctruthonly_on_tufts_reduced.fcl`: `supera_mctruthonly_on_tufts.fcl` minus
  `SuperaInstanceImage` and `SuperaLArFlow`. Those images were a way to recover 3D
  truth positions at the image level; with IDE x,y,z in the simch stream they are not
  needed.

## Samples used for training

All five were produced with the software above. Output root:
`/cluster/tufts/wongjiradlab/larbys/data/ub_on_tufts/<sample>/` at production time;
the dlmerged files have since been moved to
`/cluster/tier2/wongjiradlab/larbys/data/ub_on_tufts/`.

| Sample (output dir / TAG) | gen fcl template | run script | submit script | events/file | produced |
| --- | --- | --- | --- | --- | --- |
| `bnb_nu_corsika` / `coriska_bnb_nu` | `prodgenie_bnb_nu_corsika_uboone_on_tufts_wbaseseedtemplate.fcl` | `run_corsika_bnb_nu.sh` | `submit_bnb_nu_corsika.sh` | 20 | 2025-11-27 to 2025-12-31 |
| `bnb_nue_corsika` / `coriska_bnb_nue` | `prodgenie_bnb_intrinsic_nue_cosmic_uboone_on_tufts_wbaseseedtemplate.fcl` | `run_corsika_bnb_nue.sh` | `submit_bnbnue_corsika.sh` | 20 | 2025-12-05 to 2026-01-02 |
| `bnb_nu_pi0_corsika` / `coriska_bnb_nu_pi0` | earlier revision of `prodgenie_bnb_nu_pi0filter_cosmic_...` (see note) | earlier revision of `run_corsika_bnb_nu_pi0.sh` | `submit_bnbnu_pi0_corsika.sh` | 20 | from 2025-12-03 |
| `bnb_nu_pi0filter_corsika` / `coriska_bnb_nu_pi0filter` | `prodgenie_bnb_nu_pi0filter_cosmic_uboone_on_tufts_wbaseseedtemplate.fcl` | `run_corsika_bnb_nu_pi0.sh` | `submit_bnbnu_pi0_corsika.sh` | 50 generated, filtered | 2026-01-09 to 2026-01-11 |
| `bnb_nu_chargedpiplus_corsika` / `coriska_bnb_nu_chargedpiplus` | `prodgenie_bnb_nu_chargedpiplus_filter_cosmic_uboone_on_tufts_wbaseseedtemplate.fcl` | `run_corsika_bnb_nu_chargedpiplus.sh` | `submit_bnbnu_chargedpiplus_corsika.sh` | 50 generated, filtered | 2026-01-09 to 2026-01-27 |

Generator settings:

* `bnb_nu`: all BNB flavors, `TopVolume: volCryostat`.
* `bnb_nue`: `GenFlavors: [12,-12]`, `EventGeneratorList: CCinclMEC`, `volTPCActive`.
* `pi0filter`: `GenFlavors: [12,-12,14,-14]`, `volTPCActive`, `FinalStateSelectFilter`
  requiring >= 1 pi0 (PDG 111, inclusive), output gated with
  `outputs.out1.SelectEvents: ["simulate"]`.
* `chargedpiplus`: same as pi0filter but PDG 211.

Notes and caveats:

* **`bnb_nu_pi0_corsika` is not exactly reproducible from the current files.** It was
  made in Dec 2025 with an earlier revision of the pi0 fcl/run script (the state in
  commit `c21d403` but with the templated seed: job logs show `maxEvents: 20`,
  `nJob: 10000+fileno`). That revision had no `outputs.out1.SelectEvents`, so the pi0
  filter most likely did not gate the output and the sample is effectively unfiltered
  BNB nu/nue generated in `volTPCActive` (its ~20 events/file yield is consistent with
  this). Not verified against an output file. The larcv stage fcl for this sample
  (`_wcsimch` vs the earlier `standard_larcv_uboone_mctruth_prod_on_tufts.fcl`) is also
  unconfirmed; the `_wcsimch` fcl was present in the job directories.
* The run/submit scripts hold the `OFFSET`, `stride`, loop count and `--array` range of
  the **last** tranche launched. Earlier tranches used other values; the per-job logs
  (`logs/<sample>/`, `workdir/`, not in git) record the file numbers and the tail of
  each job's gen fcl.
* Sample names carry the original typo `coriska` in TAGs and file names.

## Files NOT used for the training samples

Kept for the record; none of these fed the training set.

| File(s) | What |
| --- | --- |
| `prodgenie_bnb_nu_chargedpi_filter_...fcl`, `run_corsika_bnb_nu_chargedpi.sh`, `corsika_bnb_nu_chargedpi.runlist` | pi+ and pi- filter; test only, no production |
| `prodgenie_bnb_nu_chargedpiminus_filter_...fcl` | pi- filter; never run in production |
| `prodgenie_bnb_intrinsic_nue_cosmic_uboone_on_tufts.fcl` | nue + corsika without per-file seed (2023) |
| `prodgenie_bnb_nu_filtered_NCPiZero_uboone.fcl`, `prodgenie_bnb_nue_uboone.fcl` | reference / test fcls |
| `prodgenie_bnb_nue_uboone_on_tufts.fcl`, `run_bnb_nue_only.sh`, `submit_nue_only.sh`, `bnb_nue_only.runlist` | 2023 nue-only (no cosmics) sample |
| `prodgenie_bnb_nu_uboone_on_tufts.fcl`, `run_bnb_nu_only.sh`, `submit_nu_only.sh`, `bnb_nu_only.runlist` | 2023 nu-only (no cosmics) sample |
| `prodgenie_bnb_intrinsic_nue_fullosc_nutau.fcl`, `run_bnb_nueflux_nue2nutau_nocosmic.sh`, `submit_nueflux_nutauxsec_nuonly.sh` | 2023 nue-flux -> nutau test |
| `standard_larcv_uboone_mctruth_prod_on_tufts.fcl`, `..._on_tufts2.fcl`, `supera_mctruthonly_on_tufts.fcl` | earlier larcv-stage configs (full supera incl. instance/larflow images) |
| `make_dlmerged.sh` | interactive version of the merge step |
