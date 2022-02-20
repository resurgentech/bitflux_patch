#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from kernel_package_builder import *


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='Linux distro', type=str)
    default_configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'configs.json')
    parser.add_argument('--config', help='Path to config file for defaults and such', default=default_configfile, type=str)

    args = parser.parse_args()

    configs = read_json_file(args.config)

    build_style = configs['distros'][args.distro]['build_style']
    if build_style == 'deb':
        image_name = get_package_deb(args, configs)
    elif build_style == 'rpm':
        image_name = get_package_dnf(args, configs)
    print()
    print()
    print("package={}".format(image_name))
    with open("package.yaml", "w") as file:
        file.write("---")
        file.write("package: {}".format(image_name))
        file.write("")
