#!/usr/bin/env bash


if [ "$1" == "-h" ]; then
  printf "\nWill run supplied test provisioned via env configured HABERTEST_PROVISIONER and HABERTEST_HEARTBEAT_SERVER\n"
  printf "\nExample usage:\n./run/aws.sh /path/to/tests --any --other --pytest --flags --you --like\n\n"
  exit 0
fi

install=""
while test $# -gt 0
do
  case $1 in
    --install)
      install="--sf=\"-p core_docker_installer\""
      ;;
    *)
      break
      ;;
  esac
  echo "$1"
  shift
done

printf "\nprovisioner: \t$HABERTEST_PROVISIONER \nheartbeat: \t$HABERTEST_HEARTBEAT_SERVER\n\n"
read -p "Change? waiting 5 seconds... (y) " -t 5 yn
  case $yn in
        [Yyq]* )
              echo "OK, exiting.."
              exit;;
            * )
              script_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))
              prefix="$script_dir/../../automation-infra/containerize.sh python -m pytest -p pytest_subprocessor -p pytest_grouper -p pytest_provisioner --provisioner=$HABERTEST_PROVISIONER --heartbeat=$HABERTEST_HEARTBEAT_SERVER --ssl-cert=$HABERTEST_SSL_CERT --ssl-key=$HABERTEST_SSL_KEY --sf=\"-p pytest_automation_infra -p devops_proxy_container -p devops_docker_installer \" -s "
              echo "running command: $prefix $install $@"
              $prefix $install $@ ;;

  esac
