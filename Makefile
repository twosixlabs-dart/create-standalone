IMAGE_PREFIX = docker.causeex.com/dart
IMAGE_NAME = dart-in-the-box
IMG := $(IMAGE_PREFIX)/$(IMAGE_NAME)

ifndef GITHUB_REF_NAME
	APP_VERSION := "latest"
else ifeq ("$(GITHUB_REF_NAME)", "master")
	APP_VERSION := "latest"
else ifeq ("$(GITHUB_REF_TYPE)", "tag")
	APP_VERSION := $(shell cat app.version)
else
	APP_VERSION := $(GITHUB_REF_NAME)
endif

version-pipeline-config:
	pip3 install requests pyaml
	./bin/pipeline-versioning.py --files dart-standalone.yml --output_dir ./

clean:
	docker images | grep $(IMAGE_NAME) | grep -v IMAGE | awk '{print $3}' | docker rmi -f
