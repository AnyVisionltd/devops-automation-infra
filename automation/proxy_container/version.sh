#!/bin/bash

function docker_tag () {
    local current_file=${BASH_SOURCE[0]}
    local current_dir=$(dirname $current_file)
    local dockerfile=${current_dir}/Dockerfile

    HASH_FILES=(${BASH_SOURCE[0]} ${dockerfile} $current_dir/requirements.txt $current_dir/docker_user.pem $current_dir/docker_user.pem.pub)
    HASH_FILES+=($(find $current_dir/etc/ -type f))
    if [[ "$OSTYPE" == "darwin"* ]]; then
        #if Running from Mac OSX the md5sum command output is a bit different
      local files_sum="$(md5sum -- ${HASH_FILES[@]} | awk {'print $4'})"
    else
      local files_sum="$(md5sum -- ${HASH_FILES[@]} | awk {'print $1'})"
    fi
    local total_sum="$(echo -n $files_sum | md5sum | awk '{print substr($1,1,12)}')"
    echo $total_sum
}

docker_tag 