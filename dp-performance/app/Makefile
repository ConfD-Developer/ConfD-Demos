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

CONFDC=$(CONFD_DIR)/bin/confdc

YANG_SOURCES        = $(wildcard yang/*.yang)
SUBMODULES          = $(shell grep -l belongs-to yang/*.yang)
ANNOTATION_MODULES  = $(wildcard yang/*-ann*.yang)
TAILF_MODULES       = $(wildcard yang/tailf-*.yang)

BUILTIN_MODULES     += ietf-yang-types.yang
BUILTIN_MODULES     += ietf-inet-types.yang
BUILTIN_MODULES     += ietf-yang-library.yang

BUILTIN_MODULES     += ietf-netconf.yang
BUILTIN_MODULES     += ietf-netconf-acm.yang
BUILTIN_MODULES     += ietf-netconf-with-defaults.yang

BUILTIN_MODULES     += ietf-restconf.yang
BUILTIN_MODULES     += ietf-yang-patch.yang
BUILTIN_MODULES     += tailf-rest-error.yang
BUILTIN_MODULES     += tailf-rest-query.yang

YANG_MODULES = $(filter-out $(SUBMODULES) $(ANNOTATION_MODULES) \
		$(BUILTIN_MODULES) $(TAILF_MODULES) ,$(YANG_SOURCES))

ALL_FXS_FILES = $(YANG_MODULES:yang/%.yang=fxs/%.fxs)
FXS_DIR = ./fxs

CSRCS = $(wildcard src/*.c)
CAPPS = $(patsubst src/%.c,%,$(CSRCS))
HSS = $(ALL_FXS_FILES:fxs/%.fxs=src/%.h)
CFLAGS += -Isrc

src/%.h:
	$(CONFDC) --emit-h src/$*.h fxs/$*.fxs

%: src/%.c
	$(CC) -c -o $@.o $^ -Wall -g -I$(CONFD_DIR)/include
	$(CC) -o $@ $@.o -Isrc $(CFLAGS) $(LIBS)

fxs/%.fxs: yang/%.yang yang/%-ann.yang
	$(CONFDC) -c --yangpath yang --yangpath $(CONFD_DIR)/src/confd/aaa \
	-o $@  -a yang/$*-ann.yang -- $<

fxs/%.fxs: yang/%.yang
	$(CONFDC) -c --yangpath yang --yangpath $(CONFD_DIR)/src/confd/aaa \
	-o $@ -- $<

$(FXS_DIR):
	-mkdir -p $(FXS_DIR)

######################################################################
all: $(FXS_DIR) \
	$(ALL_FXS_FILES) \
	$(HSS) $(CAPPS) \
	$(CDB_DIR) ssh-keydir
	@echo "Build complete"

######################################################################
clean:	iclean
	-rm -rf *.log *.trace obj fxs output.json output.confvals cli-history \
	$(CAPPS) src/*.h 2> /dev/null || true

######################################################################
start:  stop
	$(CONFD) -c confd.conf $(CONFD_FLAGS)

######################################################################
stop:
	@ # Kill the confd daemon
	$(CONFD) --stop || true
	$(KILLALL) $(CAPPS) || true

######################################################################
cli:
	$(CONFD_DIR)/bin/confd_cli --user=admin --groups=admin \
	--interactive || echo Exit

cli-c:
	$(CONFD_DIR)/bin/confd_cli -C --user=admin --groups=admin \
	--interactive  || echo Exit

######################################################################
