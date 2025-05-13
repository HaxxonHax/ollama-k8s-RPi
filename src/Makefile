APP_NAME=discord-bridge
IMAGE_TAG=latest

build:
	docker build -t $(APP_NAME):$(IMAGE_TAG) .

import:
	# Save image as tar and import into containerd
	docker save $(APP_NAME):$(IMAGE_TAG) | sudo ctr -n k8s.io images import -

rebuild: build import

