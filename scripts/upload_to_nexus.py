#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

import requests
import glob
import json
import os
import sys


def post(input_url, release_type, username, password, config, filename):
    url = "{}?repository={}".format(input_url, config['upload']['repository'])
    if "__RELEASE__" in url:
        url = url.replace("__RELEASE__", release_type)
    ## Not sure whats up with the headers
    #headers = {'accept': 'application/json', 'Content-Type': 'multipart/form-data'}
    headers = {}
    payload = {}
    for k, v in config['upload']['form'].items():
        if v == "__FILECONTENTS__":
            payload[k] = (filename, open(filename, 'rb'))
        elif v == "__FILENAME__":
            payload[k] = (None, os.path.basename(filename))
        else:
            payload[k] = (None, v)
    print("===============================================")
    print('filename={}'.format(filename))
    debug = {'url': url, 'headers': headers, 'rawform': config['upload']['form'], 'payload': payload}
    print(json.dumps(debug, indent=4, default=lambda o: str(o)))
    response = requests.post(url, headers=headers, files=payload, auth=(username, password))
    print("response={}".format(response))
    if response.status_code < 200 and response.status_code >= 300:
        raise


def list_artifacts(config):
    artifacts = []
    output = "output/*.{}".format(config['build_style'])
    for file in glob.glob(output):
        artifacts.append(file)
    if len(artifacts) == 0:
        print("Failure: '{}' returns nothing".format(output))
        raise
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
    parser.add_argument('--config', help='Path to config file for defaults and such', default=default_configfile, type=str)
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

    if args.url is None:
        print("You need a URL, --url")
        parser.print_help()
        sys.exit(1)

    config = configs['distros'][args.distro]
    artifacts = list_artifacts(config)
    for artifact in artifacts:
        post(args.url, args.release_type, args.username, args.password, config, artifact)
