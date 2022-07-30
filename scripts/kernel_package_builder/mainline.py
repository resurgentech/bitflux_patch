# Copyright (c) Resurgent Technologies 2021

from .common import *
from .patching import *
from .rpm import *


def download_mainline_kernel(build_dir, kernel_version, clean):
    filename = "linux-{}.tar.xz".format(kernel_version)
    filepath = os.path.join(build_dir, filename)
    src_dir = os.path.join(build_dir, "linux-{}".format(kernel_version))
    run_cmd("rm -rf {}".format(src_dir), verbose=False)
    if clean:
        run_cmd("rm -rf {}".format(filepath), verbose=False)
    major = kernel_version.split(".")[0]
    url = "https://cdn.kernel.org/pub/linux/kernel/v{}.x/{}".format(major, filename)
    print("Found kernel url path: {}".format(url))
    print("Found kernel src directory: {}".format(src_dir))
    if not os.path.exists(filepath):
        print("Downloading {}".format(filepath))
    sys.stdout.flush()
    run_cmd("mkdir -p {}".format(build_dir), verbose=False)
    download_file(url, filepath)
    return filename, filepath, src_dir


def download_rpm_kernel(build_dir, kernel_version, clean):
    print("Found kernel url path: {}".format(kernel_version))
    srpm_filename = kernel_version.split('/')[-1]
    srpm_unpacked_dir = os.path.join(build_dir, 'rpmbuild')
    srpm_filepath = os.path.join(build_dir,srpm_filename)
    if clean:
        run_cmd("rm -rf {}".format(srpm_filepath), verbose=False)
    if not os.path.exists(srpm_filepath):
        print("Downloading {}".format(srpm_filepath))
    sys.stdout.flush()
    run_cmd("mkdir -p {}".format(build_dir), verbose=False)
    # Download srpm
    download_file(kernel_version, srpm_filepath)
    # unpack srpm
    rpm_upack_srpm(srpm_filename, allow_errors=False, verbose=False, builddir=build_dir)
    # find tarball
    tarball_filepath = dnf_get_kernel_tarball(srpm_filename, srpm_unpacked_dir, allow_errors=False, verbose=False)
    # get .config
    rpm_config = os.path.join(srpm_unpacked_dir, 'SOURCES', 'kernel-x86_64.config')
    filename = os.path.basename(tarball_filepath)
    filepath = os.path.join(build_dir, filename)
    src_dir = filepath.split('.tar.xz')[0]
    print("Found kernel src directory: {}".format(src_dir))
    run_cmd("rm -rf {}".format(src_dir), verbose=False)
    shutil.copyfile(tarball_filepath, filepath)
    return filename, filepath, src_dir, rpm_config


def test_kernel_build(args):
    """
    Testing vanilla kernel by version against patches
    Input 5.4.120 for example
    """
    kernel_version = args.kernel_version
    build_dir = "./build"

    # Get tarball
    if 'rpm' in kernel_version:
        filename, filepath, src_dir, rpm_config = download_rpm_kernel(build_dir, kernel_version, args.clean)
    else:
        filename, filepath, src_dir = download_mainline_kernel(build_dir, kernel_version, args.clean)
        rpm_config = None

    # Untar tarball
    run_cmd("tar xf {}".format(filename), workingdir=build_dir, verbose=False)
    if rpm_config is not None:
        # rpm crap doesn't build unless you start with their .config
        shutil.copyfile(rpm_config, os.path.join(src_dir,'.config'))
    # Match up the patch directory
    patches_dir = select_patches_dir(filename, verbose=True)
    print("Found patches directory:    {}".format(patches_dir))
    sys.stdout.flush()
    if patches_dir is None:
        raise

    # Go ahead and do patching of kernel sources
    init_commit = patch_in("tarballbuild", patches_dir, src_dir, verbose=True, clean_patch=True)

    if init_commit is not None:
        filepath = os.path.join(patches_dir, "complete.patch")
        commit_and_create_patch(filepath, src_dir, commit_hash=init_commit, verbose=True)
    print("Patching Complete")
    sys.stdout.flush()
    sleep(3)


    # Run kernel build
    if args.nobuild:
        return
    run_cmd("make olddefconfig", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("./scripts/config --enable TRANSPARENT_HUGEPAGE", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("./scripts/config --enable TRANSPARENT_HUGEPAGE_ALWAYS", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("./scripts/config --enable TRANSPARENT_HUGEPAGE_MADVISE", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("./scripts/config --disable SYSTEM_TRUSTED_KEYS", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("./scripts/config --disable SYSTEM_REVOCATION_KEYS", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("make olddefconfig", workingdir=src_dir, allow_errors=False, verbose=True)
    exitcode, _, _ = run_cmd("make -j $(nproc)", workingdir=src_dir, allow_errors=True, live_output=True, verbose=True)
    if exitcode != 0:
        # If make dies run it single threaded to make debug easier
        run_cmd("make", workingdir=src_dir, allow_errors=True, verbose=True, live_output=True)
