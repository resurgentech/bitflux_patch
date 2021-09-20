# Copyright (c) Resurgent Technologies 2021

from .common import *


def git_hash(workingdir="./", short=False, verbose=False):
    if short:
        cmd = "git rev-parse --short HEAD"
    else:
        cmd = "git rev-parse HEAD"
    _, commit, _ = run_cmd(cmd, workingdir=workingdir, verbose=verbose)
    output = commit.strip()
    return output


def git_add(file, workingdir="./", allow_errors=True, verbose=False):
    cmd = "git add {}".format(file)
    run_cmd(cmd, workingdir=workingdir, allow_errors=allow_errors, verbose=verbose)


def git_commit(message, workingdir="./", allow_errors=True, verbose=False):
    cmd = "git commit -am \"{}\"".format(message)
    run_cmd(cmd, workingdir=workingdir, allow_errors=allow_errors, verbose=verbose)


def git_diff(version, path, workingdir="./", allow_errors=True, verbose=False):
    cmd = "git diff {} > {}".format(version, path)
    run_cmd(cmd, workingdir=workingdir, allow_errors=allow_errors, verbose=verbose)


def get_bitflux_version(buildnum=None, verbose=False):
    commit_hash = git_hash(short=True, verbose=verbose)
    if buildnum is None:
        bitflux_version = "bitflux{}".format(commit_hash)
    else:
        bitflux_version = "{}bitflux{}".format(buildnum, commit_hash)
    return bitflux_version


def git_create_repo(src_dir, verbose=False):
    """
    Create git repo for testing
    """
    run_cmd("git init", workingdir=src_dir, verbose=verbose)
    run_cmd("git config --local user.email \"you@example.com\"", workingdir=src_dir, verbose=verbose)
    run_cmd("git config --local user.name \"Your Name\"", workingdir=src_dir, verbose=verbose)
    git_add(".", workingdir=src_dir, verbose=verbose)
    git_commit("original", workingdir=src_dir, verbose=verbose)
    commit_hash = git_hash(workingdir=src_dir, verbose=verbose)
    sys.stdout.flush()
    sleep(1)
    return commit_hash
