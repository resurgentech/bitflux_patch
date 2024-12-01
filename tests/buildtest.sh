#!/bin/bash

DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/..
WORKING_DIR=`pwd`

KERNEL_VERSION=$1;

for i in "$@"; do
  case $i in
    # Don't actually test
    --notest)
      NO_TEST="NO_TEST"
      shift
      ;;
    # Patch but don't build
    --patchonly)
      PATCHONLY="--nobuild";
      shift
      ;;
    # Don't build or patch
    --skipbuild)
      SKIPBUILD="SKIPBUILD"
      shift
      ;;
    # Build a minimum via kernel with 
    --smallbuild)
      SMALLBUILD="SMALLBUILD"
      shift
      ;;
    --dryrun)
      DRYRUN="DRYRUN"
      shift
      ;;
    # OVERRIDE = distro to pass to build and test scripts
    --distro=*)
      DISTRO="${i#*=}"
      shift
      ;;
    # OVERRIDE = docker_image to build kernel in
    --docker_image=*)
      DOCKER_IMAGE="${i#*=}"
      shift
      ;;
    # OVERRIDE = vagrantbox to test in
    --vagrantbox=*)
      VAGRANTBOX="${i#*=}"
      shift
      ;;
    # Don't remove the VM after test, for debug
    --noteardown)
      NOTEARDOWN="--noteardown"
      shift
      ;;
    # Sets BitFlux APIToken for 
    --apitoken=*)
      BITFLUX_API_TOKEN="${i#*=}"
      shift
      ;;
    *)
      ;;
  esac
done

if [ -z ${KERNEL_VERSION} ]
then
  echo "Missing KERNEL_VERSION.  style is 5.10.1 or 'master'";
  echo "${BASH_SOURCE[0]} KERNEL_VERSION []";
fi


KVONE=$(echo ${KERNEL_VERSION} | awk -F'.' '{print $1}')
KVTWO=$(echo ${KERNEL_VERSION} | awk -F'.' '{print $2}')

if [ -z ${DISTRO} ]; then
  DISTRO=ubuntu2404
  DOCKER_IMAGE="resurgentech/kernel_build-ubuntu2404:latest"
  VMIMAGE="ubuntu2404"
fi

if [ ${KERNEL_VERSION} == "master" ]; then
  ACTUAL_KERNEL_VERSION="master"
else
  ACTUAL_KERNEL_VERSION="v${KERNEL_VERSION}"
fi

if [ -z ${SMALLBUILD} ]; then
  BUILD_TYPE="git"
else
  BUILD_TYPE="gitminimal"
  NO_TEST="NO_TEST"
fi

if [ -z ${BITFLUX_API_TOKEN} ]; then
  if [ -z "${NO_TEST}" ]; then
    BITFLUX_API_TOKEN=$(cat config.yaml | grep bitflux_api_token | awk '{print $2}')
    if [ -z ${BITFLUX_API_TOKEN} ]; then
      echo "Missing BitFlux API Token"
      echo "  Either --apitoken=XXXXX or have a line in config.yaml 'bitflux_api_token: XXXX'"
    fi
  fi
fi


echo "OPTIONS:"
echo "  NO_TEST=${NO_TEST}"
echo "  PATCHONLY=${PATCHONLY}"
echo "  SKIPBUILD=${SKIPBUILD}"
echo "  SMALLBUILD=${SMALLBUILD}"
echo "  NOTEARDOWN=${NOTEARDOWN}"
echo "  BITFLUX_API_TOKEN=${BITFLUX_API_TOKEN}"
echo ""
echo " Using:"
echo "  KERNEL_VERSION=${ACTUAL_KERNEL_VERSION}"
echo "  DISTRO=${DISTRO}"
echo "  DOCKER_IMAGE=${DOCKER_IMAGE}"
echo "  VAGRANTBOX=${VAGRANTBOX}"
echo "  BUILD_TYPE=${BUILD_TYPE}"
echo ""

sleep 2

if [ -z ${SKIPBUILD} ]
then
  cmd="\
  ./build.py --buildnumber 0 \
             --kernel_version ${ACTUAL_KERNEL_VERSION} \
             --docker_image ${DOCKER_IMAGE} \
             --distro ${DISTRO} \
             --build_type ${BUILD_TYPE} \
             ${PATCHONLY};"
  echo $cmd
  echo ""
  if [ -z ${DRYRUN} ]; then
    eval $cmd
  fi


  # Only run this if we are doing a real build, ie not a patch only build
  if [ -z ${PATCHONLY} ]; then
    # Make tarball
    cd output/;
    rm -f ../latest.tar.gz;
    rm -f a.tar.gz;
    tar czf a.tar.gz *.deb;
    cd ..;

    BUILD_CHECK=$(cat output/swaphints_build_output.json | grep check | awk '{print $2}' | sed 's/,$//')

    if [ ${BUILD_CHECK} != "0" ]; then
      echo "BUILD_CHECK=${BUILD_CHECK}"
      exit 1
    fi
  fi
fi

if [ ! -z ${NO_TEST} ]; then
  echo "${NO_TEST} - Exiting after build as requested"
  exit 1
fi

cmd="sudo cp /var/lib/libvirt/images/${DISTRO}.qcow2 /var/lib/libvirt/images/manualtest.qcow2"
echo $cmd
echo ""
if [ -z ${DRYRUN} ]; then
  eval $cmd
fi

cmd=" \
./tests/install_test.py --distro ${DISTRO} \
                        --machine_name manualtest \
                        --deviceid manualtest \
                        --manual_modprobe \
                        --kernel_revision ${KERNEL_VERSION}-custom-1 \
                        --kernel_version ${KERNEL_VERSION}-custom \
                        --tarballkernel output/a.tar.gz \
                        ${NOTEARDOWN};"
echo $cmd
echo ""
if [ -z ${DRYRUN} ]; then
  eval $cmd
fi
exit $?