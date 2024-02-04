#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}

TARGETIPS=($(cat inventory.yaml | grep ansible_ip | sed 's/\s*ansible_ip\:\s*//'))
TARGETIP="${TARGETIPS[$VAGRANT_HOST]}"
echo $TARGETIP

TARGETKEYS=($(cat inventory.yaml | grep ansible_ssh_private_key_file | sed 's/\s*ansible_ssh_private_key_file\:\s*//' | sed 's/^.\/workdir//' | sed "s|^|${PWD}//|"))
TARGETKEY="${TARGETKEYS[$VAGRANT_HOST]}"
echo $TARGETKEY

ssh -i $TARGETKEY vagrant@$TARGETIP $@
