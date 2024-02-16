# Copyright (c) Resurgent Technologies 2021

from .common import *
from .patching import *
from jinja2 import Template
import yaml


def apt_update_upgrade(allow_errors=False, verbose=False, live_output=False):
    """
    Update and upgrade apt repos to latest
    """
    run_cmd("apt autoremove -y", allow_errors=allow_errors, verbose=verbose, live_output=live_output)
    run_cmd("apt update", allow_errors=allow_errors, verbose=verbose, live_output=live_output)
    run_cmd("DEBIAN_FRONTEND=noninteractive apt upgrade -y", allow_errors=allow_errors, verbose=verbose, live_output=live_output)


def apt_linux_version_fair_name(name):
    # Version can have sections segmented '~' '-' let's make it all '.'
    fixedname1 = name.replace('-', '.')
    fixedname2 = fixedname1.replace('~', '.')
    a = fixedname2.split('.')
    a2 = []
    # Just zero pad the sections to make it fair when sorting
    # like 5.4 should be lower ranked than 5.15
    for b in a:
        if len(str(b)) > 15:
            print("did not plan for this name='{}'".format(name))
            raise
        a2.append(str(b).zfill(16))
    for i in range(16-len(a)):
        a2.append("0".zfill(16))
    output = '.'.join(a2)
    return output


def apt_cache_show(search_pkg, allow_errors=False, verbose=False):
    """
    Look up list of linux images from apt-cache

    :return: array of [{}]
    """
    _, out, _ = run_cmd("apt-cache show {}".format(search_pkg), allow_errors=allow_errors, verbose=verbose)
    sections = []
    section = []
    for line in out.splitlines():
        if line == "":
            sections.append("\n".join(section))
        section.append(line)
    output = []
    for section in sections:
        output.append(yaml.load(section, Loader=yaml.Loader))
    for section in output:
        for k, v in section.items():
            # Let's process any entries that are lists
            v1 = str(v).split(',')
            if len(v1) > 1:
                v2 = []
                for a in v1:
                    v2.append(a.strip())
                section[k] = v2
        # We want to sort on Version but it's weird so let's pad it to make it work
        section['sorthelper'] = apt_linux_version_fair_name(section["Version"])
    return output


def debsrc_list_srt_func(elem):
    return elem['sorthelper']


def apt_get_linux_image_name(search_pkg, allow_errors=False, verbose=False):
    """
    Return the newest latest linux kernel image package name
    """
    image_list = apt_cache_show(search_pkg, allow_errors=allow_errors, verbose=verbose)

    # sort list on sorthelper key
    sorted_image_list = sorted(image_list, key=debsrc_list_srt_func)
    fullimage = sorted_image_list[-1]
    print("found image '{}'".format(fullimage))

    if isinstance(fullimage["Depends"], list):
        rawversion = fullimage["Depends"][0]
    else:
        rawversion = fullimage["Depends"]
    if rawversion.find("linux-image") == -1:
        print("did not find linux-image in '{}'".format(rawversion))
        return fullimage['Package']

    if rawversion.find("("):
        image = rawversion.replace(" ", "").replace("(", "").replace(")", "")
    else:
        image = rawversion.split(" ")[0]
    return image


def apt_get_source(image_name, allow_errors=False, verbose=False, builddir='./build'):
    """
    Download source code and return where the kernel source code is
    """
    run_cmd("mkdir -p {}".format(builddir), allow_errors=allow_errors, verbose=verbose)
    cmd = "fakeroot apt-get source {}".format(image_name)
    print("cmd='{}'".format(cmd))
    run_cmd(cmd, workingdir=builddir, allow_errors=allow_errors, verbose=verbose)
    # preceding command should leave a directory containing actual patched source
    path = find_directory(searchdir=builddir)
    if path is None:
        raise
    return path


def merge_debian_master_changelog(path, src_dir, clean_patch, verbose=False):
    """
    Merge changelog changes from file

    :param path: path to file containing new entries
    :param src_dir: path with kernel files
    :param clean_patch: git magic for dealing with recording patches
    """
    print("Merging {}".format(path))
    subfolders = [f.path for f in os.scandir(src_dir) if f.is_dir()]
    for subfolder in subfolders:
        kpathname = os.path.basename(subfolder)
        if kpathname.find('debian'):
            continue
        changelog_path = os.path.join(src_dir, kpathname, 'changelog')
        if not os.path.isfile(changelog_path):
            continue
        with open(changelog_path, 'r') as file:
            original_contents_array = file.readlines()
        for i in range(len(original_contents_array)):
            a = original_contents_array.pop(0)
            if a.startswith(" -- "):
                break
        original_contents = "".join(original_contents_array)
        with open(path, 'r') as file:
            new_contents = file.read()
        with open(changelog_path, 'w') as file:
            file.write(new_contents)
            file.write(original_contents)
    if clean_patch:
        git_commit(path, workingdir=src_dir, verbose=verbose)
    sys.stdout.flush()
    sleep(1)


