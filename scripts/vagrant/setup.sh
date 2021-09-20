#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}

vagrant_tools -a up -c $1.yaml
export ANSIBLE_HOST_KEY_CHECKING=False
cd ../ansible/
ansible-playbook -i ../vagrant/inventory.yaml install.yaml
cd ../vagrant/
./copy_key.sh
TARGETIP=$(cat inventory.yaml | grep ansible_ip | sed 's/\s*ansible_ip\:\s*//')
echo $TARGETIP
