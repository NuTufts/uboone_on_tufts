#!/bin/bash

#SBATCH --job-name=train_larmatch
#SBATCH --output=gridlog_train_larvoxel_pass0.log
#SBATCH --mem-per-cpu=8000
#SBATCH --cpus-per-task=5
#SBATCH --time=3-00:00:00
#SBATCH --gres=gpu:a100:4
#SBATCH --partition=ccgpu
#SBATCH --error=gridlog_train_larvoxel.%j.%N.err

# set the location of your copy of the repo here
WORKDIR=/cluster/tufts/wongjiradlabnu/twongj01/uboone_on_tufts

# location of the sl7 container here
container=/cluster/tufts/wongjiradlabnu/larbys/larbys-container/sl7_uboonecodedep.sif

# setup singularity on the node
module load singularity/3.5.3

# activate the cvmfs regions we need
cvmfs_config probe fermilab.opensciencegrid.org uboone.opensciencegrid.org

# run job script inside container
singularity exec --nv --bind /cluster/tufts/:/cluster/tufts/,/tmp:/tmp $container bash -c "source ${WORKDIR}/run_corsika_nu.sh"

