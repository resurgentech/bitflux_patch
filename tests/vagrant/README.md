# Set up jenkins clients virtual machines

# Usage

Run this locally on a vmhost

## Input

vagrant_tools requires a yaml file as an input `machines.yaml` defines the virtual machines to create.

## Create virtual machines
```bash
./vm_create.sh
```
If this completes successfully an `inventory.yaml` is created that uses an ansible compatible syntax.

## Prepare for our lab
Uses `inventory.yaml` produced from the previous step and runs ansible to set up stuff.

Prompts for manual password entry.

```bash
./convert_vagrant.sh
```

At this point:
* root user create with password
* ender user created

# Cleanup
```bash
./vm_teardown.sh
```
This will delete the VM entirely.


# Other tools

## pull_boxes.sh
Downloads vagrant boxes.  Note this is per user.

## initial_box.sh
Creates and destroys a vm from each box.  Seems to solves some issues when vagrant_tools.  I think by creating an initial volume in libvirt.


## install vagrant_tools
See README.md in vagrant_tools
https://github.com/resurgentech/vagrant_tools
(or the internal copy)

## copy ssh keys
Add local user keys as authorized user on VM for remote debugging etc
```bash
./copy_key.sh
```

## ssh.sh
```bash
VAGRANT_HOST=1 ./ssh.sh
```
This will open a shell to the 2nd machine in inventory.yaml

## scp_push.sh
```bash
VAGRANT_HOST=1 ./scp_push.sh foo.txt
```
This will copy foo.txt to ~/foo.txt in the 2nd machine in inventory.yaml
