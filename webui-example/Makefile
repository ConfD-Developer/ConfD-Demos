######################################################################
# ConfD WebUI example
# (C) 2019 Tail-f Systems
#
# See the README files for more information
######################################################################

usage:
	@echo "See README files for more instructions"
	@echo "make all     Build all example files"
	@echo "make clean   Remove all ConfD replated built and intermediary files"
	@echo "make clean-all  Remove all build files including downloaded \
webapp dependencies"
	@echo "make start   Start CONFD daemon and example agent"
	@echo "make stop    Stop any CONFD daemon and example agent"
	@echo "make query   Run a test get query against CONFD"
	@echo "make cli     Start the CONFD Command Line Interface, J-style"
	@echo "make cli-c   Start the CONFD Command Line Interface, C-style"
	@echo "make test    Run the webapp test suite"
	@echo "make devrun  Start dev-server with webapp, blocking current shell"

######################################################################
# Where is ConfD installed? Make sure CONFD_DIR points it out
CONFD_DIR ?= ../../..

WEBAPP_DIR="./webapp"
DOCROOT_DIR="./docroot"

FXS = example-serial.fxs router.fxs

QUASAR_BIN=./node_modules/.bin/quasar

# Include standard ConfD build definitions and rules
include $(CONFD_DIR)/src/confd/build/include.mk

# In case CONFD_DIR is not set (correctly), this rule will trigger
$(CONFD_DIR)/src/confd/build/include.mk:
	@echo 'Where is ConfD installed? Set $$CONFD_DIR to point it out!'
	@echo ''

######################################################################
# Example specific definitions and rules

CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd

all: common-all $(FXS)
	@echo "Build complete"

common-all: $(CDB_DIR) ssh-keydir

load-init-data:
	#cp $(INIT_DATA_DIR)/*_init.xml $(CDB_DIR)
	confd_load -l -m -f init_data/gen-cfg.xml
	confd_load -l -m -O -f init_data/gen-state.xml
	confd_load -l -m -O -f init_data/gen-state-routes.xml

######################################################################
clean:	iclean
	-rm -rf *log trace_* cli-history 2> /dev/null || true

clean-all: clean
	-rm -rf $(DOCROOT_DIR)
	-cd $(WEBAPP_DIR); $(QUASAR_BIN) clean
	-rm -rf $(WEBAPP_DIR)/node_modules

######################################################################
start:  stop start_confd load-init-data

start_confd: $(DOCROOT_DIR)
	$(CONFD) -c confd.conf $(CONFD_FLAGS)

######################################################################
stop:
	### Killing any confd daemon
	$(CONFD) --stop    || true

######################################################################
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
		--interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
		--interactive  || echo Exit

######################################################################
query:
	$(CONFD_DIR)/bin/netconf-console cmd-get-router.xml

######################################################################

yarn:
	cd $(WEBAPP_DIR); yarn --frozen-lockfile

webapp: yarn
	cd $(WEBAPP_DIR); $(QUASAR_BIN) build

devrun: yarn
	cd $(WEBAPP_DIR); $(QUASAR_BIN) dev

$(DOCROOT_DIR):
	mkdir -p $(DOCROOT_DIR)

docroot: $(DOCROOT_DIR) webapp
	cp -r $(WEBAPP_DIR)/dist/spa/* $(DOCROOT_DIR)/
	cd $(DOCROOT_DIR); ln -f -s index.html login.html

testrun: all start yarn tests

tests:
#	cd $(WEBAPP_DIR); $(QUASAR_BIN) test --unit jest
	cd $(WEBAPP_DIR); yarn test
