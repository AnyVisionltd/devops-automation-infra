AUTOMATION_PROXY_VERSION:=$(shell ./automation/proxy_container/version.sh)
build-automation-proxy:
	echo "building automation-proxy:${AUTOMATION_PROXY_VERSION}"
	(cd ./automation/proxy_container && docker build -f Dockerfile -t gcr.io/anyvision-training/automation-proxy:${AUTOMATION_PROXY_VERSION} .)

push-automation-proxy: build-automation-proxy
	echo "pushing automation-proxy:${AUTOMATION_PROXY_VERSION}"
	docker push gcr.io/anyvision-training/automation-proxy:${AUTOMATION_PROXY_VERSION}

test-ssh-local:
	./run/local.sh automation/devops_automation_infra/tests/v3_tests/docker/test_ssh.py

test-docker-local:
	./run/local.sh automation/devops_automation_infra/tests/v3_tests/docker/
	./run/local.sh $(args) automation/devops_automation_infra/tests/v3_tests/devops_docker/

test-ssh-aws:
	./run/aws.sh automation/devops_automation_infra/tests/v3_tests/docker/test_ssh.py

test-docker-aws:
	./run/aws.sh $(args) automation/devops_automation_infra/tests/v3_tests/docker_tests/ $(parallel)

test-sanity:
	make test-docker-local args="--install"
	make test-docker-aws args="--install" parallel="--num-parallel 3"

