#!/bin/bash

#SBATCH --job-name=ubprod
#SBATCH --output=logs/gridlog_nueonly_prod.%j.%A_%a.%N.log
#SBATCH --mem-per-cpu=8000
#SBATCH --cpus-per-task=1
#SBATCH --time=4-00:00:00
#SBATCH --partition=batch,preempt
#SBATCH --error=logs/griderr_nueonly_prod.%j.%A_%a.%N.err
#SBATCH --array=500-999

# set the location of your copy of the repo here
WORKDIR=/cluster/tufts/wongjiradlabnu/twongj01/uboone_on_tufts/nu_and_cosmics

# location of the sl7 container here
container=/cluster/tufts/wongjiradlabnu/larbys/larbys-container/sl7_uboonecodedep_w_ssh.sif

# setup singularity on the node
module load singularity/3.5.3

# activate the cvmfs regions we need
cvmfs_config probe fermilab.opensciencegrid.org uboone.opensciencegrid.org

# run job script inside container
singularity exec --nv --bind /cluster:/cluster,/cvmfs:/cvmfs $container bash -c "cd ${WORKDIR} && source ${WORKDIR}/run_bnb_nue_only.sh"

