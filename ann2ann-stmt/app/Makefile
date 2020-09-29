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

CONFD_FLAGS = --addloadpath $(CONFD_DIR)/etc/confd --addloadpath /confd/src/confd/dyncfg --addloadpath fxs --ignore-initial-validation
START_FLAGS ?=

CONFDC=$(CONFD_DIR)/bin/confdc

YANG_SOURCES        = $(wildcard yang/*.yang)
SUBMODULES          = $(shell grep -l belongs-to yang/*.yang)
ANNOTATION_MODULES  = $(wildcard yang/*-ann*.yang)
TAILF_MODULES       = $(wildcard yang/tailf-*.yang)
CONFD_MODULES       = $(wildcard yang/confd*.yang)
IETF_MODULES       = $(wildcard yang/ietf-*.yang)
IANA_MODULES       = $(wildcard yang/iana-*.yang)

BUILTIN_MODULES     +=

YANG_MODULES = $(filter-out $(SUBMODULES) $(ANNOTATION_MODULES) \
		$(BUILTIN_MODULES) $(TAILF_MODULES) ,$(YANG_SOURCES))

ALL_FXS_FILES = $(YANG_MODULES:yang/%.yang=fxs/%.fxs)
FXS_DIR = ./fxs

fxs/%.fxs: yang/%.yang yang/%-ann.yang
	$(CONFDC) -c --yangpath yang --yangpath $(CONFD_DIR)/src/confd/aaa \
	-o $@  -a yang/$*-ann.yang -- $<

fxs/%.fxs: yang/%.yang
	$(CONFDC) -c --yangpath yang --yangpath $(CONFD_DIR)/src/confd/aaa \
	-o $@ -- $<

$(FXS_DIR):
	-mkdir -p $(FXS_DIR)

$(CDB_DIR)/confd_dyncfg_init.xml: confd_dyncfg_init.xml
	rm -f $@ ; cp $< $@

######################################################################
all:	$(FXS_DIR) \
	$(ALL_FXS_FILES) \
	$(CDB_DIR) ssh-keydir $(CDB_DIR)/confd_dyncfg_init.xml
	@echo "Build complete"

######################################################################
clean:	iclean
	-rm -rf yang yin *.log *.trace cli-history fxs 2> /dev/null || true

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
