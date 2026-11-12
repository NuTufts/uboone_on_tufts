#!/bin/bash
# Vendor h5py for the python 2.7 that comes with uboonecode v08 (no h5py in that stack).
# Run on the host (needs pip + network), once:  bash install_py27_h5py.sh [site_dir]
set -e
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SITE=${1:-$HERE/py27_site}
mkdir -p "$SITE/_wheels"
python3 -m pip download --no-deps --python-version 27 --implementation cp --abi cp27m \
  --platform manylinux1_x86_64 --only-binary=:all: -d "$SITE/_wheels" h5py==2.10.0 six==1.16.0
for w in "$SITE"/_wheels/*.whl; do unzip -q -o "$w" -d "$SITE"; done
echo "installed into $SITE"
