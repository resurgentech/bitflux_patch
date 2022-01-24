# Patches And Tools For Building BitFlux Patched Kernels

## Usage
### Building
`
./build_kernel_package.sh ubuntu2004
`
This will generate packages in ./build/ubuntu2004


## Explanation of ./patches directory
### ./patches/files
Contains shared files used to push to kernels.  These are symlinked into the individual patch set directories allowing us to have the _meat_ of the patches in readable shared files as this content is actually reasonably stable across versions.

### ./patches/[4,5] - major version number
Contains sub-directories for supported minor versions.  Some supported minor versions lack a unique directory.  For example, 5.10 works with the 5.9 patch set so therefore there is no ./patches/5/10 directory.

### Patching Artifacts
#### .\<distro\>
If a file/directory exists with the distro name, the .distro variant will supersede the default.

#### directories
Directories are copied into the target kernel

#### * .patch
In alphabetic order apply patches

#### *.merge
These are very convention over configuration style hacky tools.

We patch in a placeholder to a file such as `//__reclaim_page.merge//`
Then we make a file or symlink containing contents we want with a strict naming convention.
For example, `mm__vmscan_c--__reclaim_page.merge` will merge its contents into the file `mm/vmscan.c` in the kernel sources directory replacing the line `//__reclaim_page.merge//`.

#### *.new
These are generated as patch steps are applied.  `complete.patch.new` is the entire patch set rolled into one patch.

## Scripts
This explains the underlying tools and scripts of the project.

### docker
Contains Dockerfiles and scripts for building packages for specific versions.

-  **Dockerfile.*** - well you know... Dockerfiles

- **build.sh** - Builds the images and tags them.

- **run_kernel_test.sh** - `./scripts/docker/run_kernel_test.sh 5.8.18` this will patch and build a vanilla kernel.  For testing the patch set.

- **run.sh** - `./scripts/docker/run.sh ubuntu2004` helper to start a bash shell in a container.

- **push.sh** - `./scripts/docker/push.sh` uploads docker images, if docker is configured to push to the repo.  Can't remember how that is done.


### ansible
Installer helpers for installing prereqs and packages for installing bitflux.  mostly for testing with vagrant initiated vms but could be used for general installation.

### vagrant
Contains config and scripts to make and config vms.

- **setup.sh** - `./scripts/vagrant/setup.sh centos8`  will setup a vm and run ansible to install bitflux.

- **teardown.sh** - `./scripts/vagrant/teardown.sh centos8`  will destroy the vm created with setup.sh.


# Build Notes
- 5.13.19 - patches and builds
- 5.14.21 - patches but fails to build
- 5.15.15
- 5.16.1
- https://download.rockylinux.org/pub/rocky/8/BaseOS/source/tree/Packages/k/kernel-4.18.0-348.12.2.el8_5.src.rpm - patches and builds
