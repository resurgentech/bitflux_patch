#!/bin/bash

############################################################################################
#   helper functions for ./run scripts
############################################################################################

# find largest command/flag/target name length
get_max_length() {
  max_length=0
  for cmd in "${VALID_COMMANDS[@]} ${VALID_FLAGS[@]} ${VALID_TARGETS[@]}"; do
    IFS=':' read -r command description <<< "$cmd"
    if [ ${#command} -gt $max_length ]; then
      max_length=${#command}
    fi
  done
  echo $((max_length+4))
}

# Modify a Cargo.toml file to set the version from --version option
update_cargo_toml() {
  for option in "${OPTIONS[@]}"; do
    if [ ! -z "$(echo $option | grep '--version')" ]; then
      version=$(echo $option | sed 's/--version=//')
      echo "Changing version in Cargo.toml to $version"
      sed -i "s/^version = \"[0-9\.]*\"/version = \"${version}\"/" Cargo.toml
      break
    fi
  done
}

# Function to display usage information
show_usage() {
  echo ""
  if [ -z "$VALID_TARGETS" ]; then
    echo "Usage: $SCRIPT_PATH COMMAND [FLAGS]"
    echo ""
  else
    echo "Usage: $SCRIPT_PATH TARGET COMMAND [FLAGS]"
    echo ""
    echo "Targets:"
    for cmd in "${VALID_TARGETS[@]}"; do
      IFS=':' read -r command description <<< "$cmd"
      printf "  %-*s %s\n" $(get_max_length) "$command" "$description"
    done
  fi
  echo "Commands:"
  for cmd in "${VALID_COMMANDS[@]}"; do
    IFS=':' read -r command description <<< "$cmd"
    printf "  %-*s %s\n" $(get_max_length) "$command" "$description"
  done
  echo "Flags:"
  for flg in "${VALID_FLAGS[@]}"; do
    IFS=':' read -r flags description <<< "$flg"
    printf "  %-*s %s\n" $(get_max_length) "$flags" "$description"
  done
  if [ ! -z "${COMMANDS[0]}" ]; then
    echo "Options:"
    for opt in "${VALID_OPTIONS[@]}"; do
      IFS=':' read -r option package description <<< "$opt"
      IFS='=' read -r optionname valuename <<< "$option"
      if [ "$package" == "${COMMANDS[0]}" ]; then
        printf "  %-*s %s, %s\n" $(get_max_length) "$optionname" "$valuename" "$description"
      fi
    done
  fi
}

# Allows --dryrun to not actually run the commands
# also allows --verbose to show the commands being run
run_command() {
  local command="$1"
  if [ ! -z "$(parse_flags '--dryrun')" ] || [ ! -z "$(parse_flags '--verbose')" ]; then
    local LPWD=$(pwd)
    local PWD="${LPWD#$PROJECT_DIR}"
    if [ ! -z "$(parse_flags '--dryrun')" ]; then
      echo "    Would have run '$command' from '$PWD'"
    else
      echo "    Running '$command' from '$PWD'"
    fi
  fi
  if [ -z "$(parse_flags '--dryrun')" ]; then
    eval "$command"
  fi
}

# Iterate through the targets and query their valid commands lists
generate_common_commandlist() {
  VALID_COMMANDS=()
  for TARGET in "${TARGETS[@]}"; do
    if [ ${#VALID_COMMANDS[@]} -eq 0 ]; then
      # Initialize VALID_COMMANDS with the first target's commands
      while IFS= read -r line; do
        VALID_COMMANDS+=("$line")
      done < <($PROJECT_DIR/$TARGET/run list_valid_commands)
    else
      # Create a temporary array for the current target's commands
      CURRENT_COMMANDS=()
      while IFS= read -r line; do
        CURRENT_COMMANDS+=("$line")
      done < <($PROJECT_DIR/$TARGET/run list_valid_commands)

      # Keep only commands that are in both VALID_COMMANDS and CURRENT_COMMANDS
      TEMP_COMMANDS=()
      for cmd in "${VALID_COMMANDS[@]}"; do
        if [[ " ${CURRENT_COMMANDS[@]} " =~ " ${cmd} " ]]; then
          TEMP_COMMANDS+=("$cmd")
        fi
      done
      VALID_COMMANDS=("${TEMP_COMMANDS[@]}")
    fi
  done
}

# Iterate through the targets and commands and query their valid options lists
generate_combined_optionslist() {
  VALID_OPTIONS=()
  for target in "${TARGETS[@]}"; do
    local fixed_target=${target#./}
    fixed_target=${fixed_target%/run}
    for command in "${COMMANDS[@]}"; do
      while IFS= read -r line; do
        IFS=":" read -r option validcommand description <<< "$line"
        if [ "$command" == "$validcommand" ]; then
          local option_found=false
          for valid_option in "${VALID_OPTIONS[@]}"; do
            if [ "$option" == "$valid_option" ]; then
              option_found=true
              break
            fi
          done
          if [ "$option_found" == false ]; then
            VALID_OPTIONS+=("$line")
          fi
        fi
      done < <($PROJECT_DIR/$target/run list_valid_options $command)
    done
  done
}

# search for a list of valid targets using ./run whoami
# accepts a CSV list with directory_to_search:depth_to_search
search_for_sub_scripts() {
  local input_list="$1"
  IFS=',' read -ra pairs <<< "$input_list"
  for pair in "${pairs[@]}"; do
    IFS=':' read -r dir depth <<< "$pair"
    depth=$((depth + 1))
    #echo $(find "./$dir" -maxdepth "$depth" -type f -name "run" -print0)
    while IFS= read -r -d '' run_file; do
      run_path="$PROJECT_DIR/$run_file"
      local is_valid=false
      if [ -x "$run_path" ]; then
        response=$("$run_path" whoami 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$response" ]; then
          IFS=":" read -r target tags description <<< "$response"
          if [ ! -z "target" ] && [ ! -z "tags" ] && [ ! -z "description" ]; then
            is_valid=true
          fi
        fi
      fi
      if $is_valid; then
          SCRIPTS_LIST+=("$response")
      else
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        echo "!!   Invalid run file at $run_file"
        echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
      fi
    done < <(find "$dir" -maxdepth "$depth" -type f -name "run" -print0)
  done
}

# Generate a list of valid targets by searching for ./run files
# accepts a CSV list with directory_to_search:depth_to_search
generate_valid_targets_list() {
  local input_list="$1"
  SCRIPTS_LIST=()
  VALID_TARGETS=("all:All non-infrastructure targets")
  local NEW_VALID_TARGETS=()
  search_for_sub_scripts "$input_list"
  for script in "${SCRIPTS_LIST[@]}"; do
    IFS=":" read -r target tags description <<< "$script"
    NEW_VALID_TARGETS+=("$target:$description")
  done
  local VALID_TARGET_PATHS=()
  for target in "${NEW_VALID_TARGETS[@]}"; do
    IFS=':' read -r target description <<< "$target"
    target=${target%/*}
    local parts=(${target//\// })
    local current_path=""
    for part in "${parts[@]}"; do
      if [ -z "$current_path" ]; then
        current_path="$part"
      else
        current_path="$current_path/$part"
      fi
      local is_duplicate=false
      for path in "${VALID_TARGET_PATHS[@]}"; do
        if [ "$path" == "$current_path" ]; then
          is_duplicate=true
          break
        fi
      done
      if $is_duplicate; then
        continue
      else
        VALID_TARGET_PATHS+=("$current_path")
      fi
    done
  done
  #sort the VALID_TARGET_PATHS array alphabetically
  VALID_TARGET_PATHS=($(echo "${VALID_TARGET_PATHS[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '))
  for bpath in "${VALID_TARGET_PATHS[@]}"; do
    VALID_TARGETS+=("$bpath/all:All targets in $bpath/")
    for line in "${NEW_VALID_TARGETS[@]}"; do
      IFS=':' read -r target description <<< "$line"
      local childdir=false
      for b2path in "${VALID_TARGET_PATHS[@]}"; do
        if [ "${b2path:0:${#bpath}}" == "$bpath" ] && [ "$bpath" != "$b2path" ]; then
          childdir=true
          break
        fi
      done
      if $childdir; then
        break
      fi
      if [ "${target:0:${#bpath}}" == "$bpath" ]; then
        VALID_TARGETS+=("$target:$description")
      fi
    done
  done
}

# expand targets list
# basically allows us to do 'all, 'apps/all', or 'infra/all'
expand_targets_list() {
  local newtarget="$1"
  if [ "$newtarget" == "all" ] || [ "$newtarget" == "apps/all" ]; then
    # 'apps/all' should be all the apps/ targets
    # For 'all' we're not doing the infra/ targets because infrastructure
    for line in "${VALID_TARGETS[@]}"; do
      IFS=':' read -r target description <<< "$line"
      if [ "${target:0:5}" == "apps/" ] && [ "$target" != "apps/all" ]; then
        TARGETS+=("$target")
      fi
    done
  elif [ "$newtarget" == "infra/all" ]; then
    # 'infra/all' should be all the infra/ targets, not the apps/ targets
    for line in "${VALID_TARGETS[@]}"; do
      IFS=':' read -r target description <<< "$line"
      if [ "${target:0:6}" == "infra/" ] && [ "$target" != "infra/all" ]; then
        TARGETS+=("$target")
      fi
    done
  else
    TARGETS+=("$newtarget")
  fi
}

expand_targets_list() {
  local targets=("$1")
  # First, check if the targets are in TARGET_EXPANSIONS and expand it if necessary
  for expansion in "${TARGET_EXPANSIONS[@]}"; do
    IFS=':' read -r key expanded <<< "$expansion"
    for target in "${targets[@]}"; do
      if [[ "$target" == "$key" ]]; then
        IFS=' ' read -ra expanded_array <<< "$expanded"
        for expanded_target in "${expanded_array[@]}"; do
          targets+=("$expanded_target")
        done
      fi
    done
  done
  # Now remove the keys from expansion from the array
  new_targets=()
  for expansion in "${TARGET_EXPANSIONS[@]}"; do
    IFS=':' read -r key expanded <<< "$expansion"
    for target in "${targets[@]}"; do
      if [[ "$target" != "$key" ]]; then
        new_targets+=("$target")
      fi
    done
  done
  targets=("${new_targets[@]}")
  # Otherwise, expand newtarget by finding matching basedir/all or specific targets
  for newtarget in "${targets[@]}"; do
    if [[ "$newtarget" == */all ]]; then
      local basedir="${newtarget%/all}"  # Get the base directory (e.g., "apps" from "apps/all")

      # Loop through VALID_TARGETS and expand matching basedir/ targets
      for line in "${VALID_TARGETS[@]}"; do
        IFS=':' read -r target description <<< "$line"
        # skip if the target is */all
        if [[ "$target" == */all ]]; then
          continue
        fi
        if [[ "$target" == "$basedir/"* ]] && [[ "$target" != "$newtarget" ]]; then
          TARGETS+=("$target")  # Add expanded target to TARGETS
        fi
      done
    else
      # Add the specific target directly
      TARGETS+=("$newtarget")
    fi
  done
}

# validate input against a list of valid targets
validate_targets() {
  local i=$1
  # Well, we're gonna have an hack for help
  if [ "$i" == "help" ]; then
    show_usage
    exit 0
  fi
  # Check if the argument is a valid target
  for line in "${VALID_TARGETS[@]}"; do
    IFS=':' read -r target description <<< "$line"
    if [ "$target" == "$i" ]; then
      NEWTARGET="$i"
      break
    fi
  done
  if [ -z "$NEWTARGET" ]; then
    # If we get here, we didn't find a valid target
    echo "Unknown target: $i"
    show_usage
    exit 1
  fi
  TARGETS=()
  expand_targets_list "$NEWTARGET"
}

# validate input against a list of valid commands
validate_commands() {
  local i=$1
  # Check if the argument is a valid command
  #  Given the current TARGETS, we need to find the valid commands for each target
  if [ ! -z "$VALID_TARGETS" ]; then
    VALID_COMMANDS=()
    generate_common_commandlist
  fi
  # Check if the command is in the valid commands list
  for line in "${VALID_COMMANDS[@]}"; do
    IFS=':' read -r command description <<< "$line"
    if [ "$command" == "$i" ]; then
      COMMANDS+=("$i")
      break
    fi
  done
  if [ -z "$COMMANDS" ]; then
    if [ ! -z "$VALID_TARGETS" ]; then
      # if this is an invalid command, we need to list the valid commands for the targets
      echo "Unknown Command '$i' for '${TARGETS[@]}'"
      echo ""
      echo "Valid commands for '${TARGETS[@]}':"
      for cmd in "${VALID_COMMANDS[@]}"; do
        IFS=':' read -r command description <<< "$cmd"
        printf "  %-*s %s\n" $(get_max_length) "$command" "$description"
      done
    else
      echo "Unknown Command '$i'"
      show_usage
      exit 1
    fi
    exit 1
  fi
}

# validate options against a list of valid options
validate_options() {
  local i=$1
  local j=$2

  if [ ! -z "$VALID_TARGETS" ]; then
    generate_combined_optionslist
  fi

  is_valid_option=false
  for command in "${COMMANDS[@]}"; do
    # Check if the option is in the valid options list
    for line in "${VALID_OPTIONS[@]}"; do
      IFS=':' read -r option validcommand description <<< "$line"
      IFS='=' read -r option_name arg_type <<< "$option"
      if [ "$option_name" == "$i" ]; then
        if [ "$validcommand" == "$command" ]; then
          is_valid_option=true
          echo "$option_name=$j"
          break
        fi
      fi
    done
    if $is_valid_option; then
      break
    fi
  done
}

# find an flag in a list of valid flags
parse_flags() {
  local i=$1
  for flag in "${FLAGS[@]}"; do
    if [ "$flag" == "$i" ]; then
      echo "$1"
      break
    fi
  done
}

# find an option in a list of options
parse_options() {
  local i=$1
  for option in "${OPTIONS[@]}"; do
    IFS='=' read -r option_name argvalue <<< "$option"
    if [ "$option_name" == "$i" ]; then
      echo "$1 $argvalue"
      break
    fi
  done
}

# get the value from an option in a list of options
get_option_value() {
  local i=$1
  for option in "${OPTIONS[@]}"; do
    IFS='=' read -r option_name argvalue <<< "$option"
    if [ "$option_name" == "$i" ]; then
      echo "$argvalue"
      break
    fi
  done
}

# expand flags list
# example:
#  Having the variable set:
#    FLAGS_EXPANSIONS=("--debug:--debug --verbose")
#  replaces --debug with --debug and --verbose in FLAGS
expand_flags_list() {
  if [ -z "$FLAGS_EXPANSIONS" ]; then
    return
  fi
  for expansion in "${FLAGS_EXPANSIONS[@]}"; do
    IFS=":" read -r oldflag newflags <<< "$expansion"
    local expanded_flags=()
    for flag in "${FLAGS[@]}"; do
      if [ "$flag" == "$oldflag" ]; then
        for newflag in $newflags; do
          expanded_flags+=("$newflag")
        done
      else
        expanded_flags+=("$flag")
      fi
    done
    FLAGS=()
    for flag in "${expanded_flags[@]}"; do
      FLAGS+=("$flag")
    done
  done
}

# expand commands list
# example:
#  Having the variable set:
#    COMMAND_EXPANSIONS=("build:build compile")
#  replaces build with build and compile in COMMANDS
expand_commands_list() {
  if [ -z "$COMMAND_EXPANSIONS" ]; then
    return
  fi
  for expansion in "${COMMAND_EXPANSIONS[@]}"; do
    IFS=":" read -r oldcommand newcommands <<< "$expansion"
    if [ ! -z "$(parse_flags '--debug')" ]; then
      echo "expanding command '$oldcommand' to '$newcommands'"
    fi
    local expanded_commands=()
    for command in "${COMMANDS[@]}"; do
      if [ "$command" == "$oldcommand" ]; then
        for newcommand in $newcommands; do
          expanded_commands+=("$newcommand")
          if [ ! -z "$(parse_flags '--debug')" ]; then
            echo "adding command '$newcommand'"
          fi
        done
      else
        expanded_commands+=("$command")
      fi
    done
    COMMANDS=()
    for command in "${expanded_commands[@]}"; do
      COMMANDS+=("$command")
    done
  done
}

# opinionated a way to parse out cli arguments
# Depends on magic variables VALID_TARGETS, VALID_COMMANDS, VALID_FLAGS
cli_parser() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      ###### Internal Use - for dynamic validation etc ######
      is_magic_run_script)
        echo "builder_helper"
        exit 0
        ;;
      has_targets)
        # returns a string that can be used see if the script has targets or not
        if [ ! -z "$VALID_TARGETS" ]; then
          echo "true"
        fi
        exit 0
        ;;
      whoami)
        # returns a string that can be used to identify the script
        # This is useful for dynamic validation of targets
        #   Note: tags should be a comma separated list of tags
        #         tags could be used to filter the list of targets in the future
        # "target:tags:description"
        SCRIPT_TARGET_PATH="${SCRIPT_PATH#./}"
        SCRIPT_TARGET_PATH="${SCRIPT_TARGET_PATH%/run}"
        if [ -z "$SCRIPT_TAGS" ]; then
          SCRIPT_TAGS="default"
        fi
        if [ -z "$SHORT_DESC" ]; then
          SHORT_DESC="Update $SHORT_DESC"
        fi
        echo "${SCRIPT_TARGET_PATH}:$SCRIPT_TAGS:$SHORT_DESC"
        exit 0
        ;;
      list_valid_targets)
        # Let's us interrogate the script for valid targets for zsh completion
        for command in "${VALID_TARGETS[@]}"; do
          echo "$command"
        done
        exit 0
        ;;
      list_valid_commands)
        # Let's us interrogate the script for valid commands
        #  Given the current TARGETS, we need to find the valid commands to validate
        #  Also for zsh completion
        TARGETS=()
        if [ ! -z "$VALID_TARGETS" ]; then
          expand_targets_list "$2"
          generate_common_commandlist
        fi
        for command in "${VALID_COMMANDS[@]}"; do
          echo "$command"
        done
        exit 0
        ;;
      list_valid_flags)
        # Let's us interrogate the script for valid flags
        #  Also for zsh completion
        for flag in "${VALID_FLAGS[@]}"; do
          echo "$flag"
        done
        exit 0
        ;;
      list_valid_options)
        # Let's us interrogate the script for valid options
        #  Also for zsh completion
        COMMANDS=($2)
        if [ ! -z "$3" ]; then
          TARGETS=()
          expand_targets_list "$3"
        fi
        if [ ! -z "$TARGETS" ]; then
          expand_commands_list "$2"
          generate_combined_optionslist
        fi
        for option in "${VALID_OPTIONS[@]}"; do
          echo "$option"
        done
        exit 0
        ;;
      ##### End Internal Use ######
      -h|--help)
        show_usage
        exit 0
        ;;
      *)
        if [ -z "$TARGETS" ] && [ ! -z "$VALID_TARGETS" ]; then
          # If we have VALID_TARGETS, we need TARGETS so if haven't set a target yet, set it
          validate_targets $1
          shift
        else
          if [ ! -z "$COMMANDS" ]; then
            if [[ $1 == --* ]]; then
              # this is a flag or option
              IFS='=' read -ra OPTION_PARTS <<< "$1"
              if [ ${#OPTION_PARTS[@]} -ge 2 ]; then
                option=$(validate_options "${OPTION_PARTS[0]}" "${OPTION_PARTS[1]}")
              else
                option=$(validate_options $1 $2)
              fi
              if [ ! -z "$option" ]; then
                OPTIONS+=("$option")
                if [ ${#OPTION_PARTS[@]} -lt 2 ]; then
                  shift
                fi
              else
                FLAGS+=("$1")
              fi
            else
              echo "Only one command can be specified at a time: already selected '${COMMANDS[@]}' trying to add '$1'"
              show_usage
              exit 1
            fi
          fi
          # We have set TARGETS, now lets look for a command
          validate_commands $1
          if [ -z "$VALID_TARGETS" ] && [ $1 == "help" ]; then
            show_usage
            exit 0
          fi
          shift
        fi
        ;;
    esac
  done
  # These conditions probably are only hit if we have a bug in the the scripting
  if [ -z "$TARGETS" ] && [ ! -z "$VALID_TARGETS" ]; then
    echo "No target specified"
    show_usage
    exit 1
  elif [ -z "$COMMANDS" ]; then
    echo "No command specified"
    show_usage
    exit 1
  fi
  #  uses FLAGS_EXPANSIONS and COMMAND_EXPANSIONS to expand the lists
  #  This is useful for things like --debug which is expanded to --debug --verbose
  expand_flags_list
  expand_commands_list
}

install_zsh_completion() {
  run_command "mkdir -p ~/.oh-my-zsh/completions"
  run_command "cp $PROJECT_DIR/tools/scripts/run.zsh_completion $HOME/.oh-my-zsh/completions/_run"
}

# Normally this is a library but we can use it as a script
#  to install the zsh completion scripts and potentially other things
#  in the future like auto-gen of new scripts to a project etc.
if [ "$0" == "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
  PROJECT_DIR="$( cd $SCRIPT_DIR/../.. &> /dev/null && pwd )"
  cd "$SCRIPT_DIR"

  VALID_COMMANDS=("install_zsh:Install zsh completion scripts"
                  "help:Show help for TARGET")
  VALID_FLAGS=("--help|-h:Show help for this script"
                 "--dryrun:Dryrun.  Don't actually run the commands"
                 "--verbose:Verbose output")

  FLAGS=()
  COMMANDS=()
  # Parse command line arguments
  cli_parser $@

  for COMMAND in "${COMMANDS[@]}"; do
    case "$COMMAND" in
      install_zsh)
        install_zsh_completion
        exit 0
        ;;
      *)
        echo "command '$COMMAND' not implemented"
        show_usage
        exit 1
        ;;
    esac
  done
fi
