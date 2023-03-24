#!/bin/bash

WORKDIR=/cluster/tufts/wongjiradlabnu/twongj01/mlreco/uboone_on_tufts
UBOONECODE_VERSION=v08_00_00_40a_dl
UBOONECODE_QUAL=e17:prof
INPUTLIST=${WORKDIR}/corsika_bnbnu_runlist.txt
OUTPUT_DIR=/cluster/tufts/wongjiradlabnu/larbys/data/ub_on_tufts/bnbnu_corsika/

OFFSET=0
TAG=coriska_bnb_nu

stride=1
jobid=${SLURM_ARRAY_TASK_ID}
let startline=$(expr "${OFFSET}+${stride}*${jobid}")

mkdir -p $WORKDIR
jobworkdir=`printf "%s/ubprod_on_tufts_${TAG}_jobid_%03d" $WORKDIR $jobid`
mkdir -p $jobworkdir
mkdir -p $OUTPUT_DIR

local_jobdir=`printf /tmp/mlreco_dataprep_${TAG}_jobid%03d $jobid`
rm -rf $local_jobdir
mkdir -p $local_jobdir
cd $local_jobdir
touch log_${TAG}_jobid${jobid}.txt
local_logfile=`echo ${local_jobdir}/log_${TAG}_jobid${jobid}.txt`

# setup container
source /cvmfs/uboone.opensciencegrid.org/products/setup_uboone.sh
setup uboonecode ${UBOONECODE_VERSION} -q ${UBOONECODE_QUAL}

for i in {1..5}
do
    # get job request number
    fileno=`sed -n ${lineno}p ${INPUTLIST}`

    # stage 1: generate cosmic and neutrino primaries
    #lar -c ${WORKDIR}/prodgenie_bnb_intrinsic_nue_cosmic_uboone_on_tufts.fcl -s $NENTRIES
    touch prodgen_gen.root

    # get file name of stage one
    genfile=`find $PWD -name *gen.root`

    # stage 2: geant4
    #lar -c wirecell_g4_uboone.fcl -s $genfile
    touch prodgen_g4.root    
    rm $genfile
    g4file=`find $PWD -name *g4.root`

    # stage 3: detsim
    lar -c wirecell_detsim_uboone.fcl -s $g4file
    touch prodgen_detsim.root    
    rm $g4file
    detsimfile=`find $PWD -name *detsim.root`

    # stage 4: reco1
    lar -c reco_uboone_mcc9_8_driver_stage1.fcl -s $detsimfile
    touch prodgen_reco1.root        
    rm $detsimfile
    reco1file=`find $PWD -name *reco1.root`

    # stage 5: conver to larcv and larlite
    lar -c standard_larcv_uboone_mctruth_prod.fcl -s $reco1file

    # merge larcv and larlite file
    # for larlite files, we need to remove larlite_id_tree,
    # so that when we merge we do not have multiple copies concatenated together
    #rootrm larlite_reco2d.root:larlite_id_tree
    #rootrm larlite_opreco.root:larlite_id_tree
    #rootrm larlite_simch.root:larlite_id_triee
    #rootrm larlite_crt.root:larlite_id_tree
    #dlmerged=`printf \"dlmerged_${TAG}_fileno%06d.root\" ${fileno}`
    #hadd ${dlmerged} larlite_mcinfo.root larlite_simch.root larlite_opreco.root larlite_reco3d.root larlite_crt.root larcv_mctruth.root
    touch ${dlmerged}

    # copy to output location
    let nsubdir1=${fileno}/1000
    zsubdir1=`printf %03d ${nsubdir1}`

    let subdir2=${fileno}/100
    zsubdir2=`printf %03d ${nsubdir2}`

    outpath=${OUTDIR}/${zsubdir1}/${zsubdir2}/${dlmerged}

    cp ${dlmerged} ${outpath}

    # destroy all root files from this run
    rm *.root

done

ls -lh out_*.root >> ${local_logfile} 2>&1

# copy log files
cp ${local_logfile} ${jobworkdir}/

cd /tmp
rm -r $local_jobdir
