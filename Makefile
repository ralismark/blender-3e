.PHONY: all sync restart reload stop flogs log

all:
	true

sync:
	rsync -avrh . ~/Dropbox/sync-alarm/b3 --exclude-from .gitignore --include secrets.yaml
	ssh alarm sudo systemctl start --no-block sync-alarm \; journalctl -xafu sync-alarm

restart:
	ssh alarm sudo systemctl restart blender

log:
	ssh alarm journalctl -xafu blender
