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


# def create_vagrant_tools_file(config, vagrant_box, machine_name):
#     with open(config['vagrant_template']) as f:
#         template = jinja2.Template(f.read())
#         templateoutput = template.render(vagrant_box=vagrant_box, machine_name=machine_name)
#     with open(config['vagrant_definition'], 'w') as f:
#         f.write(templateoutput)


# def vagrant_tools(configs, args, script):
#     cmd = "cd {}; ./{}".format(configs['vagrant_dir'], script)
#     run_cmd(cmd, live_output=True)
#     sys.stdout.flush()


def print_line(a, tag, l):
    s = a*5
    s += ' {} '.format(tag)
    n = len(s)
    s += a*(l-n)
    print(s)


def print_ansible_output(out):
    count = 0
    # attempt find output from ansible to print nicely
    a = re.search(r'=> {', out)
    b = [ m.start() for m in re.finditer(r'}', out)]
    d = out[a.end():b[-1]]
    e = json.loads("{" + d + "}")
    print(e.keys())
    for key in ['cmd', 'exitcode', 'stdout', 'stderr']:
        if e.get(key, None) is None:
            print_line('-', '{}:MISSING'.format(key),80)
            continue
        print_line('-','{}:'.format(key),80)
        print(e[key])
        count += 1
    print('-'*80)
    if count == 0:
        raise


def do_ansible(configs, script, args, extravars=None, interpreter=None, localhost=False):
    ansible_dir = configs['ansible_dir']
    cmd = "cd {};".format(ansible_dir)
    cmd += " ANSIBLE_HOST_KEY_CHECKING=False"
    playbook = os.path.join(ansible_dir, script)
    cmd += " ansible-playbook"
    if localhost:
        invfile = os.path.join(configs['ansible_dir'], "localhost.yml")
        cmd += " --connection=local"
    else:
        invfile = os.path.join(configs['ansible_dir'], "inventory.yml")
    cmd += " -i {} {}".format(invfile, playbook)
    if interpreter is not None:
        cmd += " --extra-vars ansible_python_interpreter={}".format(interpreter)
    if extravars is not None:
        cmd += " --extra-vars {}".format(extravars)
    if args.verbosity is not None:
        cmd += " -{}".format(args.verbosity)
    print("do_ansible: '{}'".format(cmd), flush=True)
    exitcode, out, err = run_cmd(cmd, live_output=True, allow_errors=True)
    sys.stdout.flush()
    if exitcode != 0:
        print('do_ansible: FAILED')
        print("="*80)
        print("exitcode={}".format(exitcode))
        print("="*80)
        print("stderr: {}".format(err))
        print("="*80)
        try:
            print_ansible_output(out)
        except:
            print("stdout: {}".format(out))
        print("="*80)
        raise
    return exitcode, out, err


def ansible_memhog_install(configs, args, memhogconfig, script='install_memhog.yml', interpreter='python3'):
    # lets escape this structure for the command line
    ic = json.dumps(json.dumps(memhogconfig))
    return do_ansible(configs, script, args, extravars=ic, interpreter=interpreter)


def ansible_bitflux_install(configs, script, args, installer_config, installer_options, interpreter='python3'):
    # formating parameters for bitflux installer
    options = ""
    for k,v in installer_options.items():
        if k == "overrides":
            if len(v) > 0:
                options += " --{} {}".format(k, json.dumps(json.dumps(v)))
            continue
        options += " --{} {}".format(k, v)
    installer_config['installer_options'] = options
    # lets escape this structure for the command line
    ic = json.dumps(json.dumps(installer_config))
    return do_ansible(configs, script, args, extravars=ic, interpreter=interpreter)


def do_ansible_adhoc(configs, args, adhoc_cmd):
    invfile = os.path.join(configs['vagrant_dir'], "inventory.yml")
    cmd = "ANSIBLE_HOST_KEY_CHECKING=False ansible all -i {} -m shell -a '{}'".format(invfile, adhoc_cmd)
    print("do_ansible_adhoc: '{}'".format(cmd), flush=True)
    exitcode, out, err = run_cmd(cmd, allow_errors=True)
    sys.stdout.flush()
    return exitcode, out, err


