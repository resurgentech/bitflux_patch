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
        print("==============================================================================")
        print("=== DONE =====================================================================")
        print("==============================================================================")


def fill_configs(args):
    dargs = vars(args)

    if args.settings is not None and args.distro_config is not None:
        print("Can't have --settings and --distro_config")
        print(json.dump(dargs))
        raise

    config = {}
    config['basedir'] = os.path.join(os.path.dirname(os.path.realpath(__file__)))
    config['container_name'] = args.jobname
    config['image_name'] = "resurgentech_local/{}:latest".format(args.jobname)

    for arg in ['verbose', 'dumpall', 'nopull']:
        config[arg] = dargs[arg]

    ## Settings gets passed on to next level
    if args.settings is not None:
        # 1) If we get the --settings on the cli we're going to just use it
        config['settings'] = json.loads(args.settings)
        config['settings']['distro'] = args.distro
    elif args.distro_config is not None:
        # 2) Let's read this from a config file
        distro_config = read_yaml_file(args.distro_config)
        config['settings'] = distro_config['build']['kernel']
        config['settings']['distro'] = distro_config['name']
    else:
        # 3) Make a 'settings' dict from the commandline options
        config['settings'] = {}
        for arg in ['ver_ref_pkg', 'search_pkg', 'pkg_filters', 'metapkg_template', 'distro']:
            if dargs.get(arg, False):
                if arg in ['pkg_filters']:
                    config['settings'][arg] = json.loads(dargs[arg])
                else:
                    config['settings'][arg] = dargs[arg]

    for arg in ['build_type', 'kernel_version']:
        if dargs.get(arg, False):
            if not config['settings'].get(arg, False):
                config['settings'][arg] = dargs[arg]

    for arg in ['clean', 'nobuild', 'buildnumber', 'rebuild']:
        if dargs.get(arg, False):
            config['settings'][arg] = dargs[arg]

    # if --settings has nodocker, use it and remove it
    config['nodocker'] = config['settings'].get('nodocker', False)
    if config['settings'].get('nodocker', None) is not None:
        # we don't want to pass this on
        del config['settings']['nodocker']
    if args.nodocker:
        config['nodocker'] = True

    # Set up docker image
    if config['settings'].get('docker_image', None) is None:
        config['docker_image'] = args.docker_image
    else:
        # we don't want to pass this on
        config['docker_image'] = config['settings']['docker_image']
        del config['settings']['docker_image']

    return config


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--distro', help='Linux distro', default="ubuntu2004", type=str)
    parser.add_argument('--buildnumber', help='Adds to package name to increment it', default="11", type=str)
    parser.add_argument('--kernel_version', help='kernel version', type=str)
    parser.add_argument('--build_type', help='Hacks for patching and building test [distro, file, git, gitminimal]', default='distro', type=str)
    parser.add_argument('--jobname', help='Helpful in tracking jobs from jenkins', default="aaaaaa", type=str)
    parser.add_argument('--docker_image', help='Docker image to build kernel', default="resurgentech/kernel_build-ubuntu2004:latest", type=str)
    parser.add_argument('--nodocker', help="Don't run in Docker", action='store_true')
    parser.add_argument('--checkonly', help='Return the kernel package name', action='store_true')

    # .deb specifics
    parser.add_argument('--ver_ref_pkg', help='For .deb, reference pkg search', default='linux-image-unsigned', type=str)
    parser.add_argument('--search_pkg', help='For .deb, reference pkg search', default='linux-image-generic', type=str)
    parser.add_argument('--pkg_filters', help='For .deb, which pkgs to deal with', default='["hwe", "cloud", "dkms", "tools", "buildinfo"]', type=str)
    parser.add_argument('--metapkg_template', help='For .deb, what to call new package', default='linux-image-swaphints', type=str)

    # Allow for in cli complex options
    parser.add_argument('--settings', help='Overrides for building in escaped json', type=str)
    parser.add_argument('--distro_config', help='Settings imported from a file', type=str)

    # DEBUG specifics
    parser.add_argument('--verbose', help='Verbose mode - DEBUG', action='store_true')
    parser.add_argument('--dumpall', help='Dump everything from the container - DEBUG', action='store_true')
    parser.add_argument('--nopull', help="Use local docker images, don't pull - DEBUG", action='store_true')
    parser.add_argument('--nobuild', help="Don't build - DEBUG", action='store_true')
    parser.add_argument('--rebuild', help='Rebuild kernel, skips preparing - DEBUG', action='store_true')
    parser.add_argument('--clean', help='Extra clean up steps - DEBUG', action='store_true')

    args = parser.parse_args()

    print_args(args, __file__)

    config = fill_configs(args)

    print_args(config, __file__, msg="Processed Config for")

    # Only check for kernel
    if args.checkonly:
        kb = KernelBuilder(config)
        kb.check()
        sys.exit(0)

    kb = KernelBuilder(config)
    kb.build()
