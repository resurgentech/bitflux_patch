# Copyright (c) Resurgent Technologies 2021

from .common import *
from .patching import *
import jinja2
import jinja2.meta
import yaml
import glob

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


def apt_get_package_stats(search_pkg, allow_errors=False, verbose=False):
    """
    Returns the latest apt package stats
    """
    image_list = apt_cache_show(search_pkg, allow_errors=allow_errors, verbose=verbose)

    # sort list on sorthelper key
    sorted_image_list = sorted(image_list, key=debsrc_list_srt_func)
    fullimage = sorted_image_list[-1]
    return fullimage


def apt_get_linux_image_name(search_pkg, allow_errors=False, verbose=False):
    """
    Return the newest latest linux kernel image package name
    """
    fullimage = apt_get_package_stats(search_pkg, allow_errors=allow_errors, verbose=verbose)
    print("found image '{}'".format(fullimage))

    return fullimage['Package'], fullimage['Version']


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
        m = re.search(r'\([0-9\.]+-([0-9\.]+)', line)
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


def deb_set_flavour(flavour, orig_flavour, debian_dir, allow_errors=False, verbose=False):
    '''
    Generates flavour specific files for our new flavour
    '''
    file_pair = [
        [f"control.d/{orig_flavour}.inclusion-list", f"control.d/{flavour}.inclusion-list"],
        [f"control.d/vars.{orig_flavour}", f"control.d/vars.{flavour}"]
    ]

    # Hack for checking for old way of doing flavours
    if os.path.isfile(os.path.join(debian_dir, f"config/amd64/config.flavour.{orig_flavour}")):
        file_pair.append([f"config/amd64/config.flavour.{orig_flavour}", 'config/amd64/config.flavour.{}'.format(flavour)])

    for a in file_pair:
        duplicate_file(a[0], a[1], workingdir=debian_dir, verbose=verbose)
        if a[1] == f"control.d/{flavour}.inclusion-list":
            spliced = False
            # we need to add fs/proc/ to the inclusion list for the swaphints.ko to be added to the modules deb
            with open(os.path.join(debian_dir, a[1]), 'r') as file:
                lines = file.readlines()
            with open(os.path.join(debian_dir, f"{a[1]}.bak"), 'w') as file:
                for line in lines:
                    file.write(line)
            newlines = []
            for i in range(len(lines)):
                line = lines[i].strip()
                if (not spliced) and line.startswith('fs/'):
                    b = line.split('/')
                    if b[1][0] > 'proc':
                        newlines.append('fs/proc/*')
                        spliced = True
                newlines.append(line)
            if not 'fs/proc/*' in newlines:
                raise BaseException("Missing 'fs/proc/*' in {}".format(a[1]))
            with open(os.path.join(debian_dir, a[1]), 'w') as file:
                newlines.append('')
                file.write('\n'.join(newlines))
    sed_sets = [
        # We might not need this either...
        [f"amd64-{orig_flavour}", f"amd64-{flavour}", 'config/annotations'],
        # old versions had this... deprecated for now
        # ['amd64 generic lowlatency', 'amd64 generic lowlatency {}'.format(flavour), 'etc/getabis'],
        # ['amd64 generic', 'amd64 generic lowlatency {}'.format(flavour), 'etc/getabis'],
        [f"{orig_flavour} lowlatency", flavour, 'rules.d/amd64.mk'],
        [orig_flavour, flavour, 'rules.d/amd64.mk']
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


def get_package_stats(version_ref_pkg, package_dir="./build"):
    for (dirpath, dirnames, filenames) in os.walk(package_dir):
        for filename in filenames:
            subfilenames = filename.split("_", 1)
            if version_ref_pkg in filename:
                versionstr = subfilenames[1].split(".deb", 1)
                versionchunks = versionstr[0].split("_", 1)
                versionnumber = versionchunks[0]
                architecture = versionchunks[1]
                return versionnumber, architecture
    print("Failure in get_package_version()")
    print(f"  Could not find version_ref_pkg: {version_ref_pkg}")
    exit(1)

def render_jinja_template(template_content, data):
    template = jinja2.Template(template_content)
    parsed_content = template.environment.parse(template_content)
    variables = jinja2.meta.find_undeclared_variables(parsed_content)
    missing_keys = []
    for variable in variables:
        if variable not in data:
            missing_keys.append(variable)
    if len(missing_keys) > 0:
        print("Failed render_jinja_template()!!!")
        print(f"  Missing keys: {missing_keys}")
        print(f"  Data:")
        print(f"{data}")
        print(f"  Template:")
        print(f"{template_content}")
        exit(1)
    templateoutput = template.render(data)
    return templateoutput


def filter_pkg_for_meta_pkg(pkg_filters, filename):
    if not filename.endswith(".deb"):
        return True
    for token in pkg_filters:
        if token in filename:
            return True
    return False


def update_list_with_orig_flavour(key, orig_pkg, flavour, orig_flavour, builddir, overrides=[], missing_okay=False):
    elements = orig_pkg.get(key,[])
    # sometimes the list is a string, which messes stuff up here
    if not isinstance(elements, list):
        elements = [elements]
    # if the list is empty, nothing to edit
    if len(elements) == 0:
        return ""
    # iterate over the elements, and update the flavour when relevent
    missing_files = []
    fixedelements = []
    for e in elements:
        if orig_flavour in e:
            fixed_e = e.replace(orig_flavour, flavour)
            # Processing overrides if any
            for override in overrides:
                p = re.compile(override['pattern'])
                if p.search(fixed_e):
                    fixed_e = fixed_e.replace(override['original'], override['replacement'])
            fixedelements.append(fixed_e)
            # looking for matching files
            fname = fixed_e.split()[0]
            deb_files = glob.glob(f"{builddir}/{fname}*.deb")
            if len(deb_files) == 0:
                missing_files.append(fname)
        else:
            fixedelements.append(e)
    if len(missing_files) > 0 and not missing_okay:
        print(f"Missing files for {key}:")
        for f in missing_files:
            print(f"  {f}")
    output = ", ".join(fixedelements)
    return output


def build_meta_pkg(metapkg_config, maintainer, versionnumber, arch, flavour, orig_flavour, builddir='./build', allow_errors=False, verbose=False, live_output=True):
    """
    Builds a meta package that installs all other packages
    """
    # Check for required keys
    required_keys = ['orig_pkg_name', 'pkg_name', 'jinja_template']
    missing_keys = []
    for key in required_keys:
        if key not in metapkg_config.keys():
            missing_keys.append(key)
    if len(missing_keys) > 0:
        n = metapkg_config.get('orig_pkg_name','unknown')
        print(f"Failure in build_meta_pkg({n})")
        print("  Missing keys:")
        for key in missing_keys:
            print(f"    '{key}'")
        print()
        print("metapkg_config:")
        print("```")
        print(metapkg_config)
        print("```")
        sys.exit(1)

    template_content = metapkg_config['jinja_template']
    pkg_name = metapkg_config['pkg_name']
    orig_pkg_name = metapkg_config['orig_pkg_name']
    overrides = metapkg_config.get('overrides', [])

    # fetch the original version number
    orig_version = ".".join(versionnumber.split("+")[0].split(".")[:-1])
    pattern = re.escape(f"(= {orig_version})")
    overrides.append({'pattern': pattern, 'original': f"(= {orig_version})", 'replacement': f"(= {versionnumber})"})

    printfancy(f"Building {pkg_name}")

    # Get the package stats from apt-cache to get some info
    orig_pkg = apt_get_package_stats(orig_pkg_name, allow_errors=allow_errors, verbose=verbose)

    # Collect data for jinja2 template insertion
    data = {}
    data['Package'] = pkg_name
    data['Architecture'] = arch
    data['Version'] = versionnumber
    data['Maintainer'] = maintainer

    data['Provides'] = update_list_with_orig_flavour('Provides', orig_pkg, flavour, orig_flavour, builddir, missing_okay=True)
    data['Recommends'] = update_list_with_orig_flavour('Recommends', orig_pkg, flavour, orig_flavour, builddir)
    data['Depends'] = update_list_with_orig_flavour('Depends', orig_pkg, flavour, orig_flavour, builddir, overrides=overrides)

    if verbose:
        print()
        print(f"orig_pkg:")
        print(json.dumps(orig_pkg, indent=2))
        print()
        print(f"data:")
        print(json.dumps(data, indent=2))
        print()

    # Use jinja template to create package definiation for equivs to build
    templateoutput = render_jinja_template(template_content, data)
    print(templateoutput)

    # Write out metapkg template
    with open(f"{builddir}/{pkg_name}", "w") as f:
        f.write(templateoutput)
    # Actually make metapkg
    _, output, _ = run_cmd(f"equivs-build {pkg_name}", workingdir=builddir, allow_errors=allow_errors, verbose=verbose, no_stdout=False)

    # Check for alternative deb file location
    #  equivs-build has some odd behaviour, it first claims it's gonna build to ../
    #  but then says, "just kidding, I'll put it here in the current directory"
    #  yet if TMPDIR is set then it build
    deb_file = None
    for line in output.splitlines():
        # Find the line where we announce the deb name first
        if f"building package '{pkg_name}'" in line and " in " in line:
            deb_file = line.split(" in ")[1].strip().lstrip("'").rstrip("'.")
            deb_basename = os.path.basename(deb_file)
        # Now we detect when we're gonna put the deb file in the current dir
        #  and fix up the path
        elif "Attention, the package has been created in the current directory" in line:
            deb_file = os.path.join(builddir, deb_basename)
        # Find the case where we pick another path, such as TMPDIR
        elif "Attention, the package has been created in the" in line:
            alt_dir = line.split("created in the ")[1].strip()
            alt_dir = alt_dir.split("directory")[0].strip()
            deb_file = os.path.join(alt_dir, deb_basename)

    # if we can't find the deb_file error out.
    if os.path.exists(deb_file):
        print(f"Found deb file: {deb_file}")
    else:
        print(output)
        raise BaseException(f"Failed to find deb file '{deb_file}'")

    # Rename the metapkg to something easier to deal with
    os.rename(f"{builddir}/{pkg_name}", f"{builddir}/{pkg_name}.template")

    # Copy the deb file to the builddir
    dst = os.path.join(builddir, os.path.basename(deb_file))
    print(f"Copying '{deb_file}' to '{dst}'")
    shutil.copy(deb_file, dst)


# Find package without building
def get_package_deb(distro_config_path):
    # Get settings
    with open(distro_config_path) as f:
        distro_config = yaml.safe_load(f)
    try:
        search_pkg = distro_config["search_pkg"]
    except KeyError:
        print("Failed in get_package_deb()!!!")
        print(f"  No 'search_pkg' in --distro_config={distro_config_path}")
        sys.exit(1)
    try:
        orig_flavour = distro_config["orig_flavour"]
    except KeyError:
        print("Failed in get_package_deb()!!!")
        print(f"  No 'orig_flavour' in --distro_config={distro_config_path}")
        sys.exit(1)

    # Update and upgrade apt repos to latest
    apt_update_upgrade(allow_errors=True, live_output=False)
    print("apt repos updated and upgraded")
    sys.stdout.flush()
    sleep(3)

    # Return the newest latest linux kernel image package name
    image_name, version_name = apt_get_linux_image_name(search_pkg, orig_flavour, verbose=False)
    print("Found image name:           {} - ".format(image_name, version_name))
    sys.stdout.flush()
    return image_name, version_name


def printfancy(str, timeout=0.1):
    print('------------------------------------------------------------------------------')
    print('--- {}'.format(str))
    print('------------------------------------------------------------------------------')
    sys.stdout.flush()
    sleep(timeout)


def debian_style_build(distro_config_path, buildnumber, maintainer, verbose, nobuild):
    # Get settings
    if not os.path.exists(distro_config_path):
        print("Failed in debian_style_build()!!!")
        print(f"  --distro_config={distro_config_path} invalid")
        print(f"  file {distro_config_path} does not exist")
        sys.exit(1)
    try:
        with open(distro_config_path, 'r') as f:
            distro_config = yaml.safe_load(f)
    except Exception as e:
        print("Failed in debian_style_build()!!!")
        print(f"  --distro_config={distro_config_path} doesn't appear to be a valid yaml file")
        print(f"  Exception: {e}")
        sys.exit(1)
    required_keys = ['search_pkg', 'orig_flavour', 'flavour', 'version_ref_pkg', 'distro', 'metapkgs']
    missing_keys = []
    for key in required_keys:
        if key not in distro_config.keys():
            missing_keys.append(key)
    if len(missing_keys) > 0:
        print(f"Failure in debian_style_build()  --distro_config={distro_config_path}")
        print("  Missing keys:")
        for key in missing_keys:
            print(f"    '{key}'")
        sys.exit(1)

    search_pkg = distro_config["search_pkg"]
    orig_flavour = distro_config["orig_flavour"]
    flavour = distro_config["flavour"]
    version_ref_pkg = distro_config["version_ref_pkg"]
    distro = distro_config["distro"]
    metapkgs = distro_config["metapkgs"]
    if not isinstance(metapkgs, list):
        print("Failed in debian_style_build()!!!")
        print(f"  --distro_config={distro_config_file}")
        print(f"  'metapkgs' must be a list")
        sys.exit(1)

    printfancy("BUILDING DEBIAN STYLE PACKAGE")

    # Update and upgrade apt repos to latest
    printfancy("update and upgrade apt repos...")
    apt_update_upgrade(allow_errors=True)
    printfancy("DONE - apt repos updated and upgraded", timeout=3)

    bitflux_version = get_bitflux_version()
    printfancy(f"Set bitflux_version:        {bitflux_version}", timeout=3)

    # Return the newest latest linux kernel image package name
    image_name, version_name = apt_get_linux_image_name(search_pkg, orig_flavour, verbose=verbose)
    printfancy(f"Found image name:           {image_name} - {version_name}")

    # Search patches for something that should match the kernel image package
    patches_dir = select_patches_dir(image_name, patches_root_dir='./patches')
    printfancy(f"Found patches directory:    {patches_dir}")
    if patches_dir is None:
        raise

    # Download source code and return where the kernel source code is located
    #src_dir = apt_get_source('linux', verbose=verbose)
    src_dir = apt_get_source(image_name, verbose=verbose)
    printfancy(f"Found kernel src directory: {src_dir}")

    debian_dir = deb_find_debian_dir(src_dir)
    printfancy(f"Found DEBIAN directory: {debian_dir}")

    # Do patching steps
    init_commit = patch_in(distro, patches_dir, src_dir, verbose=verbose, clean_patch=True)

    # Handle flavour hacking
    printfancy("Creating flavour swaphints config files")
    deb_set_flavour(flavour, orig_flavour, debian_dir, verbose=True)
    commit_and_create_patch('flavour', src_dir, verbose=True)

    # Create the final patching
    if init_commit is not None:
        filepath = os.path.join(patches_dir, "complete.patch")
        commit_and_create_patch(filepath, src_dir, commit_hash=init_commit, verbose=verbose)
    printfancy("Patching Complete", timeout=3)

    # Modify debian changelog
    printfancy("Modifying debian changelog")
    deb_hack_changelog(bitflux_version, src_dir, buildnum=buildnumber, verbose=verbose, clean_patch=True)

    # DEPRECATED functionality required for older builds pre 6.8 24.04, not updated with flavour, orig_flavour
    try:
        printfancy("Mocking out current abi files")
        deb_hack_abi_records('swaphints', debian_dir, verbose=verbose)
    except:
        print("Failed to mock out current abi files")

    # Build deps are changing relatively often, so we need to update them
    printfancy("Installing build dependencies")
    run_cmd(f"sudo apt build-dep -y {image_name}", allow_errors=True, verbose=False)

    # Rust tools are also changing relatively often, so we need to update them
    #  ubuntu builds are depending on deb package conventions for rustc executable names
    printfancy("Update rust tools")
    update_rust_tools(src_dir, verbose=True)

    # Build deb packages
    if nobuild:
        return
    printfancy("Build .deb files")
    try:
        build_debs(src_dir, verbose=verbose)
    except:
        build_debs_hack(src_dir, verbose=verbose)

    # Getting version number from built debs
    versionnumber, arch = get_package_stats(version_ref_pkg)
    printfancy(f"Package version:            {versionnumber}  arch: {arch}")

    # Build meta packages
    printfancy("Build meta packages")
    for metapkg_config in metapkgs:
        build_meta_pkg(metapkg_config, maintainer, versionnumber, arch, flavour, orig_flavour, verbose=verbose)

    # Copy outputs
    run_cmd("rm -rf ./output;", allow_errors=True, verbose=verbose)
    copy_outputs("./build/*.deb", verbose=verbose)
    copy_outputs("./build/*.template", outputdir='./output/templates/', verbose=verbose)
    copy_outputs(f"{patches_dir}/*.new", outputdir='./output/patches/', verbose=verbose)
