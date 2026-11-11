#!/bin/bash

cp larlite_reco2d.root larlite_reco2d_temp.root
cp larlite_opreco.root larlite_opreco_temp.root
cp larlite_simch.root larlite_simch_temp.root
cp larlite_crt.root larlite_crt_temp.root

rootrm larlite_reco2d_temp.root:larlite_id_tree
rootrm larlite_opreco_temp.root:larlite_id_tree
rootrm larlite_simch_temp.root:larlite_id_tree
rootrm larlite_crt_temp.root:larlite_id_tree
dlmerged="dlmerged.root"
hadd ${dlmerged} larlite_mcinfo.root larlite_simch_temp.root larlite_opreco_temp.root larlite_reco2d_temp.root larlite_crt_temp.root larcv_mctruth.root
