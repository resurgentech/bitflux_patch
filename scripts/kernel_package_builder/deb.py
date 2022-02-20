# Copyright (c) Resurgent Technologies 2021

from .common import *
from .patching import *
from jinja2 import Template


def apt_update_upgrade(allow_errors=False, verbose=False, live_output=False):
    """
    Update and upgrade apt repos to latest
    """
    run_cmd("apt autoremove -y", allow_errors=allow_errors, verbose=verbose, live_output=live_output)
    run_cmd("apt update", allow_errors=allow_errors, verbose=verbose, live_output=live_output)
    run_cmd("DEBIAN_FRONTEND=noninteractive apt upgrade -y", allow_errors=allow_errors, verbose=verbose, live_output=live_output)


def apt_list_linux_images(searchfactor, allow_errors=False, verbose=False):
    """
    Look up list of linux images from apt

    :return: array of {name: imagename, description: description_string}
    """
    _, out, _ = run_cmd("apt-cache search linux", allow_errors=allow_errors, verbose=verbose)
    raw_list = out.splitlines()
    image_list = []
    for rawline in raw_list:
        quitter = False
        a = rawline.split(' - ')
        b = {'name': a[0], 'description': a[1]}
        for factor in searchfactor:
            if not re.search(factor, b['name']):
                quitter = True
        if not quitter:
            image_list.append(b)
    return image_list


def debsrc_list_srt_func(elem):
    versioncalculated=0
    m = re.search("(\d\.\d+\.\d+\-\d+)", str(elem))
    a = m.group(0)
    print(a)
    #if a.endswith(".0"):
    #    a = a.rstrip(".0")
    versionparts = re.split(r"\.|-", a)
    print(versionparts)
    versioncalculated += int(versionparts[0])*10000000 
    versioncalculated += int(versionparts[1])*100000 
    versioncalculated += int(versionparts[2])*1000 
    versioncalculated += int(versionparts[3]) 
    return versioncalculated


def apt_get_linux_image_name(searchfactor, allow_errors=False, verbose=False):
    """
    Return the newest latest linux kernel image package name
    """
    image_list = apt_list_linux_images(searchfactor, allow_errors=allow_errors, verbose=verbose)
    sorted_image_list = sorted(image_list, key=debsrc_list_srt_func)
    image = sorted_image_list[-1]
    print(image)
    return image['name']


def apt_get_source(image_name, allow_errors=False, verbose=False, builddir='./build'):
    """
    Download source code and return where the kernel source code is
    """
    run_cmd("mkdir -p {}".format(builddir), allow_errors=allow_errors, verbose=verbose)
    cmd = "fakeroot apt-get source {}".format(image_name)
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


def deb_set_flavour(flavour, debian_dir, allow_errors=False, verbose=False):
    file_pair = [
        ['config/amd64/config.flavour.generic', 'config/amd64/config.flavour.{}'.format(flavour)],
        ['control.d/generic.inclusion-list', 'control.d/{}.inclusion-list'.format(flavour)],
        ['control.d/vars.generic', 'control.d/vars.{}'.format(flavour)]
    ]
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


def build_debs(src_dir, allow_errors=False, verbose=False, live_output=True):
    """
    Clean and build .debs

    :param path: path with kernel sources to build
    """
    run_cmd("LANG=C fakeroot debian/rules clean", workingdir=src_dir, allow_errors=allow_errors, verbose=verbose)
    print("--debian clean--")
    sys.stdout.flush()
    sleep(3)
    run_cmd("LANG=C fakeroot debian/rules debian/control", workingdir=src_dir, allow_errors=allow_errors, verbose=verbose)
    print("--debian contrl--")
    sys.stdout.flush()
    sleep(3)
    #run_cmd("LANG=C fakeroot debian/rules binary", workingdir=src_dir, allow_errors=allow_errors, verbose=verbose, live_output=live_output)
    # Not sure why but this works
    os.system("cd {}; LANG=C fakeroot debian/rules binary skipabi=true skipmodule=true skipretpoline=true skipdbg=true disable_d_i=true".format(src_dir))


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
    run_cmd("equivs-build {}".format(metapkg_template), workingdir="./build", allow_errors=allow_errors, verbose=verbose)


# Find package without building
def get_package_deb(args, configs):
    config = configs['distros'][args.distro]
    image_searchfactors = config['image_searchfactors']

    # Update and upgrade apt repos to latest
    apt_update_upgrade(allow_errors=True, live_output=False)
    print("apt repos updated and upgraded")
    sys.stdout.flush()
    sleep(3)

    # Return the newest latest linux kernel image package name
    image_name = apt_get_linux_image_name(image_searchfactors, verbose=False)
    print("Found image name:           {}".format(image_name))
    sys.stdout.flush()
    return image_name


def debian_style_build(args, configs):

    config = configs['distros'][args.distro]
    image_searchfactors = config['image_searchfactors']
    ver_ref_pkg = config['ver_ref_pkg']
    pkg_filters = config['pkg_filters']
    metapkg_template = config['metapkg_template']

    # Update and upgrade apt repos to latest
    apt_update_upgrade(allow_errors=True, live_output=False)
    print("apt repos updated and upgraded")
    sys.stdout.flush()
    sleep(3)

    bitflux_version = get_bitflux_version()
    print("Set bitflux_version:        {}".format(bitflux_version))
    sys.stdout.flush()
    sleep(2)

    # Return the newest latest linux kernel image package name
    image_name = apt_get_linux_image_name(image_searchfactors, verbose=False)
    print("Found image name:           {}".format(image_name))
    sys.stdout.flush()

    # Search patches for something that should match the kernel image package
    patches_dir = select_patches_dir(image_name, patches_root_dir='./patches')
    print("Found patches directory:    {}".format(patches_dir))
    sys.stdout.flush()
    if patches_dir is None:
        raise

    # Download source code and return where the kernel source code is located
    src_dir = apt_get_source(image_name, verbose=True)
    print("Found kernel src directory: {}".format(src_dir))
    sys.stdout.flush()

    debian_dir = deb_find_debian_dir(src_dir)
    print("Found DEBIAN directory: {}".format(debian_dir))
    sys.stdout.flush()

    # Do patching steps
    init_commit = patch_in(args.distro, patches_dir, src_dir, verbose=True, clean_patch=True)

    deb_set_flavour('swaphints', debian_dir, verbose=True)
    commit_and_create_patch('flavour', src_dir, verbose=True)

    if init_commit is not None:
        filepath = os.path.join(patches_dir, "complete.patch")
        commit_and_create_patch(filepath, src_dir, commit_hash=init_commit, verbose=True)
    print("Patching Complete")
    sys.stdout.flush()
    sleep(3)

    deb_hack_changelog(bitflux_version, src_dir, buildnum=args.buildnumber, verbose=True, clean_patch=True)

    # Build deb packages
    if args.nobuild:
        return
    build_debs(src_dir)
    build_meta_pkg(ver_ref_pkg, pkg_filters, metapkg_template)

    # Copy outputs
    run_cmd("rm -rf ./output;", allow_errors=True)
    copy_outputs("./build/*.deb")
    copy_outputs("{}/*.new".format(patches_dir), outputdir='./output/patches/')
