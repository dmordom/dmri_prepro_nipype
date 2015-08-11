#!/bin/bash

# THIS FILE SHOULD BE COPIED INTO THE PIPELINE OUTPUT FOLDER

text()  {

echo ; echo " Call: "$0 " <CHUNK_NR>"
echo "   example: $0 1"
}
if [ $# -lt 1 ]  ;  then text ; exit ; fi
if [ $# -gt 1 ]  ;  then text ; exit ; fi
CHUNK_NR=$*
echo "chunk number: $CHUNK_NR"

export PATH="$PATH:/a/sw/misc/linux/diffusion:/usr/lib/mrtrix/bin"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/home/raid2/moreno/libs/"

# this are already written in the script but change for subject/hemi
