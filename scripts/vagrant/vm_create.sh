#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}

if [ -z $1 ]; then
  VAGRANT_MACHINE_DEF="machines.yaml"
else
  VAGRANT_MACHINE_DEF="${1}"
fi

vagrant_tools -a up -c $VAGRANT_MACHINE_DEF
