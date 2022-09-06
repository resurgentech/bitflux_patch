#!/bin/bash

KERNEL_VERSION=$1;

if [ -z ${KERNEL_VERSION} ]
then
  echo "Missing KERNEL_VERSION.  style is 5.10.1";
  echo "${BASH_SOURCE[0]} KERNEL_VERSION";
fi

if [ ! -z $2 ]
then
  EXIT_AFTER_BUILD="EXIT_AFTER_BUILD";
fi

if [ ! -z $3 ]
then
  NOBUILD="--nobuild";
fi

echo "${KERNEL_VERSION} EXIT_AFTER_BUILD=${EXIT_AFTER_BUILD} NOBUILD=${NOBUILD}";


DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/..
WORKING_DIR=`pwd`


./build.py --buildnumber 0 --kernel_version v${KERNEL_VERSION} \
           --docker_image resurgentech/kernel_build-ubuntu2204:latest \
           --build_type git ${NOBUILD};

if [ ! -z ${EXIT_AFTER_BUILD} ]
then
  echo "${EXIT_AFTER_BUILD} - Exiting after build as requested"
  exit 1
fi

pushd output/;
rm -f ../latest.tar.gz;
rm -f a.tar.gz;
tar czf a.tar.gz *.deb;
popd;

./tests/install_test.py --vagrant_box jaredeh/ubuntu2204-server \
                        --machine_name manualtest \
                        --license eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJVVUlEIjoiOGM5ZTY3MzctZWFjOC00MjU0LTg2ZGMtNDIwNDRiZGRiMWQ0IiwiaWF0IjoxNjYwMjU3NDM4LCJhdWQiOiJiaXRmbHV4LmFpIiwiaXNzIjoiYml0Zmx1eC5haSJ9.oA8DVyetpWmMfcR3XZQnlSUtQ2ccNoH2qncBFtG3coA \
                        --deviceid manualtest \
                        --manual_modprobe \
                        --kernel_revision ${KERNEL_VERSION}-custom-1 \
                        --kernel_version ${KERNEL_VERSION}-custom \
                        --tarballkernel output/a.tar.gz;
