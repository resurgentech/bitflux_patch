# Copyright (c) Resurgent Technologies 2021

from .common import *
from .patching import *


#elrepolist = ["centos8"]
elrepolist = ["xxx"]

def dnf_update_upgrade(allow_errors=False, verbose=False, live_output=False):
    """
    Update and upgrade rpm repos to latest
    """
    run_cmd("dnf update -y --enableupdate=elrepo-kernel", allow_errors=allow_errors, verbose=verbose, live_output=live_output)


def dnf_get_srpm(kernel_version, distro, allow_errors=False, verbose=True, builddir='./build'):
    """
    We will make a list of "ElRepo Distributions, and then use the LT version only for them.
    Download kernel rpm which gives us naming convention for downloading srpm
    """
#    elrepolist = ["centos8"]
    if distro in elrepolist:
        return dnf_get_elrepo_kernel_srpm(kernel_version, allow_errors, verbose, builddir)
    else:
        return dnf_get_standard_kernel_srpm(kernel_version, allow_errors, verbose, builddir)


def dnf_get_elrepo_kernel_srpm(kernel_version, allow_errors=False, verbose=True, builddir='./build'):
    """
    We will make a list of "ElRepo Distributions, and then use the LT version only for them.
    Download kernel rpm which gives us naming convention for downloading srpm
    """
    run_cmd("mkdir -p {}".format(builddir), verbose=verbose)
    if kernel_version is None:
        cmd = "dnf download --enablerepo=elrepo-kernel  kernel-lt"
    else:
        cmd = "dnf download --enablerepo=elrepo-kernel  kernel-lt-{}".format(kernel_version)
    run_cmd(cmd, workingdir=builddir, allow_errors=allow_errors, verbose=verbose)
    files = [f.path for f in os.scandir("{}".format(builddir)) if f.is_file()]
    if len(files) == 2:
        if len(files) == 0:
            print("no files found")
            raise
        for file in files:
            a = os.path.basename(file).split(".")
            # assuming this is from another run and remove it
            if a[-2] == "nosrc":
                os.remove(file)
                files.remove(file)
    if len(files) != 1:
        print("Unhandled file list = {}".format(files))
        raise
    filename = os.path.basename(files[0])
    a = filename.split(".")
    a[-2] = "nosrc"
    filename = ".".join(a)
    url = "https://elrepo.org/linux/kernel/el8/SRPMS/{}".format(filename)
    filepath = os.path.join(builddir, filename)
    download_file(url, filepath)
    return filename

def dnf_get_standard_kernel_srpm(kernel_version, allow_errors=False, verbose=True, builddir='./build'):
    """
    We will make a list of "ElRepo Distributions, and then use the LT version only for them.
    Download kernel rpm which gives us naming convention for downloading srpm
    We disable the updates repo, because it has a new hotness kernel without a matching source rpm
    """
    run_cmd("mkdir -p {}".format(builddir), verbose=verbose)
    if kernel_version is None:
        cmd = "dnf download --source --disablerepo=updates kernel"
    else:
        cmd = "dnf download --source kernel-{}".format(kernel_version)
    run_cmd(cmd, workingdir=builddir, allow_errors=allow_errors, verbose=verbose)
    files = [f.path for f in os.scandir("{}".format(builddir)) if f.is_file()]
    if len(files) == 2:
        if len(files) == 0:
            print("no files found")
            raise
        for file in files:
            a = os.path.basename(file).split(".")
            # assuming this is from another run and remove it
            if a[-2] == "nosrc":
                os.remove(file)
                files.remove(file)
    if len(files) != 1:
        print("Unhandled file list = {}".format(files))
        raise
    filename = os.path.basename(files[0])
    #a = filename.split(".")
    #a[-2] = "nosrc"
    #filename = ".".join(a)
    #url = "https://elrepo.org/linux/kernel/el8/SRPMS/{}".format(filename)
    #filepath = os.path.join(builddir, filename)
    #download_file(url, filepath)
    return filename


def dnf_get_kernel_tarball(filename, rpm_topdir, allow_errors=False, verbose=False):
#    for files in os.listdir("{}/SOURCES/".format(rpm_topdir)):
#        for file in files:
#            if "linux" in file:
#                if ".tar.xz" in file:
#                    return "{}/SOURCES/{}".format(rpm_topdir,file)
    m = re.search("(\d\.\d+\.\d+)", filename)
    a = m.group(0)
    if a.endswith(".0"):
        a = a.rstrip(".0")
    filename = "linux-{}.tar.xz".format(a)
    if ("-4." in filename):
        url = "https://cdn.kernel.org/pub/linux/kernel/v4.x/{}".format(filename)
    else:
        url = "https://cdn.kernel.org/pub/linux/kernel/v5.x/{}".format(filename)
    filepath = "{}/SOURCES/{}".format(rpm_topdir, filename)
    download_file(url, filepath)
    return filepath


def rpm_upack_srpm(srpm_filename, allow_errors=False, verbose=False, builddir='./build'):
    cmd = "rm -rf rpmbuild; mkdir -p rpmbuild rpmbuild/BUILD rpmbuild/SRPM rpmbuild/RPM rpmbuild/SPECS rpmbuild/SOURCES"
    run_cmd(cmd, workingdir=builddir, allow_errors=allow_errors, verbose=verbose)
    rpm_topdir = os.path.abspath(os.path.join(builddir, 'rpmbuild'))
    cmd = "rpm --define \"_topdir {}\" -i {}/{}".format(rpm_topdir, builddir, srpm_filename)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    return rpm_topdir


