#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021
import os
import sys
import yaml
# adding scripts to add kernel_package_builder
scriptspath = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'scripts'))
sys.path.append(scriptspath)
from kernel_package_builder.common import *
import jinja2


def create_vagrant_tools_file(config, vagrant_box, machine_name):
    with open(config['vagrant_template']) as f:
        template = jinja2.Template(f.read())
        templateoutput = template.render(vagrant_box=vagrant_box, machine_name=machine_name)
    with open(config['vagrant_definition'], 'w') as f:
        f.write(templateoutput)


def vagrant_tools(configs, args, script):
    cmd = "cd {}; ./{}".format(configs['vagrant_dir'], script)
    run_cmd(cmd, live_output=True)


def do_ansible(configs, script, args, extravars=None, interpreter=None):
    ansible_dir = configs['ansible_dir']
    invfile = os.path.join(configs['vagrant_dir'], "inventory.yaml")
    playbook = os.path.join(ansible_dir, script)
    cmd = "cd {};".format(ansible_dir)
    cmd += " ANSIBLE_HOST_KEY_CHECKING=False"
    cmd += " ansible-playbook -i {} {}".format(invfile, playbook)
    if interpreter is not None:
        cmd += " --extra-vars ansible_python_interpreter={}".format(interpreter)
    if extravars is not None:
        cmd += " --extra-vars {}".format(extravars)
    cmd += " {}".format(args.verbosity)
    run_cmd(cmd, live_output=True)


def ansible_bitflux_install(configs, script, args, installer_config, installer_options, interpreter='python3'):
    # formating parameters for bitflux installer
    options = ""
    for k,v in installer_options.items():
        if k == "overrides":
            options += " --{} {}".format(k, json.dumps(json.dumps(v)))
            continue
        options += " --{} {}".format(k, v)
    installer_config['installer_options'] = options
    # lets escape this structure for the command line
    ic = json.dumps(json.dumps(installer_config))
    do_ansible(configs, script, args, extravars=ic, interpreter=interpreter)


def do_ansible_adhoc(configs, args, adhoc_cmd):
    invfile = os.path.join(configs['vagrant_dir'], "inventory.yaml")
    cmd = "ANSIBLE_HOST_KEY_CHECKING=False ansible all -i {} -m shell -a '{}'".format(invfile, adhoc_cmd)
    return run_cmd(cmd, allow_errors=True)


def check_for_swaphints(configs, args):
    exitcode, out, err = do_ansible_adhoc(configs, args, "lsmod")
    if exitcode != 0:
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        return 1
    if out.find('swaphints') <= 0:
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        return 1
    return 0


def swapping(configs, args):
    exitcode, out, err = do_ansible_adhoc(configs, args, "cat /proc/meminfo")
    if exitcode != 0:
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        return 0
    swaptotal = 0
    swapfree = 0
    for l in out.splitlines():
        b = l.split()
        if b[0] == 'SwapTotal:':
            swaptotal = int(b[1])
        elif b[0] == 'SwapFree:':
            swapfree = int(b[1])
    swapped = swaptotal - swapfree
    # Do we see any pages swapped we'll settle for 500K
    if swapped < 500:
        print("swapped: {} swaptotal: {} swapfree: {}".format(swapped, swaptotal, swapfree))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        return 0
    return 1


def run_tests(configs, args, loops):
    # check if kernel module loads
    if check_for_swaphints(configs, args):
        print("----------------FAILED SWAPHINTS CHECK-----------------------------")
        return 1
    print("++++++++++++++++PASSED SWAPHINTS CHECK++++++++++++++++++++++++++++")

    # Loop until timing out or we detect swapped pages
    for i in range(loops):
        sleep(60)
        passed = swapping(configs, args)
        if passed:
            print("++++++++++++++++PASSED SWAPPING CHECK++++++++++++++++++++++++++++")
            return 0
    print("----------------FAILED SWAPPING CHECK-----------------------------")
    return 1


