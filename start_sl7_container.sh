#!/bin/bash

module load singularity/3.5.3
cvmfs_config probe fermilab.opensciencegrid.org uboone.opensciencegrid.org
singularity shell -B /cluster:/cluster,/cvmfs:/cvmfs /cluster/tufts/wongjiradlabnu/larbys/larbys-container/sl7_uboonecodedep.sif
