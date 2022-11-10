#!/bin/bash

DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/..
WORKING_DIR=`pwd`

KERNEL_VERSION=$1;

for i in "$@"; do
  case $i in
    --notest)
      NO_TEST="NO_TEST"
      shift
      ;;
    --patchonly)
      PATCHONLY="--nobuild";
      shift
      ;;
    --skipbuild)
      SKIPBUILD="SKIPBUILD"
      shift
      ;;
    --smallbuild)
      SMALLBUILD="SMALLBUILD"
      shift
      ;;
    --distro=*)
      DISTRO="${i#*=}"
      shift
      ;;
    --docker_image=*)
      DOCKER_IMAGE="${i#*=}"
      shift
      ;;
    --vagrantbox=*)
      VAGRANTBOX="${i#*=}"
      shift
      ;;
    --noteardown)
      NOTEARDOWN="--noteardown"
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
  if [ "$KVONE" -lt "5" ]; then
    if [ "$KVTWO" == "14" ]; then # =v4.14
      DISTRO=amazonlinux2
      DOCKER_IMAGE="resurgentech/kernel_build-amazonlinux2:latest"
      VAGRANTBOX="jaredeh/ubuntu2004-server"
    else # >v4.14 <v5.0
      DISTRO=rockylinux8
      DOCKER_IMAGE="resurgentech/kernel_build-rockylinux8:latest"
      VAGRANTBOX="jaredeh/ubuntu2004-server"
    fi
  elif [ "$KVONE" -lt "6" ]; then
    if [ "$KVTWO" -lt "12" ]; then # <v5.12
      DISTRO=ubuntu2004
      DOCKER_IMAGE="resurgentech/kernel_build-ubuntu2004:latest"
      VAGRANTBOX="jaredeh/ubuntu2004-server"
    else  # >=v5.12
      DISTRO=ubuntu2204
      DOCKER_IMAGE="resurgentech/kernel_build-ubuntu2204:latest"
      VAGRANTBOX="jaredeh/ubuntu2204-server"
    fi
  else # v6.X
    DISTRO=ubuntu2204
    DOCKER_IMAGE="resurgentech/kernel_build-ubuntu2204:latest"
    VAGRANTBOX="jaredeh/ubuntu2204-server"
  fi
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

echo "OPTIONS:"
echo "  NO_TEST=${NO_TEST}"
echo "  PATCHONLY=${PATCHONLY}"
echo "  SKIPBUILD=${SKIPBUILD}"
echo "  SMALLBUILD=${SMALLBUILD}"
echo "  NOTEARDOWN=${NOTEARDOWN}"
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

  ./build.py --buildnumber 0 \
             --kernel_version ${ACTUAL_KERNEL_VERSION} \
             --docker_image ${DOCKER_IMAGE} \
             --distro ${DISTRO} \
             --build_type ${BUILD_TYPE} \
             ${PATCHONLY};
fi

if [ ! -z ${NO_TEST} ]
then
  echo "${NO_TEST} - Exiting after build as requested"
  exit 1
fi

pushd output/;
rm -f ../latest.tar.gz;
rm -f a.tar.gz;
tar czf a.tar.gz *.deb;
popd;


./tests/install_test.py --vagrant_box ${VAGRANTBOX} \
                        --machine_name manualtest \
                        --license eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJVVUlEIjoiOGM5ZTY3MzctZWFjOC00MjU0LTg2ZGMtNDIwNDRiZGRiMWQ0IiwiaWF0IjoxNjYwMjU3NDM4LCJhdWQiOiJiaXRmbHV4LmFpIiwiaXNzIjoiYml0Zmx1eC5haSJ9.oA8DVyetpWmMfcR3XZQnlSUtQ2ccNoH2qncBFtG3coA \
                        --deviceid manualtest \
                        --manual_modprobe \
                        --kernel_revision ${KERNEL_VERSION}-custom-1 \
                        --kernel_version ${KERNEL_VERSION}-custom \
                        --tarballkernel output/a.tar.gz \
                        ${NOTEARDOWN};
