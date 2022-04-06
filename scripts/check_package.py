#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from kernel_package_builder import *


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='Linux distro', type=str)
    parser.add_argument('--image_searchfactors', help='For .deb, find the kernel package', default='["^linux-image-unsigned-", "generic$"]', type=str)
    parser.add_argument('--style', help='which package style [rpm, deb]', default='deb', type=str)
    parser.add_argument('--verbose', help='verbose', action='store_true')

    args, unknown = parser.parse_known_args()

    if args.build_style == 'deb':
        image_name = get_package_deb(args)
    elif args.build_style == 'rpm':
        image_name = get_package_dnf(args)
    print()
    print()
    print("package={}".format(image_name))
    with open("package.yaml", "w") as file:
        file.write("---\n")
        file.write("package: {}\n".format(image_name))
