#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from kernel_package_builder import *


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    # parser.add_argument('--distro', help='Linux distro', type=str)
    # parser.add_argument('--style', help='which package style [rpm, deb]', default='deb', type=str)
    # parser.add_argument('--ver_ref_pkg', help='For .deb, reference pkg search', default='linux-image-unsigned', type=str)
    # parser.add_argument('--search_pkg', help='For .deb, reference pkg search', default='linux-image-generic', type=str)
    parser.add_argument('--distro_config', help='Distro build settings', default='./templates/ubuntu2404/generic-hwe.yml', type=str)
    parser.add_argument('--verbose', help='verbose', action='store_true')

    args, unknown = parser.parse_known_args()

    if True: #args.style == 'deb':
        image_name, version_name = get_package_deb(args.distro_config)
    # TODO: implement distro_config files for rpm and yum
    # elif args.style == 'rpm':
    #     image_name = get_package_dnf(args)
    # elif args.style == 'yum':
    #     image_name = get_package_yum(args)

    print()
    print()
    print("package={}".format(image_name))
    print("version={}".format(version_name))
    with open("package.yaml", "w") as file:
        file.write("---\n")
        file.write("package: {}\n".format(image_name))
        file.write("version: {}\n".format(version_name))

