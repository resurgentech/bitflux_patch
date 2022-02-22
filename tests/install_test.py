#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021
import os
import sys
# adding scripts to add kernel_package_builder
scriptspath = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'scripts'))
sys.path.append(scriptspath)
from kernel_package_builder.common import *
import jinja2


def create_vagrant_tools_file(config, machine_template, machine_name):
    with open(config['vagrant_template']) as f:
        template = jinja2.Template(f.read())
        templateoutput = template.render(machine_template=machine_template, machine_name=machine_name)
    with open(config['vagrant_definition'], 'w') as f:
        f.write(templateoutput)


def vagrant_tools(configs, args, script):
    cmd = "cd {}; ./{}".format(configs['vagrant_dir'], script)
    run_cmd(cmd, live_output=True)


def ansible_install(configs, script, args, installer_config, installer_options, verbosity):
    ansible_dir = configs['ansible_dir']
    invfile = os.path.join(configs['vagrant_dir'], "inventory.yaml")
    playbook = os.path.join(ansible_dir, script)
    # formating parameters for installer
    options = ""
    for k,v in installer_options.items():
        if k == "overrides":
            options += " --{} \"{}\"".format(k, json.dumps(v))
            continue
        options += " --{} {}".format(k, v)
    installer_config['installer_options'] = options
    # lets escape this structure
    ic = json.dumps(json.dumps(installer_config))
    cmd = "cd {}; ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i {} {} --extra-vars {} {}".format(ansible_dir, invfile, playbook, ic, verbosity)
    run_cmd(cmd, live_output=True)


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
    basedir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),".."))
    parser = argparse.ArgumentParser()
    default_configfile = os.path.join(basedir, "tests", "configs.json")
    parser.add_argument('--config', help='Path to config file for defaults and such', default=default_configfile, type=str)
    parser.add_argument('--machine_template', help='vagrant_tools template to use', type=str)
    parser.add_argument('--machine_name', help='name for vagrant_tools to give new vm', type=str)
    parser.add_argument('--key', help='Repo keys', type=str)
    parser.add_argument('--yumrepo', help='Yum repo url', type=str)
    parser.add_argument('--yumrepokernel', help='Yum repo for kernel url', type=str)
    parser.add_argument('--aptrepo', help='apt repo url', type=str)
    parser.add_argument('--aptrepokernel', help='apt repo for kernel url', type=str)
    parser.add_argument('--license', help='license for bitflux', type=str)
    parser.add_argument('--deviceid', help='deviceid for bitflux', type=str)
    parser.add_argument('--noteardown', help='Don\'t clean up VMs, for debug', action='store_true')
    parser.add_argument('--no_grub_update', help='Don\'t tweak grub', action='store_true')
    parser.add_argument('--manual_modprobe', help='Force modprobe in script rather than relying on the system settings.', action='store_true')
    parser.add_argument('--verbosity', help='verbose mode for ansible ex. -vvv', default='', type=str)
    parser.add_argument('--tarballkernel', help='Install kernel from tarball from minio', type=str)

    args = parser.parse_args()

    if args.machine_template is None or args.machine_name is None:
        print("need machine_template, machine_name, release")
        parser.print_help()
        sys.exit(1)

    configs = read_json_file(args.config)
    configs['vagrant_dir'] = os.path.join(basedir, "scripts", "vagrant")
    configs['ansible_dir'] = os.path.join(basedir, "scripts", "ansible")
    print(configs)

    # Make machines.yaml file for vagrant_tools
    create_vagrant_tools_file(configs, args.machine_template, args.machine_name)

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

    if args.tarballkernel is not None:
        # Runs script with ansible to install kernel with a tarball
        installer_options['nokernel'] = ''
        installer_config['tarball'] = args.tarballkernel
        run_cmd("mc cp {} latest.tar.gz".format(args.tarballkernel))
        ansible_install(configs, "install_tarballkernel.yml", args, installer_config, installer_options, args.verbosity)
    elif args.aptrepokernel is not None:
        # Runs script with ansible to install kernel via apt repo
        installer_options['overrides']['apt_repo_url'] = args.aptrepokernel
        ansible_install(configs, "install_bitflux.yml", args, installer_config, installer_options, args.verbosity)
        # Set options to install collector in next round
        installer_options['nokernel'] = ''
    elif args.yumrepokernel is not None:
        # Runs script with ansible to install kernel via apt repo
        installer_options['overrides']['yum_repo_baseurl'] = args.yumrepokernel
        ansible_install(configs, "install_bitflux.yml", args, installer_config, installer_options, args.verbosity)
        # Set options to install collector in next round
        installer_options['nokernel'] = ''

    if args.yumrepo is not None:
        installer_options['overrides']['yum_repo_baseurl'] = args.yumrepo
    if args.aptrepo is not None:
        installer_options['overrides']['apt_repo_url'] = args.aptrepo

    # Runs script with ansible to install bitflux to 
    ansible_install(configs, "install_bitflux.yml", args, installer_config, installer_options, args.verbosity)

    if args.manual_modprobe:
        do_ansible_adhoc(configs, args, "sudo modprobe swaphints")

    # Testing
    retval = run_tests(configs, args, 10)

    # create and start vm
    if not args.noteardown:
        vagrant_tools(configs, args, "vm_teardown.sh")

    sys.exit(retval)
