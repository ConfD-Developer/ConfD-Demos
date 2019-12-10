######################################################################
#  ConfD cdb_get_modifications() example
# (C) 2019 Tail-f Systems
#
# See the README files for more information
######################################################################

usage:
	@echo "make all      Build all example files"
	@echo "make clean    Remove all built and intermediary files"
	@echo "make start    Start ConfD daemon and example agent"
	@echo "make stop     Stop any ConfD daemon and example agent"
	@echo "make cli      Start the ConfD Command Line Interface"
	@echo "make cli-c    Start the Cisco style ConfD Command Line Interface"

######################################################################
# Where is ConfD installed? Make sure CONFD_DIR points it out
#CONFD_DIR ?= ../../..

# Include standard ConfD build definitions and rules
include $(CONFD_DIR)/src/confd/build/include.mk

# In case CONFD_DIR is not set (correctly), this rule will trigger
$(CONFD_DIR)/src/confd/build/include.mk:
	@echo 'Where is ConfD installed? Set $$CONFD_DIR to point it out!'
	@echo ''
	@exit 1

######################################################################
# Example specific definitions and rules
CONFD_FXS_DIR = $(CONFD_DIR)/etc/confd
CONFD_FLAGS = --addloadpath $(CONFD_FXS_DIR)

CONFD_FLAGS =--ignore-initial-validation --addloadpath $(CONFD_DIR)/etc/confd
START_FLAGS ?=

YANG = user-folders.yang
FXS = $(YANG:.yang=.fxs)
YANG_PY = $(YANG:.yang=_ns.py)

######################################################################
all: $(FXS) $(YANG_PY) $(CDB_DIR) ssh-keydir
	@echo "Build complete"

######################################################################
clean:	iclean
	rm -rf *.trace 2> /dev/null || true
	rm -rf cli-history 2> /dev/null || true
	rm -f $(YANG_PY) *.pyc __init__.py || true

######################################################################
start_confd:  stop_confd
	$(CONFD) -c confd.conf $(CONFD_FLAGS)

start:  stop start_confd
	python modif-subscriber.py

######################################################################
stop_confd:
	$(CONFD) --stop    || true

stop: stop_confd
	$(KILLALL) `pgrep -f "python ./modif-subscriber.py"` || true

######################################################################
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
		--interactive || echo Exit

######################################################################
cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
		--interactive || echo Exit
