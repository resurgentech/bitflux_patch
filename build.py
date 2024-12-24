#!/usr/bin/python3
# Copyright (c) Resurgent Technologies 2021

from scripts.kernel_package_builder import *
import jinja2
import time

def compile_j2_template(template_path, output_path, config):
    with open(template_path) as f:
        template = jinja2.Template(f.read())
        templateoutput = template.render(config)
    with open(output_path, 'w') as f:
        f.write(templateoutput)


class KernelBuilder:

    def __init__(self, config):
        self.config = config
        self.metadata = {'config': config}
        self.metadata['start'] = time.time()

    def run_cmd(self, cmd, verbose=None, live_output=True, no_stdout=False):
        lverbose = verbose if verbose is not None else self.config['verbose']
        return run_cmd(cmd, verbose=lverbose, live_output=live_output, no_stdout=no_stdout)

    def build(self):
        self.build_docker_image()
        try:
            self.build_kernel_package()
        except Exception as e:
            print("ERROR: {}".format(e))
            print(" build_kernel_package() failed")
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
        if self.config['nodocker']:
            return
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
        if not self.config['nopull']:
            self.run_cmd("docker pull {}".format(self.config['docker_image']))
        self.run_cmd("docker rm --force {}".format(self.config['container_name']))
        self.run_cmd("docker rmi --force {}".format(self.config['image_name']))
        self.run_cmd("docker build -f Dockerfile . --tag {}".format(self.config['image_name']))
        self.run_cmd("rm -f Dockerfile")

    def run_docker(self, script, no_stdout=False):
        cmd = "docker run"
        cmd += " --privileged"
        cmd += " --name {}".format(self.config['container_name'])
        cmd += " --volume /boot:/boot"
        # Add mirrors directory if you can
        if os.path.exists('/opt/mirrors'):
            cmd += " --volume /opt/mirrors:/opt/mirrors"
        elif self.config['settings']['build_type'] in ['git', 'gitminimal']:
            print('!!!!Building in git mode without a mirror will take a while!!!!')
        cmd += " {} ".format(self.config['image_name'])
        cmd += script
        self.run_cmd(cmd, no_stdout=no_stdout)

    def run(self, script, no_stdout=False):
        cmd = "python3 {}".format(script)
        for k,v in self.config['settings'].items():
            if v is True:
                cmd += " --{}".format(k)
            elif v is False:
                continue
            else:
                if isinstance(v, str):
                    cmd += " --{} {}".format(k,v)
                else:
                    cmd += " --{} {}".format(k,json.dumps(json.dumps(v)))
        if self.config['nodocker']:
            self.run_cmd(cmd, no_stdout=no_stdout)
        else:
            self.run_docker(cmd, no_stdout=no_stdout)


    def build_kernel_package(self):
        print("==============================================================================")
        print("=== BUILD KERNEL PACKAGE =====================================================")
        print("==============================================================================")
        self.run("./scripts/build_kernel_package.py", no_stdout=True)

    def check_kernel_package(self):
        print("==============================================================================")
        print("=== CHECK KERNEL PACKAGE =====================================================")
        print("==============================================================================")
        self.run("./scripts/check_package.py", no_stdout=True)

    def copy_output_from_container(self):
        if self.config['nodocker']:
            return
        print("==============================================================================")
        print("=== COPY OUTPUT FROM CONTAINER ===============================================")
        print("==============================================================================")
        if not self.config['dumpall']:
            self.run_cmd("docker cp {}:/bitflux/output .".format(self.config['container_name']))
        else:
            self.run_cmd("rm -rf dumpall")
            self.run_cmd("mkdir dumpall")
            self.run_cmd("docker cp {}:/bitflux/ dumpall".format(self.config['container_name']))

    def copy_package_name_from_container(self):
        if self.config['nodocker']:
            return
        print("==============================================================================")
        print("=== COPY PACKAGENAME FROM CONTAINER ==========================================")
        print("==============================================================================")
        self.run_cmd("docker cp {}:/bitflux/package.yaml .".format(self.config['container_name']))

    def cleanup(self):
        if self.config['nodocker']:
            return
        print("==============================================================================")
        print("=== CLEAN UP DOCKER IMAGE AND CONTAINER ======================================")
        print("==============================================================================")
        self.run_cmd("docker rm {}".format(self.config['container_name']))
        self.run_cmd("docker image rm -f {}".format(self.config['image_name']))

    def done(self):
        self.metadata['end'] = time.time()
        self.metadata['elapsed'] = self.metadata['end'] - self.metadata['start']
        tdh = pretty_time_delta(self.metadata['elapsed'])
        spacer = "=============================================================================="
        doneline = f"=== DONE in {tdh} "
        doneline = doneline + "="*(len(spacer)-len(doneline))
        print(spacer)
        print(doneline)
        print(spacer)


