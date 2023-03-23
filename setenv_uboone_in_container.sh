#!/bin/bash 

echo "activating the microboone larsoft software repo on CVMFS"
echo "this needs to be run inside the SL7 container"
echo "(start container using: source start_sl7_container.sh)"

source /cvmfs/uboone.opensciencegrid.org/products/setup_uboone.sh

echo "setup the MicroBooNE larsoft environment using command such as:"
echo ""
echo "setup uboonecode v08_00_00_40a_dl -q e17:prof"
echo ""
echo "to find different code versions use: "
echo ""
echo "ups list -aK+ uboonecode"