def deb_hack_changelog(bitflux_version, src_dir, buildnum=None, verbose=True, clean_patch=True):
    subfolders = [f.path for f in os.scandir(src_dir) if f.is_dir()]
    for subfolder in subfolders:
        kpathname = os.path.basename(subfolder)
        if kpathname.find('debian'):
            continue
        changelog_path = os.path.join(src_dir, kpathname, 'changelog')
        if not os.path.isfile(changelog_path):
            continue
        with open(changelog_path, 'r') as file:
            original_contents_array = file.readlines()
        line = original_contents_array[0]
        print("old changelog line from '{}' = '{}'".format(changelog_path, line))
        m = re.search('\([0-9\.]+-([0-9\.]+)', line)
        if not m:
            continue
        a = m.group(0)
        line = line.replace(a, '{}.{}'.format(a, buildnum))
        line = line.replace(')', '+{})'.format(bitflux_version))
        if not m:
            continue
        a = m.group(0)
        if verbose:
            print("new changelog line from '{}' = '{}'".format(changelog_path, line))
        original_contents_array[0] = line
        original_contents = "".join(original_contents_array)
        with open(changelog_path, 'w') as file:
            file.write(original_contents)
    if clean_patch:
        commit_and_create_patch("changeloghack", src_dir, verbose=verbose)
    sys.stdout.flush()
    sleep(1)


def deb_get_abi_dir(debian_dir):
    abi_dir = os.path.join(debian_dir, 'abi')
    dirlist = [f.path for f in os.scandir(abi_dir) if f.is_dir()]
    # Some of these build have the directory here
    if os.path.join(abi_dir, 'amd64') in dirlist:
        return os.path.join(abi_dir, 'amd64')
    # Others have another dir in here
    if len(dirlist) != 1:
        print("I don't know how to handle this")
        print("dirlist={}".format(dirlist))
        raise
    return os.path.join(dirlist[0], 'amd64')


def deb_hack_abi_records(flavour, debian_dir, verbose=True):
    '''
    Copies debian.master/abi/amd64/generic* to debian.master/abi/amd64/'flavour'*
     or debian.master/abi/xxx/amd64/generic* to debian.master/abi/xxx/amd64/'flavour'*
    Because the build wants them to check stuff from the previous build
    '''
    abi_dir = deb_get_abi_dir(debian_dir)
    filelist = [f.path for f in os.scandir(abi_dir) if not f.is_dir()]
    for f in filelist:
        a = os.path.basename(f)
        b = a.split('.')
        if b[0] != 'generic':
            continue
        b[0] = flavour
        c = '.'.join(b)
        d = os.path.dirname(f)
        newf = os.path.join(d,c)
        print("src={}  dst={}".format(f, newf))
        shutil.copyfile(f, newf)


def deb_hack_binary_arch(src_dir, verbose=True):
    # Fixes issue with PopOS build on linux 6.6, I think it happens because the find comes up empty... which may be a symptom of a problem
    filename = os.path.join(src_dir, 'debian/rules.d/2-binary-arch.mk')
    compstr="find debian/$(1) -name '*.ko' -print0 | xargs -0 -n1 -P $(CONCURRENCY_LEVEL) zstd -19 --quiet --rm"
    repstr="find debian/$(1) -name '*.ko' -print0 | xargs -r -0 -n1 -P $(CONCURRENCY_LEVEL) zstd -19 --quiet --rm"
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            origdata = file.read()
        newdata = origdata.replace(compstr, repstr)
        if newdata == origdata:
            print("file '{}' not changed".format(filename))
            return
        else:
            print("file '{}' changed".format(filename))
        with open(filename, 'w') as file:
            file.write(newdata)
    else:
        print("file not found '{}'".format(filename))


