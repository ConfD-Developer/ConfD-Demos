######################################################################

usage:
	@echo "make all     Build all example files"
	@echo "make clean   Remove all built and intermediary files"
	@echo "make start   Start CONFD daemon"
	@echo "make stop    Stop any CONFD daemon"
	@echo "make cli     Start the CONFD Command Line Interface, J-style"
	@echo "make cli-c   Start the CONFD Command Line Interface, C-style"

######################################################################
# Where is ConfD installed? Make sure CONFD_DIR points it out
CONFD_DIR ?= ../..

# Include standard ConfD build definitions and rules
include $(CONFD_DIR)/src/confd/build/include.mk

# In case CONFD_DIR is not set (correctly), this rule will trigger
$(CONFD_DIR)/src/confd/build/include.mk:
	@echo 'Where is ConfD installed? Set $$CONFD_DIR to point it out!'
	@echo ''

######################################################################
# Example specific definitions and rules

CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd --addloadpath fxs
START_FLAGS ?=

all:	router.fxs \
	$(CDB_DIR) ssh-keydir
	@echo "Build complete"

%.fxs:  yang/%.yang
	$(CONFDC) -c --yangpath yang --yangpath $(CONFD_DIR)/src/confd/aaa \
	--yangpath $(CONFD_DIR)/src/confd/dyncfg \
	--yangpath $(CONFD_DIR)/src/confd/snmp/yang -o fxs/$@ -- $<

######################################################################
clean:	iclean
	-rm -rf *.log *.trace cli-history fxs/*.fxs 2> /dev/null || true

######################################################################
start:  stop
	$(CONFD) -c confd.conf $(CONFD_FLAGS)

######################################################################
stop:
	@ # Kill the confd daemon
	$(CONFD) --stop || true

######################################################################
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
		--interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
		--interactive  || echo Exit

######################################################################
$(CDB_DIR)/%.xml: %.xml
	rm -f $@ ; cp $< $@
######################################################################
