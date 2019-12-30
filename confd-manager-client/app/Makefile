######################################################################
# SNMP Agent example emit-mib Makefile
# (C) 2006-2009 Tail-f Systems
#
# See the README files for more information
######################################################################

usage:
	@echo "See README file for more instructions"
	@echo "make all      Build all example files"
	@echo "make clean    Remove all built and intermediary files"
	@echo "make start    Start ConfD daemon and example agent"
	@echo "make stop     Stop any ConfD daemon and example agent"
	@echo "make cli      Start the ConfD Command Line Interface"

######################################################################
# Where is ConfD installed? Make sure CONFD_DIR points it out
CONFD_DIR ?= ../../..

# Include standard ConfD build definitions and rules
include $(CONFD_DIR)/src/confd/build/include.mk

# In case CONFD_DIR is not set (correctly), this rule will trigger
$(CONFD_DIR)/src/confd/build/include.mk:
	@echo 'Where is ConfD installed? Set $$CONFD_DIR to point it out!'
	@echo ''

######################################################################
# Example specific definitions and rules

CONFD_FXS_DIR = $(CONFD_DIR)/etc/confd
CONFD_SNMP_FXS_DIR = $(CONFD_DIR)/etc/confd/snmp

CONFD_FLAGS = --addloadpath $(CONFD_FXS_DIR) \
	      --addloadpath $(CONFD_SNMP_FXS_DIR)
######################################################################


all:	routing.fxs TAIL-F-ROUTING-MIB.bin $(CDB_DIR) $(CDB_DIR)/vacm_init.xml ssh-keydir
	@echo "Build complete"

TAIL-F-ROUTING-MIB.mib: routing.fxs
	$(CONFDC) --emit-mib $@ --top tailfRoutingMIB \
		--join-names force-capitalize --no-comments \
		-f $(CONFD_FXS_DIR) -- $<
	@mv $@ $@.tmp
	@sed -e 's/@LAST-UPDATED/200006140000Z/' \
	     -e 's/@REVISION/200006140000Z/' $@.tmp > $@
	@rm $@.tmp

%.fxs: %.yang
	$(CONFDC) $(EXTRA_LINK_FLAGS) -a routing-ann.yang -c -o $@ $<

TAIL-F-ROUTING-MIB.bin: routing.fxs TAIL-F-ROUTING-MIB.mib
	$(CONFDC) -c -f $(CONFD_FXS_DIR) -- TAIL-F-ROUTING-MIB.mib routing.fxs

$(CDB_DIR)/vacm_init.xml: $(CDB_DIR)
	-mkdir -p $(CDB_DIR)
	cp *_init.xml $(CDB_DIR)

save-override: commands-c.ccl

######################################################################
clean:	iclean
	-rm -rf *.bin *.mib global.data 2>/dev/null || true
	-rm -rf *log *trace cli-history 2> /dev/null || true

start:
	$(CONFD) -c confd-running.conf $(CONFD_FLAGS)

start-candidate:
	$(CONFD) -c confd-candidate.conf $(CONFD_FLAGS)
######################################################################
stop:
	$(CONFD) --stop    || true

######################################################################
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
		--interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
		--interactive || echo Exit

######################################################################
query:
	$(CONFD_DIR)/bin/netconf-console --get-config -x /

######################################################################
walk:
	snmpwalk -m ./TAIL-F-ROUTING-MIB.mib -c public -v2c localhost:4000 enterprises