def deb_set_flavour(flavour, debian_dir, allow_errors=False, verbose=False):
    '''
    Generates flavour specific files for our new flavour
    '''
    file_pair = [
        ['control.d/generic.inclusion-list', 'control.d/{}.inclusion-list'.format(flavour)],
        ['control.d/vars.generic', 'control.d/vars.{}'.format(flavour)]
    ]

    # Hack for checking for old way of doing flavours
    if os.path.isfile(os.path.join(debian_dir, 'config/amd64/config.flavour.generic')):
        file_pair.append(['config/amd64/config.flavour.generic', 'config/amd64/config.flavour.{}'.format(flavour)])

    for a in file_pair:
        duplicate_file(a[0], a[1], workingdir=debian_dir, verbose=verbose)
    sed_sets = [
        ['amd64-generic', 'amd64-{}'.format(flavour), 'config/annotations'],
        ['amd64 generic lowlatency', 'amd64 generic lowlatency {}'.format(flavour), 'etc/getabis'],
        ['amd64 generic', 'amd64 generic lowlatency {}'.format(flavour), 'etc/getabis'],
        ['generic lowlatency', flavour, 'rules.d/amd64.mk'],
        ['generic', flavour, 'rules.d/amd64.mk']
    ]
    for a in sed_sets:
        filepath = os.path.join(debian_dir, a[2])
        cmd = "sed -i 's/{}/{}/' {}".format(a[0], a[1], filepath)
        run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)


def deb_find_debian_dir(src_dir, allow_errors=False, verbose=True):
    filepath = os.path.join(src_dir, 'debian', 'debian.env')
    cmd = ". {}; echo $DEBIAN".format(filepath)
    _, output, _ = run_cmd(cmd, allow_errors=allow_errors, verbose=verbose)
    debian = output.strip()
    debian_dir = os.path.join(src_dir, debian)
    return debian_dir


def build_debs_hack(src_dir, allow_errors=False, verbose=False, live_output=True):
    """
    Clean and build .debs

    :param path: path with kernel sources to build
    """
    printfancy("HACK", timeout=3)

    printfancy("debian clean", timeout=3)
    run_cmd("LANG=C fakeroot debian/rules clean", workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output)

    printfancy("debian control", timeout=3)
    run_cmd("LANG=C fakeroot debian/rules debian/control", workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output)

    printfancy("debian build")
    cmd = "LANG=C fakeroot debian/rules build"
    run_cmd(cmd, workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output, no_stdout=True)

    printfancy("HACK: cp vmlinux")
    cmd = "mkdir -p debian/build/tools-perarch/tools/bpf/bpftool; cp tools/bpf/bpftool/vmlinux debian/build/tools-perarch/tools/bpf/bpftool/"
    run_cmd(cmd, workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output, no_stdout=True)

    printfancy("debian binary")
    cmd = "LANG=C fakeroot debian/rules binary"
    run_cmd(cmd, workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output, no_stdout=True)


def build_debs(src_dir, allow_errors=False, verbose=False, live_output=True):
    """
    Clean and build .debs

    :param path: path with kernel sources to build
    """
    printfancy("debian clean", timeout=3)
    run_cmd("LANG=C fakeroot debian/rules clean", workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output)

    printfancy("debian control", timeout=3)
    run_cmd("LANG=C fakeroot debian/rules debian/control", workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output)

    printfancy("debian binary")
    cmd = "LANG=C fakeroot debian/rules binary"
    run_cmd(cmd, workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output, no_stdout=True)


def filter_pkg_for_meta_pkg(pkg_filters, filename):
    if not filename.endswith(".deb"):
        return True
    for token in pkg_filters:
        if token in filename:
            return True
    return False


def build_meta_pkg(ver_ref_pkg, pkg_filters, metapkg_template, allow_errors=False, verbose=False, live_output=True):
    """
    Builds a meta package that installs all other packages
    """
    dependentpkgnames = []
    versionnumber = ["", ""]
    for (dirpath, dirnames, filenames) in os.walk("./build"):
        for filename in filenames:
            # We only need a few primary packages we'll filter those out.
            if filter_pkg_for_meta_pkg(pkg_filters, filename):
                continue
            subfilenames = filename.split("_", 1)
            dependentpkgnames.append(subfilenames[0])
            print(subfilenames[0])
            # Picking a file and extracting version numbers from it's name
            if ver_ref_pkg in filename:
                versionnumber = subfilenames[1].split(".deb", 1)
                architecture = versionnumber[0].split("_", 1)
    print(versionnumber)
    # use jinja template to create package definiation for equivs to build
    template_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'template', metapkg_template + ".j2")
    with open(template_path) as file_:
        template = Template(file_.read())
    templateoutput = template.render(dependencies=", ".join(dependentpkgnames), version=architecture[0], arch=architecture[1])
    print(templateoutput)
    with open('./build/{}'.format(metapkg_template), "w") as file_:
        file_.write(templateoutput)
    # Actually make metapkg
    run_cmd("equivs-build {}".format(metapkg_template), workingdir="./build", allow_errors=allow_errors, verbose=verbose, no_stdout=True)