if __name__ == '__main__':
    import argparse
    basedir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    parser = argparse.ArgumentParser()
    parser.add_argument('--vagrant_box', help='vagrant box for vagrant_tools to use', type=str)
    parser.add_argument('--machine_name', help='name for vagrant_tools to give new vm', type=str)
    parser.add_argument('--key', help='Repo keys', type=str)
    parser.add_argument('--pkgrepo', help='apt/yum repo url', type=str)
    parser.add_argument('--pkgrepokernel', help='apt/yum repo for kernel url', type=str)
    parser.add_argument('--license', help='license for bitflux', type=str)
    parser.add_argument('--deviceid', help='deviceid for bitflux', type=str)
    parser.add_argument('--noteardown', help='Don\'t clean up VMs, for debug', action='store_true')
    parser.add_argument('--no_grub_update', help='Don\'t tweak grub', action='store_true')
    parser.add_argument('--manual_modprobe', help='Force modprobe in script rather than relying on the system settings.', action='store_true')
    parser.add_argument('--verbosity', help='verbose mode for ansible ex. -vvv', default='', type=str)
    parser.add_argument('--tarballkernel', help='Install kernel from tarball from minio', type=str)
    parser.add_argument('--tarballcollector', help='Install collector from tarball from minio', type=str)

    args = parser.parse_args()

    if args.vagrant_box is None or args.machine_name is None:
        print("need vagrant_box, machine_name")
        parser.print_help()
        sys.exit(1)

    # default and configs
    configs = {
        "vagrant_template": "vagrant/machines.yaml.j2",
        "vagrant_definition": "vagrant/machines.yaml",
        "vagrant_dir": "vagrant",
        "ansible_dir": "ansible",
        "installer_config": {
            "installer_url": "https://mirror.bitflux.ai/repository/downloads/tools/installbitflux.run",
            "installer_filename": "installbitflux.run"
        },
        "installer_options": {
            "license": "",
            "deviceid": "",
            "overrides": {
                "bitflux_key_url": "https://mirror.bitflux.ai/repository/keys/keys/bitflux_pub.key",
                "yum_repo_baseurl": "https://mirror.bitflux.ai/repository/yum/rocky/$releasever/$basearch",
                "apt_repo_url": "https://mirror.bitflux.ai/repository/ubuntu"
            }
        }
    }
    configs['vagrant_dir'] = os.path.join(basedir, configs['vagrant_dir'])
    configs['ansible_dir'] = os.path.join(basedir, configs['ansible_dir'])
    configs['vagrant_template'] = os.path.join(basedir, configs['vagrant_template'])
    configs['vagrant_definition'] = os.path.join(basedir, configs['vagrant_definition'])
    print(configs)

    # Make machines.yaml file for vagrant_tools
    create_vagrant_tools_file(configs, args.vagrant_box, args.machine_name)

    # create and start vm
    vagrant_tools(configs, args, "vm_create.sh")

    # form inputs for ansible installer script
    installer_config = helper__deepcopy(configs['installer_config'])
    installer_options = helper__deepcopy(configs['installer_options'])
    if args.key is not None:
        installer_options['overrides']['bitflux_key_url'] = args.key
    if args.license is not None:
        installer_options['license'] = args.license
    if args.deviceid is not None:
        installer_options['deviceid'] = args.deviceid
    if args.no_grub_update is None:
        installer_options['grub_update'] = ''

    # Some target machines don't have python installed
    do_ansible(configs, "install_python3.yml", args)

    if args.tarballkernel is not None:
        # Runs script with ansible to install kernel with a tarball
        installer_options['nokernel'] = ''
        installer_config['tarball'] = args.tarballkernel
        run_cmd("mc cp {} latest.tar.gz".format(args.tarballkernel))
        ansible_bitflux_install(configs, "install_tarballkernel.yml", args, installer_config, installer_options)
    elif args.pkgrepokernel is not None:
        # Runs script with ansible to install kernel
        installer_options['overrides']['apt_repo_url'] = args.pkgrepokernel
        installer_options['overrides']['yum_repo_baseurl'] = args.pkgrepokernel
        ansible_bitflux_install(configs, "install_bitflux.yml", args, installer_config, installer_options)
        # Set options to install collector in next round
        installer_options['nokernel'] = ''

    if args.pkgrepo is not None:
        installer_options['overrides']['apt_repo_url'] = args.pkgrepo
        installer_options['overrides']['yum_repo_baseurl'] = args.pkgrepo

    if args.tarballcollector is not None:
        # Runs script with ansible to install bitflux collector with a tarball
        installer_config['tarball'] = args.tarballcollector
        run_cmd("mc cp {} latest.tar.gz".format(args.tarballcollector))
        ansible_bitflux_install(configs, "install_tarballbitflux.yml", args, installer_config, installer_options)
    else:
        # Runs script with ansible to install bitflux collector
        ansible_bitflux_install(configs, "install_bitflux.yml", args, installer_config, installer_options)

    if args.manual_modprobe:
        do_ansible_adhoc(configs, args, "sudo modprobe swaphints")

    # Testing
    retval = run_tests(configs, args, 10)

    # create and start vm
    if not args.noteardown:
        vagrant_tools(configs, args, "vm_teardown.sh")

    sys.exit(retval)
