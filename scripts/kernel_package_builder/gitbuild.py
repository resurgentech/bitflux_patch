# Copyright (c) Resurgent Technologies 2021

from .common import *
from .patching import *


def git_checkout_kernel(build_dir, kernel_branch, giturl, git_ref_urls_path):
    branch_filepath = os.path.join(build_dir, kernel_branch)
    filepath = os.path.join(build_dir, kernel_branch)
    run_cmd("rm -rf {}".format(branch_filepath), verbose=False)
    sys.stdout.flush()
    run_cmd("mkdir -p {}".format(build_dir), verbose=False)
    print("Checkout branch '{}' from '{}'".format(kernel_branch, git_ref_urls_path))
    run_cmd("git clone {} --reference-if-able {} {}".format(giturl, git_ref_urls_path, branch_filepath), verbose=False)
    run_cmd("git fetch --all", workingdir=filepath, verbose=False)
    if kernel_branch =='master' or re.match(r'y$', kernel_branch):
        run_cmd("git checkout origin/{}".format(kernel_branch), workingdir=filepath, verbose=False)
    else:
        run_cmd("git checkout {}".format(kernel_branch), workingdir=filepath, verbose=False)
    if kernel_branch == "master":
        _, output, _ = run_cmd("cd {}; git tag -l | sort --version-sort".format(filepath), verbose=False)
        output = output.splitlines()
        return output[-1], filepath
    return kernel_branch, filepath


def test_git_build(args):
    """
    Testing vanilla kernel from git
    Input 5.4.120 for example
    """
    kernel_version = args.kernel_version
    build_dir = "./build"

    kernel_version, src_dir = git_checkout_kernel(build_dir, kernel_version, args.giturl, args.git_ref_urls_path)

    # Match up the patch directory
    patches_dir = select_patches_dir(kernel_version, verbose=args.verbose)
    print("Found patches directory:    {}".format(patches_dir))
    sys.stdout.flush()
    if patches_dir is None:
        raise

    # Go ahead and do patching of kernel sources
    init_commit = patch_in("gitbuild", patches_dir, src_dir, verbose=args.verbose, clean_patch=True)

    if init_commit is not None:
        filepath = os.path.join(patches_dir, "complete.patch")
        commit_and_create_patch(filepath, src_dir, commit_hash=init_commit, verbose=args.verbose)
    print("Patching Complete")
    sys.stdout.flush()
    sleep(3)


    # Run kernel build
    if args.nobuild:
        run_cmd("rm -rf ./output;", allow_errors=True)
        copy_outputs("{}/*.new".format(patches_dir), outputdir='./output/patches/')
        return

    # We're going to build ubuntu debs
    run_cmd("cp /boot/config-$(uname -r) .config", workingdir=src_dir, allow_errors=False, verbose=args.verbose)
    run_cmd("make olddefconfig", workingdir=src_dir, allow_errors=False, verbose=args.verbose)
    run_cmd("./scripts/config --disable SYSTEM_TRUSTED_KEYS", workingdir=src_dir, allow_errors=False, verbose=args.verbose)
    run_cmd("./scripts/config --disable SYSTEM_REVOCATION_KEYS", workingdir=src_dir, allow_errors=False, verbose=args.verbose)
    run_cmd("make olddefconfig", workingdir=src_dir, allow_errors=False, verbose=args.verbose)
    exitcode, _, _ = run_cmd("make -j $(nproc) deb-pkg LOCALVERSION=-custom", workingdir=src_dir, allow_errors=True, live_output=True, verbose=args.verbose)
    if exitcode != 0:
        # If make dies run it single threaded to make debug easier
        run_cmd("make", workingdir=src_dir, allow_errors=True, verbose=args.verbose, live_output=True)

    # Copy outputs
    run_cmd("rm -rf ./output;", allow_errors=True)
    copy_outputs("./build/*.deb")
    copy_outputs("{}/*.new".format(patches_dir), outputdir='./output/patches/')
