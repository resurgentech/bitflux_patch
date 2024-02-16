#!/bin/bash
DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}

if [ -z "$VAGRANT_HOST" ]; then
  VAGRANT_HOST=0
fi

# grep for a line that starts with two spaces followed by a letter.  Then strip off the trailing colon and the leading spaces.
MACHINENAMES=($(cat inventory.yaml | grep -E '^[ ]{4}[a-z]' | grep -v duh | sed 's/://'))
MACHINENAME="${MACHINENAMES[$VAGRANT_HOST]}"
echo $MACHINENAME

TARGETIPS=($(cat inventory.yaml | grep ansible_ip | sed 's/\s*ansible_ip\:\s*//'))
TARGETIP="${TARGETIPS[$VAGRANT_HOST]}"
echo $TARGETIP

# Not sure under what circumstances this works and doesn't work.
#TARGETKEYS=($(cat inventory.yaml | grep ansible_ssh_private_key_file | sed 's/\s*ansible_ssh_private_key_file\:\s*//' | sed 's/^.\/workdir//' | sed 's/^.\///' )) # | sed "s|^|${PWD}/machines/|"))
#TARGETKEY="${TARGETKEYS[$VAGRANT_HOST]}"

TARGETKEY="${DIR}/machines/${MACHINENAME}/.vagrant/machines/default/libvirt/private_key"
if [ ! -f $TARGETKEY ]; then
  # some boxes don't reset the key so we use the default insecure key
  TARGETKEY="~/.vagrant.d/insecure_private_key"
fi

echo $TARGETKEY

ssh -i $TARGETKEY vagrant@$TARGETIP $@
