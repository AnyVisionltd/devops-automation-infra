AUTOMATION_PROXY_VERSION:=$(shell ./automation/proxy_container/version.sh)
build-automation-proxy:
	echo "building automation-proxy:${AUTOMATION_PROXY_VERSION}"
	(cd ./automation/proxy_container && docker build -f Dockerfile -t gcr.io/anyvision-training/automation-proxy:${AUTOMATION_PROXY_VERSION} .)

push-automation-proxy: build-automation-proxy
	echo "pushing automation-proxy:${AUTOMATION_PROXY_VERSION}"
	docker push gcr.io/anyvision-training/automation-proxy:${AUTOMATION_PROXY_VERSION}

test-ssh-local:
	./run/local.sh $(args) automation/devops_automation_infra/tests/docker_tests/test_ssh.py

test-all-local:
	./run/local.sh $(args) automation/devops_automation_infra/tests/docker_tests/

test-ssh-aws:
	./run/aws.sh $(args) automation/devops_automation_infra/tests/docker_tests/test_ssh.py

test-all-aws:
	./run/aws.sh $(args) automation/devops_automation_infra/tests/docker_tests/ $(parallel)

test-sanity:
	make test-all-local args="--install"
	make test-all-aws args="--install" parallel="--num-parallel 3"

