# Copyright (c) Resurgent Technologies 2021

import subprocess
import re
import os
import sys
import glob
import shutil
import json
import yaml
import urllib.request
from time import sleep


def run_system(cmd, workingdir=None, allow_errors=False, verbose=False):
    """
    Like run_cmd only runs os.system which takes over the execution
    """
    if workingdir is not None:
        acmd = "cd {}; {}".format(workingdir, cmd)
    else:
        acmd = cmd
    # Not sure how else to get exit code with os.system() call
    acmd += "{}; echo \"$?\" > os_system.exitcode".format(acmd)
    if verbose:
        print("cmd: {}".format(acmd))
    # Actually run the command
    os.system(acmd)
    # Lets get the exitcode from the disk
    if workingdir is not None:
        exitcode_path = os.path.join(workingdir, 'os_system.exitcode')
    else:
        exitcode_path = 'os_system.exitcode'
    with open(exitcode_path, 'r') as file:
        exitcode = int(file.read())
    if verbose:
        print("exitcode: {}".format(exitcode))
        print("")
    if allow_errors is False and exitcode != 0:
        if not verbose:
            print("cmd: {}".format(acmd))
            print("exitcode: {}".format(exitcode))
            print("")
        raise
    sys.stdout.flush()
    return exitcode


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
    if verbose:
        print("cmd: {}".format(acmd))
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


def helper__deepcopy(data):
    a = json.dumps(data)
    b = json.loads(a)
    return b


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


def copy_outputs(src, outputdir='./output', verbose=True):
    run_cmd("mkdir -p {};".format(outputdir), allow_errors=True, verbose=verbose)
    for file in glob.glob(src):
        shutil.copy(file, outputdir)


def read_json_file(filename):
    with open(filename, "r") as file:
        contents = json.load(file)
    return contents


def read_yaml_file(filename):
    with open(filename) as file:
        contents = yaml.load(file, Loader=yaml.FullLoader)
    return contents
