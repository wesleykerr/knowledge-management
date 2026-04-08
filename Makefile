PLIST_DIR := $(HOME)/Library/LaunchAgents
SCRIPTS_DIR := scripts

.PHONY: install uninstall start stop logs

install:
	cp $(SCRIPTS_DIR)/com.wkerr.knowledge-listener.plist $(PLIST_DIR)/
	launchctl load $(PLIST_DIR)/com.wkerr.knowledge-listener.plist

uninstall:
	launchctl unload $(PLIST_DIR)/com.wkerr.knowledge-listener.plist || true
	rm -f $(PLIST_DIR)/com.wkerr.knowledge-listener.plist

start:
	launchctl start com.wkerr.knowledge-listener

stop:
	launchctl stop com.wkerr.knowledge-listener

logs:
	tail -f /tmp/knowledge-listener.log /tmp/knowledge-listener.err
