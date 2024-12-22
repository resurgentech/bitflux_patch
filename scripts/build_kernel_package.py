#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from kernel_package_builder import *


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--buildnumber', help='Adds to package name to increment it', default="11", type=str)

    # For non Distro builds for testing etc
    parser.add_argument('--kernel_version', help='kernel version', type=str)
    parser.add_argument('--build_type', help='Hacks for patching and building test [distro, file, git]', default='distro', type=str)

    # For Distro settings
    parser.add_argument('--distro_config', help='Distro build settings', default='./templates/ubuntu2404/generic-hwe.yml', type=str)
    parser.add_argument('--maintainer', help='Maintainer line', default='unknown <unknown@unknown.unknown>', type=str)

    # Overrides and special options
    parser.add_argument('--nobuild', help='Don\'t build', action='store_true')
    parser.add_argument('--rebuild', help='Rebuild prepared directory, for manual hacking kernel', action='store_true')
    parser.add_argument('--nopatch', help='This is just going to build a stock kernel', action='store_true')
    parser.add_argument('--clean', help='Extra clean up steps', action='store_true')
    parser.add_argument('--verbose', help='verbose', action='store_true')
    parser.add_argument('--git_ref_urls_path', help='Requires path to git mirror.', default='/opt/mirrors/linux-stable.git', type=str)
    parser.add_argument('--giturl', help='git repo url', default='https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git', type=str)

    args = parser.parse_args()

    print_args(args, __file__)

    if args.build_type == 'file':
        if args.kernel_version is None:
            print("Need kernel_version if kernel_build_test is True")
            parser.print_help()
            sys.exit(1)
        test_kernel_build() # TODO: Implement options
        sys.exit(0)

    if args.build_type in ['git', 'gitminimal']:
        retval = test_git_build(args)
        sys.exit(retval)

    # Find the distro config
    build_style = 'none'
    try:
        with open(args.distro_config) as f:
            distro_config = yaml.safe_load(f)
        build_style = distro_config['style']
    except:
        print("Can't find 'style' in distro config")

    # Test distro build
    if build_style == 'deb':
        debian_style_build(args.distro_config, args.buildnumber, args.maintainer, args.verbose, args.nobuild)
    elif build_style == 'rpm':
        rpm_style_build() # TODO: Implement options
    elif build_style == 'yum':
        yum_style_build(args) # TODO: Implement options
    else:
        print(f"Unknown build style: {build_style}")
        sys.exit(1)
