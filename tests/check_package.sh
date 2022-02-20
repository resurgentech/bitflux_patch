#!/bin/bash
# Copyright (c) Resurgent Technologies 2021

DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/..

SCRIPTNAME="$( basename "${BASH_SOURCE[0]}")"

if [ $# -lt 2 ]; then
  echo "USAGE: ${SCRIPTNAME} <DISTRO> <JOBNAME>"
  echo "---- args: $@"
  exit 1
fi

DISTRO=$1
LJOB=$2
# hack for testing
NOBUILD=$3

IMAGENAME="resurgentech_local/${LJOB}:latest"
CONTAINERNAME="${LJOB}"

echo "Running \"${SCRIPTNAME} ${DISTRO} ${LJOB}\""
echo "    Docker image name =${IMAGENAME}"
echo "    Container name    =${CONTAINERNAME}"

# Build image
echo "=============================================================================="
echo "=== BUILD DOCKER IMAGE ======================================================="
echo "=============================================================================="
cp ./scripts/docker/Dockerfile.${DISTRO} .
docker pull resurgentech/kernel_build-${DISTRO}:latest
docker rm --force ${CONTAINERNAME}
docker rmi --force ${IMAGENAME}
docker build -f Dockerfile.${DISTRO} . --tag ${IMAGENAME}
rm Dockerfile.${DISTRO}

echo "=============================================================================="
echo "=== BUILD KERNEL PACKAGE ====================================================="
echo "=============================================================================="
docker run --privileged --name ${CONTAINERNAME} ${IMAGENAME} python3 ./scripts/check_package.py --distro ${DISTRO}

# Pull output
echo "=============================================================================="
echo "=== COPY OUTPUT FROM CONTAINER ==============================================="
echo "=============================================================================="
docker cp ${CONTAINERNAME}:/bitflux/package.yaml .

# Clean
echo "=============================================================================="
echo "=== CLEAN UP DOCKER IMAGE AND CONTAINER ======================================"
echo "=============================================================================="
docker rm ${CONTAINERNAME}
docker image rm -f ${IMAGENAME}

echo "=============================================================================="
echo "=== DONE ====================================================================="
echo "=============================================================================="
