# Copyright (c) Resurgent Technologies 2021

from .common import *
from .git import *
import distutils.dir_util


def select_patches_dir(image_name, patches_root_dir='./patches', verbose=False):
    """
    Search patches for something that should match.

    :param image_name: name of deb package
    :param patches_root_dir: root of patches dir
    :param verbose:
    :return: path to directory with patches for this kernel or None
    """
    m = re.search("(\d\.\d+)", image_name)
    a = m.group(0)
    b = a.split('.')
    major = b[0]
    minor = b[1]

    if find_directory(searchdir=patches_root_dir, matchdir=major) is None:
        print("can't find {} kernel in {} - image_name: {}".format(major, patches_root_dir, image_name))
        return None
    major_dir = os.path.join(os.path.abspath(patches_root_dir), major)
    if find_directory(searchdir=major_dir, matchdir=minor) is not None:
        minor_dir = os.path.join(major_dir, minor)
        return minor_dir
    iminor = int(minor)
    for i in range(iminor + 1):
        j = iminor - i
        if find_directory(searchdir=major_dir, matchdir="{}".format(j)) is not None:
            if verbose:
                print("Couldn't find patch for {}.{}, trying next best option {}.{}".format(major, minor, major, j))
            minor_dir = os.path.join(major_dir, "{}".format(j))
            return minor_dir
    print("Couldn't find and patches for {}.{}".format(major, minor))
    return None


def commit_and_create_patch(patchname, src_dir, commit_hash=None, verbose=False):
    if commit_hash is None:
        commit_hash = git_hash(workingdir=src_dir, verbose=verbose)
    git_add("*", workingdir=src_dir, verbose=verbose)
    git_commit(patchname, workingdir=src_dir, verbose=verbose)
    filepath = "{}.new".format(patchname)
    git_diff(commit_hash, filepath, workingdir=src_dir, verbose=verbose)


def copy_files_into_src(path, src_dir, clean_patch, allow_errors=False, verbose=False):
    print("\tCopying {}".format(path))
    dst_dir = os.path.join(src_dir, os.path.basename(path))
    distutils.dir_util.copy_tree(path, dst_dir)
    if clean_patch:
        commit_and_create_patch(path, src_dir, verbose=verbose)
    sys.stdout.flush()
    sleep(1)


def apply_patch_deprecated(path, src_dir, clean_patch, allow_errors=False, verbose=False):
    print("Patching {}".format(path))
    _, files, _ = run_cmd("ls {}* | grep -v new$".format(path), allow_errors=allow_errors, verbose=verbose)
    print("files = '{}'".format(files))
    exitcode = 1
    for file in files.split():
        print("file = '{}'".format(file))
        exitcode, _, _ = run_cmd("patch -p1 -F 100 -i {}".format(path), workingdir=src_dir, allow_errors=True, verbose=verbose)
        # Clean up leftovers
        cmd = "find . | grep .orig$ | sed 's/^/rm /' | bash"
        run_cmd(cmd, workingdir=src_dir, allow_errors=True, verbose=verbose)
        cmd = "find . | grep .rej$ | sed 's/^/rm /' | bash"
        run_cmd(cmd, workingdir=src_dir, allow_errors=True, verbose=verbose)
        if exitcode == 0:
            break
    if exitcode != 0 and not allow_errors:
        sys.stdout.flush()
        sleep(1)
        raise
    if clean_patch:
        commit_and_create_patch(path, src_dir, verbose=verbose)
    sys.stdout.flush()
    sleep(1)


def apply_patch(path, src_dir, clean_patch, allow_errors=False, verbose=False):
    print("\tPatching {}".format(path))
    # First try to apply the patch with dry-run to see if it will work
    patch_cmd = "patch -p1 -i {} --dry-run".format(path)
    exitcode, stdout, stderr = run_cmd(patch_cmd, workingdir=src_dir, allow_errors=True, verbose=verbose)
    if exitcode != 0 and not allow_errors:
        print_run_cmd(patch_cmd, exitcode, stdout, stderr)
        sys.stdout.flush()
        sleep(1)
        return False
    # Now apply the patch, if dry-run worked
    patch_cmd = "patch -p1 -i {}".format(path)
    exitcode, _, _ = run_cmd(patch_cmd, workingdir=src_dir, allow_errors=True, verbose=verbose)
    # Clean up leftovers
    cmd = "find . | grep .orig$ | sed 's/^/rm /' | bash"
    run_cmd(cmd, workingdir=src_dir, allow_errors=True, verbose=verbose)
    cmd = "find . | grep .rej$ | sed 's/^/rm /' | bash"
    run_cmd(cmd, workingdir=src_dir, allow_errors=True, verbose=verbose)
    # Really shouldn't fail here, given the testing above, but just in case
    if exitcode != 0 and not allow_errors:
        print_run_cmd(patch_cmd, exitcode, stdout, stderr)
        sys.stdout.flush()
        sleep(1)
        return False
    if clean_patch:
        commit_and_create_patch(path, src_dir, verbose=verbose)
    sys.stdout.flush()
    sleep(1)
    return True


def merge_c_file(path, src_dir, clean_patch, verbose=False):
    """
    Merging contents from .merge file into c file.  Uses convention
    """
    a = os.path.basename(path)
    b = a.split("--")
    c = "/".join(b[0].split("__"))
    dst_file = ".".join(c.split("_"))
    print("\tMerging {} into {}".format(path, dst_file))

    d = "{}.merge".format(b[1].split('.merge')[0])
    insertion_point = "//{}//".format(d)
    dst_path = os.path.join(src_dir, dst_file)
    with open(dst_path, 'r') as file:
        original_contents_array = file.readlines()
    with open(path, 'r') as file:
        insert_data = file.readlines()
    new_contents = []
    for line in original_contents_array:
        if line.strip() == insertion_point:
            for nline in insert_data:
                new_contents.append(nline)
            continue
        new_contents.append(line)
    new_file_contents = "".join(new_contents)
    with open(dst_path, 'w') as file:
        file.write(new_file_contents)
    if clean_patch:
        commit_and_create_patch(path, src_dir, verbose=verbose)
    sys.stdout.flush()
    sleep(1)