def setup_config(basedir, args):
    configs = {
        "vagrant_template": "vagrant/machines.yaml.j2",
        "vagrant_definition": "vagrant/machines.yaml",
        "vagrant_dir": "vagrant",
        "ansible_dir": "ansible",
        "memhog_config": {
            "memhog_url": "https://mirror.bitflux.ai/repository/downloads/tools/memhog",
            "memhog_path": "/usr/bin/memhog"
        },
        "installer_config": {
            "installer_url": "https://mirror.bitflux.ai/repository/downloads/tools/installbitflux.run",
            "installer_filename": "installbitflux.run"
        },
        "installer_options": {
            "deviceid": "",
            "overrides": {}
        }
    }
    configs['vagrant_dir'] = os.path.join(basedir, configs['vagrant_dir'])
    configs['ansible_dir'] = os.path.join(basedir, configs['ansible_dir'])
    configs['vagrant_template'] = os.path.join(basedir, configs['vagrant_template'])
    configs['vagrant_definition'] = os.path.join(basedir, configs['vagrant_definition'])
    # form inputs for ansible installer script
    installer_config = helper__deepcopy(configs['installer_config'])
    installer_options = helper__deepcopy(configs['installer_options'])
    if args.key is not None:
        installer_options['overrides']['bitflux_key_url'] = args.key
    if args.deviceid is not None:
        installer_options['deviceid'] = args.deviceid
    if args.no_grub_update is None:
        installer_options['grub_update'] = ''
    if args.installer_url is not None:
        installer_config["installer_url"] = args.installer_url
    if args.tarballkernel is not None:
        # extracting kernel version
        _, out, _ = run_cmd("tar -tf latest.tar.gz | grep linux-image")
        if args.kernel_revision is None:
            args.kernel_revision = out.split("_")[1]

    return configs, installer_config, installer_options


def install_kernel(args, configs, installer_options, installer_config):
    if args.tarballkernel is not None:
        # Runs script with ansible to install kernel with a tarball
        installer_options['nokernel'] = ''
        installer_config['tarball'] = args.tarballkernel
        installer_config['kernel_version'] = args.kernel_version
        ansible_bitflux_install(configs, "install_tarballkernel.yml", args, installer_config, installer_options)
    elif args.pkgrepokernel is not None:
        # Runs script with ansible to install kernel
        installer_options['nobitflux'] = ''
        installer_options['overrides']['apt_repo_url'] = args.pkgrepokernel
        installer_options['overrides']['yum_repo_baseurl'] = args.pkgrepokernel
        ansible_bitflux_install(configs, "install_bitflux.yml", args, installer_config, installer_options)
        # Set options to install bitflux in next round
        del installer_options['nobitflux']
        installer_options['nokernel'] = ''


def install_bitflux(args, configs, installer_options, installer_config):
    if args.pkgrepo is not None:
        installer_options['overrides']['apt_repo_url'] = args.pkgrepo
        installer_options['overrides']['yum_repo_baseurl'] = args.pkgrepo

    if args.tarballbitflux is not None:
        # Runs script with ansible to install bitflux bitflux with a tarball
        # Getting tarball from either local fs or minio
        if os.path.exists(args.tarballbitflux):
            shutil.copyfile(args.tarballbitflux, 'latest.tar.gz')
        else:
            run_cmd("mc cp {} latest.tar.gz".format(args.tarballbitflux))
        a = {}
        for k in ['license', 'deviceid']:
            a[k] = installer_options[k]
        ansible_bitflux_install(configs, "install_tarballbitflux.yml", args, a, {})
    else:
        # Runs script with ansible to install bitflux bitflux
        ansible_bitflux_install(configs, "install_bitflux.yml", args, installer_config, installer_options)


def check_build_style(configs, args):
    exitcode, out, err = do_ansible_adhoc(configs, args, "cat /etc/redhat-release")
    if exitcode == 0:
        return 'redhat'
    exitcode, out, err = do_ansible_adhoc(configs, args, "cat /etc/system-release")
    if exitcode == 0:
        return 'amazon'
    return 'debian'


def do_check_version(configs, args, params, expected):
    build_style = check_build_style(configs, args)
    print("PARAMS")
    print(params)
    exitcode, out, err = do_ansible_adhoc(configs, args, params[build_style]['cmd'])
    if exitcode != 0:
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        sys.stdout.flush()
    m = re.findall(params[build_style]['re'], out)
    if len(m) != 0:
        actual = re.sub('\033\\[([0-9]+)(;[0-9]+)*m', '', m[-1])
    else:
        actual = ""
    print(m) 
    print("stdout: '{}'".format(out))
    if expected != actual:
        print("actual: '{}' expected: '{}'".format(actual, expected))
        return 1
    return 0


