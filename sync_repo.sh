#!/bin/bash

export AWS_PROFILE=jared


# These files are created and managed elsewhere direct to the AWS S3
# So we first have to sync just these AWS to minio, then we can
# lazyly mirror everything from minio to AWS
LIST_OF_FILES=("repo_signing.key"
               "error.html"
               "index.html")

for FILE in "${LIST_OF_FILES[@]}"; do
    mc stat sdf1/apt.bitflux.ai/$FILE
    if [ $? -ne 0 ]; then
        aws s3 cp s3://apt.bitflux.ai/$FILE /tmp/$FILE
        mc cp /tmp/$FILE sdf1/apt.bitflux.ai/$FILE
        rm /tmp/$FILE
    fi
done

mc mirror sdf1/apt.bitflux.ai s3/apt.bitflux.ai --overwrite --retry --remove
