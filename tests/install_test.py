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


def ansible_install(configs, args, installer_config, installer_options):
    ansible_dir = configs['ansible_dir']
    invfile = os.path.join(configs['vagrant_dir'], "inventory.yaml")
    playbook = os.path.join(ansible_dir, "install_bitflux.yml")
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
    cmd = "cd {}; ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i {} {} --extra-vars {}".format(ansible_dir, invfile, playbook, ic)
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
        return 1
    swaptotal = 0
    swapfree = 0
    for l in out.splitlines():
        b = l.split()
        if b[0] == 'SwapTotal:':
            swaptotal = int(b[1])
        elif b[0] == 'SwapFree:':
            swapfree = int(b[1])
    swapped = swaptotal - swapfree
    if swapped < 50000:
        print("swapped: {} swaptotal: {} swapfree: {}".format(swapped, swaptotal, swapfree))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        return 1
    return 0

# cd machines/name
# ansible 
# - dl installer  (make path configurable)
# - run install (variable options?)
# - reboot
# - wait
# using ssh?
# - check kernel
# - look for savings in log
# 


def run_tests(configs, args, loops):
    # check if kernel module loads
    if check_for_swaphints(configs, args):
        print("=========FAILED SWAPHINTS CHECK=================================")
        return 1

    # Loop until timing out or pasing
    for i in range(loops):
        sleep(60)
        if not swapping(configs, args):
            return 0
    print("=========FAILED SWAPPING CHECK=================================")
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
    parser.add_argument('--aptrepo', help='apt repo url', type=str)
    parser.add_argument('--noteardown', help='Don\'t clean up VMs, for debug', action='store_true')

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
    if args.yumrepo is not None:
        installer_options['overrides']['yum_repo_baseurl'] = args.key
    if args.aptrepo is not None:
        installer_options['overrides']['apt_repo_url'] = args.key

    # Runs script with ansible to install bitflux to 
    ansible_install(configs, args, installer_config, installer_options)

    # Testing
    run_tests(configs, args, 10)

    # create and start vm
    if not args.noteardown:
        vagrant_tools(configs, args, "vm_teardown.sh")
