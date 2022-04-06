#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from kernel_package_builder import *


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='Linux distro', default="ubuntu2004", type=str)
    parser.add_argument('--buildnumber', help='Adds to package name to increment it', default="11", type=str)
    parser.add_argument('--kernel_version', help='kernel version', type=str)
    parser.add_argument('--build_type', help='Hacks for patching and building test [distro, file, git]', default='distro', type=str)
    parser.add_argument('--style', help='which package style [rpm, deb]', default='deb', type=str)
    parser.add_argument('--image_searchfactors', help='For .deb, find the kernel package', default='["^linux-image-unsigned-", "generic$"]', type=str)
    parser.add_argument('--ver_ref_pkg', help='For .deb, reference pkg search', default='linux-image-unsigned', type=str)
    parser.add_argument('--pkg_filters', help='For .deb, which pkgs to deal with', default='["hwe", "cloud", "dkms", "tools", "buildinfo"]', type=str)
    parser.add_argument('--metapkg_template', help='For .dev, what to call new package', default='linux-image-swaphints', type=str)
    parser.add_argument('--nobuild', help='Don\'t build', action='store_true')
    parser.add_argument('--clean', help='Extra clean up steps', action='store_true')
    parser.add_argument('--verbose', help='verbose', action='store_true')
    parser.add_argument('--gitmirrorpath', help='Requires path to git mirror.', default='/opt/mirrors/linux-stable.git', type=str)
    parser.add_argument('--giturl', help='git repo url', default='https://github.com/gregkh/linux.git', type=str)

    args = parser.parse_args()

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

    if args.style == 'deb':
        debian_style_build(args)
    elif args.style == 'rpm':
        rpm_style_build(args)

