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
	./run/local.sh --install automation/devops_automation_infra/tests/v3_tests/devops_docker/

test-ssh-aws:
	./run/aws.sh automation/devops_automation_infra/tests/v3_tests/docker/test_ssh.py

test-docker-aws:
	./run/aws.sh automation/devops_automation_infra/tests/v3_tests/docker/ $(parallel)
	./run/aws.sh --install automation/devops_automation_infra/tests/v3_tests/devops_docker/ $(parallel)

test-sanity:
	make test-sanity-local
	make test-sanity-aws

# TODO: deprecate the non-v3 targets when the time comes
test-docker-local-v3:
	./run/v3/local.sh automation/devops_automation_infra/tests/v3_tests/docker/
	./run/v3/local.sh --sf=--install automation/devops_automation_infra/tests/v3_tests/devops_docker/

test-docker-aws-v3:
	./run/v3/aws.sh automation/devops_automation_infra/tests/v3_tests/docker/ $(parallel)
	./run/v3/aws.sh --sf=--install automation/devops_automation_infra/tests/v3_tests/devops_docker/ $(parallel)

test-sanity-aws:
	make test-docker-aws parallel="--num-parallel 3"
	make test-docker-aws-v3 parallel="--num-parallel 3"

test-sanity-local:
	make test-docker-local
	make test-docker-local-v3
