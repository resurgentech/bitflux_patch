#!/bin/bash

# Find the directory of the script and change to it
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Project root, adjust as needed
PROJECT_DIR="$( cd $SCRIPT_DIR &> /dev/null && pwd )"
cd "$SCRIPT_DIR"
# Strip the script path to be relative to project root
SCRIPT_PATH="${0#$PROJECT_DIR}"; [[ ! "$SCRIPT_PATH" =~ ^\..*$ ]] && SCRIPT_PATH=".$SCRIPT_PATH"
# Include the run_helpers.sh for 'library' functions
source $PROJECT_DIR/scripts/run_helpers.sh || exit 1


############################################################################################
SHORT_DESC="testing"
############################################################################################

# These lists will be parsed and used for the help output and validation
VALID_COMMANDS=("clean:Delete aptly repo"
                "generate:Set up aptly repo"
                "upload:Upload files to repo"
                "publish:Publish from repo to s3"
                "help:Show help for TARGET")
VALID_FLAGS=("--help|-h:Show help for this script"
               "--debug:Enable debug mode"
               "--dryrun:Dryrun.  Don't actually run the commands"
               "--verbose:Verbose output")
VALID_OPTIONS=("--reponame=<str>:generate:Repository name in Aptly"
               "--reponame=<str>:upload:Repository name in Aptly"
               "--reponame=<str>:publish:Repository name in Aptly"
               "--dest=<str>:upload:Push to this "
               "--prefix=<str>:publish:Prefix for repo publish target"
               "--gpg_passphrase=<str>:publish:GPG passphrase for signing on publish"
               "--distro=<str>:generate:Distribution for repo")

FLAGS=()
OPTIONS=()
COMMANDS=()

# Parse command line arguments
cli_parser $@


upload_to_aptly() {
  local reponame=$1
  local uploaddir=$(uuidgen)
  if [ -z "$uploaddir" ]; then
    echo "upload_to_aptly: uuidgen might not be working"
    exit 1
  fi
  if [ -z "$reponame" ]; then
    echo "upload_to_aptly: no reponame defined"
    exit 1
  fi

  # list file in this directory and filter out every but *.deb
  listoffiles=$(find $SCRIPT_DIR/output -type f -name "*.deb")
  for file in $listoffiles; do
    echo "    ----- Uploading: $file -----"
    run_command "aptly-cli file_upload --upload ${file} --directory /${uploaddir}"
    echo "    ----- Installing: $file -----"
    run_command "aptly-cli repo_upload --name ${reponame} --dir ${uploaddir} --forcereplace"
    echo ""
  done
}

publish_from_aptly() {
  local reponame=$1
  local repoprefix=$2
  local aptly_gpg_passphrase=$3
  run_command "aptly-cli publish_repo --sourcekind local --name ${reponame} --prefix ${repoprefix} --forceoverwrite --gpg_passphrase ${aptly_gpg_passphrase} --gpg_batch"
}

upload_to_minio() {
  local reponame=$1
  local srcpath=$2
  local dstpath=$3

  # Copy files or paths
  run_command "mc cp --recursive ${srcpath} ${MINIO_ALIAS}/${MINIO_BUCKET}/${reponame}/${dstpath}"
}

source $SCRIPT_DIR/.env

if [ -n "$(get_option_value '--reponame')" ]; then
  APTLY_REPO_NAME="$(get_option_value '--reponame')"
fi

if [ -n "$(get_option_value '--prefix')" ]; then
  APTLY_CONFIG_FILE="$(get_option_value '--prefix')"
fi

if [ -n "$(get_option_value '--reponame')" ]; then
  APTLY_REPO_NAME="$(get_option_value '--reponame')"
fi

#
if [ -z "$APTLY_REPO_NAME" ]; then
  echo "Missing APTLY_REPO_NAME envar"
  exit 1
fi


echo "  ##################################################################"
echo "  # Running '$SCRIPT_PATH' script"
echo "  #   Commands: ${COMMANDS[@]}"
echo "  #   Flags: ${FLAGS[@]}"
echo "  #   Options: ${OPTIONS[@]}"
echo "  #-----------------------------------------------------------------"

# Execute the command
for COMMAND in "${COMMANDS[@]}"; do
  case "$COMMAND" in
    clean)
      echo "  Cleaning..."
      run_command "aptly-cli repo_delete --name ${APTLY_REPO_NAME}"
      ;;
    generate)
      echo "  Generating..."
      run_command "aptly-cli repo_create --name ${APTLY_REPO_NAME} --default_distribution ${APTLY_DISTRIBUTION}"
      ;;
    upload)
      echo "  Uploading..."
      # tore minio S3
      ftimestamp=$(find output/ -type f -printf '%TY-%Tm-%Td_%TH-%TM-%TS\n' | sort | head -n 1)
      upload_to_minio "$APTLY_REPO_NAME" "./output/" "${MINIO_BUCKET}/${ftimestamp}/"
      if [ -f "./build.log" ]; then
        upload_to_minio "$APTLY_REPO_NAME" "./build.log" "${MINIO_BUCKET}/${ftimestamp}/"
      fi
      # upload to aptly
      upload_to_aptly "$APTLY_REPO_NAME"
      ;;
    publish)
      echo "  Publish..."
      if [ -z "$APTLY_REPO_PREFIX" ]; then
        echo "Missing APTLY_REPO_PREFIX envar"
        exit 1
      fi
      if [ -z "$APTLY_GPG_PASSPHRASE" ]; then
        echo "Missing APTLY_GPG_PASSPHRASE envar"
        exit 1
      fi

      publish_from_aptly "$APTLY_REPO_NAME" "$APTLY_REPO_PREFIX" "$APTLY_GPG_PASSPHRASE"
      ;;
    *)
      echo "command '$COMMAND' not implemented"
      show_usage
      exit 1
      ;;
  esac
done

echo "  #-----------------------------------------------------------------"
echo "  # '$SCRIPT_PATH' script DONE"
echo "  ##################################################################"