def filter_dir(sorted_subfolders, src_dir, clean_patch, splitter, distro, only_dirs=False, allow_errors=False, verbose=False):
    """
    Filter paths in patching dir for .distro files
    """
    bucket = []
    # Filter contents
    for path in sorted_subfolders:
        #print("\tpath={}".format(path))
        if os.path.splitext(path)[1] == '.new':
            continue
        if only_dirs:
            if not os.path.isdir(path):
                #print("only_dirs")
                continue
        else:
            if os.path.isdir(path):
                #print("os.path.isdir(path)")
                continue
            if not splitter in path:
                #print("no splitter")
                continue
        split_path = path.split(splitter)
        # name for distro specfic variant
        #print("\tsplit_path={}".format(split_path))
        if split_path[-1] == '':
            split_path.pop(-1)
        #print("\tdistro={}".format(distro))
        if distro is None:
            distro_path = None
        elif splitter == '.':
            # special case for directories vs .patch/.merge files
            distro_path = splitter.join([split_path[0]] + [distro])
        else:
            distro_path = splitter.join([split_path[0]] + [".{}".format(distro)])
        #print("\tdistro_path={}".format(distro_path))
        if len(split_path) > 2:
            print("Not sure what this is '{}'".format(path))
            continue
        if len(split_path) > 1:
            # only log path with extension if it's specific to this distro
            if distro_path == path:
                #print("distro_path == path")
                bucket.append(path)
            #print("len(split_path) > 1")
            continue
        if distro_path is None:
            bucket.append(path)
        else:
            if not os.path.exists(distro_path):
                #print("\tadding path '{}'".format(path))
                bucket.append(path)
    #print("\tfiltering:")
    #print("\t\t{}".format(bucket))
    return bucket


def patch_copy_dirs(sorted_subfolders, src_dir, clean_patch, distro, allow_errors=False, verbose=False):
    """
    Copy directory trees
    """
    bucket = filter_dir(sorted_subfolders, src_dir, clean_patch, '.', distro, only_dirs=True, allow_errors=allow_errors, verbose=verbose)
    print("Copying Directories:")
    for path in bucket:
        copy_files_into_src(path, src_dir, clean_patch, allow_errors=allow_errors, verbose=verbose)


def apply_patches(sorted_subfolders, src_dir, clean_patch, distro, allow_errors=False, verbose=False):
    """
    Apply patches to sources will try alternate patch if first fails
       alternate patch is same name with a number as a final prefix appended
    """
    bucket = filter_dir(sorted_subfolders, src_dir, clean_patch, '.patch', distro, allow_errors=allow_errors, verbose=verbose)
    print(f"bucket: {bucket}")
    print("Appyling Patches:")
    for path in bucket:
        failed = True
        alternates = glob.glob('{}.[0-9]'.format(path))
        if not apply_patch(path, src_dir, clean_patch, verbose=verbose):
            for alt in alternates:
                print("Trying alternate '{}'".format(alt))
                if apply_patch(alt, src_dir, clean_patch, verbose=verbose):
                    failed = False
                    break
        else:
            failed = False
        if failed:
            print("Failed to apply patch or alternates '{}'".format(path))
            raise


def merge_c_files(sorted_subfolders, src_dir, clean_patch, distro, allow_errors=False, verbose=False):
    """
    Merge segments to sources
    """
    bucket = filter_dir(sorted_subfolders, src_dir, clean_patch, '.merge', distro, allow_errors=allow_errors, verbose=verbose)
    print("Merge C files:")
    for path in bucket:
        merge_c_file(path, src_dir, clean_patch, verbose=verbose)


def patch_in(distro, patches_dir, src_dir, allow_errors=False, verbose=False, clean_patch=False):
    """
    Apply patches, merge changelog files, and add files to kernel

    :param distro: 
    :param patches_dir: path containing patches
    :param src_dir: path to kernel sources
    """
    if clean_patch:
        init_commit = git_create_repo(src_dir, verbose=False)
    else:
        init_commit = None
    subfolders = [f.path for f in os.scandir(patches_dir)]
    sorted_subfolders = sorted(subfolders)
    print(sorted_subfolders)
    patch_copy_dirs(sorted_subfolders, src_dir, clean_patch, distro, allow_errors=allow_errors, verbose=verbose)
    apply_patches(sorted_subfolders, src_dir, clean_patch, distro, allow_errors=allow_errors, verbose=verbose)
    merge_c_files(sorted_subfolders, src_dir, clean_patch, distro, allow_errors=allow_errors, verbose=verbose)
    return init_commit


def make_unified_patch(distro, patches_dir, tarball, allow_errors=False, verbose=False, builddir='./build/kernel_source'):
    run_cmd("rm -rf {};".format(builddir), allow_errors=True, verbose=verbose)
    cmd = "mkdir -p {}; cd {}; tar xvf {}".format(builddir, builddir, tarball)
    run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    src_dir = find_directory(searchdir=builddir)
    init_commit = patch_in(distro, patches_dir, src_dir, allow_errors=allow_errors, verbose=verbose, clean_patch=True)
    print("aaa\n")
    filepath = os.path.join(patches_dir, "complete.patch.new")
    git_diff(init_commit, filepath, workingdir=src_dir, verbose=verbose)
    return filepath
