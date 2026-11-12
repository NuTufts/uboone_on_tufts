# wireplane_extract: raw wire-plane waveforms + truth from art files -> HDF5

Extracts, per event, the simulated raw TPC waveforms and the truth needed to label
them from a MicroBooNE LArSoft (art) file, for studies of 2D wire-plane encoders.

| HDF5 group | art product | default tag | what |
| --- | --- | --- | --- |
| `rawdigit` | `raw::RawDigit` | `driftWC:orig:Detsim` | simulated raw waveforms (field + electronics response, noise) |
| `wire` | `recob::Wire` | `butcher::McRecoStage1` | deconvolved waveforms, for comparison |
| `simch` | `sim::SimChannel` | `driftWC:simpleSC:Detsim` | ionization arriving at each wire: (channel, time, track, electrons) |
| `edep` | `sim::SimEnergyDeposit` | `ionization::G4EDep` | 3D energy deposits with track ID |
| `particles` | `simb::MCParticle` | `largeant::G4EDep` | lookup table for the track IDs |

The input must be an art file that still has the detsim products (the `*_reco1.root`
or `*_postdlmctruth.root` of the chain in `../nu_and_cosmics`). The production
`dlmerged_*.root` files do **not** contain them; the production scripts delete the
art files.

## Running

On a compute node (inside a Slurm allocation):

```
bash install_py27_h5py.sh        # once: vendors h5py 2.10 for the stack's python 2.7 into py27_site/
bash run_extract_wireplane.sh <input_art.root> <output.h5> [extractor options]
```

`run_extract_wireplane.sh` starts the SL7 container with cvmfs (singcvmfs), sets up
`uboonecode v08_00_00_40a_dl -q e17:prof` (override with `UBOONECODE_VERSION`,
`UBOONECODE_QUAL`) and runs `extract_wireplane_h5.py`. Options: `-n`, `--start`,
`--*-tag` to change input tags (`--wire-tag ''` / `--particle-tag ''` to skip),
`--tdc-offset`, `--gzip`. About 16 s and 67 MB per event on the test file.

Check an output file (python3 with h5py + matplotlib, e.g. the pointcept container):

```
python3 validate_wireplane_h5.py <output.h5> [-o plot_dir]
```

Files: `wireplane_products.cxx` (gallery reader, compiled with ACLiC on first use
into `build_<version>/`), `extract_wireplane_h5.py` (PyROOT driver, python 2.7),
`run_extract_wireplane.sh`, `install_py27_h5py.sh`, `validate_wireplane_h5.py`.

## Schema

File attributes: `source_file`, the input tags, `uboonecode_version`,
`extractor_git_commit`, `nevents`, `plane_first_channel = [0, 2400, 4800]`,
`plane_nwires = [2400, 2400, 3456]` (U, V, Y), `simch_tdc_to_tick_offset = 4900`,
`wire_tick0_raw_tick = 2400`.

One group per event, `event_%06d` (attrs `run`, `subrun`, `event`, `entry`):

| Dataset | Shape, type | Meaning |
| --- | --- | --- |
| `rawdigit/adc` | (8256, 9600) int16 | row = channel, column = tick (0.5 us). Pedestal NOT subtracted |
| `rawdigit/pedestal` | (8256,) float32 | nominal pedestal from the RawDigit (2046 U/V, 473 Y) |
| `rawdigit/sigma`, `present` | (8256,) | RawDigit sigma (0 in this sim); 1 if the channel was in the product |
| `wire/signal` | (8256, 6400) float32 | deconvolved signal, zero outside ROIs. Wire tick `t` = raw tick `t + 2400` |
| `simch/channel`, `tdc`, `track_id` | (N_IDE,) int32 | one row per IDE, sorted by channel then TDC |
| `simch/tick` | (N_IDE,) int32 | `tdc - 4900`: the raw tick at which the charge arrives |
| `simch/num_electrons`, `energy` | (N_IDE,) float32 | electrons collected; energy in MeV |
| `simch/x`, `y`, `z` | (N_IDE,) float32 | cm. **x is not the true drift position** (see below) |
| `edep/track_id`, `pdg` | (N_dep,) int32 | Geant4 track that made the deposit |
| `edep/energy` | (N_dep,) float32 | MeV |
| `edep/num_electrons`, `num_photons` | (N_dep,) int32 | ionization electrons (after recombination) and scintillation photons |
| `edep/start_xyz`, `end_xyz` | (N_dep, 3) float32 | cm, true position of the step |
| `edep/t_start`, `t_end` | (N_dep,) float64 | ns, Geant4 time |
| `particles/track_id`, `pdg`, `mother`, `status` | (N_part,) int32 | `mother` = 0 for primaries |
| `particles/ancestor` | (N_part,) int32 | track ID of the primary at the top of the mother chain |
| `particles/origin` | (N_part,) int32 | 1 = beam neutrino, 2 = cosmic (from the MCTruth) |
| `particles/truth_index` | (N_part,) int32 | index of the MCTruth the particle belongs to |
| `particles/process` | (N_part,) int32 | index into the `;`-separated attr `process_names` |
| `particles/energy`, `mass`, `momentum` | float32 | GeV at production; `momentum` is (N_part, 3) |
| `particles/start_xyz`, `end_xyz`, `t_start`, `t_end` | | cm, ns |

Conventions and things to know:

* **Track IDs.** `simch/track_id` and `edep/track_id` use the same ID space. A
  negative ID `-N` means the charge came from an EM-shower daughter that Geant4 did
  not store; it is attributed to stored particle `N`. Look up
  `abs(track_id)` in `particles/track_id` (100% of rows resolve on the test event).
* **Time alignment.** `simch/tick` is when the charge arrives. The raw waveform peak
  comes 1-5 ticks later (electronics shaping; measured lags 1/5/4 ticks on U/V/Y).
  The deconvolved signal lines up with `simch/tick - 2400` exactly.
  SimChannel TDCs cover the full 9600-tick readout.
* **SimChannel positions.** In the WireCell `simpleSC` SimChannels, `x` only takes
  ~10 discrete values between -0.6 and 0 cm (response/wire-plane positions); only
  `y` and `z` are true deposit coordinates. For true 3D positions use `edep`
  (join on track ID, or use `edep` x with SimChannel time).
* **Electron counts.** `simch/num_electrons` summed over a plane is the same for
  all three planes and is ~57% of `edep/num_electrons` summed on the test event
  (drift attenuation plus deposits outside the readout window; not broken down
  further).
* **Dead channels are not in the raw waveforms.** In `driftWC:orig` every channel
  has noise and essentially every channel with truth charge shows signal. The
  detector's bad-channel list is applied later, in reconstruction: `wire/signal` has
  no ROI on ~770 channels that have truth charge (blocks of 16, e.g. 4976-4991).
  A channel-status mask is not extracted yet; until it is, channels with truth
  charge and an all-zero `wire/signal` row are a usable proxy.
* Noise differs by channel (RMS 0.8 to 24 ADC, median 2.9, including signal).

## Validation on the test file

`../nu_and_cosmics/prodgenie_bnb_intrinsic_nue_cosmic_uboone_..._reco1_postdlmctruth.root`
(1 event; despite the file name the neutrino interaction is a numu CC with a pi0).

Neutrino interaction region, raw / SimChannel truth / deconvolved per plane:

![nu zoom](figures/event_000000_nuzoom.png)

One collection-plane channel:

![waveform](figures/event_000000_waveform_ch5749.png)