# Find package without building
def get_package_deb(args):
    # Update and upgrade apt repos to latest
    apt_update_upgrade(allow_errors=True, live_output=False)
    print("apt repos updated and upgraded")
    sys.stdout.flush()
    sleep(3)

    # Return the newest latest linux kernel image package name
    image_name = apt_get_linux_image_name(args.search_pkg, verbose=False)
    print("Found image name:           {}".format(image_name))
    sys.stdout.flush()
    return image_name


def printfancy(str, timeout=0.1):
    print('------------------------------------------------------------------------------')
    print('--- {}'.format(str))
    print('------------------------------------------------------------------------------')
    sys.stdout.flush()
    sleep(timeout)


def debian_style_build(args):
    ver_ref_pkg = args.ver_ref_pkg
    search_pkg = args.search_pkg
    pkg_filters = json.loads(args.pkg_filters)
    metapkg_template = args.metapkg_template
    printfancy("BUILDING DEBIAN STYLE PACKAGE")

    # Update and upgrade apt repos to latest
    printfancy("update and upgrade apt repos...")
    apt_update_upgrade(allow_errors=True)
    printfancy("DONE - apt repos updated and upgraded", timeout=3)

    bitflux_version = get_bitflux_version()
    printfancy("Set bitflux_version:        {}".format(bitflux_version), timeout=3)

    # Return the newest latest linux kernel image package name
    image_name = apt_get_linux_image_name(search_pkg, verbose=args.verbose)
    printfancy("Found image name:           {}".format(image_name))

    # Search patches for something that should match the kernel image package
    patches_dir = select_patches_dir(image_name, patches_root_dir='./patches')
    printfancy("Found patches directory:    {}".format(patches_dir))
    if patches_dir is None:
        raise

    # Download source code and return where the kernel source code is located
    #src_dir = apt_get_source('linux', verbose=args.verbose)
    src_dir = apt_get_source(image_name, verbose=args.verbose)
    printfancy("Found kernel src directory: {}".format(src_dir))

    debian_dir = deb_find_debian_dir(src_dir)
    printfancy("Found DEBIAN directory: {}".format(debian_dir))

    # Do patching steps
    init_commit = patch_in(args.distro, patches_dir, src_dir, verbose=args.verbose, clean_patch=True)

    printfancy("Creating flavour swaphints config files")
    deb_set_flavour('swaphints', debian_dir, verbose=True)
    commit_and_create_patch('flavour', src_dir, verbose=True)

    if init_commit is not None:
        filepath = os.path.join(patches_dir, "complete.patch")
        commit_and_create_patch(filepath, src_dir, commit_hash=init_commit, verbose=args.verbose)
    printfancy("Patching Complete", timeout=3)

    printfancy("Modifying debian changelog")
    deb_hack_changelog(bitflux_version, src_dir, buildnum=args.buildnumber, verbose=args.verbose, clean_patch=True)

    printfancy("Mocking out current abi files")
    deb_hack_abi_records('swaphints', debian_dir, verbose=args.verbose)

    printfancy("Modifying debian/rules.d/2-binary-arch.mk")
    deb_hack_binary_arch(src_dir, verbose=args.verbose)

    # Build deb packages
    if args.nobuild:
        return
    printfancy("Build .deb files")
    try:
        build_debs(src_dir, verbose=args.verbose)
    except:
        build_debs_hack(src_dir, verbose=args.verbose)
    printfancy("Build meta_pkg .deb")
    build_meta_pkg(ver_ref_pkg, pkg_filters, metapkg_template)

    # Copy outputs
    run_cmd("rm -rf ./output;", allow_errors=True, verbose=args.verbose)
    copy_outputs("./build/*.deb", verbose=args.verbose)
    copy_outputs("{}/*.new".format(patches_dir), outputdir='./output/patches/', verbose=args.verbose)
