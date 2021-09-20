# Copyright (c) Resurgent Technologies 2021

from .common import *
from .patching import *


def test_kernel_build(args):
    """
    Testing vanilla kernel by version against patches
    Input 5.4.120 for example
    """
    kernel_version = args.kernel_version
    # Get tarball
    build_dir = "./build"
    filename = "linux-{}.tar.xz".format(kernel_version)
    filepath = os.path.join(build_dir, filename)
    src_dir = os.path.join(build_dir, "linux-{}".format(kernel_version))
    run_cmd("rm -rf {}; rm -rf {}".format(filepath, src_dir), verbose=False)
    major = kernel_version.split(".")[0]
    url = "https://cdn.kernel.org/pub/linux/kernel/v{}.x/{}".format(major, filename)
    print("Found kernel url path: {}".format(url))
    print("Found kernel src directory: {}".format(src_dir))
    print("Downloading {}".format(filepath))
    sys.stdout.flush()
    run_cmd("mkdir -p {}".format(build_dir), verbose=False)
    download_file(url, filepath)

    # Untar tarball
    run_cmd("tar xf {}".format(filename), workingdir=build_dir, verbose=False)

    # Match up the patch directory
    patches_dir = select_patches_dir(filename, verbose=True)
    print("Found patches directory:    {}".format(patches_dir))
    sys.stdout.flush()
    if patches_dir is None:
        raise

    # Go ahead and do patching of kernel sources
    init_commit = patch_in(args.distro, patches_dir, src_dir, verbose=True, clean_patch=True)

    if init_commit is not None:
        filepath = os.path.join(patches_dir, "complete.patch")
        commit_and_create_patch(filepath, src_dir, commit_hash=init_commit, verbose=True)
    print("Patching Complete")
    sys.stdout.flush()
    sleep(3)


    # Run kernel build
    if args.nobuild:
        return
    run_cmd("make defconfig", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("./scripts/config --enable TRANSPARENT_HUGEPAGE", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("./scripts/config --enable TRANSPARENT_HUGEPAGE_ALWAYS", workingdir=src_dir, allow_errors=False, verbose=True)
    run_cmd("./scripts/config --enable TRANSPARENT_HUGEPAGE_MADVISE", workingdir=src_dir, allow_errors=False, verbose=True)
    exitcode, _, _ = run_cmd("make -j $(nproc)", workingdir=src_dir, allow_errors=True, live_output=True, verbose=True)
    if exitcode != 0:
        # If make dies run it single threaded to make debug easier
        run_cmd("make", workingdir=src_dir, allow_errors=True, verbose=True, live_output=True)
