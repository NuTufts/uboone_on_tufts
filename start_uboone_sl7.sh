#!/bin/bash

# Uses a cvmfsexec dist built for EL7 (cvmfs 2.12.7) to match the SL7 container.
# The module cvmfsexec/4.5.1 dist is built for EL9 and its cvmfs2 binary cannot
# run inside the SL7 container (needs GLIBC_2.34; SL7 has 2.17).
CVMFSEXEC_EL7=/cluster/tufts/wongjiradlab/larbys/cvmfs_containers/cvmfsexec-el7

ORIGINAL_PWD="${SLURM_SUBMIT_DIR:-$PWD}"
export SINGCVMFS_REPOSITORIES=uboone.opensciencegrid.org,fermilab.opensciencegrid.org,larsoft.opensciencegrid.org
export container=/cluster/tufts/wongjiradlab/larbys/cvmfs_containers/uboone-devel-sl7-11
export SINGCVMFS_LOGDIR="${ORIGINAL_PWD}/singcvmfs-logs"

"$CVMFSEXEC_EL7/singcvmfs" shell -B /cluster:/cluster "$container"
