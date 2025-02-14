# Copyright (c) Resurgent Technologies 2021

import subprocess
import re
import os
import sys
import glob
import shutil
import json
import yaml
import pty
import select
import errno
import urllib.request
from time import sleep


def make_str(data):
    if isinstance(data, str):
        output = data
    elif isinstance(data, bytes):
        output = data.decode('utf-8')
    else:
        output = str(data)
    return output


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


def run_cmd(cmd, shell=True, workingdir=None, allow_errors=False, verbose=False, live_output=False, no_stdout=False):
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
        cmd = "cd {}; {}".format(workingdir, cmd)
        shell = True
    sources, replicas = zip(pty.openpty(), pty.openpty())
    if verbose or live_output:
        print("cmd: {}".format(cmd))
    if not shell and isinstance(cmd, str):
        cmd = cmd.split()
    with subprocess.Popen(cmd, shell=shell, stdin=replicas[0], stdout=replicas[0], stderr=replicas[1]) as p:
        for fd in replicas:
            os.close(fd)
            readable = {
                sources[0]: sys.stdout.buffer,
                sources[1]: sys.stderr.buffer,
            }
        while readable:
            for fd in select.select(readable, [], [])[0]:
                try:
                    data = os.read(fd, 1024)
                except OSError as e:
                    if e.errno != errno.EIO:
                        raise
                    del readable[fd]
                    continue
                if not data:
                    #if there is no data but we selected, assume end of stream
                    del readable[fd]
                    continue
                if fd == sources[0]:
                    aout.append(data)
                    if live_output:
                        sys.stdout.buffer.write(data)
                        sys.stdout.buffer.flush()
                else:
                    aerr.append(data)
                    if live_output:
                        sys.stdout.buffer.write(data)
                        sys.stderr.buffer.flush()
                readable[fd].flush()
    for fd in sources:
        os.close(fd)
    exitcode = p.returncode
    out = b"".join(aout)
    err = b"".join(aerr)
    if verbose:
        if not no_stdout:
            print("stdout: {}".format(out))
        print("stderr: {}".format(err))
        print("exitcode: {}".format(exitcode))
        print("")
    if allow_errors is False and exitcode != 0:
        if not verbose:
            print("cmd: {}".format(cmd))
            if not no_stdout:
                print("stdout: {}".format(out))
            print("stderr: {}".format(err))
            print("exitcode: {}".format(exitcode))
            print("")
        raise
    sys.stdout.flush()
    sys.stderr.flush()
    return exitcode, make_str(out), make_str(err)


def print_run_cmd(cmd, exitcode, stdout, stderr):
    print()
    print("??????????????????????????????????????????????????????????????????????????????")
    print("??????????=- Failed run_cmd() -=??????????????????????????????????????????????")
    print("???[ cmd: ]???????????????????????????????????????????????????????????????????")
    print(cmd)
    print("???[ exitcode: ]??????????????????????????????????????????????????????????????")
    print(exitcode)
    print("???[ stdout: ]????????????????????????????????????????????????????????????????")
    print(stdout)
    print("???[ stderr: ]????????????????????????????????????????????????????????????????")
    print(stderr)
    print("??????????????????????????????????????????????????????????????????????????????")
    print()


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


def write_json_file(filename, data):
    with open(filename, "w") as file:
        file.write(json.dumps(data, indent=4))


def read_yaml_file(filename):
    with open(filename, "r") as file:
        contents = file.read()
    output = yaml.load(contents, Loader=yaml.Loader)
    return output


def print_args(oargs, filename, msg="Args into"):
    if not isinstance(oargs, dict):
        args = vars(oargs)
    else:
        args = oargs
    print("!----------------------------------------------------------------------------")
    print("!-- {} {}".format(msg, filename))
    print("!----------------------------------------------------------------------------")
    print(json.dumps(args, indent=4))
    print("!----------------------------------------------------------------------------")

def pretty_time_delta(seconds):
    # if isinstance(timedelta):
    #     seconds = delta.total_seconds()
    # else:
    #     seconds = delta
    seconds = int(seconds)
    if seconds < 1:
        return "less than 1s"
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def get_envars(var, filename='.env'):
    """
    Get environment variables from a file or override from environment
    """

    # We have the var in the env use it
    if os.environ.get(var, False):
        return os.environ.get(var)

    # Get envars
    output = None
    if not os.path.exists(filename):
        return output
    with open(filename) as f:
        lines = f.readlines()
    for line in lines:
        if var not in line:
            continue
        for e in line.split():
            if not e.startswith(var):
                continue
            if "=" not in e:
                continue
            if len(e.split("=")) > 1:
                continue
            output = e.split("=")[1]
    return output


def update_rust_tools(src_dir, verbose=False):
    """
    With rust in the kernel the toolchain is still in flux, so we need to update it often
    """
    _, ver, _ = run_cmd("./scripts/min-tool-version.sh rustc", workingdir=src_dir, allow_errors=True, verbose=verbose)
    if len(ver) < 1:
        print("rustc requirement not found, skipping rustup")
        return

    altfile = os.path.join(src_dir, "debian.master/config/annotations")
    #if this file exists then find the first line with the word rustc and get the version
    # for reasons dumb beyond my ken min-tool-version.sh isn't the source of truth
    if os.path.exists(altfile):
        with open(altfile) as f:
            lines = f.readlines()
        for line in lines:
            if "rustc" in line:
                ver = line.split("rustc")[1]
                ver = ver.split()[0]
                break

    _, out, _ = run_cmd(f"rustup show | grep ^{ver}", workingdir=src_dir, allow_errors=True, verbose=verbose)
    if len(out) < 1:
        ec, _, _ = run_cmd(f"rustup install {ver}", workingdir=src_dir, allow_errors=True, verbose=verbose)
    run_cmd(f"rustup override set {ver}", workingdir=src_dir, allow_errors=True, verbose=verbose)
    run_cmd("rustup component add rust-src", workingdir=src_dir, allow_errors=True, verbose=verbose)
