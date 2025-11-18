# Generating fully simulated neutrino interactions + cosmics

We use a modified version of the "Full MC BNB" fhicl list on the [Production Wiki](https://cdcvs.fnal.gov/redmine/projects/uboone-physics-analysis/wiki/MCC9_Production_Fhicls).

These are:

1a. `prodgenie_bnb_intrinsic_nue_cosmic_uboone_on_tufts.fcl` (modified)

1b. `prodgenie_bnb_cosmic_uboone_on_tufts.fcl` (modified)

2\. `wirecell_g4_uboone.fcl` (original)

3\. `wirecell_detsim_uboone.fcl` (original)

4\. `reco_uboone_mcc9_8_driver_stage1.fcl` (original)

5\. `standard_larcv_uboone_mctruth_prod.fcl` (modified)

The modifications are the following.

For `prodgenie_bnb_[X]_cosmic_uboone_on_tufts.fcl`, paths to corsika shower data and BNB flux data have been copied from FNAL to Tufts.
The modified fhicl in this repo points to the these locations.

For `standard_larcv_uboone_mctruth_prod.fcl`, we convert more larsoft products into the larlite format.

## Scripts

We have a run script and a submission script.

| Sample Type       | submission script        | run script            | base fcl file |
| ----------------- | ------------------------ | --------------------- | ------------- |
| BNB nue + Corsika | submit_bnbnue_corsika.sh | run_corsika_bnb_nu.sh | prodgenie_bnb_intrinsic_nue_cosmic_uboone_on_tufts.fcl |
| BNB nue only      | submit_nue_only.sh       | run_bnb_nue_only.sh   | prodgenie_bnb_nue_uboone_on_tufts.fcl | 
| BNB nu only       | submit_nu_only.sh        | run_bnb_nu_only.sh    | prodgenie_bnb_nu_uboone_on_tufts.fcl |


## Notes

To properly extract CRT hit info from the simulation, we need a modified litemaker, which is in the ublite repo.

To build, use MRB version `v3_05_03`. So to setup the build environment for uboonecode `v08_00_00_29e_dl`:


   '''
   setup mrb v3_05_03
   mrb newDev -v v08_05_00_10 -q e17:prof
   '''


To build the repo on Tufts, we need to provide a missing export:

    export IFDHC_INC=${IFDHC_FQ_DIR}/inc