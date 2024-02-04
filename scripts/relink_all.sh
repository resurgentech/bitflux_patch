#!/bin/bash

DIR="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${DIR}/..
WORKING_DIR=`pwd`

./scripts/relink_patches.sh 4.14 ./patches/files/swaphints.01.4_14.c ./patches/files/reclaim_page.01.4_14.c
./scripts/relink_patches.sh 4.14 ./patches/files/swaphints.01.4_14.c ./patches/files/reclaim_page.01.4_14.2.c,amazonlinux2

./scripts/relink_patches.sh 4.18 ./patches/files/swaphints.01.4_18.c ./patches/files/reclaim_page.01.4_18.c
./scripts/relink_patches.sh 4.18 ./patches/files/swaphints.01.4_18.c ./patches/files/reclaim_page.01.4_18.3.c,rockylinux8

./scripts/relink_patches.sh 4.19 ./patches/files/swaphints.01.4_18.c ./patches/files/reclaim_page.01.4_18.c

./scripts/relink_patches.sh 5.0  ./patches/files/swaphints.01.4_18.c ./patches/files/reclaim_page.01.4_18.c

./scripts/relink_patches.sh 5.4  ./patches/files/swaphints.02.5_04.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.6  ./patches/files/swaphints.02.5_06.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.8  ./patches/files/swaphints.02.5_06.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.9  ./patches/files/swaphints.02.5_06.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.10 ./patches/files/swaphints.02.5_06.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.11 ./patches/files/swaphints.02.5_06.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.12 ./patches/files/swaphints.02.5_06.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.15 ./patches/files/swaphints.02.5_06.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.17 ./patches/files/swaphints.02.5_17.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 5.18 ./patches/files/swaphints.02.5_17.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 6.0  ./patches/files/swaphints.02.5_17.c ./patches/files/reclaim_page.02.5_04.c

./scripts/relink_patches.sh 6.1  ./patches/files/swaphints.02.5_17.c ./patches/files/reclaim_page.02.5_04.c
