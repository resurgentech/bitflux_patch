#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from kernel_package_builder import *


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='Linux distro', type=str)
    parser.add_argument('--buildnumber', help='Adds to package name to increment it', type=str)
    parser.add_argument('--kernel_version', help='kernel version', type=str)
    parser.add_argument('--build_type', help='Hacks for patching and building test [distro, file, git]', default='distro', type=str)
    default_configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'configs.json')
    parser.add_argument('--config', help='Path to config file for defaults and such', default=default_configfile, type=str)
    parser.add_argument('--nobuild', help='Don\'t build', action='store_true')
    parser.add_argument('--clean', help='Extra clean up steps', action='store_true')
    parser.add_argument('--gitmirrorpath', help='Requires path to git mirror.', default='/opt/mirrors/linux-stable.git', type=str)
    parser.add_argument('--giturl', help='git repo url', default='https://github.com/gregkh/linux.git', type=str)

    args = parser.parse_args()

    configs = read_json_file(args.config)

    if args.build_type == 'file':
        if args.kernel_version is None:
            print("Need kernel_version if kernel_build_test is True")
            parser.print_help()
            sys.exit(1)
        test_kernel_build(args)
        sys.exit(0)

    if args.build_type == 'git':
        test_git_build(args)
        sys.exit(0)

    if configs['distros'].get(args.distro, None) is None:
        print("Invalid Distro specified {}.  Valid choices {}".format(args.distro, configs['distros'].keys()))
        parser.print_help()
        sys.exit(1)

    build_style = configs['distros'][args.distro]['build_style']
    if build_style == 'deb':
        debian_style_build(args, configs)
    elif build_style == 'rpm':
        rpm_style_build(args, configs)

