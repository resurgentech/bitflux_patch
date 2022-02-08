#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}

TARGETIPS=($(cat inventory.yaml | grep ansible_ip | sed 's/\s*ansible_ip\:\s*//'))
TARGETIP="${TARGETIPS[$VAGRANT_HOST]}"
echo $TARGETIP

scp -r $1 vagrant@$TARGETIP:~/
