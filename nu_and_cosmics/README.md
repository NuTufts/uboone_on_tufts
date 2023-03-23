# Generating fully simulated neutrino interactions + cosmics

We use a modified version of the "Full MC BNB" fhicl list on the [Production Wiki](https://cdcvs.fnal.gov/redmine/projects/uboone-physics-analysis/wiki/MCC9_Production_Fhicls).

These are:

  1a. `prodgenie_bnb_intrinsic_nue_cosmic_uboone_on_tufts.fcl` (modified)
  1b. `prodgenie_bnb_cosmic_uboone_on_tufts.fcl` (modified)
  2. `wirecell_g4_uboone.fcl` (original)
  3. `wirecell_detsim_uboone.fcl` (original)
  4. `reco_uboone_mcc9_8_driver_stage1.fcl` (original)
  5. `standard_larcv_uboone_mctruth_prod.fcl` (modified)

The modifications are the following.

For `prodgenie_bnb_[X]_cosmic_uboone_on_tufts.fcl`, paths to corsika shower data and BNB flux data have been copied from FNAL to Tufts.
The modified fhicl in this repo points to the these locations.

For `standard_larcv_uboone_mctruth_prod.fcl`, we convert more larsoft products into the larlite format.

## Scripts

We have a run script and a submission script.


