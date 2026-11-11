#!/bin/bash

#module load singularity/3.5.3
module load apptainer/1.2.4-suid

cvmfs_config probe fermilab.opensciencegrid.org uboone.opensciencegrid.org

# singularity shell -B /cluster:/cluster,/cvmfs:/cvmfs /cluster/tufts/wongjiradlabnu/larbys/larbys-container/sl7_uboonecodedep_w_ssh.sif
apptainer shell -B /cluster:/cluster,/cvmfs:/cvmfs /cvmfs/uboone.opensciencegrid.org/containers/uboone-devel-sl7
