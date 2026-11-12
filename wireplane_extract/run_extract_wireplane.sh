#!/bin/bash
# run_extract_wireplane.sh -- art file -> wire-plane HDF5, in the uboonecode container.
#
#   bash run_extract_wireplane.sh <input_art.root> <output.h5> [extra extractor args]
#
# Run on a compute node (inside a Slurm allocation). Starts the SL7 container with
# cvmfs through singcvmfs (EL7 cvmfsexec dist), sets up uboonecode and runs
# extract_wireplane_h5.py. The first run on a node is slow (cold cvmfs cache).
set -e
IN=$(readlink -f "${1:?input art ROOT file}")
OUT=$(readlink -m "${2:?output hdf5 file}")
shift 2
UBOONECODE_VERSION=${UBOONECODE_VERSION:-v08_00_00_40a_dl}
UBOONECODE_QUAL=${UBOONECODE_QUAL:-e17:prof}

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CVMFSEXEC_EL7=/cluster/tufts/wongjiradlab/larbys/cvmfs_containers/cvmfsexec-el7
CONTAINER=/cluster/tufts/wongjiradlab/larbys/cvmfs_containers/uboone-devel-sl7-11
PY27_SITE=${PY27_SITE:-$HERE/py27_site}
if [ ! -d "$PY27_SITE/h5py" ]; then
  echo "h5py for python 2.7 not found in $PY27_SITE; run: bash $HERE/install_py27_h5py.sh"; exit 1
fi
BUILD_DIR=${WIREPLANE_BUILD_DIR:-$HERE/build_${UBOONECODE_VERSION}}
OUTDIR=$(dirname "$OUT"); mkdir -p "$OUTDIR" "$BUILD_DIR"

export SINGCVMFS_REPOSITORIES=uboone.opensciencegrid.org,larsoft.opensciencegrid.org,fermilab.opensciencegrid.org
export SINGCVMFS_CACHEDIR=/tmp/cvmfs-cache-${USER}-el7
export SINGCVMFS_LOGDIR=${SINGCVMFS_LOGDIR:-/tmp/singcvmfs-logs-${USER}}
mkdir -p "$SINGCVMFS_CACHEDIR" "$SINGCVMFS_LOGDIR"

GIT_COMMIT=$(git -C "$HERE" rev-parse --short HEAD 2>/dev/null || echo unknown)
git -C "$HERE" diff --quiet HEAD -- "$HERE" 2>/dev/null || GIT_COMMIT="${GIT_COMMIT}+dirty"

INNER=$(mktemp "$OUTDIR/_wireplane_inner.XXXXXX.sh")
trap 'rm -f "$INNER"' EXIT
cat > "$INNER" <<EOS
source /cvmfs/uboone.opensciencegrid.org/products/setup_uboone.sh > /dev/null 2>&1
setup uboonecode $UBOONECODE_VERSION -q $UBOONECODE_QUAL || { echo "setup uboonecode failed"; exit 1; }
export PYTHONPATH=$PY27_SITE:\$PYTHONPATH
export HDF5_USE_FILE_LOCKING=FALSE
export WIREPLANE_GIT_COMMIT=$GIT_COMMIT
python $HERE/extract_wireplane_h5.py -i "$IN" -o "$OUT" --build-dir "$BUILD_DIR" $@
EOS
"$CVMFSEXEC_EL7/singcvmfs" -s exec -B /cluster:/cluster "$CONTAINER" bash "$INNER" 2>&1 \
  | grep -v '^%MSG\|^Product created with id\|^$'
exit ${PIPESTATUS[0]}
