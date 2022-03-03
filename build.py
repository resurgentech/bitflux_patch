#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from scripts.kernel_package_builder import *
import jinja2


def compile_j2_template(template_path, output_path, config):
    with open(template_path) as f:
        template = jinja2.Template(f.read())
        templateoutput = template.render(config)
    with open(output_path, 'w') as f:
        f.write(templateoutput)


class KernelBuilder:

    def __init__(self, config):
        self.config = config

    def run_cmd(self, cmd, verbose=None, live_output=True):
        lverbose = verbose if verbose is not None else self.config['verbose']
        return run_cmd(cmd, verbose=lverbose, live_output=live_output)

    def run_system(self, cmd, allow_errors=False, verbose=None):
        lverbose = verbose if verbose is not None else self.config['verbose']
        return run_system(cmd, verbose=lverbose, allow_errors=allow_errors)

    def build(self):
        self.build_docker_image()
        self.build_kernel_package()
        self.copy_output_from_container()
        self.cleanup()
        self.done()

    def check(self):
        self.build_docker_image()
        self.check_kernel_package()
        self.copy_package_name_from_container()
        self.cleanup()
        self.done()

    def build_docker_image(self):
        print("==============================================================================")
        print("=== BUILD DOCKER IMAGE =======================================================")
        print("==============================================================================")
        print(">-----------------------------------------------------------------------------")
        print("    Docker image name = {}".format(self.config['image_name']))
        print("    Container name    = {}".format(self.config['container_name']))
        print("<-----------------------------------------------------------------------------")
        template_path = os.path.join(self.config['basedir'], 'scripts', 'Dockerfile.j2')
        output_path = os.path.join(self.config['basedir'], 'Dockerfile')
        compile_j2_template(template_path, output_path, self.config)
        self.run_cmd("docker pull {}".format(self.config['docker_image']))
        self.run_cmd("docker rm --force {}".format(self.config['container_name']))
        self.run_cmd("docker rmi --force {}".format(self.config['image_name']))
        self.run_cmd("docker build -f Dockerfile . --tag {}".format(self.config['image_name']))
        self.run_cmd("rm -f Dockerfile")

    def run_docker(self, script):
        cmd = "docker run"
        cmd += " --privileged"
        cmd += " --name {}".format(self.config['container_name'])
        cmd += " --volume /boot:/boot"
        cmd += " {}".format(self.config['image_name'])
        cmd += " python3 {}".format(script)
        for k,v in self.config['settings'].items():
            cmd += " --{} {}".format(k,v)
        # So the build for debian at least hates not having a tty or something,
        # This workaround is what we have.
        self.run_system(cmd)

    def build_kernel_package(self):
        print("==============================================================================")
        print("=== BUILD KERNEL PACKAGE =====================================================")
        print("==============================================================================")
        self.run_docker("./scripts/build_kernel_package.py")

    def check_kernel_package(self):
        print("==============================================================================")
        print("=== CHECK KERNEL PACKAGE =====================================================")
        print("==============================================================================")
        self.run_docker("./scripts/check_package.py")

    def copy_output_from_container(self):
        print("==============================================================================")
        print("=== COPY OUTPUT FROM CONTAINER ===============================================")
        print("==============================================================================")
        if self.config.get('dumpall', None) is None:
            self.run_cmd("docker cp {}:/bitflux/output .".format(self.config['container_name']))
        else:
            self.run_cmd("rm -rf dumpall")
            self.run_cmd("mkdir dumpall")
            self.run_cmd("docker cp {}:/bitflux/ dumpall".format(self.config['container_name']))

    def copy_package_name_from_container(self):
        print("==============================================================================")
        print("=== COPY PACKAGENAME FROM CONTAINER ==========================================")
        print("==============================================================================")
        self.run_cmd("docker cp {}:/bitflux/package.yaml .".format(self.config['container_name']))

    def cleanup(self):
        print("==============================================================================")
        print("=== CLEAN UP DOCKER IMAGE AND CONTAINER ======================================")
        print("==============================================================================")
        self.run_cmd("docker rm {}".format(self.config['container_name']))
        self.run_cmd("docker image rm -f {}".format(self.config['image_name']))

    def done(self):
        print("==============================================================================")
        print("=== DONE =====================================================================")
        print("==============================================================================")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='Linux distro', default="ubuntu2004", type=str)
    parser.add_argument('--buildnumber', help='Adds to package name to increment it', default="11", type=str)
    parser.add_argument('--kernel_version', help='kernel version', type=str)
    parser.add_argument('--build_type', help='Hacks for patching and building test [distro, file, git]', default='distro', type=str)
    parser.add_argument('--jobname', help='Helpful in tracking jobs from jenkins', default="aaaaaa", type=str)
    parser.add_argument('--docker_image', help='Docker image to build kernel', default="resurgentech/kernel_build-ubuntu2004:latest", type=str)
    parser.add_argument('--checkonly', help='Return the kernel package name', action='store_true')
    parser.add_argument('--verbose', help='Verbose mode - DEBUG', action='store_true')
    parser.add_argument('--dumpall', help='Dump everything from the container - DEBUG', action='store_true')
    parser.add_argument('--nobuild', help="Don't build - DEBUG", action='store_true')
    parser.add_argument('--clean', help='Extra clean up steps - DEBUG', action='store_true')
    parser.add_argument('--settings', help='Overrides for building in escaped json', type=str)

    args = parser.parse_args()

    config = {}
    config['basedir'] = os.path.join(os.path.dirname(os.path.realpath(__file__)))
    config['container_name'] = args.jobname
    config['image_name'] = "resurgentech_local/{}:latest".format(args.jobname)
    config['verbose'] = args.verbose
    if args.dumpall:
        config['dumpall'] = args.dumpall
    if args.settings is None:
        config['settings'] = {}
    else:
        config['settings'] = json.loads(args.settings)
    config['settings']['buildnumber'] = args.buildnumber
    config['settings']['distro'] = args.distro
    config['settings']['build_type'] = args.build_type
    if args.clean:
        config['settings']['clean'] = args.clean
    if args.nobuild:
        config['settings']['nobuild'] = args.nobuild
    if args.kernel_version is not None:
        config['settings']['kernel_version'] = args.kernel_version
    if config['settings'].get('docker_image', None) is None:
        config['docker_image'] = args.docker_image
    else:
        config['docker_image'] = config['settings']['docker_image']
        del config['settings']['docker_image']

    # Only check for kernel
    if args.checkonly:
        kb = KernelBuilder(config)
        kb.check()
        sys.exit(0)

    kb = KernelBuilder(config)
    kb.build()