def dnf_hack_elrepo_specfile(bitflux_version, pkg_release, patchfile_path, rpm_topdir, allow_errors=False, verbose=False):
    specfile = find_file(searchdir="{}/SPECS".format(rpm_topdir), matchfile=".spec$")
    print("specfile = {}".format(specfile))
    shutil.copyfile(patchfile_path, "{}/SOURCES/demandswapping.patch".format(rpm_topdir))
    cmd = "sed -i '/buildid .local/a %define buildid .{}' {}".format(bitflux_version, specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    cmd = "sed -i 's/%define pkg_release [[:digit:]]\+%/%define pkg_release {}%/' {}".format(pkg_release, specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    cmd = "sed -i '/NoSource: 0/d' {}".format(specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    cmd = "sed -i '/Sources./a Patch8000: demandswapping.patch' {}".format(specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    cmd = "sed -i '/# Purge the source tree of all unrequired dot-files/i patch -p1 -F1 -s < $RPM_SOURCE_DIR/demandswapping.patch' {}".format(specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    return specfile

def dnf_hack_srpm_specfile(bitflux_version, pkg_release, patchfile_path, rpm_topdir, allow_errors=False, verbose=False):
    specfile = find_file(searchdir="{}/SPECS".format(rpm_topdir), matchfile=".spec$")
    print("specfile = {}".format(specfile))
    shutil.copyfile(patchfile_path, "{}/SOURCES/demandswapping.patch".format(rpm_topdir))
    cmd = "sed -i '/buildid .local/a %define buildid .{}' {}".format(bitflux_version, specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    cmd = "sed -i 's/%define pkg_release [[:digit:]]\+%/%define pkg_release {}%/' {}".format(pkg_release, specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    cmd = "sed -i '/NoSource: 0/d' {}".format(specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    cmd = "sed -i '/Patches./a Patch8000: demandswapping.patch' {}".format(specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    cmd = "sed -i '/# END OF PATCH APPLICATIONS/i ApplyOptionalPatch demandswapping.patch' {}".format(specfile)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    return specfile

def generate_srpm_config_local(bitflux_version, pkg_release, patchfile_path, rpm_topdir, allow_errors=False, verbose=False):
#    from jinja2 import Template
#    with open('scripts/kernel_package_builder/template/config-local.j2') as file_:
#        template = Template(file_.read())
#    templateoutput = template.render()
    #This is supposed to help with RHEL and hurts no one else
#    with open('{}/SOURCES/config-local'.format(rpm_topdir),"w") as file_:
#        file_.write(templateoutput)
    #This helps with fedora and hurts no one else
#    with open('{}/SOURCES/kernel-local'.format(rpm_topdir),"w") as file_:
#        file_.write(templateoutput)
    #This is bringing a gun to a knife fight
    files = os.listdir("{}/SOURCES/.".format(rpm_topdir))
    for file in files:
        if "x86_64" in file:
            if file.endswith(".config"):
                cmd = "sed -i '/# CONFIG_IDLE_PAGE_TRACKING is not set/cCONFIG_IDLE_PAGE_TRACKING=y' {}/SOURCES/{}".format(rpm_topdir,file)
                run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)


def rpm_style_build(args, configs):
    # Update and upgrade apt repos to latest
    dnf_update_upgrade(allow_errors=True, live_output=False)
    print("rpm repos updated and upgraded")
    sys.stdout.flush()
    sleep(2)

    bitflux_version = get_bitflux_version()
    print("Set bitflux_version:        {}".format(bitflux_version))
    sys.stdout.flush()
    sleep(2)

    pkg_release = args.buildnumber
    print("Set pkg_release:        {}".format(pkg_release))
    sys.stdout.flush()
    sleep(2)

    srpm_filename = dnf_get_srpm(args.kernel_version, args.distro, allow_errors=False, verbose=False)
    print("Found srpm name:            {}".format(srpm_filename))
    sys.stdout.flush()
    sleep(2)

    patches_dir = select_patches_dir(srpm_filename, verbose=True)
    print("Found patches directory:    {}".format(patches_dir))
    sys.stdout.flush()
    if patches_dir is None:
        raise
    sleep(2)

    rpm_topdir = rpm_upack_srpm(srpm_filename, allow_errors=False, verbose=False)

    tarball = dnf_get_kernel_tarball(srpm_filename, rpm_topdir, allow_errors=False, verbose=False)

    patchfile_path = make_unified_patch(args.distro, patches_dir, tarball, allow_errors=False, verbose=False)
    print("Created patch file:         {}".format(patchfile_path))
    sys.stdout.flush()
    sleep(2)

    if args.distro in elrepolist:
        specfile = dnf_hack_elrepo_specfile(bitflux_version, pkg_release, patchfile_path, rpm_topdir, allow_errors=False, verbose=False)
    else:
        specfile = dnf_hack_srpm_specfile(bitflux_version, pkg_release, patchfile_path, rpm_topdir, allow_errors=False, verbose=False)
    print("Modified RPM SPEC file:     {}".format(specfile))

    #config-local provides an override location for the spec file to apply config changes. ours just guarantees page_idle and soft_dirty
    generate_srpm_config_local(bitflux_version, pkg_release, patchfile_path, rpm_topdir, allow_errors=False, verbose=False)

    sys.stdout.flush()
    sleep(2)
    # Do build
    if args.nobuild:
        return
    os.system("rpmbuild --define \"_topdir {}\" -ba {}".format(rpm_topdir, specfile))

    # Copy outputs and patches
    run_cmd("rm -rf ./output;", allow_errors=True)
    copy_outputs("{}/RPMS/x86_64/*.rpm".format(rpm_topdir))
    copy_outputs("{}/*.new".format(patches_dir), outputdir='./output/patches/')

    # Write file for artifactory upload
    make_artifactory_file_spec(args.distro)
