#!/usr/bin/env bash

if [ "$1" == "-h" ]; then
  printf "\nWill run suppled test using aws provisioner\n"
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
prefix="$script_dir/../../automation-infra/containerize.sh python -m pytest -p pytest_subprocessor -p pytest_grouper -p pytest_provisioner --provisioner=https://provisioner.tls.ai --heartbeat=https://heartbeat-server.tls.ai --ssl-cert=$HOME/.habertest/habertest.crt --ssl-key=$HOME/.habertest/habertest.key --sf=\"-p pytest_automation_infra -p devops_proxy_container \" -s --noconftest"
echo "running command: $prefix $install $*"
sleep 3
$prefix $install "$*"
