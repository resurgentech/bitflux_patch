#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )/../.." >/dev/null 2>&1 && pwd )"
cd ${DIR}

SCRIPTNAME="$( basename "${BASH_SOURCE[0]}")"

if [ $# -ne 1 ]; then
  echo "USAGE: ${SCRIPTNAME} <DISTRO>"
  echo "---- args: $@"
  exit 1
fi

mkdir -p build

docker run -it --rm \
  --volume ${DIR}:/bitflux \
  --workdir /bitflux \
  resurgentech/kernel_build-$1:latest \
  /bin/bash
