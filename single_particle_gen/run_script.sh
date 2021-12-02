#!/bin/bash

# create kinemetic information for particles
SCRIPT_1="prod_proton_0-2GeV_isotropic_uboone.fcl"
# lar -c ${SCRIPT_1} -n 3
lar -c ${SCRIPT_1} -n 3
#DATE_1= date +"%Y%m%dT%H%M%S"
FILE_1="prod_p_0-2GeV_isotropic_uboone_"*"_gen.root"

# run the geant4 simulation for these particles
SCRIPT_2="wirecell_g4_uboone.fcl"
lar -c ${SCRIPT_2} --source ${FILE_1}
#DATE_2= date +"%Y%m%dT%H%M%S"
FILE_2="prod_p_0-2GeV_isotropic_uboone_"*"_gen_"*"_g4.root"

# run the wire simulation
SCRIPT_3="wirecell_detsim_uboone.fcl"
lar -c ${SCRIPT_3} -s ${FILE_2}
#DATE_3= date +"%Y%m%dT%H%M%S"
FILE_3="prod_p_0-2GeV_isotropic_uboone_"*"_gen_"*"_g4_"*"_detsim.root"

# run the first stage reconstruction (reco1):
SCRIPT_4="reco_uboone_mcc9_8_driver_stage1.fcl"
lar -c ${SCRIPT_4} -s ${FILE_3}
#DATE_4= date +"%Y%m%dT%H%M%S"
FILE_4="prod_p_0-2GeV_isotropic_uboone_"*"_gen_"*"_g4_"*"_detsim_"*"_reco1.root"

# run the larcv data maker:
SCRIPT_5="standard_larcv_uboone_mctruth_prodtufts.fcl"
lar -c ${SCRIPT_5} -s ${FILE_4}
# FILE_5= "prod_p_0-2GeV_isotropic_uboone_${DATE_1}_gen_${DATE_2}_g4_${DATE_3}_detsim_${DATE_4}_reco1__postdlmctruth.root"

hadd FINAL.root larcv_mctruth.root larlite_mcinfo.root
