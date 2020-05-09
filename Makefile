.PHONY: all sync restart log

all: sync restart log

sync:
	rsync -avrh . alarm:/home/alarm/b3 --exclude-from .gitignore --include secrets.yaml

restart:
	ssh alarm sudo systemctl restart blender

log:
	ssh alarm journalctl -xafu blender
