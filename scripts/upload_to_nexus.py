#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

import requests
import glob
import json
import os
import sys


def post(input_url, release_type, username, password, config, filename):
    url = "{}?repository={}".format(input_url, config['upload']['repository'])
    headers = {'accept': 'application/json', 'Content-Type': 'multipart/form-data'}
    payload = {}
    for k, v in config['upload']['form'].items():
        if v == "__FILECONTENTS__":
            open(filename, 'rb')
        elif v == "__FILENAME__":
            os.path.basename(filename)
        elif "__RELEASE__" in v:
            payload[k] = v.replace("__RELEASE__", release_type)
        else:
            payload[k] = v
    print(payload)
    response = requests.post(url, headers=headers, data=payload, auth=(username, password))
    if response.status_code != 200:
        print(response)
        print("url: {}, headers: {}, form: {}, filename: {}".format(url, headers, config['upload']['form'], filename))
        raise


def list_artifacts(config):
    artifacts = []
    for file in glob.glob("output/*.{}".format(config['build_style'])):
        artifacts.append(file)
    return artifacts


def read_json_file(filename):
    with open(filename, "r") as file:
        contents = json.load(file)
    return contents


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='Linux distro', type=str)
    default_configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'configs.json')
    parser.add_argument('--config', help='Path to config file for defaults and such', default=default_configfile, action='store_true')
    parser.add_argument('--url', help='URL for nexus system', type=str)
    parser.add_argument('--release_type', help='Release type for Nexus', type=str)
    parser.add_argument('--username', help='username for Nexus', type=str)
    parser.add_argument('--password', help='password for Nexus', type=str)

    args = parser.parse_args()

    configs = read_json_file(args.config)

    if configs['distros'].get(args.distro, None) is None:
        print("Invalid Distro specified {}.  Valid choices {}".format(args.distro, configs['distros'].keys()))
        parser.print_help()
        sys.exit(1)

    if configs['url'] is None:
        print("You need a URL, --url")
        parser.print_help()
        sys.exit(1)

    config = configs['distros'][args.distro]
    artifacts = list_artifacts(config)
    for artifact in artifacts:
        post(configs['url'], args.release_type, args.username, args.password, config, artifact)
