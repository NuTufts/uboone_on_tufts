#!/bin/bash

#SBATCH --job-name=ubprod
#SBATCH --output=logs/bnb_nu_corsika/gridlog_ubprod_bnb_nu_corsika.%j.%A_%a.%N.log
#SBATCH --mem-per-cpu=8000
#SBATCH --cpus-per-task=1
#SBATCH --time=1-00:00:00
#SBATCH --partition=batch
#SBATCH --error=logs/bnb_nu_corsika/griderr_ubprod_bnb_nu_corsika.%j.%A_%a.%N.err
#SBATCH --array=500-999

# set the location of your copy of the repo here
WORKDIR=/cluster/tufts/wongjiradlabnu/twongj01/uboone_on_tufts/nu_and_cosmics

# location of the sl7 container here
container=/cvmfs/uboone.opensciencegrid.org/containers/uboone-devel-sl7

# setup singularity on the node
#module load singularity/3.5.3
module load apptainer/1.2.4-suid

# activate the cvmfs regions we need
cvmfs_config probe fermilab.opensciencegrid.org uboone.opensciencegrid.org

# run job script inside container
apptainer exec --bind /cluster:/cluster,/cvmfs:/cvmfs $container bash -c "cd ${WORKDIR} && source ${WORKDIR}/run_corsika_bnb_nu.sh"

