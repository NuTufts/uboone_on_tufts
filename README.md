# uboone_on_tufts
Scripts for running the MicroBooNE simulation on the Tufts cluster

Production workflow wiki: https://cdcvs.fnal.gov/redmine/projects/uboone-physics-analysis/wiki/MCC9_Production_Fhicls

Steps

* if not at Tufts, connect to Tufts VPN (using Cisco anyconnect)
* ssh into the Tufts cluster: `ssh -XY [username]@login.pax.tufts.edu`
* start an interactive job: `srun --pty -p wongjiradlab --mem-per-cpu=4000 --cpus-per-task=2 --time 4:00:00 bash`
* go to some working directory in one of your folders on the wongjiradlabnu drive
* setup to be able to use singularity: `module load singularity/3.5.3`
* activate cvmfs remote drives: `cvmfs_config probe fermilab.opensciencegrid.org uboone.opensciencegrid.org`
* can check you see them: `ls /cvmfs/`
* start the SL7 container: `singularity shell -B /cluster:/cluster,/cvmfs:/cvmfs /cluster/tufts/wongjiradlabnu/larbys/larbys-container/sl7_uboonecodedep.sif`
* start a bash shell in the container: `bash`
* setup microboone software environment: `source /cvmfs/uboone.opensciencegrid.org/products/setup_uboone.sh`
* setup microboone sim/reco software: `setup uboonecode v08_00_00_40a_dl -q e17:prof`
* go to a folder where you want to put output files
* create kinemetic information for particles we will sim: `lar -c [prod_single_....fcl] -n [number of particles e.g. 50]`
* run the geant4 simulation for these particles: `lar -c wirecell_g4_uboone.fcl -s [output of previous step]`
* run the wire simulation: `lar -c wirecell_detsim_uboone.fcl -s [output of previous step]`
* run the first stage reconstruction (reco1): `lar -c reco_uboone_mcc9_8_driver_stage1.fcl -s [output of previous step]`
* run the larcv data maker: `lar -c standard_larcv_uboone_mctruth_prodtufts.fcl -s [output of previous step]`

From here, you should have images with truth metadata inside a one or more rootfiles.

Note that in the last step, you need a bug-fixed `.fcl` file that is note found in the MicroBooNE code saved in `/cvmfs`.
You'll find a copy in the folders with scripts for generating particular datasets. e.g.

    single_particle_gen/standard_larcv_uboone_mctruth_prodtufts.fcl
    single_particle_gen/supera_mctruthonly_prodtufts.fcl




