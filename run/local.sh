#!/usr/bin/env bash

if [ "$1" == "-h" ]; then
  printf "\nWill run supplied test using locally configured hardware on hardware.yaml\n"
  printf "\nExample usage:\n./run/aws.sh /path/to/tests --any --other --pytest --flags --you --like\n\n"
  exit 0
fi

install=""
while test $# -gt 0
do
  case $1 in
    --install)
      install="--sf=\"-p devops_docker_installer --yaml-file=docker-compose-devops.yml\""
      ;;
    *)
      break
      ;;
  esac
  echo "$1"
  shift
done


script_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))
prefix="$script_dir/../../automation-infra/containerize.sh python -m pytest -p pytest_subprocessor --sf=\"-p pytest_automation_infra -p devops_proxy_container \" -s "
echo "running command: $prefix $install $@"
sleep 3
$prefix $install $@