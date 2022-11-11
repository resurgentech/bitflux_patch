#!/bin/bash

#Helper to edit directories under ./patches/X/Y/ to link files back in ./patches/files/

DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/..
WORKING_DIR=`pwd`


KERNEL_VERSION=$1;
SWAPHINTS=$2
RECLAIM_PAGE=$3
DRYRUN=$4

if [ -z ${KERNEL_VERSION} ]
then
  echo "Missing KERNEL_VERSION.  style is 5.10";
  failed="1"
fi

if [ -z ${SWAPHINTS} ]
then
  echo "Missing SWAPHINTS. style is ./patches/files/swaphints.02.c[,ubuntu2204]";
  failed="1"
fi

if [ -z ${RECLAIM_PAGE} ]
then
  echo "Missing RECLAIM_PAGE. style is ./patches/files/reclaim_page.02.c[,ubuntu2204]";
  failed="1"
fi

if [ ! -z $failed ]; then
  echo "Run \"./$( basename "${BASH_SOURCE[0]}") KERNEL_VERSION SWAPHINTS RECLAIM_PAGE [DRYRUN]\"";
  exit 1;
fi


KVONE=$(echo ${KERNEL_VERSION} | awk -F'.' '{print $1}')
KVTWO=$(echo ${KERNEL_VERSION} | awk -F'.' '{print $2}')
KERNEL_DIR="${WORKING_DIR}/patches/${KVONE}/${KVTWO}"

SONE=$(echo $(basename ${SWAPHINTS}) | awk -F',' '{print $1}')
STWO=$(echo $(basename ${SWAPHINTS}) | awk -F',' '{print "."$2}')
if [ ${STWO} == "." ]; then
  STWO=""
fi
SWAPHINTS_SRC="../../../../files/${SONE}"
SWAPHINTS_DST="swaphints.c${STWO}"

RONE=$(echo $(basename ${RECLAIM_PAGE}) | awk -F',' '{print $1}')
RTWO=$(echo $(basename ${RECLAIM_PAGE}) | awk -F',' '{print "."$2}')
if [ ${RTWO} == "." ]; then
  RTWO=""
fi
RECLAIM_PAGE_SRC="../../files/${RONE}"
RECLAIM_PAGE_DST="mm__vmscan_c--__reclaim_page.merge${RTWO}"

echo "Editing ${KERNEL_DIR}"
echo "Soft linking ${SWAPHINTS_SRC} to ${SWAPHINTS_DST}"
echo "Soft linking ${RECLAIM_PAGE_SRC} to ${RECLAIM_PAGE_DST}"

echo ""
sleep 2

if [ ! -z $DRYRUN ]; then
  exit 0
fi

cd ${KERNEL_DIR}/fs/proc
rm ${SWAPHINTS_DST}
ln -s ${SWAPHINTS_SRC} ${SWAPHINTS_DST}

cd ${KERNEL_DIR}
rm ${RECLAIM_PAGE_DST}
ln -s ${RECLAIM_PAGE_SRC} ${RECLAIM_PAGE_DST}
