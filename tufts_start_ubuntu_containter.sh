#!/bin/bash
#container=/cluster/tufts/wongjiradlab/larbys/larbys-containers/ubdl_py3deps_u18.04_cu11_pytorch1.7.1.simg
#container=/cluster/tufts/wongjiradlab/larbys/larbys-containers/ubdldeps_u20.02_pytorch1.9_py3.simg
#container=/cluster/tufts/wongjiradlabnu//larbys/larbys-container/singularity_minkowskiengine_u20.04.cu111.torch1.9.0.sif
container=/cluster/tufts/wongjiradlabnu//larbys/larbys-container/singularity_minkowskiengine_u20.04.cu111.torch1.9.0_comput8.sif
module load singularity/3.1.0
singularity shell --nv --bind /cluster/tufts/:/cluster/tufts/,/tmp:/tmp $container
