PLIST_DIR := $(HOME)/Library/LaunchAgents
SCRIPTS_DIR := scripts

.PHONY: install uninstall start stop logs

install:
	cp $(SCRIPTS_DIR)/com.wkerr.knowledge-server.plist $(PLIST_DIR)/
	cp $(SCRIPTS_DIR)/com.wkerr.knowledge-listener.plist $(PLIST_DIR)/
	launchctl load $(PLIST_DIR)/com.wkerr.knowledge-server.plist
	launchctl load $(PLIST_DIR)/com.wkerr.knowledge-listener.plist

uninstall:
	launchctl unload $(PLIST_DIR)/com.wkerr.knowledge-server.plist || true
	launchctl unload $(PLIST_DIR)/com.wkerr.knowledge-listener.plist || true
	rm -f $(PLIST_DIR)/com.wkerr.knowledge-server.plist
	rm -f $(PLIST_DIR)/com.wkerr.knowledge-listener.plist

start:
	launchctl start com.wkerr.knowledge-server
	launchctl start com.wkerr.knowledge-listener

stop:
	launchctl stop com.wkerr.knowledge-server
	launchctl stop com.wkerr.knowledge-listener

logs:
	tail -f /tmp/knowledge-server.log /tmp/knowledge-server.err /tmp/knowledge-listener.log /tmp/knowledge-listener.err