def check_packages(configs, args):
    test_params = {
        'kerneltarball': {
            'debian': {
                're': r'\S+\s+(\S+)\s+\S+\s+\[installed',
                'cmd': "apt list | grep {}".format(re.sub('-1$', '', str(args.kernel_revision)))
            },
            'expected': None if args.tarballkernel is None else args.kernel_revision
        },
        'kernel': {
            'redhat': {
                're': r'\S+\s+(\S+)',
                'cmd': "dnf list installed kernel-swaphints"
            },
            'amazon': {
                're': r'\S+\s+\S+\s+(\S+)',
                'cmd': "yum list installed kernel-swaphints"
            },
            'debian': {
                're': r'\S+\s+(\S+)\s+\S+\s+\[installed',
                'cmd': "apt list linux-image-swaphints -a"
            },
            'expected': args.kernel_revision if args.tarballkernel is None else None
        },
        'bitflux': {
            'redhat': {
                're': r'\S+\s+([0-9\.\-]+)',
                'cmd': "dnf list installed bitfluxd"
            },
            'amazon': {
                're': r'\S+\s+([0-9\.\-]+)',
                'cmd': "yum list installed bitfluxd"
            },
            'debian': {
                're': r'\S+\s+([0-9\.\-]+)+\s+\S+\s+\[installed',
                'cmd': "apt list bitfluxd -a"
            },
            'expected': args.bitflux_revision
        }
    }
    for name, params in test_params.items():
        expected = params['expected']
        if expected is None:
            continue
        if args.tarballkernel is not None and name == 'kernel':
            continue
        if do_check_version(configs, args, params, expected):
            print("----------------FAILED {} PACKAGE VERSION CHECK-----------------------------".format(name), flush=True)
            return 1
        print("++++++++++++++++PASSED {} PACKAGE VERSION CHECK++++++++++++++++++++++++++++".format(name), flush=True)
    return 0


def check_kernel_version(configs, args):
    test_params = {
        'unamekernel': {
            'redhat': {
                're': r'(\S+)',
                'cmd': "uname -r"
            },
            'amazon': {
                're': r'(\S+)',
                'cmd': "uname -r"
            },
            'debian': {
                're': r'(\S+)',
                'cmd': "uname -r"
            },
            'expected': args.kernel_version
        }
    }
    for name, params in test_params.items():
        expected = params['expected']
        if expected is None:
            continue
        if do_check_version(configs, args, params, expected):
            print("----------------FAILED {} UNAME KERNEL VERSION CHECK-----------------------------".format(name), flush=True)
            return 1
        print("++++++++++++++++PASSED {} UNAME KERNEL VERSION CHECK++++++++++++++++++++++++++++".format(name), flush=True)
    return 0


def check_for_swaphints(configs, args):
    exitcode, out, err = do_ansible_adhoc(configs, args, "lsmod")
    if exitcode != 0:
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        sys.stdout.flush()
    if out.find('swaphints') <= 0:
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        sys.stdout.flush()
        return 1
    return 0


def check_for_bitflux(configs, args):
    cmd = "sudo systemctl status bitflux -n 0"
    exitcode, out, err = do_ansible_adhoc(configs, args, cmd)
    if exitcode != 0:
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        sys.stdout.flush()
        cmd = "sudo journalctl -u bitflux"
        exitcode, out, err = do_ansible_adhoc(configs, args, cmd)
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        sys.stdout.flush()
        return 1
    return 0


def check_for_memhog(configs, args):
    cmd = "ps aux | grep memhog | grep -v grep"
    exitcode, out, err = do_ansible_adhoc(configs, args, cmd)
    if exitcode != 0:
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        sys.stdout.flush()
        return 1
    return 0


def memhog(configs, args):
    exitcode, out, err = do_ansible_adhoc(configs, args, "bash -c \"nohup memhog --size 1G --test 6 --waitTime 1 &> /dev/null &\"")
    if exitcode != 0:
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        sys.stdout.flush()
        return 1
    return 0


