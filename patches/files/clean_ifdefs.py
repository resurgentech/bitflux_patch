#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021
import os
import sys
# adding scripts to add kernel_package_builder
basedir = os.path.dirname(os.path.realpath(__file__))
scriptspath = os.path.realpath(os.path.join(basedir, '..', '..', 'scripts'))
sys.path.append(scriptspath)
from kernel_package_builder.common import *


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='file to parse', type=str)
    parser.add_argument('-o', '--output', help='output file', type=str)
    parser.add_argument('-l', '--linux', help='linux version, eg. 5.12.1', type=str)
    args = parser.parse_args()

    linuxversion = args.linux.split(".")
    cmd = "gcc -I. -E -CC -P -dDI -nostdinc -fdirectives-only"
    cmd += " -D LINUX_VERSION_MAJOR={}".format(linuxversion[0])
    cmd += " -D LINUX_VERSION_SUBLEVEL={}".format(linuxversion[1])
    cmd += " -D LINUX_VERSION_PATCHLEVEL={}".format(linuxversion[2])
    cmd += " -D CLEAN_IFDEFS__TOGGLE"
    cmd += " {}".format(args.input)
    _, output, err = run_cmd(cmd, workingdir=basedir, allow_errors=True)

    print(output)

    outputdata = []
    startoutput = False
    for line in output.splitlines():
        if "CLEAN_IFDEFS__TOGGLE" in line:
            if not startoutput:
                startoutput = True
            else:
                startoutput = False
        elif startoutput:
            outputdata.append(line)
    outputdata.append("")

    with open(args.output, 'w') as file:
        file.write("\n".join(outputdata))

    