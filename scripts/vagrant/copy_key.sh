target_ip=$(cat inventory.yaml | grep ip: | grep -v ansible_ip | sed 's/\s*ip\:\s*//')
target_user=$(cat inventory.yaml | grep ansible_user: | sed 's/\s*ansible_user\:\s*//')
target_key=$(cat inventory.yaml | grep ansible_ssh_private_key_file: | sed 's/\s*ansible_ssh_private_key_file\:\s*//')
local_host_key=$(cat ~/.ssh/id_rsa.pub)

o=$(ssh -o IdentitiesOnly=yes -i ${target_key} ${target_user}@${target_ip} "echo ${local_host_key} >> .ssh/authorized_keys")
cmd="ssh -o IdentitiesOnly=yes -i ${target_key} ${target_user}@${target_ip} 'uname -a'"

echo $o