def swapping(configs, args):
    exitcode, out, err = do_ansible_adhoc(configs, args, "cat /proc/meminfo")
    if exitcode != 0:
        print("exitcode: {}".format(exitcode))
        print("stdout: '{}'".format(out))
        print("stderr: '{}'".format(err))
        sys.stdout.flush()
        return 0
    swaptotal = 0
    swapfree = 0
    swapcached = 0
    for l in out.splitlines():
        b = l.split()
        if b[0].find('SwapTotal:') != -1:
            swaptotal = int(b[1])
        elif b[0].find('SwapFree:') != -1:
            swapfree = int(b[1])
        elif b[0].find('SwapCached:') != -1:
            swapcached = int(b[1])
    swapped = swaptotal - swapfree - swapcached
    # Do we see any pages swapped we'll settle for 10M
    if (swapped < 10000) or (swapcached > swapped/10):
        print("swapped: {} swaptotal: {} swapfree: {} swapcached: {}".format(swapped, swaptotal, swapfree, swapcached))
        #print("stdout: '{}'".format(out))
        #print("stderr: '{}'".format(err))
        sys.stdout.flush()
        return 0
    print("swapped: {} swaptotal: {} swapfree: {} swapcached: {}".format(swapped, swaptotal, swapfree, swapcached))
    return 1


def run_tests(configs, args, loops):
    # check package version
    if check_packages(configs, args):
        print("----------------FAILED PACKAGE VERSION CHECK-----------------------------", flush=True)
        return 1
    print("++++++++++++++++PASSED PACKAGE VERSION CHECK++++++++++++++++++++++++++++", flush=True)

    # check uname version
    if check_kernel_version(configs, args):
        print("----------------FAILED UNAME KERNEL VERSION CHECK-----------------------------", flush=True)
        return 1
    print("++++++++++++++++PASSED UNAME KERNEL VERSION CHECK++++++++++++++++++++++++++++", flush=True)

    # check if kernel module loads
    if check_for_swaphints(configs, args):
        print("----------------FAILED SWAPHINTS CHECK-----------------------------", flush=True)
        return 1
    print("++++++++++++++++PASSED SWAPHINTS CHECK++++++++++++++++++++++++++++", flush=True)

    # check if bitflux is running
    if check_for_bitflux(configs, args):
        print("----------------FAILED bitflux CHECK-----------------------------", flush=True)
        return 1
    print("++++++++++++++++PASSED bitflux CHECK++++++++++++++++++++++++++++", flush=True)

    memhog(configs, args)
    sleep(30)

    if check_for_memhog(configs, args):
        print("----------------FAILED MEMHOG CHECK-----------------------------", flush=True)
        return 1
    print("++++++++++++++++PASSED MEMHOG CHECK++++++++++++++++++++++++++++", flush=True)

    # Loop until timing out or we detect swapped pages
    for i in range(loops):
        sleep(60)
        passed = swapping(configs, args)
        print("passed={}  i={}".format(passed, i))
        if passed:
            print("++++++++++++++++PASSED SWAPPING CHECK++++++++++++++++++++++++++++", flush=True)
            return 0
    print("----------------FAILED SWAPPING CHECK-----------------------------", flush=True)
    exitcode, out,err = do_ansible_adhoc(configs, args, "sudo journalctl -u bitflux")
    print(out)
    print(err)
    return 1


