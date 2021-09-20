#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from kernel_package_builder import *


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='Linux distro', type=str)
    parser.add_argument('--buildnumber', help='Adds to package name to increment it', type=str)
    parser.add_argument('--kernel_version', help='kernel version', type=str)
    parser.add_argument('--kernel_build_test', help='Hacks for patching and building test', action='store_true')
    default_configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'kernel_package_builder', 'configs.json')
    parser.add_argument('--config', help='Path to config file for defaults and such', default=default_configfile, action='store_true')
    parser.add_argument('--nobuild', help='Don\'t build', action='store_true')
    args = parser.parse_args()

    configs = read_json_file(args.config)

    if args.kernel_build_test:
        if args.kernel_version is None:
            print("Need kernel_version if kernel_build_test is True")
            args.print_help()
            sys.exit(1)
        test_kernel_build(args)
        # 5.4.120 - patches / okay
        # 5.8.18 - patches / okay
        # 5.9.16 - patches / okay
        # 5.10.38 - patches / okay
        # 5.11.22 - patches / warnings
        # 5.12.5 - patches / warnings
        sys.exit(1)

    if configs['distros'].get(args.distro, None) is None:
        print("Invalid Distro specified {}.  Valid choices {}".format(args.distro, configs['distros'].keys()))

    build_style = configs['distros'][args.distro]['build_style']
    if build_style == 'deb':
        debian_style_build(args, configs)
    elif build_style == 'rpm':
        rpm_style_build(args, configs)

