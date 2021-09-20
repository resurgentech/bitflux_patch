# README - setup

## Install vagrant_tools
See README.md in vagrant_tools
https://github.com/resurgentech/vagrant_tools
(or the internal copy)

## Create VM
```bash
vagrant_tools -a up -c ubuntu2004.yaml
```
(or centos8.yaml...)

## Install and configure VM
```bash
export ANSIBLE_HOST_KEY_CHECKING=False
ansible-playbook -i inventory.yaml install.yaml
```

## Reboot VM

## Add local user keys as authorized user on VM for pycharm remote debugging
```bash
./copy_key.sh
```

Now you should have a VM with the swaphints extensions in the kernel.  inventory.yaml has the IP and the keys.
