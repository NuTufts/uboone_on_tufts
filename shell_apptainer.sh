#! /bin/bash
#=====================================================================
#
# Name: shell_apptainer.sh
#
# Purpose: Start SL7 interactive container.
#
# Usage:
#
# shell_apptainer.sh [options]
#
# Options:
#
# -h|--help          - Print help message.
# -u|--uboone        - Start standard MicroBooNE container (default).
# -d|--devel         - Start standard Fermilab development container.
# -g|--grid          - Start standard Fermilab grid container.
# -i|--image <image> - Start specified container image.
# -w|--writable      - Make container writable.
# -B|--bind <path>   - Specify extra bind paths (repeatable).
# --no-pnfs          - Do not bind /pnfs.
# --no-jobsub        - Do not bind jobsub_lite files.
#
# Standard container images.
#
# MicroBooNE container:
# /cvmfs/uboone.opensciencegrid.org/containers/uboone-devel-sl7
#
# Fermilab jobsub-enabled development container:
# /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:jsl
#
# Fermilab grid container:
# /cvmfs/singularity.opensciencegrid.org/fermilab/fnal-wn-sl7:latest
#
# Created: 1-Mar-2024  H. Greenlee
#
#=====================================================================

# Help function.

function dohelp {
  f=$0
  cut -c3- $f | awk '/Usage:/,/Created:/{print $0}' | head -n-3
}


# Parse arguments.

img=/cvmfs/uboone.opensciencegrid.org/containers/uboone-devel-sl7
write=0
bind=''
nopnfs=0
nojobsub=0

while [ $# -gt 0 ]; do
  case "$1" in

    # Help.
    -h|--help )
      dohelp
      exit
      ;;

    -u|--uboone )
      img=/cvmfs/uboone.opensciencegrid.org/containers/uboone-devel-sl7
      ;;

    -d|--devel )
      img=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-dev-sl7:jsl
      ;;

    -g|--grid )
      img=/cvmfs/singularity.opensciencegrid.org/fermilab/fnal-wn-sl7:latest
      ;;

    -i|--image )
      if [ $# -gt 1 ]; then
        img=$2
        shift
      fi
      ;;

    -w|--writable )
      write=1
      ;;

    -B|--bind )
      if [ $# -gt 1 ]; then
        b=$2
        if [ -e $b ]; then
          echo "Binding $b"
          bind="$bind -B $b"
        else
          echo "Bind path $b does not exist."
          exit 1
        fi
        shift
      fi
      ;;

    --no-pnfs )
      nopnfs=1
      ;;

    --no-jobsub )
      nojobsub=1
      ;;

    * )
      echo "Unknown option."
      dohelp
      exit 1
      
  esac
  shift

done

# Make sure container image is specified and exists.

if [ x$img = x ]; then
  echo "No container specified."
  exit 1
fi

if [ ! -f $img -a ! -d $img ]; then
  echo "Container does not exist: $img"
fi

echo "Using container $img"

# Add default bind options.

for dir in /cvmfs /exp/uboone /uboone /grid /run/user /opt/$USER /home /nashome /data /scratch /web /publicweb /pubhosting /etc/grid-security
do
  if [ -d $dir ]; then
    echo "Binding $dir"
    bind="$bind -B $dir"
  fi
done

dir=/pnfs/uboone
if [ $nopnfs -eq 0 ]; then
  if [ -d $dir ]; then
    echo "Binding $dir"
    bind="$bind -B $dir"
  fi
fi

if [ $nojobsub -eq 0 ]; then
  for dir in /opt/jobsub_lite /etc/condor
  do
    if [ -d $dir ]; then
      echo "Binding $dir"
      bind="$bind -B $dir"
    fi
  done

  for f in /etc/profile.d/jobsub_lite.sh
  do
    if [ -f $f ]; then
      echo "Binding $f"
      bind="$bind -B $f"
    fi
  done

fi


# Create and bind expanded passwd and group.

mypasswd=`mktemp`
getent passwd > $mypasswd
bind="$bind -B ${mypasswd}:/etc/passwd"

mygroup=`mktemp`
getent group > $mygroup
bind="$bind -B ${mygroup}:/etc/group"

# Other options.

opt=''
if [ $write -ne 0 ]; then
  opt='-w'
fi

# Forget cached platform information, if any.

unset CET_PLATINFO

# Start container.

apptainer shell $opt $bind \
          -s /bin/bash \
          --env UPS_OVERRIDE='-H Linux64bit+3.10-2.17' \
          --env PS1="[SL7][\u@\h \W]\$ " \
          $img

# Clean up.

rm -f $mypasswd
rm -f $mygroup
