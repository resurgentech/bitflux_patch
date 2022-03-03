#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}

if [ -z $1 ]; then
  VAGRANT_MACHINE_DEF="machines.yaml"
else
  VAGRANT_MACHINE_DEF="${1}"
fi

TARGETIPS=($(cat inventory.yaml | grep ansible_ip | sed 's/\s*ansible_ip\:\s*//'))

vagrant_tools -a killthemall -c $VAGRANT_MACHINE_DEF

for TARGETIP in ${TARGETIPS[@]}
do
  echo $TARGETIP
  ssh-keygen -f ~/.ssh/known_hosts -R $TARGETIP
done
