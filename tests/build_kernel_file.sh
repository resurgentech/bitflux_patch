#!/bin/bash
# Copyright (c) Resurgent Technologies 2021

# Good for building a specific version of the mainline kernel

DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/..

SCRIPTNAME="$( basename "${BASH_SOURCE[0]}")"

if [ $# -lt 2 ]; then
  echo "USAGE: ${SCRIPTNAME} <DISTRO> <KERNEL_VERSION>"
  echo "---- args: $@"
  exit 1
fi

DISTRO=$1
KERNEL_VERSION=$2
LJOB="build_kernel_file"
# hack for testing
DUMPALL=$3

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

# Build Kernel
echo "=============================================================================="
echo "=== BUILD KERNEL PACKAGE ====================================================="
echo "=============================================================================="
docker run --privileged --name ${CONTAINERNAME} ${IMAGENAME} python3 ./scripts/build_kernel_package.py --distro ${DISTRO} --kernel_version ${KERNEL_VERSION} --build_type file

# Pull output
echo "=============================================================================="
echo "=== COPY OUTPUT FROM CONTAINER ==============================================="
echo "=============================================================================="
if [ -z $DUMPALL ]; then
  docker cp ${CONTAINERNAME}:/bitflux/output .
else
  rm -rf dumpall
  mkdir dumpall
  docker cp ${CONTAINERNAME}:/bitflux/ dumpall
fi


# Clean
echo "=============================================================================="
echo "=== CLEAN UP DOCKER IMAGE AND CONTAINER ======================================"
echo "=============================================================================="
docker rm ${CONTAINERNAME}
docker image rm -f ${IMAGENAME}

echo "=============================================================================="
echo "=== DONE ====================================================================="
echo "=============================================================================="
