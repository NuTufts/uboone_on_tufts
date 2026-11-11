#!/bin/bash

WORKDIR=/cluster/tufts/wongjiradlabnu/twongj01/uboone_on_tufts/nu_and_cosmics/
UBOONECODE_VERSION=v08_00_00_40a_dl
UBOONECODE_QUAL=e17:prof
DEV_UBOONECODE_FOLDER=v08_00_00_40a_dl

# setup container
source /cvmfs/uboone.opensciencegrid.org/products/setup_uboone.sh
unsetup mrb
setup mrb v3_05_03
setup uboonecode ${UBOONECODE_VERSION} -q ${UBOONECODE_QUAL}

# we need our ublite modifications
cd $WORKDIR/dev/${DEV_UBOONECODE_FOLDER}
source localProducts_larsoft_v08_05_00_13_e17_prof/setup
mrbsetenv
