#!/bin/bash

WORKDIR=/cluster/tufts/wongjiradlabnu/twongj01/uboone_on_tufts/nu_and_cosmics/
UBOONECODE_VERSION=v08_00_00_40a_dl
UBOONECODE_QUAL=e17:prof
INPUTLIST=${WORKDIR}/bnb_nue_only.runlist
OUTPUT_DIR=/cluster/tufts/wongjiradlabnu/larbys/data/ub_on_tufts/bnb_nue_only/

NENTRIES=50

OFFSET=0
TAG=bnb_nue_only

stride=5
jobid=${SLURM_ARRAY_TASK_ID}
let startline=$(expr "${OFFSET}+${stride}*${jobid}")

mkdir -p $WORKDIR
jobworkdir=`printf "%s/workdir/nueprod_on_tufts_${TAG}_jobid_%03d" $WORKDIR $jobid`
mkdir -p $jobworkdir
mkdir -p $OUTPUT_DIR

local_jobdir=`printf /tmp/nue_prod_tufts_${TAG}_jobid%03d $jobid`
rm -rf $local_jobdir
mkdir -p $local_jobdir
cd $local_jobdir
touch log_${TAG}_jobid${jobid}.txt
local_logfile=`echo ${local_jobdir}/log_${TAG}_jobid${jobid}.txt`

# setup container
source /cvmfs/uboone.opensciencegrid.org/products/setup_uboone.sh
setup uboonecode ${UBOONECODE_VERSION} -q ${UBOONECODE_QUAL}

# we need our ublite modifications
cd $WORKDIR/dev/${UBOONECODE_VERSION}
source localProducts_larsoft_v08_05_00_13_e17_prof/setup
mrbsetenv

# go back to the job dir
cd $local_jobdir

# copy fcl files
cp $WORKDIR/*.fcl .

ls >> $local_logfile

for i in {1..5}
do

    let lineno=$startline+$i

    # get job request number
    fileno=`sed -n ${lineno}p ${INPUTLIST}`
    echo "FILE NO: ${fileno}"

    # stage 1: generate cosmic and neutrino primaries

    job_fcl=$(printf "prodgenie_bnb_nue_uboone_on_tufts_file%d.fcl" ${fileno})
    cp prodgenie_bnb_nue_uboone_on_tufts.fcl $job_fcl
    echo "prodgenie job fcl: ${job_fcl}"
    echo "source.firstEvent: 1" >> $job_fcl
    echo "source.firstRun: ${fileno}" >> $job_fcl
    
    lar -c $job_fcl -n $NENTRIES >> $local_logfile

    # get file name of stage one
    genfile=`find $PWD -name *gen.root` >> $local_logfile
    echo "Created gen file: ${genfile}"

    # stage 2: geant4
    lar -c wirecell_g4_uboone.fcl -s $genfile -n $NENTRIES >> $local_logfile
    rm $genfile
    g4file=`find $PWD -name *g4.root`
    echo "Created g4 file: ${genfile}"

    # stage 3: detsim
    lar -c wirecell_detsim_uboone.fcl -s $g4file -n $NENTRIES >> $local_logfile
    rm $g4file
    detsimfile=`find $PWD -name *detsim.root`
    echo "Created detsim file: ${detsimfile}"

    # stage 4: reco1
    lar -c reco_uboone_mcc9_8_driver_stage1.fcl -s $detsimfile -n $NENTRIES >> $local_logfile
    rm $detsimfile
    reco1file=`find $PWD -name *reco1.root`
    echo "Created reco1 file: ${reco1file}"

    # stage 5: conver to larcv and larlite
    lar -c standard_larcv_uboone_mctruth_prod_on_tufts.fcl -s $reco1file -n $NENTRIES >> $local_logfile

    # merge larcv and larlite file
    # for larlite files, we need to remove larlite_id_tree,
    # so that when we merge we do not have multiple copies concatenated together
    rootrm larlite_reco2d.root:larlite_id_tree
    rootrm larlite_opreco.root:larlite_id_tree
    rootrm larlite_simch.root:larlite_id_tree
    rootrm larlite_crt.root:larlite_id_tree
    dlmerged=`printf dlmerged_${TAG}_fileno%06d.root ${fileno}`
    hadd ${dlmerged} larlite_mcinfo.root larlite_simch.root larlite_opreco.root larlite_reco2d.root larlite_crt.root larcv_mctruth.root >> $local_logfile

    # copy to output location
    let nsubdir1=$(expr "${fileno}/1000")
    zsubdir1=`printf %03d ${nsubdir1}`

    let nsubdir2=$(expr "${fileno}/100")
    zsubdir2=`printf %03d ${nsubdir2}`

    outfolder=${OUTPUT_DIR}/${zsubdir1}/${zsubdir2}/
    echo "Output folder: ${outfolder}"

    mkdir -p $outfolder
    outpath=${OUTPUT_DIR}/${zsubdir1}/${zsubdir2}/${dlmerged}

    cp ${dlmerged} ${outpath}

    # destroy all root files from this run
    rm *.root

done

# copy log files
cp ${local_logfile} ${jobworkdir}/

# clean up
cd /tmp
rm -r $local_jobdir