def fill_configs(args):
    dargs = vars(args)
    orig_args = json.loads(json.dumps(dargs, indent=4))

    # Get the config file from the command line
    config = {}
    config['basedir'] = os.path.join(os.path.dirname(os.path.realpath(__file__)))
    config['container_name'] = args.jobname
    config['image_name'] = "resurgentech_local/{}:latest".format(args.jobname)

    # managing docker_image is a bit tricky.
    # It can be in the distro_config file, overridden in the cli, or might be unnecessary if --nodocker
    config_path = dargs.get('distro_config', 'unknown')
    if not os.path.exists(config_path):
        raise Exception("Config file {} does not exist".format(config_path))
    with open(config_path, 'r') as f:
        dconfig = yaml.safe_load(f)
    if dargs.get('docker_image', False):
        config['docker_image'] = dargs['docker_image']
    elif dconfig.get('docker_image', False):
        config['docker_image'] = dconfig['docker_image']
    elif dargs.get('nodocker', False):
        raise Exception("You must specify a docker image to use as --docker_image or --distro_config file.")

    # These settings are for the local building state
    for arg in ['verbose', 'dumpall', 'nopull', 'nodocker']:
        config[arg] = dargs[arg]

    # These settings get passed to build_kernel_package.py
    config['settings'] = {}
    for arg, value in dargs.items():
        if arg in ['dumpall', 'nopull', 'nodocker', 'docker_image']:
            continue
        config['settings'][arg] = value

    # Set up docker image
    config['docker_image'] = args.docker_image

    config['args'] = orig_args
    return config


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--buildnumber', help='Adds to package name to increment it', default="11", type=str)
    parser.add_argument('--kernel_version', help='kernel version', type=str)
    parser.add_argument('--build_type', help='Hacks for patching and building test [distro, file, git, gitminimal]', default='distro', type=str)
    parser.add_argument('--jobname', help='Helpful in tracking jobs from jenkins', default="aaaaaa", type=str)
    parser.add_argument('--nodocker', help="Don't run in Docker", action='store_true')
    parser.add_argument('--checkonly', help='Return the kernel package name', action='store_true')
    parser.add_argument('--docker_image', help='Docker image to build kernel', type=str)

    # .deb specifics
    parser.add_argument('--distro_config', help='Distro build settings', default='./templates/ubuntu2404/generic-hwe.yml', type=str)

    # DEBUG specifics
    parser.add_argument('--verbose', help='Verbose mode - DEBUG', action='store_true')
    parser.add_argument('--dumpall', help='Dump everything from the container - DEBUG', action='store_true')
    parser.add_argument('--nopull', help="Use local docker images, don't pull - DEBUG", action='store_true')
    parser.add_argument('--nobuild', help="Don't build - DEBUG", action='store_true')
    parser.add_argument('--rebuild', help='Rebuild kernel, skips preparing - DEBUG', action='store_true')
    parser.add_argument('--nopatch', help='This is just going to build a stock kernel', action='store_true')
    parser.add_argument('--clean', help='Extra clean up steps - DEBUG', action='store_true')

    args = parser.parse_args()

    try:
        config = fill_configs(args)
    except:
        # For debugging issues with fill_config
        print_args(args, __file__)
        print("!"*60)
        print("fill_configs failed")
        config = fill_configs(args)

    print_args(config, __file__, msg="Processed Config for")

    # Only check for kernel
    if args.checkonly:
        kb = KernelBuilder(config)
        kb.check()
        sys.exit(0)

    # Clean up build
    if args.clean or not args.nobuild:
        shutil.rmtree("./build", ignore_errors=True)

    kb = KernelBuilder(config)
    kb.build()
