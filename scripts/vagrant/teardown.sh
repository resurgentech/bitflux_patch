#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}

TARGETIP=$(cat inventory.yaml | grep ansible_ip | sed 's/\s*ansible_ip\:\s*//')

vagrant_tools -a killthemall -c $1.yaml

ssh-keygen -f ~/.ssh/known_hosts -R $TARGETIP
