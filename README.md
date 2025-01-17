# Patches And Tools For Building BitFlux Patched Kernels

## Usage
### Building
`
./tests/buildtest.sh 5.4.223
`
This will run a build and test basic .deb packages for the v5.4.223 tag in the linux-stable git tree

`
./tests/buildtest.sh 5.4.223 --smallbuild
`
This will build the minimum kernel including the swaphints patches.


## Explanation of ./patches directory
### ./patches/files
Contains shared files used to push to kernels.  These are symlinked into the individual patch set directories allowing us to have the _meat_ of the patches in readable shared files as this content is actually reasonably stable across versions.

### ./patches/[4,5] - major version number
Contains sub-directories for supported minor versions.  Some supported minor versions lack a unique directory.  For example, 5.10 works with the 5.9 patch set so therefore there is no ./patches/5/10 directory.

### Patching Artifacts
#### .[distro]
If a file/directory exists with the distro suffix, the .distro variant will supersede the default.

#### directories
Directories are copied into the target kernel

#### \*.patch
In alphabetic order apply patches

#### \*.merge
These are very convention over configuration style hacky tools.

We patch in a placeholder to a file such as `//__reclaim_page.merge//`
Then we make a file or symlink containing contents we want with a strict naming convention.
For example, `mm__vmscan_c--__reclaim_page.merge` will merge its contents into the file `mm/vmscan.c` in the kernel sources directory replacing the line `//__reclaim_page.merge//`.

#### \*.new
These are generated as patch steps are applied.  `complete.patch.new` is the entire patch set rolled into one patch.

## build.py
This script coordinates several stages involving docker containers and the build_kernel_package.py script to make kernel packages.

## ./scripts Directory
This explains the underlying tools and scripts of the project.

### build_kernel_package.py
Script that runs the job to build kernel packages inside the environment for each distro.  Either inside a container or machine running the target distro.

### check_package.py
Script that runs in the environment for each distro to get the latest kernel package.

### parse_swaphints_out.py
Script that can parse the output of /fs/swaphints.

### relink_all.sh
Script/documentation of the links between ./patches/x/ and ./patches/files/

### relink_patches.sh
Helper script that just makes it easier to link files in ./patches/x/ and ./patches/files.

### ./kernel_package_builder
Python module.  Its fairly complicated code used to auto patch and build kernel packages for various distros inside their own environment.

## ./tests Directory
Contains code and config required to run automated tests against kernel packages with bitflux.

### buildtest.sh
Script runs some simple tests with building and install.

### install_test.py
Script that will start a vm, install BitFlux, and test it works

### ansible
Ansible playbook that installs bitflux.

### ./vagrant
Contains config and scripts to make and config vms.

- **setup.sh** - `./scripts/vagrant/setup.sh centos8`  will setup a vm and run ansible to install bitflux.

- **teardown.sh** - `./scripts/vagrant/teardown.sh centos8`  will destroy the vm created with setup.sh.


# ./upload.sh
This script uploads the kernel packages to aptly, to a lab local minio, and can publish from aptly to public S3.


# TODO: add this to ansible for dealing with mirrors
git config --global --add safe.directory /opt/mirrors/linux-stable.git

# TODO: rust adds a new wrinkle
# if we call this script with rustc or whatever it returns the min version
scripts/min-tool-version.sh
# we can us that version to install a compatible version of the rust tools as follows:
rustup install 1.75.0
rustup override set 1.75.0
rustup component add rust-src


# Uploading
Uploading is a bear.
There are three moving parts to this. aptly locally hosted, minio, and s3.

### First, you need to have a repo generated.
`./upload.sh generate`
This interacts with aptly to create a repo.

### Second, you need to upload the packages.
`./upload.sh upload`
This adds the packages to the aptly repo but does not publish them.  Not sure how they are stored at this state, but they are locally saved in the aptly containers data directory.

### Third, you need to publish the repo.
`./upload.sh publish`
This publishes the aptly repo to minio.  Basically it copies the aptly repo to the minio server, with the manifests and files in the right structure.

### Fourth, you need to sync the repo to s3 from minio.
Right now this is a seperate script.
This uses the mc cli to sync the minio repo to s3.
s3 is set up to be web accessible so that you can just point to that as your repo.

## Problems

* s3 is stupid slow like upload is 1MB/s as some point.
* aptly publishing to the s3 times out.  That's why we go to the minio.
* aptly forgets to publish to minio sometimes.  I'm not sure why.  workaround is to restart aptly container and try again.

## TODO:
* 3 level. aptly local, aptly mirror to minio, sync s3
* aptly to local, webscrape to minio, sync to s3
* script to confirm that the files are published to minio
