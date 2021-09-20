# Copyright (c) Resurgent Technologies 2021

import subprocess
import re
import os
import sys
import glob
import shutil
import json
import urllib.request
from time import sleep


def run_cmd(cmd, workingdir=None, allow_errors=False, verbose=False, live_output=False):
    """
    run a command in the shell

    :param cmd: string with command to run in shell
    :param workingdir: string with working directory to run cmd in
    :param allow_errors: don't fail
    :param verbose: print stuff
    :param live_output: print data to stdout from process as you go
    :return: exitcode, stdout, stderr
    """
    aout = []
    aerr = []
    if workingdir is not None:
        acmd = "cd {}; {}".format(workingdir, cmd)
    else:
        acmd = cmd
    with subprocess.Popen(acmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True) as p:
        for line in p.stdout:
            if live_output:
                print(line, end='')
                sys.stdout.flush()
            aout.append(line)
        for line in p.stderr:
            if live_output:
                print(line, end='')
                sys.stdout.flush()
            aerr.append(line)
    exitcode = p.returncode
    out = "".join(aout)
    err = "".join(aerr)
    if verbose:
        print("cmd: {}".format(acmd))
    if verbose and not live_output:
        print("stdout: {}".format(out))
        print("stderr: {}".format(err))
    if verbose:
        print("exitcode: {}".format(exitcode))
        print("")
    if allow_errors is False and exitcode != 0:
        if not verbose:
            print("cmd: {}".format(acmd))
            print("stdout: {}".format(out))
            print("stderr: {}".format(err))
            print("exitcode: {}".format(exitcode))
            print("")
        raise
    sys.stdout.flush()
    return exitcode, out, err


def find_directory(searchdir='./', matchdir=None):
    """
    find sub directory in searchdir, return the expected matchdir, the first subdir (if matchdir is None) or None

    :return: None or path
    """
    subfolders = [f.path for f in os.scandir(searchdir) if f.is_dir()]
    if len(subfolders) < 1:
        return None
    if matchdir is None:
        path = subfolders[0]
        return path
    for path in subfolders:
        match_path = os.path.join(searchdir, matchdir)
        if path == match_path:
            return path
    return None


def find_file(searchdir='./', matchfile=None):
    """
    find file in searchdir, return the expected file, the first file or None

    :return: None or path
    """
    files = [f.path for f in os.scandir(searchdir) if f.is_file()]
    if len(files) < 1:
        return None
    if matchfile is None:
        path = files[0]
        return path
    for path in files:
        if re.search(matchfile, path):
            return path
    return None


def duplicate_file(src, dst, workingdir='./', verbose=False):
    src_path = os.path.join(workingdir, src)
    dst_path = os.path.join(workingdir, dst)
    shutil.copy(src_path, dst_path)
    if verbose:
        print("duplicating '{}' as '{}'".format(src_path, dst_path))


def download_file(url, filepath):
    with open(filepath, "wb") as file:
        data = urllib.request.urlopen(url)
        file.write(data.read())

#deprecated...?
def make_artifactory_file_spec(distro, outputdir='./output'):
    output = {'files': []}
    chunk = {}
    if distro == 'centos8':
        chunk['pattern'] = "{}/*.rpm".format(outputdir)
        chunk['target'] = "yum/centos/8/x86_64/"
    elif distro == 'fedora34':
        chunk['pattern'] = "{}/*.rpm".format(outputdir)
        chunk['target'] = "yum/fedora/34/x86_64/"
    elif distro == 'ubuntu2004':
        chunk['pattern'] = "{}/*.deb".format(outputdir)
        chunk['target'] = "ubuntu/"
        chunk['props'] = "deb.distribution=focal;deb.component=main;deb.architecture=amd64"
    elif distro == 'popos2004':
        chunk['pattern'] = "{}/*.deb".format(outputdir)
        chunk['target'] = "pop/"
        chunk['props'] = "deb.distribution=focal;deb.component=main;deb.architecture=amd64"
    else:
        print("unsupported distro = '{}'".format(distro))
        raise
    output['files'].append(chunk)
    json_data = json.dumps(output, indent=4)
    filepath = "{}/artifactory.json".format(outputdir)
    with open(filepath, "w") as file:
        file.write(json_data)


def copy_outputs(src, outputdir='./output', verbose=True):
    run_cmd("mkdir -p {};".format(outputdir), allow_errors=True, verbose=verbose)
    for file in glob.glob(src):
        shutil.copy(file, outputdir)

def read_json_file(filename):
    with open(filename, "r") as file:
        contents = json.load(file)
    return contents