#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}

target_ips=($(cat inventory.yaml | grep ip: | grep -v ansible_ip | sed 's/\s*ip\:\s*//'))
target_users=($(cat inventory.yaml | grep ansible_user: | sed 's/\s*ansible_user\:\s*//'))
target_keys=($(cat inventory.yaml | grep ansible_ssh_private_key_file: | sed 's/\s*ansible_ssh_private_key_file\:\s*//'))
local_host_key=$(cat ~/.ssh/id_rsa.pub)

#Get number of targets
l=$((${#target_ips[@]} - 1))

for i in $(seq 0 $l)
do
  cmd="ssh -o IdentitiesOnly=yes -i ${target_keys[$i]} ${target_users[$i]}@${target_ips[$i]} \"echo ${local_host_key} >> .ssh/authorized_keys\""
  echo $cmd
  o=$(eval $cmd)
  echo $o
done