if __name__ == '__main__':
    import argparse
    basedir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='distro to use', type=str)
    parser.add_argument('--machine_name', help='name to give new vm', type=str)
    parser.add_argument('--key', help='Repo keys', type=str)
    parser.add_argument('--pkgrepo', help='apt/yum repo url', type=str)
    parser.add_argument('--pkgrepokernel', help='apt/yum repo for kernel url', type=str)
    #parser.add_argument('--license', help='license for bitflux', type=str)
    parser.add_argument('--deviceid', help='deviceid for bitflux', type=str)
    parser.add_argument('--noteardown', help='Don\'t clean up VMs, for debug', action='store_true')
    parser.add_argument('--no_grub_update', help='Don\'t tweak grub', action='store_true')
    parser.add_argument('--manual_modprobe', help='Force modprobe in script rather than relying on the system settings.', action='store_true')
    parser.add_argument('--verbosity', help='verbose mode for ansible ex. -vvv', type=str)
    parser.add_argument('--tarballkernel', help='Install kernel from tarball from minio or local fs', type=str)
    parser.add_argument('--tarballbitflux', help='Install bitflux from tarball from minio or local fs', type=str)
    parser.add_argument('--tarballcollector', help='[DEPRECATED] Install collector from tarball from minio', type=str)
    parser.add_argument('--collector_revision', help='[DEPRECATED] Collector revision to confirm install', type=str)
    parser.add_argument('--bitflux_revision', help='bitflux package revision to confirm install', type=str)
    parser.add_argument('--kernel_revision', help='kernel package revision to confirm install', type=str)
    parser.add_argument('--kernel_version', help='kernel version to kernel is running, from uname', type=str)
    parser.add_argument('--installer_url', help='override installer url', type=str)
    parser.add_argument('--zram', help='create swapfile backed zram instead of just swapfile', action='store_true')

    args = parser.parse_args()
    print_args(args, __file__)

    if args.distro is None or args.machine_name is None:
        print("need distro, machine_name")
        parser.print_help()
        sys.exit(1)

    if args.tarballkernel is not None:
        # Getting tarball from either local fs or minio
        if os.path.exists(args.tarballkernel):
            shutil.copyfile(args.tarballkernel, 'latest.tar.gz')
        else:
            run_cmd("mc cp {} latest.tar.gz".format(args.tarballkernel))

    # default and configs
    configs, installer_config, installer_options = setup_config(basedir, args)
    print_args(args, __file__, msg="Processed args for")
    print_args(configs, __file__, msg="Processed config for")
    print_args(installer_config, __file__, msg="'installer_config' for")
    print_args(installer_options, __file__, msg="'installer_options' for")

    #DEPRECATED
    if args.collector_revision is not None:
        args.bitflux_revision = args.collector_revision
        print("--collector_revision is deprecated")
    if args.tarballcollector is not None:
        args.tarballbitflux = args.tarballcollector
        print("--tarballcollector is deprecated")

    # Make machines.yaml file for vagrant_tools
    #create_vagrant_tools_file(configs, args.vagrant_box, args.machine_name)

    # Clean up any failed tests that conflict
    # _default is kind of a hack but it works on our machines
    #virsh_domain = "{}_default".format(args.machine_name)
    virsh_domain = "{}".format(args.machine_name)
    run_cmd("sudo virsh destroy --domain {}".format(virsh_domain), allow_errors=True)
    run_cmd("sudo virsh undefine --domain {} --remove-all-storage".format(virsh_domain), allow_errors=True)

    # create and start vm
    vmdisk_path = f"/var/lib/libvirt/images/{args.machine_name}.qcow2"
    original_path = f"/var/lib/libvirt/images/{args.distro}.qcow2"
    run_cmd(f"sudo cp {original_path} {vmdisk_path}")
    a = {"vmdisk_path": vmdisk_path, "machine_name": args.machine_name, "PKR_VAR_username": "packer", "PKR_VAR_password": "packer"}
    c = json.dumps(json.dumps(a))
    do_ansible(configs, "vm_start.yml", args, extravars=c, localhost=True)

    # Update repos to get latest entries
    do_ansible(configs, "update_repos.yml", args)

    # Some target machines don't have python installed
    do_ansible(configs, "install_python3.yml", args)

    # Install the kernel packages
    install_kernel(args, configs, installer_options, installer_config)

    # Update repos to get latest entries and wipe kernel settings
    do_ansible(configs, "update_repos.yml", args)

    # Install bitflux packages
    install_bitflux(args, configs, installer_options, installer_config)

    if args.zram:
        # Create zram
        do_ansible(configs, "set_zramfile.yml", args)
    else:
        # Create swapfile if necessary
        do_ansible(configs, "set_swapfile.yml", args)

    # Some modes don't autoload module
    if args.manual_modprobe:
        do_ansible_adhoc(configs, args, "sudo modprobe swaphints")

    # Set up memhog to make swapping test easier
    ansible_memhog_install(configs, args, configs['memhog_config'])

    # No do the actual testing
    retval = run_tests(configs, args, 10)

    # Look at swaphints
    do_ansible(configs, "extract_swaphints.yml", args)

    # create and start vm
    if not args.noteardown:
        do_ansible(configs, "vm_stop.yml", args, localhost=True)

    sys.exit(retval)
