AUTOMATION_PROXY_VERSION:=$(shell ./automation/proxy_container/version.sh)
build-automation-proxy:
	echo "building automation-proxy:${AUTOMATION_PROXY_VERSION}"
	(cd ./automation/proxy_container && docker build -f Dockerfile -t gcr.io/anyvision-training/automation-proxy:${AUTOMATION_PROXY_VERSION} .)

push-automation-proxy: build-automation-proxy
	echo "pushing automation-proxy:${AUTOMATION_PROXY_VERSION}"
	docker push gcr.io/anyvision-training/automation-proxy:${AUTOMATION_PROXY_VERSION}